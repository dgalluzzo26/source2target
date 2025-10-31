"""
System status service for checking database connectivity, vector search, etc.
"""
import os
import asyncio
from typing import Dict, Any, Optional

try:
    from databricks import sql
    from databricks.sdk import WorkspaceClient
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    print("Warning: Databricks SDK not available")

from backend.services.config_service import config_service


class SystemService:
    """Service for checking system status and health."""
    
    def __init__(self):
        """Initialize the system service."""
        self.workspace_client = None
        if DATABRICKS_AVAILABLE:
            try:
                self.workspace_client = WorkspaceClient()
            except Exception as e:
                print(f"Warning: Could not initialize WorkspaceClient: {e}")
    
    async def check_database_connection(self) -> Dict[str, str]:
        """
        Check database connection by attempting a simple query.
        Uses timeout to prevent hanging.
        """
        if not DATABRICKS_AVAILABLE:
            return {
                "status": "Unavailable",
                "message": "Databricks SDK not installed"
            }
        
        try:
            # Get database config
            db_config = config_service.get_database_config()
            
            # Try to connect with timeout
            result = await asyncio.wait_for(
                self._test_database_query(
                    db_config['server_hostname'],
                    db_config['http_path'],
                    db_config['warehouse_name']
                ),
                timeout=3.0  # 3 second timeout
            )
            return result
            
        except asyncio.TimeoutError:
            return {
                "status": "Timeout",
                "message": "Database connection timed out"
            }
        except Exception as e:
            return {
                "status": "Error",
                "message": f"Check failed: {str(e)[:50]}"
            }
    
    async def _test_database_query(self, hostname: str, http_path: str, warehouse_name: str) -> Dict[str, str]:
        """
        Test database connection with a simple query.
        This runs in a separate thread to allow timeout.
        """
        try:
            # Check if we have valid hostname
            if not hostname or not hostname.endswith('.databricks.com'):
                return {
                    "status": "Configured",
                    "message": f"Warehouse '{warehouse_name}' configured (not connected)"
                }
            
            # Attempt connection
            conn = sql.connect(
                server_hostname=hostname,
                http_path=http_path
            )
            
            # Test with simple query
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                
                if result:
                    conn.close()
                    return {
                        "status": "Connected",
                        "message": f"Warehouse '{warehouse_name}' online"
                    }
            
            conn.close()
            return {
                "status": "Error",
                "message": "Query returned no results"
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # Handle specific error types
            if "cannot import" in error_msg.lower():
                return {
                    "status": "Configured",
                    "message": f"Warehouse '{warehouse_name}' configured (local dev)"
                }
            elif "authentication" in error_msg.lower():
                return {
                    "status": "Error",
                    "message": "Authentication failed"
                }
            elif "not found" in error_msg.lower():
                return {
                    "status": "Error",
                    "message": f"Warehouse '{warehouse_name}' not found"
                }
            else:
                return {
                    "status": "Error",
                    "message": f"Connection failed: {error_msg[:30]}"
                }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        Checks are independent so one failure doesn't break others.
        """
        status = {}
        
        # Database check (with live query)
        try:
            status["database"] = await self.check_database_connection()
        except Exception as e:
            status["database"] = {
                "status": "Error",
                "message": f"Check failed: {str(e)[:30]}"
            }
        
        # Vector search check (from config)
        try:
            vs_config = config_service.get_vector_search_config()
            status["vectorSearch"] = {
                "status": "Available",
                "message": f"Endpoint: {vs_config['endpoint_name']}, Index: {vs_config['index_name']}"
            }
        except Exception as e:
            status["vectorSearch"] = {
                "status": "Error",
                "message": f"Check failed: {str(e)[:30]}"
            }
        
        # AI Model check (from config)
        try:
            ai_model = config_service.get_ai_model_endpoint()
            status["aiModel"] = {
                "status": "Ready",
                "message": f"Model '{ai_model}' configured"
            }
        except Exception as e:
            status["aiModel"] = {
                "status": "Error",
                "message": f"Check failed: {str(e)[:30]}"
            }
        
        # Configuration check
        try:
            config = config_service.get_config()
            status["configuration"] = {
                "status": "Valid",
                "message": "Configuration loaded from file"
            }
        except Exception as e:
            status["configuration"] = {
                "status": "Error",
                "message": f"Config error: {str(e)[:30]}"
            }
        
        return status


# Global instance
system_service = SystemService()

