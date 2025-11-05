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
        
    def _get_db_config(self) -> Dict[str, str]:
        """Get database configuration."""
        config = self.config_service.get_config()
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "semantic_table": config.database.semantic_table
        }
    
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
    
    def _read_semantic_table_sync(self, server_hostname: str, http_path: str, semantic_table: str) -> List[Dict[str, Any]]:
        """
        Read all records from the semantic table (synchronous, for thread pool).
        """
        print(f"[Semantic Service] Starting read from table: {semantic_table}")
        print(f"[Semantic Service] Server: {server_hostname}")
        print(f"[Semantic Service] HTTP Path: {http_path}")
        
        try:
            print(f"[Semantic Service] Connecting to database...")
            connection = sql.connect(
                server_hostname=server_hostname,
                http_path=http_path,
                auth_type="databricks-oauth"
            )
            print(f"[Semantic Service] Connection established")
        except Exception as e:
            print(f"[Semantic Service] Connection failed: {str(e)}")
            raise
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                SELECT 
                    id,
                    tgt_table_name,
                    tgt_table_physical_name,
                    tgt_column_name,
                    tgt_column_physical_name,
                    tgt_nullable,
                    tgt_physical_datatype,
                    tgt_comments,
                    semantic_field
                FROM {semantic_table}
                ORDER BY tgt_table_name, tgt_column_name
                """
                print(f"[Semantic Service] Executing query...")
                cursor.execute(query)
                
                print(f"[Semantic Service] Fetching results...")
                # Fetch results as arrow table and convert to list of dicts
                arrow_table = cursor.fetchall_arrow()
                df = arrow_table.to_pandas()
                records = df.to_dict('records')
                
                print(f"[Semantic Service] Successfully retrieved {len(records)} records")
                return records
        except Exception as e:
            print(f"[Semantic Service] Query execution failed: {str(e)}")
            raise
        finally:
            connection.close()
            print(f"[Semantic Service] Connection closed")
    
    def _insert_semantic_record_sync(
        self,
        server_hostname: str,
        http_path: str,
        semantic_table: str,
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
        
        connection = sql.connect(
            server_hostname=server_hostname,
            http_path=http_path,
            auth_type="databricks-oauth"
        )
        
        try:
            with connection.cursor() as cursor:
                # Get next ID
                max_id_query = f"SELECT COALESCE(MAX(id), 0) + 1 as next_id FROM {semantic_table}"
                cursor.execute(max_id_query)
                next_id = cursor.fetchone()[0]
                
                # Insert with calculated ID
                query = f"""
                INSERT INTO {semantic_table} (
                    id,
                    tgt_table_name,
                    tgt_table_physical_name,
                    tgt_column_name,
                    tgt_column_physical_name,
                    tgt_nullable,
                    tgt_physical_datatype,
                    tgt_comments,
                    semantic_field
                ) VALUES (
                    {next_id},
                    '{record_data.tgt_table_name}',
                    '{record_data.tgt_table_physical_name}',
                    '{record_data.tgt_column_name}',
                    '{record_data.tgt_column_physical_name}',
                    '{record_data.tgt_nullable}',
                    '{record_data.tgt_physical_datatype}',
                    '{record_data.tgt_comments or ""}',
                    '{semantic_field}'
                )
                """
                cursor.execute(query)
                connection.commit()
                
                print(f"[Semantic Service] Successfully inserted record with ID: {next_id}")
                
                return {
                    "id": next_id,
                    "tgt_table_name": record_data.tgt_table_name,
                    "tgt_table_physical_name": record_data.tgt_table_physical_name,
                    "tgt_column_name": record_data.tgt_column_name,
                    "tgt_column_physical_name": record_data.tgt_column_physical_name,
                    "tgt_nullable": record_data.tgt_nullable,
                    "tgt_physical_datatype": record_data.tgt_physical_datatype,
                    "tgt_comments": record_data.tgt_comments,
                    "semantic_field": semantic_field
                }
        finally:
            connection.close()
    
    def _update_semantic_record_sync(
        self,
        server_hostname: str,
        http_path: str,
        semantic_table: str,
        record_id: int,
        record_data: SemanticRecordUpdate
    ) -> Dict[str, Any]:
        """
        Update an existing record in the semantic table (synchronous, for thread pool).
        """
        print(f"[Semantic Service] Updating record ID: {record_id}")
        
        connection = sql.connect(
            server_hostname=server_hostname,
            http_path=http_path,
            auth_type="databricks-oauth"
        )
        
        try:
            with connection.cursor() as cursor:
                # First, get the existing record
                select_query = f"SELECT * FROM {semantic_table} WHERE id = {record_id}"
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
                
                # Update query
                update_query = f"""
                UPDATE {semantic_table}
                SET 
                    tgt_table_name = '{updated_data["tgt_table_name"]}',
                    tgt_table_physical_name = '{updated_data["tgt_table_physical_name"]}',
                    tgt_column_name = '{updated_data["tgt_column_name"]}',
                    tgt_column_physical_name = '{updated_data["tgt_column_physical_name"]}',
                    tgt_nullable = '{updated_data["tgt_nullable"]}',
                    tgt_physical_datatype = '{updated_data["tgt_physical_datatype"]}',
                    tgt_comments = '{updated_data["tgt_comments"]}',
                    semantic_field = '{semantic_field}'
                WHERE id = {record_id}
                """
                cursor.execute(update_query)
                connection.commit()
                
                print(f"[Semantic Service] Successfully updated record ID: {record_id}")
                
                return {
                    "id": record_id,
                    **updated_data,
                    "semantic_field": semantic_field
                }
        finally:
            connection.close()
    
    def _delete_semantic_record_sync(
        self,
        server_hostname: str,
        http_path: str,
        semantic_table: str,
        record_id: int
    ) -> Dict[str, str]:
        """
        Delete a record from the semantic table (synchronous, for thread pool).
        """
        print(f"[Semantic Service] Deleting record ID: {record_id}")
        
        connection = sql.connect(
            server_hostname=server_hostname,
            http_path=http_path,
            auth_type="databricks-oauth"
        )
        
        try:
            with connection.cursor() as cursor:
                query = f"DELETE FROM {semantic_table} WHERE id = {record_id}"
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
            print(f"[Semantic Service] Config loaded: {db_config['semantic_table']}")
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
                        db_config['semantic_table']
                    )
                ),
                timeout=15.0
            )
            
            # Convert to Pydantic models
            print(f"[Semantic Service] Converting {len(records)} records to Pydantic models")
            return [SemanticRecord(**record) for record in records]
        except asyncio.TimeoutError:
            print("[Semantic Service] Query timed out after 15 seconds")
            raise Exception("Database query timed out")
        except Exception as e:
            print(f"[Semantic Service] Error in get_all_records: {str(e)}")
            raise
    
    async def create_record(self, record_data: SemanticRecordCreate) -> SemanticRecord:
        """Create a new semantic table record."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                functools.partial(
                    self._insert_semantic_record_sync,
                    db_config['server_hostname'],
                    db_config['http_path'],
                    db_config['semantic_table'],
                    record_data
                )
            ),
            timeout=15.0
        )
        
        return SemanticRecord(**result)
    
    async def update_record(self, record_id: int, record_data: SemanticRecordUpdate) -> SemanticRecord:
        """Update an existing semantic table record."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                functools.partial(
                    self._update_semantic_record_sync,
                    db_config['server_hostname'],
                    db_config['http_path'],
                    db_config['semantic_table'],
                    record_id,
                    record_data
                )
            ),
            timeout=15.0
        )
        
        return SemanticRecord(**result)
    
    async def delete_record(self, record_id: int) -> Dict[str, str]:
        """Delete a semantic table record."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                functools.partial(
                    self._delete_semantic_record_sync,
                    db_config['server_hostname'],
                    db_config['http_path'],
                    db_config['semantic_table'],
                    record_id
                )
            ),
            timeout=15.0
        )
        
        return result

