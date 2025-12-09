"""
Mapping service V3 for simplified single-table mapping CRUD operations.

V3 KEY CHANGES:
- Single table (mapped_fields) - no more mapping_details, mapping_joins
- SQL expression captures all logic
- Simpler CRUD operations
- source_semantic_field populated on insert for vector search
- Vector search index synced after create/update operations

Manages:
- Creating mappings (single row with SQL expression)
- Reading mappings (simple SELECT)
- Updating mappings (source_expression, metadata)
- Deleting mappings
- Syncing vector search index
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import List, Dict, Any, Optional
from databricks import sql
from databricks.sdk import WorkspaceClient
from backend.models.mapping_v3 import (
    MappedFieldV3,
    MappedFieldCreateV3,
    MappedFieldUpdateV3,
    MappingFeedbackCreateV3
)
from backend.services.config_service import ConfigService

# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=3)


class MappingServiceV3:
    """Service for managing simplified V3 mappings."""
    
    def __init__(self):
        """Initialize the mapping service V3."""
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self):
        """Lazy initialization of WorkspaceClient."""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
    
    def _get_db_config(self) -> Dict[str, str]:
        """Get database configuration for V3 tables."""
        config = self.config_service.get_config()
        catalog = config.database.catalog
        schema = config.database.schema
        
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "mapped_fields_table": f"{catalog}.{schema}.mapped_fields",
            "unmapped_fields_table": f"{catalog}.{schema}.unmapped_fields",
            "semantic_fields_table": f"{catalog}.{schema}.semantic_fields",
            "mapping_feedback_table": f"{catalog}.{schema}.mapping_feedback",
            "transformation_library_table": f"{catalog}.{schema}.transformation_library"
        }
    
    def _get_vector_search_config(self) -> Dict[str, str]:
        """Get vector search configuration."""
        config = self.config_service.get_config()
        return {
            "endpoint_name": config.vector_search.endpoint_name,
            "mapped_fields_index": config.vector_search.mapped_fields_index,
            "semantic_fields_index": config.vector_search.semantic_fields_index
        }
    
    def _sync_vector_search_index(self, index_name: str) -> bool:
        """
        Sync/refresh a vector search index after data changes.
        
        This ensures new mappings are immediately searchable by the AI.
        
        Args:
            index_name: Fully qualified index name (catalog.schema.index_name)
            
        Returns:
            True if sync was successful, False otherwise
        """
        try:
            print(f"[Mapping Service V3] Syncing vector search index: {index_name}")
            
            # Use the workspace client to sync the index
            # The sync operation triggers an incremental update of the index
            self.workspace_client.vector_search_indexes.sync_index(
                index_name=index_name
            )
            
            print(f"[Mapping Service V3] Vector search index sync initiated: {index_name}")
            return True
            
        except Exception as e:
            # Log but don't fail - VS sync is best-effort
            # Index will eventually catch up via scheduled sync
            print(f"[Mapping Service V3] Warning: Could not sync vector search index: {e}")
            return False
    
    def _get_sql_connection(self, server_hostname: str, http_path: str):
        """Get SQL connection with proper OAuth token handling."""
        access_token = None
        if self.workspace_client and hasattr(self.workspace_client.config, 'authenticate'):
            try:
                headers = self.workspace_client.config.authenticate()
                if headers and 'Authorization' in headers:
                    access_token = headers['Authorization'].replace('Bearer ', '')
            except Exception as e:
                print(f"[Mapping Service V3] Could not get OAuth token: {e}")
        
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
    
    def _build_source_semantic_field(
        self,
        source_tables: Optional[str],
        source_columns: Optional[str],
        source_descriptions: Optional[str],
        transformations_applied: Optional[str],
        tgt_table_name: str,
        tgt_column_name: str
    ) -> str:
        """
        Build the source_semantic_field for vector indexing.
        
        This field enables AI pattern matching by combining source context.
        """
        parts = []
        
        if source_tables:
            parts.append(f"SOURCE TABLES: {source_tables}")
        if source_columns:
            parts.append(f"SOURCE COLUMNS: {source_columns}")
        if source_descriptions:
            parts.append(f"SOURCE DESCRIPTIONS: {source_descriptions}")
        if transformations_applied:
            parts.append(f"TRANSFORMATIONS: {transformations_applied}")
        parts.append(f"TARGET: {tgt_table_name}.{tgt_column_name}")
        
        return " | ".join(parts)
    
    def _escape_sql(self, value: str) -> str:
        """Escape single quotes for SQL strings."""
        if value is None:
            return ""
        return value.replace("'", "''")
    
    # =========================================================================
    # CREATE MAPPING
    # =========================================================================
    
    def _create_mapping_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapped_fields_table: str,
        unmapped_fields_table: str,
        data: MappedFieldCreateV3,
        unmapped_field_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Create a V3 mapping (synchronous).
        
        Steps:
        1. Build source_semantic_field
        2. Insert into mapped_fields
        3. Optionally delete from unmapped_fields
        """
        print(f"[Mapping Service V3] Creating mapping: {data.tgt_table_name}.{data.tgt_column_name}")
        print(f"[Mapping Service V3] Source expression: {data.source_expression[:100]}...")
        
        # Note: source_semantic_field is a generated column in the database
        # It auto-generates from source_tables, source_columns, source_descriptions, etc.
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Insert into mapped_fields (without source_semantic_field - it may be a generated column)
                insert_sql = f"""
                INSERT INTO {mapped_fields_table} (
                    semantic_field_id,
                    tgt_table_name,
                    tgt_table_physical_name,
                    tgt_column_name,
                    tgt_column_physical_name,
                    tgt_comments,
                    source_expression,
                    source_tables,
                    source_tables_physical,
                    source_columns,
                    source_columns_physical,
                    source_descriptions,
                    source_datatypes,
                    source_domain,
                    source_relationship_type,
                    transformations_applied,
                    confidence_score,
                    mapping_source,
                    ai_reasoning,
                    ai_generated,
                    mapping_status,
                    mapped_by
                ) VALUES (
                    {data.semantic_field_id},
                    '{self._escape_sql(data.tgt_table_name)}',
                    '{self._escape_sql(data.tgt_table_physical_name)}',
                    '{self._escape_sql(data.tgt_column_name)}',
                    '{self._escape_sql(data.tgt_column_physical_name)}',
                    {f"'{self._escape_sql(data.tgt_comments)}'" if data.tgt_comments else 'NULL'},
                    '{self._escape_sql(data.source_expression)}',
                    {f"'{self._escape_sql(data.source_tables)}'" if data.source_tables else 'NULL'},
                    {f"'{self._escape_sql(data.source_tables_physical)}'" if data.source_tables_physical else 'NULL'},
                    {f"'{self._escape_sql(data.source_columns)}'" if data.source_columns else 'NULL'},
                    {f"'{self._escape_sql(data.source_columns_physical)}'" if data.source_columns_physical else 'NULL'},
                    {f"'{self._escape_sql(data.source_descriptions)}'" if data.source_descriptions else 'NULL'},
                    {f"'{self._escape_sql(data.source_datatypes)}'" if data.source_datatypes else 'NULL'},
                    {f"'{self._escape_sql(data.source_domain)}'" if data.source_domain else 'NULL'},
                    '{data.source_relationship_type}',
                    {f"'{self._escape_sql(data.transformations_applied)}'" if data.transformations_applied else 'NULL'},
                    {data.confidence_score if data.confidence_score is not None else 'NULL'},
                    '{data.mapping_source}',
                    {f"'{self._escape_sql(data.ai_reasoning)}'" if data.ai_reasoning else 'NULL'},
                    {str(data.ai_generated).lower()},
                    'ACTIVE',
                    {f"'{self._escape_sql(data.mapped_by)}'" if data.mapped_by else 'NULL'}
                )
                """
                
                print(f"[Mapping Service V3] Executing INSERT...")
                cursor.execute(insert_sql)
                
                # Get the new mapping ID
                cursor.execute(f"""
                    SELECT MAX(mapped_field_id) as id 
                    FROM {mapped_fields_table}
                    WHERE tgt_column_physical_name = '{self._escape_sql(data.tgt_column_physical_name)}'
                """)
                result = cursor.fetchone()
                mapping_id = result[0] if result else None
                
                print(f"[Mapping Service V3] Created mapping ID: {mapping_id}")
                
                # Delete from unmapped_fields if IDs provided
                if unmapped_field_ids and len(unmapped_field_ids) > 0:
                    ids_str = ", ".join(str(id) for id in unmapped_field_ids)
                    delete_sql = f"""
                        DELETE FROM {unmapped_fields_table}
                        WHERE unmapped_field_id IN ({ids_str})
                    """
                    print(f"[Mapping Service V3] Deleting {len(unmapped_field_ids)} unmapped fields...")
                    cursor.execute(delete_sql)
                
                return {
                    "mapping_id": mapping_id,
                    "message": "Mapping created successfully"
                }
                
        finally:
            connection.close()
    
    async def create_mapping(
        self,
        data: MappedFieldCreateV3,
        unmapped_field_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Create a V3 mapping (async wrapper).
        
        After creating the mapping, syncs the vector search index to make
        the new mapping immediately available for AI pattern matching.
        """
        db_config = self._get_db_config()
        vs_config = self._get_vector_search_config()
        loop = asyncio.get_event_loop()
        
        # Create the mapping
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._create_mapping_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["mapped_fields_table"],
                db_config["unmapped_fields_table"],
                data,
                unmapped_field_ids
            )
        )
        
        # Sync vector search index (best-effort, non-blocking)
        try:
            await loop.run_in_executor(
                executor,
                functools.partial(
                    self._sync_vector_search_index,
                    vs_config["mapped_fields_index"]
                )
            )
        except Exception as e:
            print(f"[Mapping Service V3] VS sync failed (non-fatal): {e}")
        
        return result
    
    # =========================================================================
    # GET ALL MAPPINGS
    # =========================================================================
    
    def _get_mappings_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapped_fields_table: str,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all mappings (synchronous)."""
        print("[Mapping Service V3] Fetching mappings...")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                where_clause = ""
                if status_filter:
                    where_clause = f"WHERE mapping_status = '{status_filter}'"
                
                query = f"""
                    SELECT 
                        mapped_field_id,
                        semantic_field_id,
                        tgt_table_name,
                        tgt_table_physical_name,
                        tgt_column_name,
                        tgt_column_physical_name,
                        tgt_comments,
                        source_expression,
                        source_tables,
                        source_columns,
                        source_descriptions,
                        source_datatypes,
                        source_relationship_type,
                        transformations_applied,
                        confidence_score,
                        mapping_source,
                        ai_reasoning,
                        ai_generated,
                        mapping_status,
                        mapped_by,
                        mapped_ts,
                        updated_by,
                        updated_ts,
                        source_semantic_field
                    FROM {mapped_fields_table}
                    {where_clause}
                    ORDER BY mapped_ts DESC
                """
                
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                mappings = []
                for row in rows:
                    mapping = dict(zip(columns, row))
                    mappings.append(mapping)
                
                print(f"[Mapping Service V3] Found {len(mappings)} mappings")
                return mappings
                
        finally:
            connection.close()
    
    async def get_mappings(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all mappings (async wrapper)."""
        db_config = self._get_db_config()
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_mappings_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["mapped_fields_table"],
                status_filter
            )
        )
    
    # =========================================================================
    # GET SINGLE MAPPING
    # =========================================================================
    
    def _get_mapping_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapped_fields_table: str,
        mapping_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a single mapping by ID (synchronous)."""
        print(f"[Mapping Service V3] Fetching mapping ID: {mapping_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                    SELECT 
                        mapped_field_id,
                        semantic_field_id,
                        tgt_table_name,
                        tgt_table_physical_name,
                        tgt_column_name,
                        tgt_column_physical_name,
                        tgt_comments,
                        source_expression,
                        source_tables,
                        source_columns,
                        source_descriptions,
                        source_datatypes,
                        source_relationship_type,
                        transformations_applied,
                        confidence_score,
                        mapping_source,
                        ai_reasoning,
                        ai_generated,
                        mapping_status,
                        mapped_by,
                        mapped_ts,
                        updated_by,
                        updated_ts,
                        source_semantic_field
                    FROM {mapped_fields_table}
                    WHERE mapped_field_id = {mapping_id}
                """
                
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                
                if row:
                    return dict(zip(columns, row))
                return None
                
        finally:
            connection.close()
    
    async def get_mapping(self, mapping_id: int) -> Optional[Dict[str, Any]]:
        """Get a single mapping by ID (async wrapper)."""
        db_config = self._get_db_config()
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_mapping_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["mapped_fields_table"],
                mapping_id
            )
        )
    
    # =========================================================================
    # UPDATE MAPPING
    # =========================================================================
    
    def _update_mapping_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapped_fields_table: str,
        mapping_id: int,
        data: MappedFieldUpdateV3
    ) -> Dict[str, Any]:
        """Update a mapping (synchronous)."""
        print(f"[Mapping Service V3] Updating mapping ID: {mapping_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Build SET clause dynamically
                set_parts = []
                
                if data.source_expression is not None:
                    set_parts.append(f"source_expression = '{self._escape_sql(data.source_expression)}'")
                if data.source_tables is not None:
                    set_parts.append(f"source_tables = '{self._escape_sql(data.source_tables)}'")
                if data.source_tables_physical is not None:
                    set_parts.append(f"source_tables_physical = '{self._escape_sql(data.source_tables_physical)}'")
                if data.source_columns is not None:
                    set_parts.append(f"source_columns = '{self._escape_sql(data.source_columns)}'")
                if data.source_columns_physical is not None:
                    set_parts.append(f"source_columns_physical = '{self._escape_sql(data.source_columns_physical)}'")
                if data.source_descriptions is not None:
                    set_parts.append(f"source_descriptions = '{self._escape_sql(data.source_descriptions)}'")
                if data.source_datatypes is not None:
                    set_parts.append(f"source_datatypes = '{self._escape_sql(data.source_datatypes)}'")
                if data.source_domain is not None:
                    set_parts.append(f"source_domain = '{self._escape_sql(data.source_domain)}'")
                if data.source_relationship_type is not None:
                    set_parts.append(f"source_relationship_type = '{data.source_relationship_type}'")
                if data.transformations_applied is not None:
                    set_parts.append(f"transformations_applied = '{self._escape_sql(data.transformations_applied)}'")
                if data.ai_reasoning is not None:
                    set_parts.append(f"ai_reasoning = '{self._escape_sql(data.ai_reasoning)}'")
                if data.ai_generated is not None:
                    set_parts.append(f"ai_generated = {str(data.ai_generated).lower()}")
                if data.mapping_status is not None:
                    set_parts.append(f"mapping_status = '{data.mapping_status}'")
                if data.updated_by is not None:
                    set_parts.append(f"updated_by = '{self._escape_sql(data.updated_by)}'")
                
                # Always update timestamp
                set_parts.append("updated_ts = CURRENT_TIMESTAMP()")
                
                if not set_parts:
                    return {"message": "No fields to update"}
                
                # Note: source_semantic_field is a generated column in the database
                # It auto-updates based on source_tables, source_columns, etc.
                # No need to explicitly update it here
                
                set_clause = ", ".join(set_parts)
                
                update_sql = f"""
                    UPDATE {mapped_fields_table}
                    SET {set_clause}
                    WHERE mapped_field_id = {mapping_id}
                """
                
                cursor.execute(update_sql)
                
                return {
                    "mapping_id": mapping_id,
                    "message": "Mapping updated successfully"
                }
                
        finally:
            connection.close()
    
    async def update_mapping(
        self,
        mapping_id: int,
        data: MappedFieldUpdateV3
    ) -> Dict[str, Any]:
        """
        Update a mapping (async wrapper).
        
        After updating, syncs the vector search index if source_semantic_field
        was modified to keep AI pattern matching current.
        """
        db_config = self._get_db_config()
        vs_config = self._get_vector_search_config()
        loop = asyncio.get_event_loop()
        
        # Update the mapping
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._update_mapping_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["mapped_fields_table"],
                mapping_id,
                data
            )
        )
        
        # Sync vector search index if source info changed (best-effort)
        # The _update_mapping_sync rebuilds source_semantic_field when source info changes
        if any([data.source_tables, data.source_tables_physical, data.source_columns, 
                data.source_columns_physical, data.source_descriptions, data.transformations_applied]):
            try:
                await loop.run_in_executor(
                    executor,
                    functools.partial(
                        self._sync_vector_search_index,
                        vs_config["mapped_fields_index"]
                    )
                )
            except Exception as e:
                print(f"[Mapping Service V3] VS sync failed (non-fatal): {e}")
        
        return result
    
    # =========================================================================
    # DELETE MAPPING
    # =========================================================================
    
    def _delete_mapping_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapped_fields_table: str,
        unmapped_fields_table: str,
        mapping_id: int,
        restore_to_unmapped: bool = False
    ) -> Dict[str, Any]:
        """Delete a mapping (synchronous)."""
        print(f"[Mapping Service V3] Deleting mapping ID: {mapping_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Optionally restore source fields to unmapped
                if restore_to_unmapped:
                    # Get the mapping's full source info including physical names, mapped_by and domain
                    cursor.execute(f"""
                        SELECT 
                            source_tables, 
                            source_tables_physical,
                            source_columns, 
                            source_columns_physical,
                            source_datatypes, 
                            source_descriptions,
                            mapped_by,
                            source_domain
                        FROM {mapped_fields_table}
                        WHERE mapped_field_id = {mapping_id}
                    """)
                    row = cursor.fetchone()
                    
                    if row and row[0] and row[2]:  # source_tables and source_columns
                        # Helper to parse pipe or comma delimited strings
                        def parse_delimited(val):
                            if not val:
                                return []
                            return [v.strip() for v in val.split(" | ")] if " | " in val else [v.strip() for v in val.split(", ")]
                        
                        # Logical names (for display)
                        tables = parse_delimited(row[0])
                        # Physical names (for database) - REQUIRED
                        tables_physical = parse_delimited(row[1]) if row[1] else []
                        # Logical column names
                        columns = parse_delimited(row[2])
                        # Physical column names - REQUIRED
                        columns_physical = parse_delimited(row[3]) if row[3] else []
                        # Data types
                        datatypes = parse_delimited(row[4]) if row[4] else ["STRING"] * len(columns)
                        # Descriptions
                        descriptions = row[5].split(" | ") if row[5] else [""] * len(columns)
                        mapped_by = row[6] if row[6] else None
                        source_domain = row[7] if len(row) > 7 and row[7] else None
                        
                        # Infer domain from table name if not stored
                        if not source_domain and tables_physical:
                            table_lower = tables_physical[0].lower()
                            if 'member' in table_lower:
                                source_domain = 'member'
                            elif 'claim' in table_lower:
                                source_domain = 'claims'
                            elif 'provider' in table_lower:
                                source_domain = 'provider'
                            elif 'pharmacy' in table_lower or 'drug' in table_lower:
                                source_domain = 'pharmacy'
                            elif 'finance' in table_lower or 'payment' in table_lower:
                                source_domain = 'finance'
                        
                        # Skip restore if physical names not available
                        if not tables_physical or not columns_physical:
                            print(f"[Mapping Service V3] WARNING: Cannot restore - physical names not stored for mapping {mapping_id}")
                        
                        for i in range(len(columns)):
                            table = tables[min(i, len(tables)-1)]
                            table_phys = tables_physical[min(i, len(tables_physical)-1)]
                            column = columns[i]
                            column_phys = columns_physical[i] if i < len(columns_physical) else column
                            datatype = datatypes[i] if i < len(datatypes) else "STRING"
                            desc = descriptions[i] if i < len(descriptions) else ""
                            
                            insert_sql = f"""
                                INSERT INTO {unmapped_fields_table} (
                                    src_table_name,
                                    src_table_physical_name,
                                    src_column_name,
                                    src_column_physical_name,
                                    src_nullable,
                                    src_physical_datatype,
                                    src_comments,
                                    domain,
                                    uploaded_by,
                                    uploaded_at
                                ) VALUES (
                                    '{self._escape_sql(table)}',
                                    '{self._escape_sql(table_phys)}',
                                    '{self._escape_sql(column)}',
                                    '{self._escape_sql(column_phys)}',
                                    'YES',
                                    '{self._escape_sql(datatype)}',
                                    '{self._escape_sql(desc)}',
                                    {f"'{self._escape_sql(source_domain)}'" if source_domain else 'NULL'},
                                    {f"'{self._escape_sql(mapped_by)}'" if mapped_by else 'NULL'},
                                    CURRENT_TIMESTAMP()
                                )
                            """
                            cursor.execute(insert_sql)
                        
                        print(f"[Mapping Service V3] Restored {len(columns)} fields to unmapped with domain={source_domain}, uploaded_by={mapped_by}")
                
                # Delete the mapping
                delete_sql = f"""
                    DELETE FROM {mapped_fields_table}
                    WHERE mapped_field_id = {mapping_id}
                """
                cursor.execute(delete_sql)
                
                return {
                    "mapping_id": mapping_id,
                    "message": "Mapping deleted successfully"
                }
                
        finally:
            connection.close()
    
    async def delete_mapping(
        self,
        mapping_id: int,
        restore_to_unmapped: bool = False
    ) -> Dict[str, Any]:
        """Delete a mapping (async wrapper)."""
        db_config = self._get_db_config()
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            executor,
            functools.partial(
                self._delete_mapping_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["mapped_fields_table"],
                db_config["unmapped_fields_table"],
                mapping_id,
                restore_to_unmapped
            )
        )
    
    # =========================================================================
    # RECORD FEEDBACK (REJECTION)
    # =========================================================================
    
    def _record_feedback_sync(
        self,
        server_hostname: str,
        http_path: str,
        feedback_table: str,
        data: MappingFeedbackCreateV3
    ) -> Dict[str, Any]:
        """Record a rejected AI suggestion (synchronous)."""
        print(f"[Mapping Service V3] Recording feedback: {data.suggested_src_table}.{data.suggested_src_column} -> {data.suggested_tgt_table}.{data.suggested_tgt_column}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                insert_sql = f"""
                    INSERT INTO {feedback_table} (
                        suggested_src_table,
                        suggested_src_column,
                        suggested_tgt_table,
                        suggested_tgt_column,
                        src_comments,
                        src_datatype,
                        tgt_comments,
                        ai_confidence_score,
                        ai_reasoning,
                        vector_search_score,
                        suggestion_rank,
                        feedback_action,
                        user_comments,
                        modified_src_table,
                        modified_src_column,
                        modified_expression,
                        domain,
                        feedback_by
                    ) VALUES (
                        '{self._escape_sql(data.suggested_src_table)}',
                        '{self._escape_sql(data.suggested_src_column)}',
                        '{self._escape_sql(data.suggested_tgt_table)}',
                        '{self._escape_sql(data.suggested_tgt_column)}',
                        {f"'{self._escape_sql(data.src_comments)}'" if data.src_comments else 'NULL'},
                        {f"'{self._escape_sql(data.src_datatype)}'" if data.src_datatype else 'NULL'},
                        {f"'{self._escape_sql(data.tgt_comments)}'" if data.tgt_comments else 'NULL'},
                        {data.ai_confidence_score if data.ai_confidence_score is not None else 'NULL'},
                        {f"'{self._escape_sql(data.ai_reasoning)}'" if data.ai_reasoning else 'NULL'},
                        {data.vector_search_score if data.vector_search_score is not None else 'NULL'},
                        {data.suggestion_rank if data.suggestion_rank is not None else 'NULL'},
                        '{data.feedback_action}',
                        {f"'{self._escape_sql(data.user_comments)}'" if data.user_comments else 'NULL'},
                        {f"'{self._escape_sql(data.modified_src_table)}'" if data.modified_src_table else 'NULL'},
                        {f"'{self._escape_sql(data.modified_src_column)}'" if data.modified_src_column else 'NULL'},
                        {f"'{self._escape_sql(data.modified_expression)}'" if data.modified_expression else 'NULL'},
                        {f"'{self._escape_sql(data.domain)}'" if data.domain else 'NULL'},
                        {f"'{self._escape_sql(data.feedback_by)}'" if data.feedback_by else 'NULL'}
                    )
                """
                
                cursor.execute(insert_sql)
                
                return {"message": "Feedback recorded successfully"}
                
        finally:
            connection.close()
    
    async def record_feedback(self, data: MappingFeedbackCreateV3) -> Dict[str, Any]:
        """Record a rejected AI suggestion (async wrapper)."""
        db_config = self._get_db_config()
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            executor,
            functools.partial(
                self._record_feedback_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["mapping_feedback_table"],
                data
            )
        )
    
    # =========================================================================
    # GET TRANSFORMATIONS
    # =========================================================================
    
    def _get_transformations_sync(
        self,
        server_hostname: str,
        http_path: str,
        transformation_table: str
    ) -> List[Dict[str, Any]]:
        """Get transformation library (synchronous)."""
        print("[Mapping Service V3] Fetching transformations...")
        
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
                        is_system
                    FROM {transformation_table}
                    ORDER BY category, transformation_name
                """
                
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                transformations = []
                for row in rows:
                    transformations.append(dict(zip(columns, row)))
                
                print(f"[Mapping Service V3] Found {len(transformations)} transformations")
                return transformations
                
        finally:
            connection.close()
    
    async def get_transformations(self) -> List[Dict[str, Any]]:
        """Get transformation library (async wrapper)."""
        db_config = self._get_db_config()
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_transformations_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["transformation_library_table"]
            )
        )

