"""
Mapping service for managing source-to-target field mappings.
Based on the original Streamlit app's mapping operations.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import List, Dict, Any
from databricks import sql
from databricks.sdk import WorkspaceClient
from backend.models.mapping import MappedField, UnmappedField
from backend.services.config_service import ConfigService


# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=3)


class MappingService:
    """Service for managing field mappings."""
    
    def __init__(self):
        """Initialize the mapping service."""
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self):
        """Lazy initialization of WorkspaceClient."""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
        
    def _get_db_config(self) -> Dict[str, str]:
        """Get database configuration."""
        config = self.config_service.get_config()
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "mapping_table": config.database.mapping_table
        }
    
    def _get_sql_connection(self, server_hostname: str, http_path: str):
        """Get SQL connection with proper OAuth token handling."""
        # Try to get OAuth token from WorkspaceClient config
        access_token = None
        if self.workspace_client and hasattr(self.workspace_client.config, 'authenticate'):
            try:
                headers = self.workspace_client.config.authenticate()
                if headers and 'Authorization' in headers:
                    access_token = headers['Authorization'].replace('Bearer ', '')
            except Exception as e:
                print(f"[Mapping Service] Could not get OAuth token: {e}")
        
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
    
    def _read_mapped_fields_sync(
        self, 
        server_hostname: str, 
        http_path: str, 
        mapping_table: str,
        current_user_email: str
    ) -> List[Dict[str, Any]]:
        """
        Read all mapped fields from the mapping table (synchronous, for thread pool).
        Filters by source_owners to show only user's mappings.
        """
        print(f"[Mapping Service] Reading mapped fields from table: {mapping_table}")
        print(f"[Mapping Service] User email: {current_user_email}")
        
        try:
            print(f"[Mapping Service] Connecting to database...")
            connection = self._get_sql_connection(server_hostname, http_path)
            print(f"[Mapping Service] Connection established")
        except Exception as e:
            print(f"[Mapping Service] Connection failed: {str(e)}")
            raise
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                SELECT DISTINCT 
                    src_table_name,
                    src_column_name, 
                    tgt_columns.tgt_column_name as tgt_mapping,
                    tgt_columns.tgt_table_name as tgt_table_name,
                    tgt_columns.tgt_column_physical_name as tgt_column_physical,
                    tgt_columns.tgt_table_physical_name as tgt_table_physical
                FROM {mapping_table} 
                WHERE tgt_columns IS NOT NULL
                  AND tgt_columns.tgt_column_name IS NOT NULL
                  AND tgt_columns.tgt_column_name != ''
                  AND (source_owners IS NULL OR source_owners LIKE '%{current_user_email}%')
                ORDER BY src_table_name, src_column_name
                """
                print(f"[Mapping Service] Executing query...")
                cursor.execute(query)
                
                print(f"[Mapping Service] Fetching results...")
                arrow_table = cursor.fetchall_arrow()
                df = arrow_table.to_pandas()
                records = df.to_dict('records')
                
                print(f"[Mapping Service] Successfully retrieved {len(records)} mapped fields")
                return records
        except Exception as e:
            print(f"[Mapping Service] Query execution failed: {str(e)}")
            raise
        finally:
            connection.close()
            print(f"[Mapping Service] Connection closed")
    
    async def get_all_mapped_fields(self, current_user_email: str) -> List[MappedField]:
        """Get all mapped fields for the current user."""
        print("[Mapping Service] get_all_mapped_fields called")
        
        try:
            db_config = self._get_db_config()
            print(f"[Mapping Service] Config loaded: {db_config['mapping_table']}")
        except Exception as e:
            print(f"[Mapping Service] Failed to get config: {str(e)}")
            raise
        
        try:
            loop = asyncio.get_event_loop()
            print("[Mapping Service] Running query in executor...")
            records = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    functools.partial(
                        self._read_mapped_fields_sync,
                        db_config['server_hostname'],
                        db_config['http_path'],
                        db_config['mapping_table'],
                        current_user_email
                    )
                ),
                timeout=30.0
            )
            
            # Convert to Pydantic models
            print(f"[Mapping Service] Converting {len(records)} records to Pydantic models")
            return [MappedField(**record) for record in records]
        except asyncio.TimeoutError:
            print("[Mapping Service] Query timed out after 30 seconds")
            raise Exception("Database query timed out after 30 seconds. Check if warehouse is running.")
        except Exception as e:
            print(f"[Mapping Service] Error in get_all_mapped_fields: {str(e)}")
            raise
    
    def _read_unmapped_fields_sync(
        self, 
        server_hostname: str, 
        http_path: str, 
        mapping_table: str,
        current_user_email: str
    ) -> List[Dict[str, Any]]:
        """
        Read all unmapped fields from the mapping table (synchronous, for thread pool).
        Filters by source_owners to show only user's data and where tgt_column_name IS NULL.
        """
        print(f"[Mapping Service] Reading unmapped fields from table: {mapping_table}")
        print(f"[Mapping Service] User email: {current_user_email}")
        
        try:
            print(f"[Mapping Service] Connecting to database...")
            connection = self._get_sql_connection(server_hostname, http_path)
            print(f"[Mapping Service] Connection established")
        except Exception as e:
            print(f"[Mapping Service] Connection failed: {str(e)}")
            raise
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                SELECT DISTINCT 
                    src_table_name,
                    src_column_name,
                    src_columns.src_column_physical_name as src_column_physical_name,
                    src_columns.src_nullable as src_nullable,
                    src_columns.src_physical_datatype as src_physical_datatype,
                    src_columns.src_comments as src_comments
                FROM {mapping_table} 
                WHERE (tgt_columns IS NULL OR tgt_columns.tgt_column_name IS NULL OR tgt_columns.tgt_column_name = '')
                  AND (source_owners IS NULL OR source_owners LIKE '%{current_user_email}%')
                ORDER BY src_table_name, src_column_name
                """
                print(f"[Mapping Service] Executing unmapped fields query...")
                cursor.execute(query)
                
                print(f"[Mapping Service] Fetching unmapped results...")
                arrow_table = cursor.fetchall_arrow()
                df = arrow_table.to_pandas()
                records = df.to_dict('records')
                
                print(f"[Mapping Service] Successfully retrieved {len(records)} unmapped fields")
                return records
        except Exception as e:
            print(f"[Mapping Service] Query execution failed: {str(e)}")
            raise
        finally:
            connection.close()
            print(f"[Mapping Service] Connection closed")
    
    async def get_all_unmapped_fields(self, current_user_email: str) -> List[UnmappedField]:
        """Get all unmapped fields for the current user."""
        print("[Mapping Service] get_all_unmapped_fields called")
        
        try:
            db_config = self._get_db_config()
            print(f"[Mapping Service] Config loaded: {db_config['mapping_table']}")
        except Exception as e:
            print(f"[Mapping Service] Failed to get config: {str(e)}")
            raise
        
        try:
            loop = asyncio.get_event_loop()
            print("[Mapping Service] Running unmapped query in executor...")
            records = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    functools.partial(
                        self._read_unmapped_fields_sync,
                        db_config['server_hostname'],
                        db_config['http_path'],
                        db_config['mapping_table'],
                        current_user_email
                    )
                ),
                timeout=30.0
            )
            
            # Convert to Pydantic models
            print(f"[Mapping Service] Converting {len(records)} unmapped records to Pydantic models")
            return [UnmappedField(**record) for record in records]
        except asyncio.TimeoutError:
            print("[Mapping Service] Unmapped query timed out after 30 seconds")
            raise Exception("Database query timed out after 30 seconds. Check if warehouse is running.")
        except Exception as e:
            print(f"[Mapping Service] Error in get_all_unmapped_fields: {str(e)}")
            raise
    
    def _apply_bulk_mappings_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapping_table: str,
        current_user_email: str,
        mappings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Apply bulk mappings from CSV upload (synchronous, for thread pool).
        Updates tgt_columns for the specified source fields.
        """
        print(f"[Mapping Service] Applying {len(mappings)} bulk mappings to table: {mapping_table}")
        print(f"[Mapping Service] User email: {current_user_email}")
        
        try:
            print(f"[Mapping Service] Connecting to database...")
            connection = self._get_sql_connection(server_hostname, http_path)
            print(f"[Mapping Service] Connection established")
        except Exception as e:
            print(f"[Mapping Service] Connection failed: {str(e)}")
            raise
        
        successful = 0
        failed = 0
        errors = []
        
        try:
            with connection.cursor() as cursor:
                for mapping in mappings:
                    try:
                        # First check if the record exists
                        check_query = f"""
                        SELECT COUNT(*) as cnt FROM {mapping_table}
                        WHERE src_table_name = '{mapping['src_table_name']}'
                          AND src_column_name = '{mapping['src_column_name']}'
                        """
                        cursor.execute(check_query)
                        result = cursor.fetchone()
                        record_exists = result[0] > 0 if result else False
                        
                        if record_exists:
                            # Update existing record
                            query = f"""
                            UPDATE {mapping_table}
                            SET tgt_columns = named_struct(
                                'tgt_table_name', '{mapping['tgt_table_name']}',
                                'tgt_column_name', '{mapping['tgt_column_name']}',
                                'tgt_column_physical_name', '{mapping['tgt_column_physical_name']}',
                                'tgt_table_physical_name', '{mapping['tgt_table_physical_name']}'
                            )
                            WHERE src_table_name = '{mapping['src_table_name']}'
                              AND src_column_name = '{mapping['src_column_name']}'
                            """
                            print(f"[Mapping Service] Updating mapping for {mapping['src_table_name']}.{mapping['src_column_name']}")
                        else:
                            # Insert new record
                            src_physical = mapping.get('src_column_physical_name', mapping['src_column_name'])
                            src_nullable = mapping.get('src_nullable', 'YES')
                            src_datatype = mapping.get('src_physical_datatype', 'STRING')
                            src_comments = mapping.get('src_comments', '')
                            
                            query = f"""
                            INSERT INTO {mapping_table} (
                                src_table_name,
                                src_column_name,
                                src_columns,
                                tgt_columns,
                                source_owners
                            ) VALUES (
                                '{mapping['src_table_name']}',
                                '{mapping['src_column_name']}',
                                named_struct(
                                    'src_column_physical_name', '{src_physical}',
                                    'src_nullable', '{src_nullable}',
                                    'src_physical_datatype', '{src_datatype}',
                                    'src_comments', '{src_comments}'
                                ),
                                named_struct(
                                    'tgt_table_name', '{mapping['tgt_table_name']}',
                                    'tgt_column_name', '{mapping['tgt_column_name']}',
                                    'tgt_column_physical_name', '{mapping['tgt_column_physical_name']}',
                                    'tgt_table_physical_name', '{mapping['tgt_table_physical_name']}'
                                ),
                                '{current_user_email}'
                            )
                            """
                            print(f"[Mapping Service] Inserting new mapping for {mapping['src_table_name']}.{mapping['src_column_name']}")
                        
                        cursor.execute(query)
                        successful += 1
                    except Exception as e:
                        failed += 1
                        error_msg = f"Failed to map {mapping['src_table_name']}.{mapping['src_column_name']}: {str(e)}"
                        print(f"[Mapping Service] {error_msg}")
                        errors.append(error_msg)
                
                print(f"[Mapping Service] Bulk mapping complete: {successful} successful, {failed} failed")
                
        except Exception as e:
            print(f"[Mapping Service] Bulk mapping failed: {str(e)}")
            raise
        finally:
            connection.close()
            print(f"[Mapping Service] Connection closed")
        
        return {
            "successful": successful,
            "failed": failed,
            "errors": errors
        }
    
    async def apply_bulk_mappings(
        self,
        current_user_email: str,
        mappings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply bulk mappings from CSV upload."""
        print(f"[Mapping Service] apply_bulk_mappings called with {len(mappings)} mappings")
        
        try:
            db_config = self._get_db_config()
            print(f"[Mapping Service] Config loaded: {db_config['mapping_table']}")
        except Exception as e:
            print(f"[Mapping Service] Failed to get config: {str(e)}")
            raise
        
        try:
            loop = asyncio.get_event_loop()
            print("[Mapping Service] Running bulk mapping in executor...")
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    functools.partial(
                        self._apply_bulk_mappings_sync,
                        db_config['server_hostname'],
                        db_config['http_path'],
                        db_config['mapping_table'],
                        current_user_email,
                        mappings
                    )
                ),
                timeout=60.0  # Longer timeout for bulk operations
            )
            
            return result
        except asyncio.TimeoutError:
            print("[Mapping Service] Bulk mapping timed out after 60 seconds")
            raise Exception("Bulk mapping timed out after 60 seconds.")
        except Exception as e:
            print(f"[Mapping Service] Error in apply_bulk_mappings: {str(e)}")
            raise
    
    def _unmap_field_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapping_table: str,
        current_user_email: str,
        src_table_name: str,
        src_column_name: str
    ) -> Dict[str, Any]:
        """
        Remove mapping for a field (synchronous, for thread pool).
        Sets tgt_columns to NULL for the specified source field.
        """
        print(f"[Mapping Service] Unmapping field: {src_table_name}.{src_column_name}")
        print(f"[Mapping Service] User email: {current_user_email}")
        
        try:
            print(f"[Mapping Service] Connecting to database...")
            connection = self._get_sql_connection(server_hostname, http_path)
            print(f"[Mapping Service] Connection established")
        except Exception as e:
            print(f"[Mapping Service] Connection failed: {str(e)}")
            raise
        
        try:
            with connection.cursor() as cursor:
                # Set tgt_columns to NULL to unmap the field
                query = f"""
                UPDATE {mapping_table}
                SET tgt_columns = NULL
                WHERE src_table_name = '{src_table_name}'
                  AND src_column_name = '{src_column_name}'
                  AND (source_owners IS NULL OR source_owners LIKE '%{current_user_email}%')
                """
                print(f"[Mapping Service] Executing unmap query...")
                cursor.execute(query)
                
                print(f"[Mapping Service] Successfully unmapped {src_table_name}.{src_column_name}")
                
        except Exception as e:
            print(f"[Mapping Service] Unmap failed: {str(e)}")
            raise
        finally:
            connection.close()
            print(f"[Mapping Service] Connection closed")
        
        return {
            "status": "success",
            "message": f"Unmapped {src_table_name}.{src_column_name}"
        }
    
    async def unmap_field(
        self,
        current_user_email: str,
        src_table_name: str,
        src_column_name: str
    ) -> Dict[str, Any]:
        """Remove mapping for a specific field."""
        print(f"[Mapping Service] unmap_field called for {src_table_name}.{src_column_name}")
        
        try:
            db_config = self._get_db_config()
            print(f"[Mapping Service] Config loaded: {db_config['mapping_table']}")
        except Exception as e:
            print(f"[Mapping Service] Failed to get config: {str(e)}")
            raise
        
        try:
            loop = asyncio.get_event_loop()
            print("[Mapping Service] Running unmap in executor...")
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    functools.partial(
                        self._unmap_field_sync,
                        db_config['server_hostname'],
                        db_config['http_path'],
                        db_config['mapping_table'],
                        current_user_email,
                        src_table_name,
                        src_column_name
                    )
                ),
                timeout=30.0
            )
            
            return result
        except asyncio.TimeoutError:
            print("[Mapping Service] Unmap timed out after 30 seconds")
            raise Exception("Unmap operation timed out after 30 seconds.")
        except Exception as e:
            print(f"[Mapping Service] Error in unmap_field: {str(e)}")
            raise

