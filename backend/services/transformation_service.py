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
from backend.models.shared import TransformationV2, TransformationCreateV2
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
            "transformation_library_table": self.config_service.get_fully_qualified_table_name(config.database.transformation_library_table)
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
                    transformation_id,
                    transformation_name,
                    transformation_code,
                    transformation_expression,
                    transformation_description,
                    category,
                    is_system,
                    created_ts
                FROM {transformation_library_table}
                ORDER BY category, transformation_name
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
    
    def _get_transformation_by_id_sync(
        self,
        server_hostname: str,
        http_path: str,
        transformation_library_table: str,
        transformation_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get transformation by ID (synchronous)."""
        print(f"[Transformation Service] Fetching transformation {transformation_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                SELECT 
                    transformation_id,
                    transformation_name,
                    transformation_code,
                    transformation_expression,
                    transformation_description,
                    category,
                    is_system,
                    created_ts
                FROM {transformation_library_table}
                WHERE transformation_id = {transformation_id}
                """
                
                cursor.execute(query)
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
                
        except Exception as e:
            print(f"[Transformation Service] Error fetching transformation {transformation_id}: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_transformation_by_id(self, transformation_id: int) -> Optional[TransformationV2]:
        """Get transformation by ID (async)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        record = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_transformation_by_id_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['transformation_library_table'],
                transformation_id
            )
        )
        
        return TransformationV2(**record) if record else None
    
    def _get_transformation_by_code_sync(
        self,
        server_hostname: str,
        http_path: str,
        transformation_library_table: str,
        transformation_code: str
    ) -> Optional[Dict[str, Any]]:
        """Get transformation by code (synchronous)."""
        print(f"[Transformation Service] Fetching transformation with code '{transformation_code}'")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                SELECT 
                    transformation_id,
                    transformation_name,
                    transformation_code,
                    transformation_expression,
                    transformation_description,
                    category,
                    is_system,
                    created_ts
                FROM {transformation_library_table}
                WHERE transformation_code = '{transformation_code}'
                """
                
                cursor.execute(query)
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
                
        except Exception as e:
            print(f"[Transformation Service] Error fetching transformation by code: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_transformation_by_code(self, transformation_code: str) -> Optional[TransformationV2]:
        """Get transformation by code (async)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        record = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_transformation_by_code_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['transformation_library_table'],
                transformation_code
            )
        )
        
        return TransformationV2(**record) if record else None
    
    def _create_transformation_sync(
        self,
        server_hostname: str,
        http_path: str,
        transformation_library_table: str,
        transformation: TransformationCreateV2
    ) -> int:
        """Create a new transformation (synchronous)."""
        print(f"[Transformation Service] Creating transformation: {transformation.transformation_name}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Insert the transformation
                query = f"""
                INSERT INTO {transformation_library_table} (
                    transformation_name,
                    transformation_code,
                    transformation_expression,
                    transformation_description,
                    category,
                    is_system,
                    created_by
                ) VALUES (
                    '{transformation.transformation_name.replace("'", "''")}',
                    '{transformation.transformation_code.replace("'", "''")}',
                    '{transformation.transformation_expression.replace("'", "''")}',
                    '{transformation.transformation_description.replace("'", "''") if transformation.transformation_description else ""}',
                    '{transformation.category.replace("'", "''") if transformation.category else ""}',
                    {transformation.is_system or False},
                    'admin'
                )
                """
                
                cursor.execute(query)
                
                # Get the last inserted ID
                cursor.execute(f"""
                    SELECT MAX(transformation_id) as id 
                    FROM {transformation_library_table}
                """)
                row = cursor.fetchone()
                new_id = row[0] if row else None
                
                if not new_id:
                    raise Exception("Failed to get new transformation ID")
                
                print(f"[Transformation Service] Created transformation with ID: {new_id}")
                return new_id
                
        except Exception as e:
            print(f"[Transformation Service] Error creating transformation: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def create_transformation(self, transformation: TransformationCreateV2) -> TransformationV2:
        """Create a new transformation (async)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        new_id = await loop.run_in_executor(
            executor,
            functools.partial(
                self._create_transformation_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['transformation_library_table'],
                transformation
            )
        )
        
        # Fetch and return the newly created transformation
        return await self.get_transformation_by_id(new_id)
    
    def _update_transformation_sync(
        self,
        server_hostname: str,
        http_path: str,
        transformation_library_table: str,
        transformation_id: int,
        transformation: TransformationCreateV2
    ) -> None:
        """Update an existing transformation (synchronous)."""
        print(f"[Transformation Service] Updating transformation {transformation_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                UPDATE {transformation_library_table}
                SET 
                    transformation_name = '{transformation.transformation_name.replace("'", "''")}',
                    transformation_code = '{transformation.transformation_code.replace("'", "''")}',
                    transformation_expression = '{transformation.transformation_expression.replace("'", "''")}',
                    transformation_description = '{transformation.transformation_description.replace("'", "''") if transformation.transformation_description else ""}',
                    category = '{transformation.category.replace("'", "''") if transformation.category else ""}'
                WHERE transformation_id = {transformation_id}
                """
                
                cursor.execute(query)
                print(f"[Transformation Service] Updated transformation {transformation_id}")
                
        except Exception as e:
            print(f"[Transformation Service] Error updating transformation: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def update_transformation(self, transformation_id: int, transformation: TransformationCreateV2) -> TransformationV2:
        """Update an existing transformation (async)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            executor,
            functools.partial(
                self._update_transformation_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['transformation_library_table'],
                transformation_id,
                transformation
            )
        )
        
        # Fetch and return the updated transformation
        return await self.get_transformation_by_id(transformation_id)
    
    def _delete_transformation_sync(
        self,
        server_hostname: str,
        http_path: str,
        transformation_library_table: str,
        transformation_id: int
    ) -> None:
        """Delete a transformation (synchronous)."""
        print(f"[Transformation Service] Deleting transformation {transformation_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                DELETE FROM {transformation_library_table}
                WHERE transformation_id = {transformation_id}
                """
                
                cursor.execute(query)
                print(f"[Transformation Service] Deleted transformation {transformation_id}")
                
        except Exception as e:
            print(f"[Transformation Service] Error deleting transformation: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def delete_transformation(self, transformation_id: int) -> None:
        """Delete a transformation (async)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            executor,
            functools.partial(
                self._delete_transformation_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['transformation_library_table'],
                transformation_id
            )
        )

