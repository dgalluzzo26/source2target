"""
Unmapped fields service for V2 multi-field mapping.

Manages source fields that are awaiting mapping to target fields.
Based on the V2 schema with separate unmapped_fields table.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import List, Dict, Any, Optional
from databricks import sql
from databricks.sdk import WorkspaceClient
from backend.models.mapping_v2 import UnmappedFieldV2, UnmappedFieldCreateV2
from backend.services.config_service import ConfigService


# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=3)


class UnmappedFieldsService:
    """Service for managing unmapped source fields (V2 schema)."""
    
    def __init__(self):
        """Initialize the unmapped fields service."""
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self):
        """Lazy initialization of WorkspaceClient."""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
    
    def _get_db_config(self) -> Dict[str, str]:
        """
        Get database configuration for unmapped fields.
        
        Returns:
            Dictionary with server_hostname, http_path, and unmapped_fields_table
        """
        config = self.config_service.get_config()
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "unmapped_fields_table": self.config_service.get_fully_qualified_table_name(config.database.unmapped_fields_table)
        }
    
    def _get_sql_connection(self, server_hostname: str, http_path: str):
        """
        Get SQL connection with proper OAuth token handling.
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            
        Returns:
            Databricks SQL connection
        """
        # Try to get OAuth token from WorkspaceClient config
        access_token = None
        if self.workspace_client and hasattr(self.workspace_client.config, 'authenticate'):
            try:
                headers = self.workspace_client.config.authenticate()
                if headers and 'Authorization' in headers:
                    access_token = headers['Authorization'].replace('Bearer ', '')
            except Exception as e:
                print(f"[Unmapped Fields Service] Could not get OAuth token: {e}")
        
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
    
    def _read_unmapped_fields_sync(
        self,
        server_hostname: str,
        http_path: str,
        unmapped_fields_table: str,
        current_user: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Read unmapped fields from the database for the current user (synchronous, for thread pool).
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            unmapped_fields_table: Fully qualified table name
            current_user: Email of the current user (for filtering)
            limit: Optional limit on number of records to return
            
        Returns:
            List of unmapped field dictionaries for the current user
        """
        print(f"[Unmapped Fields Service] Starting read from table: {unmapped_fields_table}")
        print(f"[Unmapped Fields Service] Server: {server_hostname}")
        print(f"[Unmapped Fields Service] HTTP Path: {http_path}")
        print(f"[Unmapped Fields Service] Current User: {current_user}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Query unmapped fields filtered by current user
                query = f"""
                SELECT 
                    unmapped_field_id as id,
                    src_table_name,
                    src_table_physical_name,
                    src_column_name,
                    src_column_physical_name,
                    src_nullable,
                    src_physical_datatype,
                    src_comments,
                    domain,
                    uploaded_ts as uploaded_at,
                    uploaded_by
                FROM {unmapped_fields_table}
                WHERE uploaded_by = '{current_user.replace("'", "''")}'
                ORDER BY src_table_name, src_column_name
                """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                print(f"[Unmapped Fields Service] Executing query...")
                cursor.execute(query)
                
                print(f"[Unmapped Fields Service] Fetching results...")
                rows = cursor.fetchall()
                
                print(f"[Unmapped Fields Service] Found {len(rows)} unmapped fields for user {current_user}")
                
                # Convert to list of dictionaries
                columns = [desc[0] for desc in cursor.description]
                result = []
                for row in rows:
                    record = dict(zip(columns, row))
                    result.append(record)
                
                return result
                
        except Exception as e:
            print(f"[Unmapped Fields Service] Error reading unmapped fields: {str(e)}")
            raise
        finally:
            connection.close()
    
    def _insert_unmapped_field_sync(
        self,
        server_hostname: str,
        http_path: str,
        unmapped_fields_table: str,
        field_data: UnmappedFieldCreateV2
    ) -> Dict[str, Any]:
        """
        Insert a new unmapped field (synchronous, for thread pool).
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            unmapped_fields_table: Fully qualified table name
            field_data: Unmapped field data to insert
            
        Returns:
            Dictionary with the inserted field data
        """
        print(f"[Unmapped Fields Service] Inserting unmapped field: {field_data.src_table_name}.{field_data.src_column_name}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Insert with auto-generated ID
                query = f"""
                INSERT INTO {unmapped_fields_table} (
                    src_table_name,
                    src_table_physical_name,
                    src_column_name,
                    src_column_physical_name,
                    src_nullable,
                    src_physical_datatype,
                    src_comments,
                    domain,
                    uploaded_by
                ) VALUES (
                    '{field_data.src_table_name.replace("'", "''")}',
                    '{field_data.src_table_physical_name.replace("'", "''")}',
                    '{field_data.src_column_name.replace("'", "''")}',
                    '{field_data.src_column_physical_name.replace("'", "''")}',
                    '{field_data.src_nullable}',
                    '{field_data.src_physical_datatype.replace("'", "''")}',
                    {'NULL' if not field_data.src_comments else "'" + field_data.src_comments.replace("'", "''") + "'"},
                    {'NULL' if not field_data.domain else "'" + field_data.domain.replace("'", "''") + "'"},
                    {'NULL' if not field_data.uploaded_by else "'" + field_data.uploaded_by.replace("'", "''") + "'"}
                )
                """
                
                cursor.execute(query)
                connection.commit()
                
                print(f"[Unmapped Fields Service] Unmapped field inserted successfully")
                
                # Return the inserted data
                return field_data.model_dump()
                
        except Exception as e:
            print(f"[Unmapped Fields Service] Error inserting unmapped field: {str(e)}")
            raise
        finally:
            connection.close()
    
    def _delete_unmapped_field_sync(
        self,
        server_hostname: str,
        http_path: str,
        unmapped_fields_table: str,
        field_id: int
    ) -> Dict[str, str]:
        """
        Delete an unmapped field by ID (synchronous, for thread pool).
        
        This is typically called after a field has been successfully mapped.
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            unmapped_fields_table: Fully qualified table name
            field_id: ID of the field to delete
            
        Returns:
            Dictionary with status message
        """
        print(f"[Unmapped Fields Service] Deleting unmapped field ID: {field_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"DELETE FROM {unmapped_fields_table} WHERE id = {field_id}"
                cursor.execute(query)
                connection.commit()
                
                print(f"[Unmapped Fields Service] Unmapped field deleted successfully")
                return {"status": "success", "message": f"Deleted unmapped field ID {field_id}"}
                
        except Exception as e:
            print(f"[Unmapped Fields Service] Error deleting unmapped field: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_all_unmapped_fields(self, current_user: str, limit: Optional[int] = None) -> List[UnmappedFieldV2]:
        """
        Get all unmapped fields from the database for the current user.
        
        Args:
            current_user: Email of the current user (for filtering)
            limit: Optional limit on number of records to return
            
        Returns:
            List of UnmappedFieldV2 models for the current user
        """
        try:
            db_config = self._get_db_config()
            print(f"[Unmapped Fields Service] Config loaded: {db_config['unmapped_fields_table']}")
        except Exception as e:
            print(f"[Unmapped Fields Service] Failed to get config: {str(e)}")
            raise
        
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        try:
            records = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    functools.partial(
                        self._read_unmapped_fields_sync,
                        db_config['server_hostname'],
                        db_config['http_path'],
                        db_config['unmapped_fields_table'],
                        current_user,
                        limit
                    )
                ),
                timeout=30.0
            )
            
            # Convert to Pydantic models
            return [UnmappedFieldV2(**record) for record in records]
            
        except asyncio.TimeoutError:
            print(f"[Unmapped Fields Service] Query timeout after 30 seconds")
            raise Exception("Database query timed out")
        except Exception as e:
            print(f"[Unmapped Fields Service] Error: {str(e)}")
            raise
    
    async def create_unmapped_field(self, field_data: UnmappedFieldCreateV2) -> UnmappedFieldV2:
        """
        Create a new unmapped field record.
        
        Args:
            field_data: Unmapped field data to insert
            
        Returns:
            UnmappedFieldV2 model with inserted data
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._insert_unmapped_field_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['unmapped_fields_table'],
                field_data
            )
        )
        
        return UnmappedFieldV2(**result)
    
    async def delete_unmapped_field(self, field_id: int) -> Dict[str, str]:
        """
        Delete an unmapped field by ID.
        
        Args:
            field_id: ID of the field to delete
            
        Returns:
            Dictionary with status message
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            functools.partial(
                self._delete_unmapped_field_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['unmapped_fields_table'],
                field_id
            )
        )
    
    async def get_columns_by_table(self, current_user: str) -> Dict[str, List[str]]:
        """
        Get all unique columns grouped by table for the current user.
        
        Used for join configuration - returns all available columns for each table
        from unmapped fields (and eventually mapped fields).
        
        Args:
            current_user: Email of the current user (for filtering)
            
        Returns:
            Dictionary mapping table names to lists of column names
        """
        # Get all unmapped fields for this user
        unmapped_fields = await self.get_all_unmapped_fields(current_user)
        
        # Group columns by table
        columns_by_table: Dict[str, set] = {}
        for field in unmapped_fields:
            if field.src_table_name not in columns_by_table:
                columns_by_table[field.src_table_name] = set()
            columns_by_table[field.src_table_name].add(field.src_column_name)
        
        # Convert sets to sorted lists
        result = {
            table: sorted(list(columns))
            for table, columns in columns_by_table.items()
        }
        
        print(f"[Unmapped Fields Service] Found {len(result)} tables with columns for user {current_user}")
        return result

