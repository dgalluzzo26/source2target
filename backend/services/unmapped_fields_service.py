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
from backend.models.shared import UnmappedFieldV2, UnmappedFieldCreateV2, UnmappedFieldStatusUpdate
from backend.services.config_service import ConfigService


# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=3)


class UnmappedFieldsService:
    """Service for managing unmapped source fields (V3 schema with vector search)."""
    
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
    
    def _get_vector_search_config(self) -> Dict[str, str]:
        """Get vector search configuration."""
        config = self.config_service.get_config()
        return {
            "endpoint_name": config.vector_search.endpoint_name,
            "unmapped_fields_index": config.vector_search.unmapped_fields_index
        }
    
    def _sync_vector_search_index(self, index_name: str) -> bool:
        """
        Sync/refresh the unmapped_fields vector search index after data changes.
        
        This ensures new/updated fields are immediately searchable for 
        template slot matching and join key suggestions.
        
        Args:
            index_name: Fully qualified index name (catalog.schema.index_name)
            
        Returns:
            True if sync was successful, False otherwise
        """
        try:
            print(f"[Unmapped Fields Service] Syncing vector search index: {index_name}")
            
            self.workspace_client.vector_search_indexes.sync_index(
                index_name=index_name
            )
            
            print(f"[Unmapped Fields Service] Vector search index sync initiated: {index_name}")
            return True
            
        except Exception as e:
            # Log but don't fail - VS sync is best-effort
            print(f"[Unmapped Fields Service] Warning: Could not sync vector search index: {e}")
            return False
    
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
        limit: Optional[int] = None,
        include_mapped: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Read unmapped fields from the database for the current user (synchronous, for thread pool).
        
        V3 Change: Fields are NOT deleted when mapped - they stay in the table with 
        mapping_status = 'MAPPED'. By default, only PENDING fields are returned for 
        the mapping UI. Set include_mapped=True to get all fields (for join key search).
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            unmapped_fields_table: Fully qualified table name
            current_user: Email of the current user (for filtering)
            limit: Optional limit on number of records to return
            include_mapped: If True, include MAPPED fields (for join key search)
            
        Returns:
            List of unmapped field dictionaries for the current user
        """
        print(f"[Unmapped Fields Service] Starting read from table: {unmapped_fields_table}")
        print(f"[Unmapped Fields Service] Server: {server_hostname}")
        print(f"[Unmapped Fields Service] HTTP Path: {http_path}")
        print(f"[Unmapped Fields Service] Current User: {current_user}")
        print(f"[Unmapped Fields Service] Include Mapped: {include_mapped}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # V3: Query unmapped fields for current user
                # Filter by mapping_status unless include_mapped is True
                status_filter = "IN ('PENDING', 'MAPPED')" if include_mapped else "= 'PENDING'"
                
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
                    COALESCE(mapping_status, 'PENDING') as mapping_status,
                    mapped_field_id,
                    uploaded_ts as uploaded_at,
                    uploaded_by
                FROM {unmapped_fields_table}
                WHERE uploaded_by = '{current_user.replace("'", "''")}'
                  AND COALESCE(mapping_status, 'PENDING') {status_filter}
                ORDER BY src_table_name, src_column_name
                """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                print(f"[Unmapped Fields Service] Executing query...")
                cursor.execute(query)
                
                print(f"[Unmapped Fields Service] Fetching results...")
                rows = cursor.fetchall()
                
                print(f"[Unmapped Fields Service] Found {len(rows)} fields for user {current_user} (include_mapped={include_mapped})")
                
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
        
        Checks for duplicates before inserting. A duplicate is defined as:
        - Same src_table_physical_name
        - Same src_column_physical_name
        - Same uploaded_by (user)
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            unmapped_fields_table: Fully qualified table name
            field_data: Unmapped field data to insert
            
        Returns:
            Dictionary with the inserted field data
            
        Raises:
            Exception: If duplicate field already exists for this user
        """
        print(f"[Unmapped Fields Service] Inserting unmapped field: {field_data.src_table_name}.{field_data.src_column_name}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Check for duplicates
                duplicate_check_query = f"""
                SELECT COUNT(*) as count
                FROM {unmapped_fields_table}
                WHERE src_table_physical_name = '{field_data.src_table_physical_name.replace("'", "''")}'
                  AND src_column_physical_name = '{field_data.src_column_physical_name.replace("'", "''")}'
                  AND uploaded_by = '{field_data.uploaded_by.replace("'", "''")}'
                """
                
                cursor.execute(duplicate_check_query)
                result = cursor.fetchone()
                duplicate_count = result[0] if result else 0
                
                if duplicate_count > 0:
                    print(f"[Unmapped Fields Service] Duplicate field found: {field_data.src_table_physical_name}.{field_data.src_column_physical_name} for user {field_data.uploaded_by}")
                    raise Exception(f"Field {field_data.src_table_name}.{field_data.src_column_name} already exists for this user")
                
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
        
        Note: In V3, prefer using update_status to set ARCHIVED instead of deleting.
        This preserves the field for join key search history.
        
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
                query = f"DELETE FROM {unmapped_fields_table} WHERE unmapped_field_id = {field_id}"
                cursor.execute(query)
                rows_deleted = cursor.rowcount
                connection.commit()
                
                if rows_deleted == 0:
                    raise ValueError(f"Unmapped field ID {field_id} not found")
                
                print(f"[Unmapped Fields Service] Unmapped field deleted successfully")
                return {"status": "success", "message": f"Deleted unmapped field ID {field_id}"}
                
        except Exception as e:
            print(f"[Unmapped Fields Service] Error deleting unmapped field: {str(e)}")
            raise
        finally:
            connection.close()
    
    def _update_status_sync(
        self,
        server_hostname: str,
        http_path: str,
        unmapped_fields_table: str,
        field_ids: List[int],
        new_status: str,
        mapped_field_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update mapping_status for one or more unmapped fields (synchronous).
        
        This is the V3 way to mark fields as mapped instead of deleting them.
        Fields stay in the table and can still be found for join key suggestions.
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            unmapped_fields_table: Fully qualified table name
            field_ids: List of field IDs to update
            new_status: New status (PENDING, MAPPED, ARCHIVED)
            mapped_field_id: FK to mapped_fields table (required when status is MAPPED)
            
        Returns:
            Dictionary with status message and count of updated records
        """
        if not field_ids:
            return {"status": "success", "message": "No fields to update", "updated_count": 0}
        
        print(f"[Unmapped Fields Service] Updating status to {new_status} for {len(field_ids)} fields")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                ids_str = ", ".join(str(id) for id in field_ids)
                
                # Build SET clause
                set_parts = [
                    f"mapping_status = '{new_status}'",
                    "updated_ts = CURRENT_TIMESTAMP()"
                ]
                
                if new_status == 'MAPPED' and mapped_field_id is not None:
                    set_parts.append(f"mapped_field_id = {mapped_field_id}")
                elif new_status == 'PENDING':
                    set_parts.append("mapped_field_id = NULL")
                
                set_clause = ", ".join(set_parts)
                
                query = f"""
                    UPDATE {unmapped_fields_table}
                    SET {set_clause}
                    WHERE unmapped_field_id IN ({ids_str})
                """
                
                cursor.execute(query)
                
                print(f"[Unmapped Fields Service] Updated {len(field_ids)} fields to status {new_status}")
                return {
                    "status": "success",
                    "message": f"Updated {len(field_ids)} fields to {new_status}",
                    "updated_count": len(field_ids)
                }
                
        except Exception as e:
            print(f"[Unmapped Fields Service] Error updating status: {str(e)}")
            raise
        finally:
            connection.close()
    
    def _restore_by_mapped_field_id_sync(
        self,
        server_hostname: str,
        http_path: str,
        unmapped_fields_table: str,
        mapped_field_id: int
    ) -> Dict[str, Any]:
        """
        Restore fields to PENDING status when a mapping is deleted (synchronous).
        
        Finds all unmapped fields that reference the given mapped_field_id
        and sets their status back to PENDING.
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            unmapped_fields_table: Fully qualified table name
            mapped_field_id: The mapped_field_id to search for
            
        Returns:
            Dictionary with status and count of restored fields
        """
        print(f"[Unmapped Fields Service] Restoring fields for mapped_field_id: {mapped_field_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                    UPDATE {unmapped_fields_table}
                    SET mapping_status = 'PENDING',
                        mapped_field_id = NULL,
                        updated_ts = CURRENT_TIMESTAMP()
                    WHERE mapped_field_id = {mapped_field_id}
                """
                
                cursor.execute(query)
                
                # Count how many were updated
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {unmapped_fields_table}
                    WHERE mapped_field_id = {mapped_field_id} OR mapping_status = 'PENDING'
                """)
                
                print(f"[Unmapped Fields Service] Restored fields for mapped_field_id {mapped_field_id}")
                return {
                    "status": "success",
                    "message": f"Restored fields for mapping {mapped_field_id}"
                }
                
        except Exception as e:
            print(f"[Unmapped Fields Service] Error restoring fields: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_all_unmapped_fields(
        self,
        current_user: str,
        limit: Optional[int] = None,
        include_mapped: bool = False
    ) -> List[UnmappedFieldV2]:
        """
        Get unmapped fields from the database for the current user.
        
        V3: By default only returns PENDING fields. Set include_mapped=True
        to also get MAPPED fields (useful for join key suggestions).
        
        Args:
            current_user: Email of the current user (for filtering)
            limit: Optional limit on number of records to return
            include_mapped: If True, include MAPPED fields too
            
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
                        limit,
                        include_mapped
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
        
        After creating, syncs the vector search index to make the field
        immediately available for template matching and join suggestions.
        
        Args:
            field_data: Unmapped field data to insert
            
        Returns:
            UnmappedFieldV2 model with inserted data
        """
        db_config = self._get_db_config()
        vs_config = self._get_vector_search_config()
        
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
        
        # Sync vector search index (best-effort, non-blocking)
        try:
            await loop.run_in_executor(
                executor,
                functools.partial(
                    self._sync_vector_search_index,
                    vs_config['unmapped_fields_index']
                )
            )
        except Exception as e:
            print(f"[Unmapped Fields Service] VS sync after create failed (non-fatal): {e}")
        
        return UnmappedFieldV2(**result)
    
    async def delete_unmapped_field(self, field_id: int) -> Dict[str, str]:
        """
        Delete an unmapped field by ID.
        
        Note: In V3, prefer using update_status to set ARCHIVED instead.
        
        After deleting, syncs the vector search index.
        
        Args:
            field_id: ID of the field to delete
            
        Returns:
            Dictionary with status message
        """
        db_config = self._get_db_config()
        vs_config = self._get_vector_search_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._delete_unmapped_field_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['unmapped_fields_table'],
                field_id
            )
        )
        
        # Sync vector search index (best-effort)
        try:
            await loop.run_in_executor(
                executor,
                functools.partial(
                    self._sync_vector_search_index,
                    vs_config['unmapped_fields_index']
                )
            )
        except Exception as e:
            print(f"[Unmapped Fields Service] VS sync after delete failed (non-fatal): {e}")
        
        return result
    
    async def update_status(
        self,
        field_ids: List[int],
        new_status: str,
        mapped_field_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update mapping_status for one or more unmapped fields.
        
        V3: This is the preferred way to mark fields as mapped.
        Fields stay in the table for join key suggestions.
        
        After updating, syncs the vector search index.
        
        Args:
            field_ids: List of field IDs to update
            new_status: New status (PENDING, MAPPED, ARCHIVED)
            mapped_field_id: FK to mapped_fields (required when MAPPED)
            
        Returns:
            Dictionary with status and updated count
        """
        db_config = self._get_db_config()
        vs_config = self._get_vector_search_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._update_status_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['unmapped_fields_table'],
                field_ids,
                new_status,
                mapped_field_id
            )
        )
        
        # Sync vector search index (best-effort)
        try:
            await loop.run_in_executor(
                executor,
                functools.partial(
                    self._sync_vector_search_index,
                    vs_config['unmapped_fields_index']
                )
            )
        except Exception as e:
            print(f"[Unmapped Fields Service] VS sync after status update failed (non-fatal): {e}")
        
        return result
    
    async def restore_by_mapped_field_id(self, mapped_field_id: int) -> Dict[str, Any]:
        """
        Restore fields to PENDING when a mapping is deleted.
        
        Finds all unmapped fields that reference the given mapped_field_id
        and sets their status back to PENDING.
        
        After restoring, syncs the vector search index.
        
        Args:
            mapped_field_id: The mapped_field_id being deleted
            
        Returns:
            Dictionary with status
        """
        db_config = self._get_db_config()
        vs_config = self._get_vector_search_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._restore_by_mapped_field_id_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['unmapped_fields_table'],
                mapped_field_id
            )
        )
        
        # Sync vector search index (best-effort)
        try:
            await loop.run_in_executor(
                executor,
                functools.partial(
                    self._sync_vector_search_index,
                    vs_config['unmapped_fields_index']
                )
            )
        except Exception as e:
            print(f"[Unmapped Fields Service] VS sync after restore failed (non-fatal): {e}")
        
        return result
    
    async def get_all_fields_for_tables(
        self,
        current_user: str,
        table_names: List[str]
    ) -> List[UnmappedFieldV2]:
        """
        Get all fields (PENDING and MAPPED) for specific tables.
        
        Used for join key selection - returns all known columns for the
        given tables regardless of mapping status.
        
        Args:
            current_user: Email of the current user
            table_names: List of table names to filter by
            
        Returns:
            List of UnmappedFieldV2 for the specified tables
        """
        # Get all fields including mapped ones
        all_fields = await self.get_all_unmapped_fields(current_user, include_mapped=True)
        
        # Filter to requested tables
        table_set = set(t.lower() for t in table_names)
        return [
            f for f in all_fields 
            if (f.src_table_physical_name or f.src_table_name or '').lower() in table_set
        ]
    
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
    
    # =========================================================================
    # V4 PROJECT-BASED METHODS
    # =========================================================================
    
    def _bulk_upload_with_project_sync(
        self,
        server_hostname: str,
        http_path: str,
        unmapped_fields_table: str,
        fields: List[Dict[str, Any]],
        project_id: int
    ) -> Dict[str, Any]:
        """
        Bulk upload source fields with project_id (synchronous).
        
        Efficiently inserts multiple fields in a single transaction.
        Skips duplicates within the same project.
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            unmapped_fields_table: Fully qualified table name
            fields: List of field dictionaries
            project_id: Project ID to associate fields with
            
        Returns:
            Dictionary with upload results
        """
        print(f"[Unmapped Fields Service] Bulk uploading {len(fields)} fields for project {project_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                inserted_count = 0
                skipped_count = 0
                
                for field in fields:
                    # Check for duplicate within project
                    src_table = field.get("src_table_physical_name", "").replace("'", "''")
                    src_column = field.get("src_column_physical_name", "").replace("'", "''")
                    
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM {unmapped_fields_table}
                        WHERE src_table_physical_name = '{src_table}'
                          AND src_column_physical_name = '{src_column}'
                          AND project_id = {project_id}
                    """)
                    
                    if cursor.fetchone()[0] > 0:
                        skipped_count += 1
                        continue
                    
                    # Insert field
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
                        project_id,
                        mapping_status
                    ) VALUES (
                        '{field.get("src_table_name", "").replace("'", "''")}',
                        '{field.get("src_table_physical_name", "").replace("'", "''")}',
                        '{field.get("src_column_name", "").replace("'", "''")}',
                        '{field.get("src_column_physical_name", "").replace("'", "''")}',
                        '{field.get("src_nullable", "YES")}',
                        '{field.get("src_physical_datatype", "STRING").replace("'", "''")}',
                        {f"'{field.get('src_comments', '').replace(chr(39), chr(39)+chr(39))}'" if field.get("src_comments") else "NULL"},
                        {f"'{field.get('domain', '').replace(chr(39), chr(39)+chr(39))}'" if field.get("domain") else "NULL"},
                        {project_id},
                        'PENDING'
                    )
                    """
                    
                    cursor.execute(query)
                    inserted_count += 1
                
                print(f"[Unmapped Fields Service] Uploaded {inserted_count} fields, skipped {skipped_count} duplicates")
                
                return {
                    "fields_uploaded": inserted_count,
                    "fields_skipped": skipped_count,
                    "project_id": project_id,
                    "status": "success"
                }
                
        except Exception as e:
            print(f"[Unmapped Fields Service] Error in bulk upload: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def bulk_upload_with_project(
        self,
        fields: List[Dict[str, Any]],
        project_id: int
    ) -> Dict[str, Any]:
        """
        Bulk upload source fields for a project.
        
        V4: Uploads fields with project_id association.
        
        Args:
            fields: List of field dictionaries with src_* columns
            project_id: Project ID to associate fields with
            
        Returns:
            Dictionary with upload results
        """
        db_config = self._get_db_config()
        vs_config = self._get_vector_search_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._bulk_upload_with_project_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['unmapped_fields_table'],
                fields,
                project_id
            )
        )
        
        # Sync vector search index (best-effort)
        try:
            await loop.run_in_executor(
                executor,
                functools.partial(
                    self._sync_vector_search_index,
                    vs_config['unmapped_fields_index']
                )
            )
        except Exception as e:
            print(f"[Unmapped Fields Service] VS sync after bulk upload failed (non-fatal): {e}")
        
        return result
    
    def _get_fields_by_project_sync(
        self,
        server_hostname: str,
        http_path: str,
        unmapped_fields_table: str,
        project_id: int,
        table_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get source fields for a project (synchronous).
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            unmapped_fields_table: Fully qualified table name
            project_id: Project ID to filter by
            table_filter: Optional table name filter
            
        Returns:
            List of field dictionaries
        """
        print(f"[Unmapped Fields Service] Getting fields for project {project_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                table_clause = ""
                if table_filter:
                    table_clause = f"AND UPPER(src_table_physical_name) = UPPER('{table_filter.replace(chr(39), chr(39)+chr(39))}')"
                
                query = f"""
                SELECT 
                    unmapped_field_id,
                    src_table_name,
                    src_table_physical_name,
                    src_column_name,
                    src_column_physical_name,
                    src_nullable,
                    src_physical_datatype,
                    src_comments,
                    domain,
                    mapping_status,
                    mapped_field_id,
                    project_id,
                    uploaded_ts,
                    uploaded_by
                FROM {unmapped_fields_table}
                WHERE project_id = {project_id}
                {table_clause}
                ORDER BY src_table_name, src_column_name
                """
                
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                fields = [dict(zip(columns, row)) for row in rows]
                
                print(f"[Unmapped Fields Service] Found {len(fields)} fields for project {project_id}")
                return fields
                
        except Exception as e:
            print(f"[Unmapped Fields Service] Error getting project fields: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_fields_by_project(
        self,
        project_id: int,
        table_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get source fields for a project.
        
        V4: Gets all source fields associated with a project_id.
        
        Args:
            project_id: Project ID to filter by
            table_filter: Optional table name filter
            
        Returns:
            List of field dictionaries
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_fields_by_project_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['unmapped_fields_table'],
                project_id,
                table_filter
            )
        )
        
        return result
    
    # =========================================================================
    # UPDATE FIELD
    # =========================================================================
    
    def _update_field_sync(
        self,
        server_hostname: str,
        http_path: str,
        unmapped_fields_table: str,
        field_id: int,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a source field (synchronous).
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            unmapped_fields_table: Fully qualified table name
            field_id: ID of the field to update
            updates: Dictionary of field updates
            
        Returns:
            Dictionary with status and updated field info
        """
        print(f"[Unmapped Fields Service] Updating field {field_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Build SET clause from updates
                allowed_fields = [
                    'src_table_name', 'src_table_physical_name',
                    'src_column_name', 'src_column_physical_name',
                    'src_comments', 'src_physical_datatype',
                    'src_nullable', 'domain', 'mapping_status'
                ]
                
                set_parts = ["updated_ts = CURRENT_TIMESTAMP()"]
                
                for field, value in updates.items():
                    if field in allowed_fields:
                        if value is None:
                            set_parts.append(f"{field} = NULL")
                        else:
                            # Escape single quotes
                            escaped_value = str(value).replace("'", "''")
                            set_parts.append(f"{field} = '{escaped_value}'")
                
                if len(set_parts) <= 1:
                    return {"status": "error", "message": "No valid fields to update"}
                
                set_clause = ", ".join(set_parts)
                
                cursor.execute(f"""
                    UPDATE {unmapped_fields_table}
                    SET {set_clause}
                    WHERE unmapped_field_id = {field_id}
                """)
                
                print(f"[Unmapped Fields Service] Updated field {field_id}")
                return {"status": "success", "field_id": field_id}
                
        except Exception as e:
            print(f"[Unmapped Fields Service] Error updating field: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def update_field(
        self,
        field_id: int,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a source field.
        
        Args:
            field_id: ID of the field to update
            updates: Dictionary of field updates
            
        Returns:
            Dictionary with status
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._update_field_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['unmapped_fields_table'],
                field_id,
                updates
            )
        )
        
        return result
    
    # =========================================================================
    # DELETE FIELDS BY PROJECT
    # =========================================================================
    
    def _delete_fields_by_project_sync(
        self,
        server_hostname: str,
        http_path: str,
        unmapped_fields_table: str,
        project_id: int,
        table_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete all source fields for a project (synchronous).
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            unmapped_fields_table: Fully qualified table name
            project_id: Project ID
            table_name: Optional - only delete fields from this table
            
        Returns:
            Dictionary with deleted count
        """
        print(f"[Unmapped Fields Service] Deleting fields for project {project_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Build WHERE clause
                where_clause = f"WHERE project_id = {project_id}"
                
                if table_name:
                    escaped_table = table_name.replace("'", "''")
                    where_clause += f" AND UPPER(src_table_physical_name) = UPPER('{escaped_table}')"
                
                # Get count first
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {unmapped_fields_table}
                    {where_clause}
                """)
                count_row = cursor.fetchone()
                delete_count = count_row[0] if count_row else 0
                
                # Delete
                cursor.execute(f"""
                    DELETE FROM {unmapped_fields_table}
                    {where_clause}
                """)
                
                print(f"[Unmapped Fields Service] Deleted {delete_count} fields for project {project_id}")
                return {"status": "success", "deleted_count": delete_count}
                
        except Exception as e:
            print(f"[Unmapped Fields Service] Error deleting project fields: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def delete_fields_by_project(
        self,
        project_id: int,
        table_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete all source fields for a project.
        
        Args:
            project_id: Project ID
            table_name: Optional - only delete fields from this table
            
        Returns:
            Dictionary with deleted count
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._delete_fields_by_project_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['unmapped_fields_table'],
                project_id,
                table_name
            )
        )
        
        return result

