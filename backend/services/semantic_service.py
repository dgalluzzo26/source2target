"""
Semantic table service for managing target field definitions.
Based on the original Streamlit app's semantic table operations.
"""
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import List, Dict, Any, Optional
from databricks import sql
from databricks.sdk import WorkspaceClient
from backend.models.semantic import SemanticRecord, SemanticRecordCreate, SemanticRecordUpdate
from backend.services.config_service import ConfigService


# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=3)


class SemanticService:
    """Service for managing semantic table data."""
    
    def __init__(self):
        """Initialize the semantic service."""
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self):
        """Lazy initialization of WorkspaceClient."""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
    
    async def _sync_vector_search_index(self) -> bool:
        """
        Trigger vector search index sync after semantic table changes.
        
        When the semantic table (Delta table) is updated, the vector search index
        needs to be synced to pick up the changes. Otherwise, AI suggestions will
        use stale data until the index auto-syncs (which can take several minutes).
        
        This matches the behavior of the original Streamlit app.
        
        Returns:
            bool: True if sync was triggered successfully, False otherwise
        """
        try:
            config = self.config_service.get_config()
            index_name = config.vector_search.index_name
            
            print(f"\n{'='*80}")
            print(f"[Vector Search Sync] Triggering sync for index: {index_name}")
            print(f"{'='*80}")
            
            # Run sync in executor since WorkspaceClient methods are synchronous
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                executor,
                functools.partial(
                    self.workspace_client.vector_search_indexes.sync_index,
                    index_name
                )
            )
            
            print(f"[Vector Search Sync] ✅ Sync triggered successfully")
            print(f"[Vector Search Sync] Note: Full sync may take a few moments to complete")
            print(f"{'='*80}\n")
            return True
            
        except Exception as e:
            # Don't fail the entire operation if index sync fails
            # The index will eventually auto-sync
            print(f"\n{'!'*80}")
            print(f"[Vector Search Sync] ⚠️  Warning: Could not sync vector search index")
            print(f"[Vector Search Sync] Error type: {type(e).__name__}")
            print(f"[Vector Search Sync] Error message: {str(e)}")
            print(f"[Vector Search Sync] The index will auto-sync eventually (may take 5-10 minutes)")
            print(f"{'!'*80}\n")
            
            import traceback
            print(f"[Vector Search Sync] Full traceback:")
            print(traceback.format_exc())
            
            return False
        
    def _get_db_config(self) -> Dict[str, str]:
        """Get database configuration."""
        config = self.config_service.get_config()
        db = config.database
        return {
            "server_hostname": db.server_hostname,
            "http_path": db.http_path,
            "semantic_fields_table": db.semantic_fields_table
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
                print(f"[Semantic Service] Could not get OAuth token: {e}")
        
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
    
    def _generate_semantic_field(
        self,
        tgt_table_name: str,
        tgt_column_name: str,
        tgt_comments: Optional[str],
        tgt_nullable: str,
        tgt_physical_datatype: str
    ) -> str:
        """
        Generate semantic field text for vector search.
        Format matches original Streamlit app.
        """
        nullable_text = "Not Null" if tgt_nullable == "NO" else "Nullable"
        comments_text = tgt_comments if tgt_comments and tgt_comments.strip() else "No description provided"
        
        semantic_field = (
            f"TABLE NAME: {tgt_table_name.upper()}; "
            f"COLUMN NAME: {tgt_column_name}; "
            f"COLUMN DESCRIPTION: {comments_text}; "
            f"IS COLUMN NULLABLE: {nullable_text}; "
            f"COLUMN DATATYPE: {tgt_physical_datatype.upper()}"
        )
        return semantic_field
    
    def _read_semantic_table_sync(self, server_hostname: str, http_path: str, semantic_fields_table: str) -> List[Dict[str, Any]]:
        """
        Read all records from the semantic_fields table (V2 schema, synchronous, for thread pool).
        """
        print(f"\n{'='*80}")
        print(f"[Semantic Service] Starting read from table: {semantic_fields_table}")
        print(f"[Semantic Service] Server: {server_hostname}")
        print(f"[Semantic Service] HTTP Path: {http_path}")
        print(f"{'='*80}\n")
        
        # Check warehouse state first (extract warehouse ID from http_path)
        try:
            # Extract warehouse ID from http_path like "/sql/1.0/warehouses/173ea239ed13be7d"
            warehouse_id = http_path.split('/warehouses/')[-1] if '/warehouses/' in http_path else None
            if warehouse_id:
                print(f"[Semantic Service] Checking warehouse state: {warehouse_id}")
                warehouse = self.workspace_client.warehouses.get(warehouse_id)
                print(f"[Semantic Service] Warehouse state: {warehouse.state}")
                if warehouse.state and hasattr(warehouse.state, 'value'):
                    state_value = str(warehouse.state.value).upper()
                    if 'STOPPED' in state_value or 'DELETED' in state_value:
                        raise Exception(f"Warehouse is {state_value}. Please start the warehouse first.")
        except Exception as wh_error:
            print(f"[Semantic Service] Warning: Could not check warehouse state: {str(wh_error)}")
            # Continue anyway - the connection will fail if warehouse is actually stopped
        
        try:
            print(f"[Semantic Service] Connecting to database...")
            connection = self._get_sql_connection(server_hostname, http_path)
            print(f"[Semantic Service] Connection established")
        except Exception as e:
            print(f"[Semantic Service] Connection failed: {str(e)}")
            raise
        
        try:
            with connection.cursor() as cursor:
                # Note: Skipping table existence check because service principal 
                # doesn't have access to system.information_schema
                # Table must exist or query will fail with clear error
                print(f"[Semantic Service] Querying table: {semantic_fields_table}")
                
                query = f"""
                SELECT 
                    semantic_field_id as id,
                    tgt_table_name,
                    tgt_table_physical_name,
                    tgt_column_name,
                    tgt_column_physical_name,
                    tgt_nullable,
                    tgt_physical_datatype,
                    tgt_comments,
                    semantic_field
                FROM {semantic_fields_table}
                ORDER BY tgt_table_name, tgt_column_name
                """
                print(f"[Semantic Service] Executing main query to fetch semantic fields...")
                cursor.execute(query)
                
                print(f"[Semantic Service] Query executed successfully, fetching results...")
                # Fetch results as arrow table and convert to list of dicts
                arrow_table = cursor.fetchall_arrow()
                print(f"[Semantic Service] Converting Arrow table to Pandas...")
                df = arrow_table.to_pandas()
                print(f"[Semantic Service] ✓ Fetched {len(df)} records")
                records = df.to_dict('records')
                
                print(f"[Semantic Service] Successfully retrieved {len(records)} records")
                return records
        except Exception as e:
            print(f"\n{'!'*80}")
            print(f"[Semantic Service] ❌ ERROR reading semantic table")
            print(f"[Semantic Service] Error type: {type(e).__name__}")
            print(f"[Semantic Service] Error message: {str(e)}")
            import traceback
            print(f"[Semantic Service] Full traceback:")
            print(traceback.format_exc())
            print(f"{'!'*80}\n")
            raise
        finally:
            connection.close()
            print(f"[Semantic Service] Connection closed")
    
    def _insert_semantic_record_sync(
        self,
        server_hostname: str,
        http_path: str,
        semantic_fields_table: str,
        record_data: SemanticRecordCreate
    ) -> Dict[str, Any]:
        """
        Insert a new record into the semantic table (synchronous, for thread pool).
        """
        print(f"[Semantic Service] Inserting record: {record_data.tgt_table_name}.{record_data.tgt_column_name}")
        
        # Generate semantic field
        semantic_field = self._generate_semantic_field(
            record_data.tgt_table_name,
            record_data.tgt_column_name,
            record_data.tgt_comments,
            record_data.tgt_nullable,
            record_data.tgt_physical_datatype
        )
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Note: semantic_field_id is auto-generated (IDENTITY column)
                # semantic_field is a computed column, so we don't need to insert it
                # V2 schema: semantic_field_id is auto-generated, so we don't include it in INSERT
                
                query = f"""
                INSERT INTO {semantic_fields_table} (
                    tgt_table_name,
                    tgt_table_physical_name,
                    tgt_column_name,
                    tgt_column_physical_name,
                    tgt_nullable,
                    tgt_physical_datatype,
                    tgt_comments
                ) VALUES (
                    '{record_data.tgt_table_name.replace("'", "''")}',
                    '{record_data.tgt_table_physical_name.replace("'", "''")}',
                    '{record_data.tgt_column_name.replace("'", "''")}',
                    '{record_data.tgt_column_physical_name.replace("'", "''")}',
                    '{record_data.tgt_nullable}',
                    '{record_data.tgt_physical_datatype}',
                    '{(record_data.tgt_comments or "").replace("'", "''")}'
                )
                """
                print(f"[Semantic Service] Insert query: {query[:200]}...")
                cursor.execute(query)
                connection.commit()
                
                # Get the auto-generated ID
                get_id_query = f"""
                SELECT semantic_field_id 
                FROM {semantic_fields_table}
                WHERE tgt_table_name = '{record_data.tgt_table_name.replace("'", "''")}'
                  AND tgt_column_name = '{record_data.tgt_column_name.replace("'", "''")}'
                ORDER BY semantic_field_id DESC
                LIMIT 1
                """
                cursor.execute(get_id_query)
                inserted_id = cursor.fetchone()[0]
                
                print(f"[Semantic Service] Successfully inserted record with ID: {inserted_id}")
                
                # Get the computed semantic_field value
                get_record_query = f"SELECT * FROM {semantic_fields_table} WHERE semantic_field_id = {inserted_id}"
                cursor.execute(get_record_query)
                inserted_record = cursor.fetchone()
                
                return {
                    "id": inserted_id,
                    "tgt_table_name": record_data.tgt_table_name,
                    "tgt_table_physical_name": record_data.tgt_table_physical_name,
                    "tgt_column_name": record_data.tgt_column_name,
                    "tgt_column_physical_name": record_data.tgt_column_physical_name,
                    "tgt_nullable": record_data.tgt_nullable,
                    "tgt_physical_datatype": record_data.tgt_physical_datatype,
                    "tgt_comments": record_data.tgt_comments,
                    "semantic_field": inserted_record[8] if inserted_record else ""  # semantic_field is column 8
                }
        finally:
            connection.close()
    
    def _update_semantic_record_sync(
        self,
        server_hostname: str,
        http_path: str,
        semantic_fields_table: str,
        record_id: int,
        record_data: SemanticRecordUpdate
    ) -> Dict[str, Any]:
        """
        Update an existing record in the semantic_fields table (V2 schema, synchronous, for thread pool).
        """
        print(f"[Semantic Service] Updating record ID: {record_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # First, get the existing record
                select_query = f"SELECT * FROM {semantic_fields_table} WHERE semantic_field_id = {record_id}"
                cursor.execute(select_query)
                existing = cursor.fetchone()
                
                if not existing:
                    raise ValueError(f"Record with ID {record_id} not found")
                
                # Merge updates with existing values
                updated_data = {
                    "tgt_table_name": record_data.tgt_table_name or existing[1],
                    "tgt_table_physical_name": record_data.tgt_table_physical_name or existing[2],
                    "tgt_column_name": record_data.tgt_column_name or existing[3],
                    "tgt_column_physical_name": record_data.tgt_column_physical_name or existing[4],
                    "tgt_nullable": record_data.tgt_nullable or existing[5],
                    "tgt_physical_datatype": record_data.tgt_physical_datatype or existing[6],
                    "tgt_comments": record_data.tgt_comments if record_data.tgt_comments is not None else existing[7]
                }
                
                # Regenerate semantic field
                semantic_field = self._generate_semantic_field(
                    updated_data["tgt_table_name"],
                    updated_data["tgt_column_name"],
                    updated_data["tgt_comments"],
                    updated_data["tgt_nullable"],
                    updated_data["tgt_physical_datatype"]
                )
                
                # Update query with proper SQL escaping
                # Note: semantic_field is a computed column in V2, so we don't update it manually
                update_query = f"""
                UPDATE {semantic_fields_table}
                SET 
                    tgt_table_name = '{updated_data["tgt_table_name"].replace("'", "''")}',
                    tgt_table_physical_name = '{updated_data["tgt_table_physical_name"].replace("'", "''")}',
                    tgt_column_name = '{updated_data["tgt_column_name"].replace("'", "''")}',
                    tgt_column_physical_name = '{updated_data["tgt_column_physical_name"].replace("'", "''")}',
                    tgt_nullable = '{updated_data["tgt_nullable"]}',
                    tgt_physical_datatype = '{updated_data["tgt_physical_datatype"]}',
                    tgt_comments = '{updated_data["tgt_comments"].replace("'", "''")}'
                WHERE semantic_field_id = {record_id}
                """
                print(f"[Semantic Service] Update query: {update_query[:200]}...")
                cursor.execute(update_query)
                connection.commit()
                
                # Get the updated record with computed semantic_field
                get_updated_query = f"SELECT * FROM {semantic_fields_table} WHERE semantic_field_id = {record_id}"
                cursor.execute(get_updated_query)
                updated_record = cursor.fetchone()
                
                print(f"[Semantic Service] Successfully updated record ID: {record_id}")
                
                return {
                    "id": record_id,
                    **updated_data,
                    "semantic_field": updated_record[8] if updated_record else ""  # semantic_field is column 8
                }
        finally:
            connection.close()
    
    def _delete_semantic_record_sync(
        self,
        server_hostname: str,
        http_path: str,
        semantic_fields_table: str,
        record_id: int
    ) -> Dict[str, str]:
        """
        Delete a record from the semantic_fields table (V2 schema, synchronous, for thread pool).
        """
        print(f"[Semantic Service] Deleting record ID: {record_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"DELETE FROM {semantic_fields_table} WHERE semantic_field_id = {record_id}"
                cursor.execute(query)
                connection.commit()
                
                print(f"[Semantic Service] Successfully deleted record ID: {record_id}")
                return {"status": "success", "message": f"Record {record_id} deleted"}
        finally:
            connection.close()
    
    async def get_all_records(self) -> List[SemanticRecord]:
        """Get all semantic table records."""
        print("[Semantic Service] get_all_records called")
        
        try:
            db_config = self._get_db_config()
            print(f"[Semantic Service] Config loaded: {db_config['semantic_fields_table']}")
        except Exception as e:
            print(f"[Semantic Service] Failed to get config: {str(e)}")
            raise
        
        try:
            loop = asyncio.get_event_loop()
            print("[Semantic Service] Running query in executor...")
            records = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    functools.partial(
                        self._read_semantic_table_sync,
                        db_config['server_hostname'],
                        db_config['http_path'],
                        db_config['semantic_fields_table']
                    )
                ),
                timeout=30.0  # Increased to 30 seconds
            )
            
            # Convert to Pydantic models
            print(f"[Semantic Service] Converting {len(records)} records to Pydantic models")
            return [SemanticRecord(**record) for record in records]
        except asyncio.TimeoutError:
            print("[Semantic Service] Query timed out after 30 seconds - warehouse may be stopped")
            raise Exception("Database query timed out after 30 seconds. Check if warehouse is running.")
        except Exception as e:
            print(f"[Semantic Service] Error in get_all_records: {str(e)}")
            raise
    
    async def create_record(self, record_data: SemanticRecordCreate) -> SemanticRecord:
        """
        Create a new semantic table record.
        
        After creating the record, triggers a vector search index sync to ensure
        AI suggestions immediately reflect the new target field.
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                functools.partial(
                    self._insert_semantic_record_sync,
                    db_config['server_hostname'],
                    db_config['http_path'],
                    db_config['semantic_fields_table'],
                    record_data
                )
            ),
            timeout=15.0
        )
        
        # Trigger vector search index sync after creating record
        # This ensures AI suggestions reflect the new target field immediately
        await self._sync_vector_search_index()
        
        return SemanticRecord(**result)
    
    async def update_record(self, record_id: int, record_data: SemanticRecordUpdate) -> SemanticRecord:
        """
        Update an existing semantic table record.
        
        After updating the record, triggers a vector search index sync to ensure
        AI suggestions immediately reflect the updated target field metadata.
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                functools.partial(
                    self._update_semantic_record_sync,
                    db_config['server_hostname'],
                    db_config['http_path'],
                    db_config['semantic_fields_table'],
                    record_id,
                    record_data
                )
            ),
            timeout=15.0
        )
        
        # Trigger vector search index sync after updating record
        # This ensures AI suggestions reflect the updated field metadata immediately
        await self._sync_vector_search_index()
        
        return SemanticRecord(**result)
    
    async def delete_record(self, record_id: int) -> Dict[str, str]:
        """
        Delete a semantic table record.
        
        After deleting the record, triggers a vector search index sync to ensure
        AI suggestions no longer include the deleted target field.
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                functools.partial(
                    self._delete_semantic_record_sync,
                    db_config['server_hostname'],
                    db_config['http_path'],
                    db_config['semantic_fields_table'],
                    record_id
                )
            ),
            timeout=15.0
        )
        
        # Trigger vector search index sync after deleting record
        # This ensures AI suggestions no longer include the deleted field
        await self._sync_vector_search_index()
        
        return result

