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
        """
        if not user_email:
            return False
        
        try:
            # Get admin group from config
            config = self.config_service.get_config()
            admin_group = config.security.admin_group_name
            
            if not admin_group:
                print(f"[Auth Service] No admin group configured")
                return False
            
            print(f"[Auth Service] Checking if {user_email} is in group: {admin_group}")
            
            # Use WorkspaceClient API to check group membership
            try:
                # First, find the group by name
                print(f"[Auth Service] Looking up group: {admin_group}")
                groups = list(self.workspace_client.groups.list(filter=f'displayName eq "{admin_group}"'))
                
                if not groups:
                    print(f"[Auth Service] Admin group '{admin_group}' not found in workspace")
                    return False
                
                group = groups[0]
                print(f"[Auth Service] Found group with ID: {group.id}")
                
                # Get all members of the group
                print(f"[Auth Service] Fetching group members...")
                members = list(self.workspace_client.groups.list_members(id=group.id))
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
                print(f"[Auth Service] WorkspaceClient API check failed: {str(api_error)}")
                import traceback
                print(f"[Auth Service] Traceback: {traceback.format_exc()}")
                return False
                    
        except Exception as e:
            print(f"[Auth Service] Error checking admin group: {str(e)}")
            import traceback
            print(f"[Auth Service] Traceback: {traceback.format_exc()}")
            return False


# Global instance
auth_service = AuthService()

