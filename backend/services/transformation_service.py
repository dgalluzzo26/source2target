"""
Transformation library service for V2 mapping.

Manages reusable SQL transformation templates.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import List, Dict, Any, Optional
from databricks import sql
from databricks.sdk import WorkspaceClient
from backend.models.mapping_v2 import TransformationV2, TransformationCreateV2
from backend.services.config_service import ConfigService

# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=3)


class TransformationService:
    """Service for managing transformation templates (V2 schema)."""
    
    def __init__(self):
        """Initialize the transformation service."""
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self):
        """Lazy initialization of WorkspaceClient."""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
    
    def _get_db_config(self) -> Dict[str, str]:
        """Get database configuration for transformation library."""
        config = self.config_service.get_config()
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "transformation_library_table": config.database.transformation_library_table
        }
    
    def _get_sql_connection(self, server_hostname: str, http_path: str):
        """Get SQL connection with proper OAuth token handling."""
        access_token = None
        if self.workspace_client and hasattr(self.workspace_client.config, 'authenticate'):
            try:
                headers = self.workspace_client.config.authenticate()
                if headers and 'Authorization' in headers:
                    access_token = headers['Authorization'].replace('Bearer ', '')
            except Exception as e:
                print(f"[Transformation Service] Could not get OAuth token: {e}")
        
        if access_token:
            return sql.connect(
                server_hostname=server_hostname,
                http_path=http_path,
                access_token=access_token
            )
        else:
            return sql.connect(
                server_hostname=server_hostname,
                http_path=http_path,
                auth_type="databricks-oauth"
            )
    
    def _get_all_transformations_sync(
        self,
        server_hostname: str,
        http_path: str,
        transformation_library_table: str
    ) -> List[Dict[str, Any]]:
        """Get all transformation templates (synchronous)."""
        print(f"[Transformation Service] Fetching all transformations")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                SELECT 
                    transform_id,
                    transform_name,
                    transform_code,
                    description,
                    category,
                    created_at
                FROM {transformation_library_table}
                ORDER BY category, transform_name
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                result = []
                for row in rows:
                    record = dict(zip(columns, row))
                    result.append(record)
                
                print(f"[Transformation Service] Found {len(result)} transformations")
                return result
                
        except Exception as e:
            print(f"[Transformation Service] Error fetching transformations: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_all_transformations(self) -> List[TransformationV2]:
        """Get all transformation templates (async)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        records = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_all_transformations_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['transformation_library_table']
            )
        )
        
        return [TransformationV2(**record) for record in records]

