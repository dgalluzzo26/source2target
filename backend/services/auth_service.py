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
        Uses SQL is_member() function for group checking.
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
            
            # Try using SQL is_member() function (most reliable in Databricks)
            try:
                # Get OAuth token from WorkspaceClient
                access_token = None
                if self.workspace_client and hasattr(self.workspace_client.config, 'authenticate'):
                    try:
                        headers = self.workspace_client.config.authenticate()
                        if headers and 'Authorization' in headers:
                            access_token = headers['Authorization'].replace('Bearer ', '')
                    except Exception as e:
                        print(f"[Auth Service] Could not get OAuth token: {e}")
                
                # Connect to SQL warehouse
                if access_token:
                    connection = sql.connect(
                        server_hostname=config.database.server_hostname,
                        http_path=config.database.http_path,
                        access_token=access_token
                    )
                else:
                    connection = sql.connect(
                        server_hostname=config.database.server_hostname,
                        http_path=config.database.http_path,
                        auth_type="databricks-oauth"
                    )
                
                with connection.cursor() as cursor:
                    # Use is_member() function to check group membership
                    query = f"SELECT is_member('{admin_group}') as is_member"
                    cursor.execute(query)
                    result = cursor.fetchone()
                    
                    if result and result[0]:
                        print(f"[Auth Service] User IS in admin group")
                        connection.close()
                        return True
                    else:
                        print(f"[Auth Service] User is NOT in admin group")
                        connection.close()
                        return False
                        
            except Exception as sql_error:
                print(f"[Auth Service] SQL group check failed: {str(sql_error)}")
                
                # Fallback: Try using WorkspaceClient API
                try:
                    print(f"[Auth Service] Trying WorkspaceClient API fallback...")
                    groups = list(self.workspace_client.groups.list(filter=f'displayName eq "{admin_group}"'))
                    
                    if not groups:
                        print(f"[Auth Service] Admin group not found in workspace")
                        return False
                    
                    group = groups[0]
                    members = list(self.workspace_client.groups.list_members(id=group.id))
                    
                    # Check if user email is in members
                    for member in members:
                        if hasattr(member, 'display') and user_email.lower() in member.display.lower():
                            print(f"[Auth Service] User found in group via API")
                            return True
                    
                    print(f"[Auth Service] User not found in group members")
                    return False
                    
                except Exception as api_error:
                    print(f"[Auth Service] WorkspaceClient API check failed: {str(api_error)}")
                    return False
                    
        except Exception as e:
            print(f"[Auth Service] Error checking admin group: {str(e)}")
            return False


# Global instance
auth_service = AuthService()

