"""
System status service for checking database connectivity, vector search, etc.
"""
import os
import asyncio
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import functools

try:
    from databricks import sql
    from databricks.sdk import WorkspaceClient
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    print("Warning: Databricks SDK not available")

from backend.services.config_service import config_service

# Thread pool for running blocking database operations
executor = ThreadPoolExecutor(max_workers=3)


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
        Runs in thread pool to avoid blocking the event loop.
        """
        if not DATABRICKS_AVAILABLE:
            return {
                "status": "Unavailable",
                "message": "Databricks SDK not installed"
            }
        
        try:
            # Get database config
            db_config = config_service.get_database_config()
            
            # Run blocking database query in thread pool with LONGER timeout
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    functools.partial(
                        self._test_database_query_sync,
                        db_config['server_hostname'],
                        db_config['http_path'],
                        db_config['warehouse_name']
                    )
                ),
                timeout=10.0  # Increased to 10 seconds for warehouse startup
            )
            return result
            
        except asyncio.TimeoutError:
            db_config = config_service.get_database_config()
            return {
                "status": "Warning",
                "message": f"Warehouse '{db_config['warehouse_name']}' timeout (may be starting)"
            }
        except Exception as e:
            return {
                "status": "Error",
                "message": f"Check failed: {str(e)[:50]}"
            }
    
    def _test_database_query_sync(self, hostname: str, http_path: str, warehouse_name: str) -> Dict[str, str]:
        """
        SYNCHRONOUS method to test database connection.
        This runs in a thread pool to avoid blocking the async event loop.
        """
        try:
            # Check if we have valid hostname
            if not hostname or not hostname.endswith('.databricks.com'):
                return {
                    "status": "Configured",
                    "message": f"Warehouse '{warehouse_name}' configured (not connected)"
                }
            
            # First, check if warehouse is running using WorkspaceClient
            if self.workspace_client:
                try:
                    print(f"[DB Check] Checking warehouse state for {warehouse_name}")
                    warehouses = list(self.workspace_client.warehouses.list())
                    
                    for wh in warehouses:
                        if wh.name == warehouse_name:
                            print(f"[DB Check] Found warehouse, state: {wh.state}")
                            
                            if hasattr(wh, 'state'):
                                if str(wh.state).upper() == 'STOPPED':
                                    return {
                                        "status": "Warning",
                                        "message": f"Warehouse '{warehouse_name}' is stopped"
                                    }
                                elif str(wh.state).upper() == 'STARTING':
                                    return {
                                        "status": "Warning",
                                        "message": f"Warehouse '{warehouse_name}' is starting..."
                                    }
                            
                            # Warehouse is running, proceed with connection
                            break
                    else:
                        print(f"[DB Check] Warehouse {warehouse_name} not found in list")
                        return {
                            "status": "Error",
                            "message": f"Warehouse '{warehouse_name}' not found"
                        }
                        
                except Exception as e:
                    print(f"[DB Check] Could not check warehouse state: {e}")
                    # Continue anyway, maybe warehouse check requires different permissions
            
            print(f"[DB Check] Attempting connection to {hostname} with path {http_path}")
            
            # Try to get OAuth token from WorkspaceClient config
            access_token = None
            if self.workspace_client and hasattr(self.workspace_client.config, 'authenticate'):
                try:
                    # Try to get the access token that WorkspaceClient is using
                    headers = self.workspace_client.config.authenticate()
                    if headers and 'Authorization' in headers:
                        access_token = headers['Authorization'].replace('Bearer ', '')
                        print(f"[DB Check] Using OAuth token from WorkspaceClient")
                except Exception as e:
                    print(f"[DB Check] Could not get OAuth token: {e}")
            
            # Attempt connection
            if access_token:
                print(f"[DB Check] Connecting with OAuth token")
                conn = sql.connect(
                    server_hostname=hostname,
                    http_path=http_path,
                    access_token=access_token
                )
            else:
                print(f"[DB Check] Connecting without explicit token (using default auth)")
                conn = sql.connect(
                    server_hostname=hostname,
                    http_path=http_path
                )
            
            print(f"[DB Check] Connection established, executing test query")
            
            # Test with simple query
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                
                if result:
                    conn.close()
                    print(f"[DB Check] Query successful!")
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
            print(f"[DB Check] Error: {error_msg}")
            
            # Handle specific error types
            if "cannot import" in error_msg.lower():
                return {
                    "status": "Configured",
                    "message": f"Warehouse '{warehouse_name}' configured (local dev)"
                }
            elif "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                return {
                    "status": "Error",
                    "message": "Authentication failed - check app permissions"
                }
            elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                return {
                    "status": "Error",
                    "message": f"Warehouse '{warehouse_name}' not found"
                }
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                return {
                    "status": "Timeout", 
                    "message": f"Warehouse may be stopped or unreachable"
                }
            elif "stopped" in error_msg.lower():
                return {
                    "status": "Error",
                    "message": f"Warehouse '{warehouse_name}' is stopped"
                }
            else:
                # Return more detailed error for debugging
                return {
                    "status": "Error",
                    "message": f"Failed: {error_msg[:60]}"
                }
    
    async def check_vector_search(self) -> Dict[str, str]:
        """
        Check if vector search endpoint and index are available.
        Tests actual endpoint existence using WorkspaceClient.
        """
        if not DATABRICKS_AVAILABLE or not self.workspace_client:
            return {
                "status": "Unavailable",
                "message": "Databricks SDK not available"
            }
        
        try:
            vs_config = config_service.get_vector_search_config()
            endpoint_name = vs_config['endpoint_name']
            index_name = vs_config['index_name']
            
            # Try to check vector search with timeout
            result = await asyncio.wait_for(
                self._test_vector_search(endpoint_name, index_name),
                timeout=3.0  # 3 second timeout
            )
            return result
            
        except asyncio.TimeoutError:
            return {
                "status": "Timeout",
                "message": "Vector search check timed out"
            }
        except Exception as e:
            return {
                "status": "Error",
                "message": f"Check failed: {str(e)[:50]}"
            }
    
    async def _test_vector_search(self, endpoint_name: str, index_name: str) -> Dict[str, str]:
        """Test vector search endpoint availability."""
        try:
            # Try to list vector search endpoints
            from databricks.sdk.service import vectorsearch
            
            try:
                # Check if endpoint exists
                endpoints = list(self.workspace_client.vector_search_endpoints.list_endpoints())
                endpoint_names = [ep.name for ep in endpoints]
                
                if endpoint_name in endpoint_names:
                    # Endpoint exists, now check index
                    try:
                        indexes = list(self.workspace_client.vector_search_indexes.list_indexes(
                            endpoint_name=endpoint_name
                        ))
                        index_names = [idx.name for idx in indexes]
                        
                        if index_name in index_names:
                            return {
                                "status": "Available",
                                "message": f"Endpoint and index verified online"
                            }
                        else:
                            return {
                                "status": "Warning",
                                "message": f"Endpoint found, index '{index_name}' not found"
                            }
                    except Exception:
                        # Can't list indexes, but endpoint exists
                        return {
                            "status": "Available",
                            "message": f"Endpoint '{endpoint_name}' verified"
                        }
                else:
                    return {
                        "status": "Error",
                        "message": f"Endpoint '{endpoint_name}' not found"
                    }
                    
            except Exception as e:
                # If we can't check, assume it's configured
                return {
                    "status": "Configured",
                    "message": f"Endpoint: {endpoint_name}, Index: {index_name}"
                }
                
        except ImportError:
            # Vector search module not available
            return {
                "status": "Configured",
                "message": f"Endpoint: {endpoint_name}, Index: {index_name}"
            }
        except Exception as e:
            return {
                "status": "Error",
                "message": f"Check failed: {str(e)[:30]}"
            }
    
    async def check_ai_model(self) -> Dict[str, str]:
        """
        Check if AI model serving endpoint is available.
        Tests actual endpoint using WorkspaceClient.
        """
        if not DATABRICKS_AVAILABLE or not self.workspace_client:
            return {
                "status": "Unavailable",
                "message": "Databricks SDK not available"
            }
        
        try:
            ai_model = config_service.get_ai_model_endpoint()
            
            # Try to check AI model with timeout
            result = await asyncio.wait_for(
                self._test_ai_model(ai_model),
                timeout=3.0  # 3 second timeout
            )
            return result
            
        except asyncio.TimeoutError:
            return {
                "status": "Timeout",
                "message": "AI model check timed out"
            }
        except Exception as e:
            return {
                "status": "Error",
                "message": f"Check failed: {str(e)[:50]}"
            }
    
    async def _test_ai_model(self, model_endpoint: str) -> Dict[str, str]:
        """Test AI model serving endpoint availability."""
        try:
            # Try to list serving endpoints
            endpoints = list(self.workspace_client.serving_endpoints.list())
            endpoint_names = [ep.name for ep in endpoints]
            
            if model_endpoint in endpoint_names:
                # Check endpoint state
                endpoint = self.workspace_client.serving_endpoints.get(model_endpoint)
                
                print(f"[AI Model Check] Found endpoint, checking state...")
                print(f"[AI Model Check] Has state attr: {hasattr(endpoint, 'state')}")
                if hasattr(endpoint, 'state'):
                    print(f"[AI Model Check] State: {endpoint.state}")
                    print(f"[AI Model Check] Has ready attr: {hasattr(endpoint.state, 'ready')}")
                    if hasattr(endpoint.state, 'ready'):
                        print(f"[AI Model Check] Ready value: {endpoint.state.ready}")
                
                if hasattr(endpoint, 'state') and hasattr(endpoint.state, 'ready'):
                    if endpoint.state.ready == 'READY':
                        return {
                            "status": "Ready",
                            "message": f"Model '{model_endpoint}' is online and ready"
                        }
                    else:
                        return {
                            "status": "Warning",
                            "message": f"Model '{model_endpoint}' exists but not ready (state: {endpoint.state.ready})"
                        }
                else:
                    return {
                        "status": "Ready",
                        "message": f"Model '{model_endpoint}' endpoint found"
                    }
            else:
                # Check if it's a foundation model (doesn't appear in serving endpoints)
                if any(fm in model_endpoint.lower() for fm in ['dbrx', 'llama', 'mistral', 'mixtral']):
                    return {
                        "status": "Ready",
                        "message": f"Foundation model '{model_endpoint}' configured"
                    }
                else:
                    return {
                        "status": "Error",
                        "message": f"Model '{model_endpoint}' not found"
                    }
                    
        except Exception as e:
            # If we can't check, assume it's configured
            return {
                "status": "Configured",
                "message": f"Model '{model_endpoint}' configured"
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status with LIVE checks.
        All checks are independent so one failure doesn't break others.
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
        
        # Vector search check (with live endpoint verification)
        try:
            status["vectorSearch"] = await self.check_vector_search()
        except Exception as e:
            status["vectorSearch"] = {
                "status": "Error",
                "message": f"Check failed: {str(e)[:30]}"
            }
        
        # AI Model check (with live endpoint verification)
        try:
            status["aiModel"] = await self.check_ai_model()
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

