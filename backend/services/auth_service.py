"""
Authentication service for user detection and admin authorization.
Based on the original Streamlit app's auth.py
"""
from databricks.sdk import WorkspaceClient
from databricks import sql
from backend.services.config_service import ConfigService
from typing import Optional


class AuthService:
    """Service for authentication and authorization."""
    
    def __init__(self):
        """Initialize the auth service."""
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self):
        """Lazy initialization of WorkspaceClient."""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
    
    def check_admin_group_membership(self, user_email: str) -> bool:
        """
        Check if user is in the configured admin group.
        Uses WorkspaceClient API to check group membership for the specified user email.
        Falls back to allowing access if permissions are insufficient.
        """
        if not user_email:
            return False
        
        try:
            # Get admin group from config
            config = self.config_service.get_config()
            admin_group = config.security.admin_group_name
            
            if not admin_group:
                print(f"[Auth Service] No admin group configured - granting admin access by default")
                return True  # If no group configured, allow access
            
            print(f"[Auth Service] Checking if {user_email} is in group: {admin_group}")
            
            # Use WorkspaceClient API to check group membership
            try:
                # First, find the group by name
                print(f"[Auth Service] Looking up group: {admin_group}")
                groups = list(self.workspace_client.groups.list(filter=f'displayName eq "{admin_group}"'))
                
                if not groups:
                    print(f"[Auth Service] Admin group '{admin_group}' not found in workspace")
                    print(f"[Auth Service] Defaulting to DENY access when group not found")
                    return False
                
                group = groups[0]
                print(f"[Auth Service] Found group with ID: {group.id}")
                
                # Get the group details which includes members
                print(f"[Auth Service] Fetching group details...")
                group_details = self.workspace_client.groups.get(id=group.id)
                
                # Members are in the 'members' attribute
                members = group_details.members if hasattr(group_details, 'members') and group_details.members else []
                print(f"[Auth Service] Group has {len(members)} members")
                
                # Check if user email is in members
                for member in members:
                    # Check various member attributes
                    member_email = None
                    
                    # Try different attribute names
                    if hasattr(member, 'display'):
                        member_email = member.display
                    elif hasattr(member, 'value'):
                        member_email = member.value
                    elif hasattr(member, 'email'):
                        member_email = member.email
                    
                    if member_email and user_email.lower() in member_email.lower():
                        print(f"[Auth Service] ✓ User {user_email} IS in admin group (matched: {member_email})")
                        return True
                
                print(f"[Auth Service] ✗ User {user_email} is NOT in admin group")
                return False
                    
            except Exception as api_error:
                error_message = str(api_error)
                print(f"[Auth Service] WorkspaceClient API check failed: {error_message}")
                
                # Check if it's a permission error (403, Forbidden, etc.)
                if '403' in error_message or 'Forbidden' in error_message or 'permission' in error_message.lower():
                    print(f"[Auth Service] ⚠️  Permission denied to read group - DEFAULTING TO ALLOW ACCESS")
                    print(f"[Auth Service] This is a fallback for service principals without group read permissions")
                    return True  # Allow access if we can't check due to permissions
                
                import traceback
                print(f"[Auth Service] Traceback: {traceback.format_exc()}")
                print(f"[Auth Service] Non-permission error - DENYING access")
                return False
                    
        except Exception as e:
            print(f"[Auth Service] Error checking admin group: {str(e)}")
            import traceback
            print(f"[Auth Service] Traceback: {traceback.format_exc()}")
            return False


# Global instance
auth_service = AuthService()

