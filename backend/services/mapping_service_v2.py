"""
Mapping service V2 for multi-field mapping CRUD operations.

Manages the complete lifecycle of multi-field mappings:
- Creating mappings (mapped_fields + mapping_details)
- Reading mappings with all source fields
- Updating mappings (concat strategy, transformations, etc.)
- Deleting mappings
- Moving fields from unmapped_fields to mapped state
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import List, Dict, Any, Optional
from databricks import sql
from databricks.sdk import WorkspaceClient
from backend.models.mapping_v2 import (
    MappedFieldV2,
    MappedFieldCreateV2,
    MappingDetailV2,
    MappingDetailCreateV2,
    MappingJoinCreateV2
)
from backend.services.config_service import ConfigService

# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=3)


class MappingServiceV2:
    """Service for managing multi-field mappings (V2 schema)."""
    
    def __init__(self):
        """Initialize the mapping service V2."""
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self):
        """Lazy initialization of WorkspaceClient."""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
    
    def _get_db_config(self) -> Dict[str, str]:
        """Get database configuration for V2 tables."""
        config = self.config_service.get_config()
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "mapped_fields_table": self.config_service.get_fully_qualified_table_name(config.database.mapped_fields_table),
            "mapping_details_table": self.config_service.get_fully_qualified_table_name(config.database.mapping_details_table),
            "mapping_joins_table": self.config_service.get_fully_qualified_table_name(config.database.mapping_joins_table),
            "unmapped_fields_table": self.config_service.get_fully_qualified_table_name(config.database.unmapped_fields_table)
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
                print(f"[Mapping Service V2] Could not get OAuth token: {e}")
        
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
    
    def _create_mapping_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapped_fields_table: str,
        mapping_details_table: str,
        mapping_joins_table: str,
        unmapped_fields_table: str,
        mapped_field_data: MappedFieldCreateV2,
        mapping_details: List[MappingDetailCreateV2],
        mapping_joins: List[MappingJoinCreateV2]
    ) -> Dict[str, Any]:
        """
        Create a complete multi-field mapping (synchronous).
        
        Transaction workflow:
        1. Insert into mapped_fields (get mapping_id)
        2. Insert all mapping_details records
        3. Insert all mapping_joins records (if any)
        4. Delete source fields from unmapped_fields
        5. Commit transaction
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            mapped_fields_table: Fully qualified mapped_fields table name
            mapping_details_table: Fully qualified mapping_details table name
            mapping_joins_table: Fully qualified mapping_joins table name
            unmapped_fields_table: Fully qualified unmapped_fields table name
            mapped_field_data: Mapped field data (target field info)
            mapping_details: List of mapping detail data (source fields)
            mapping_joins: List of join definitions
        
        Returns:
            Dictionary with mapping_id and success message
        """
        print(f"[Mapping Service V2] Creating mapping: {mapped_field_data.tgt_table_name}.{mapped_field_data.tgt_column_name}")
        print(f"[Mapping Service V2] Source fields: {len(mapping_details)}")
        print(f"[Mapping Service V2] Join conditions: {len(mapping_joins)}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Step 1: Insert into mapped_fields
                mapped_insert = f"""
                INSERT INTO {mapped_fields_table} (
                    semantic_field_id,
                    tgt_table_name,
                    tgt_table_physical_name,
                    tgt_column_name,
                    tgt_column_physical_name,
                    concat_strategy,
                    concat_separator,
                    transformation_expression,
                    mapped_by,
                    confidence_score,
                    mapping_source,
                    ai_reasoning,
                    mapping_status
                ) VALUES (
                    {mapped_field_data.semantic_field_id},
                    '{mapped_field_data.tgt_table_name.replace("'", "''")}',
                    '{mapped_field_data.tgt_table_physical_name.replace("'", "''")}',
                    '{mapped_field_data.tgt_column_name.replace("'", "''")}',
                    '{mapped_field_data.tgt_column_physical_name.replace("'", "''")}',
                    '{mapped_field_data.concat_strategy}',
                    {'NULL' if not mapped_field_data.concat_separator else "'" + mapped_field_data.concat_separator.replace("'", "''") + "'"},
                    {'NULL' if not mapped_field_data.transformation_expression else "'" + mapped_field_data.transformation_expression.replace("'", "''") + "'"},
                    {'NULL' if not mapped_field_data.mapped_by else "'" + mapped_field_data.mapped_by.replace("'", "''") + "'"},
                    {mapped_field_data.confidence_score if mapped_field_data.confidence_score else 'NULL'},
                    {'NULL' if not mapped_field_data.mapping_source else "'" + mapped_field_data.mapping_source.replace("'", "''") + "'"},
                    {'NULL' if not mapped_field_data.ai_reasoning else "'" + mapped_field_data.ai_reasoning.replace("'", "''") + "'"},
                    {'NULL' if not mapped_field_data.mapping_status else "'" + mapped_field_data.mapping_status.replace("'", "''") + "'"}
                )
                """
                
                cursor.execute(mapped_insert)
                
                # Get the generated mapped_field_id
                cursor.execute(f"SELECT MAX(mapped_field_id) FROM {mapped_fields_table}")
                mapped_field_id = cursor.fetchone()[0]
                
                print(f"[Mapping Service V2] Created mapped_field with mapped_field_id: {mapped_field_id}")
                
                # Step 2: Insert all mapping_details
                for detail in mapping_details:
                    detail_insert = f"""
                    INSERT INTO {mapping_details_table} (
                        mapped_field_id,
                        src_table_name,
                        src_column_name,
                        src_column_physical_name,
                        field_order,
                        transformations
                    ) VALUES (
                        {mapped_field_id},
                        '{detail.src_table_name.replace("'", "''")}',
                        '{detail.src_column_name.replace("'", "''")}',
                        '{detail.src_column_physical_name.replace("'", "''")}',
                        {detail.field_order},
                        {'NULL' if not detail.transformation_expr else "'" + detail.transformation_expr.replace("'", "''") + "'"}
                    )
                    """
                    
                    cursor.execute(detail_insert)
                
                print(f"[Mapping Service V2] Inserted {len(mapping_details)} mapping details")
                
                # Step 3: Insert all mapping_joins (if any)
                if mapping_joins:
                    for join in mapping_joins:
                        join_insert = f"""
                        INSERT INTO {mapping_joins_table} (
                            mapped_field_id,
                            left_table_name,
                            left_table_physical_name,
                            left_join_column,
                            right_table_name,
                            right_table_physical_name,
                            right_join_column,
                            join_type,
                            join_order
                        ) VALUES (
                            {mapped_field_id},
                            '{join.left_table_name.replace("'", "''")}',
                            '{join.left_table_physical_name.replace("'", "''")}',
                            '{join.left_join_column.replace("'", "''")}',
                            '{join.right_table_name.replace("'", "''")}',
                            '{join.right_table_physical_name.replace("'", "''")}',
                            '{join.right_join_column.replace("'", "''")}',
                            '{join.join_type}',
                            {join.join_order}
                        )
                        """
                        
                        cursor.execute(join_insert)
                    
                    print(f"[Mapping Service V2] Inserted {len(mapping_joins)} join conditions")
                
                # Step 4: Delete source fields from unmapped_fields
                for detail in mapping_details:
                    delete_unmapped = f"""
                    DELETE FROM {unmapped_fields_table}
                    WHERE src_table_physical_name = '{detail.src_table_physical_name.replace("'", "''")}'
                      AND src_column_physical_name = '{detail.src_column_physical_name.replace("'", "''")}'
                    """
                    
                    cursor.execute(delete_unmapped)
                
                print(f"[Mapping Service V2] Removed {len(mapping_details)} fields from unmapped_fields")
                
                # Commit transaction
                connection.commit()
                
                print(f"[Mapping Service V2] Mapping created successfully")
                
                return {
                    "mapping_id": mapped_field_id,
                    "status": "success",
                    "message": f"Created mapping with {len(mapping_details)} source fields"
                }
                
        except Exception as e:
            print(f"[Mapping Service V2] Error creating mapping: {str(e)}")
            connection.rollback()
            raise
        finally:
            connection.close()
    
    def _get_all_mappings_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapped_fields_table: str,
        mapping_details_table: str,
        mapping_joins_table: str,
        user_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all mappings with their source fields and joins (synchronous).
        
        Returns a list of mappings where each mapping includes:
        - Target field info (from mapped_fields)
        - List of source fields (from mapping_details)
        - List of join conditions (from mapping_joins)
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            mapped_fields_table: Fully qualified mapped_fields table name
            mapping_details_table: Fully qualified mapping_details table name
            mapping_joins_table: Fully qualified mapping_joins table name
            user_filter: Optional email filter (None for admins to see all)
        
        Returns:
            List of mapping dictionaries with nested source_fields and mapping_joins
        """
        if user_filter:
            print(f"[Mapping Service V2] Fetching mappings for user: {user_filter}")
        else:
            print(f"[Mapping Service V2] Fetching all mappings (admin mode)")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Build WHERE clause for user filtering
                where_clause = ""
                if user_filter:
                    escaped_email = user_filter.replace("'", "''")
                    where_clause = f"WHERE mf.mapped_by = '{escaped_email}'"
                
                # Query all mappings with their details
                query = f"""
                SELECT 
                    mf.mapped_field_id,
                    mf.semantic_field_id,
                    mf.tgt_table_name,
                    mf.tgt_table_physical_name,
                    mf.tgt_column_name,
                    mf.tgt_column_physical_name,
                    mf.concat_strategy,
                    mf.concat_separator,
                    mf.transformation_expression,
                    mf.mapped_ts as mapped_at,
                    mf.mapped_by,
                    mf.confidence_score,
                    mf.mapping_source,
                    mf.ai_reasoning,
                    mf.mapping_status,
                    md.mapping_detail_id as detail_id,
                    md.src_table_name,
                    md.src_column_name,
                    md.src_column_physical_name,
                    md.field_order,
                    md.transformations as transformation_expr,
                    md.created_ts as added_at
                FROM {mapped_fields_table} mf
                LEFT JOIN {mapping_details_table} md ON mf.mapped_field_id = md.mapped_field_id
                {where_clause}
                ORDER BY mf.mapped_field_id, md.field_order
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                # Group by mapped_field_id
                mappings_dict = {}
                for row in rows:
                    record = dict(zip(columns, row))
                    mapping_id = record['mapped_field_id']
                    
                    if mapping_id not in mappings_dict:
                        # Create mapping entry
                        mappings_dict[mapping_id] = {
                            'mapping_id': mapping_id,
                            'semantic_field_id': record['semantic_field_id'],
                            'tgt_table_name': record['tgt_table_name'],
                            'tgt_table_physical_name': record['tgt_table_physical_name'],
                            'tgt_column_name': record['tgt_column_name'],
                            'tgt_column_physical_name': record['tgt_column_physical_name'],
                            'concat_strategy': record['concat_strategy'],
                            'concat_separator': record['concat_separator'],
                            'transformation_expression': record['transformation_expression'],
                            'mapped_at': record['mapped_at'],
                            'mapped_by': record['mapped_by'],
                            'confidence_score': record['confidence_score'],
                            'mapping_source': record['mapping_source'],
                            'ai_reasoning': record['ai_reasoning'],
                            'mapping_status': record['mapping_status'],
                            'source_fields': []
                        }
                    
                    # Add source field detail
                    if record['detail_id'] is not None:
                        mappings_dict[mapping_id]['source_fields'].append({
                            'detail_id': record['detail_id'],
                            'src_table_name': record['src_table_name'],
                            'src_column_name': record['src_column_name'],
                            'src_column_physical_name': record['src_column_physical_name'],
                            'field_order': record['field_order'],
                            'transformation_expr': record['transformation_expr'],
                            'added_at': record['added_at']
                        })
                
                # Fetch joins for each mapping (from mapping_joins table)
                for mapping_id, mapping_data in mappings_dict.items():
                    join_query = f"""
                    SELECT 
                        mapping_join_id,
                        left_table_name,
                        left_table_physical_name,
                        left_join_column,
                        right_table_name,
                        right_table_physical_name,
                        right_join_column,
                        join_type,
                        join_order
                    FROM {mapping_joins_table}
                    WHERE mapped_field_id = {mapping_id}
                    ORDER BY join_order
                    """
                    
                    cursor.execute(join_query)
                    join_rows = cursor.fetchall()
                    join_columns = [desc[0] for desc in cursor.description]
                    
                    mapping_data['mapping_joins'] = [
                        dict(zip(join_columns, join_row))
                        for join_row in join_rows
                    ]
                
                result = list(mappings_dict.values())
                print(f"[Mapping Service V2] Found {len(result)} mappings")
                return result
                
        except Exception as e:
            print(f"[Mapping Service V2] Error fetching mappings: {str(e)}")
            raise
        finally:
            connection.close()
    
    def _delete_mapping_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapped_fields_table: str,
        mapping_details_table: str,
        mapping_joins_table: str,
        unmapped_fields_table: str,
        mapped_field_id: int
    ) -> Dict[str, str]:
        """
        Delete a mapping and restore source fields to unmapped (synchronous).
        
        Transaction workflow:
        1. Get all source fields from mapping_details
        2. Delete from mapping_joins (if any)
        3. Delete from mapping_details
        4. Delete from mapped_fields
        5. Commit transaction
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            mapped_fields_table: Fully qualified mapped_fields table name
            mapping_details_table: Fully qualified mapping_details table name
            mapping_joins_table: Fully qualified mapping_joins table name
            unmapped_fields_table: Fully qualified unmapped_fields table name
            mapped_field_id: ID of the mapping to delete
        
        Returns:
            Dictionary with status message
        """
        print(f"[Mapping Service V2] Deleting mapping ID: {mapped_field_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Step 1: Get source fields before deleting
                get_details = f"""
                SELECT 
                    src_table_name,
                    src_table_physical_name,
                    src_column_name,
                    src_column_physical_name
                FROM {mapping_details_table}
                WHERE mapped_field_id = {mapped_field_id}
                """
                
                cursor.execute(get_details)
                source_fields = cursor.fetchall()
                
                # Step 2: Delete from mapping_joins (if any)
                delete_joins = f"DELETE FROM {mapping_joins_table} WHERE mapped_field_id = {mapped_field_id}"
                cursor.execute(delete_joins)
                
                # Step 3: Delete from mapping_details
                delete_details = f"DELETE FROM {mapping_details_table} WHERE mapped_field_id = {mapped_field_id}"
                cursor.execute(delete_details)
                
                # Step 4: Delete from mapped_fields
                delete_mapped = f"DELETE FROM {mapped_fields_table} WHERE mapped_field_id = {mapped_field_id}"
                cursor.execute(delete_mapped)
                
                connection.commit()
                
                print(f"[Mapping Service V2] Mapping deleted successfully")
                
                return {
                    "status": "success",
                    "message": f"Deleted mapping ID {mapped_field_id} with {len(source_fields)} source fields"
                }
                
        except Exception as e:
            print(f"[Mapping Service V2] Error deleting mapping: {str(e)}")
            connection.rollback()
            raise
        finally:
            connection.close()
    
    async def create_mapping(
        self,
        mapped_field_data: MappedFieldCreateV2,
        mapping_details: List[MappingDetailCreateV2],
        mapping_joins: List[MappingJoinCreateV2] = []
    ) -> Dict[str, Any]:
        """
        Create a complete multi-field mapping (async).
        
        Args:
            mapped_field_data: Target field information
            mapping_details: List of source field details with ordering
            mapping_joins: Optional list of join conditions for multi-table mappings
        
        Returns:
            Dictionary with mapping_id and status
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            functools.partial(
                self._create_mapping_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['mapped_fields_table'],
                db_config['mapping_details_table'],
                db_config['mapping_joins_table'],
                db_config['unmapped_fields_table'],
                mapped_field_data,
                mapping_details,
                mapping_joins
            )
        )
    
    async def get_all_mappings(self, user_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all mappings with their source fields and joins (async).
        
        Args:
            user_filter: Optional email filter (None for admins to see all)
        
        Returns:
            List of mapping dictionaries with nested source_fields and mapping_joins
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_all_mappings_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['mapped_fields_table'],
                db_config['mapping_details_table'],
                db_config['mapping_joins_table'],
                user_filter
            )
        )
    
    async def delete_mapping(self, mapped_field_id: int) -> Dict[str, str]:
        """
        Delete a mapping by ID (async).
        
        Args:
            mapped_field_id: ID of the mapping to delete
        
        Returns:
            Dictionary with status message
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            functools.partial(
                self._delete_mapping_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['mapped_fields_table'],
                db_config['mapping_details_table'],
                db_config['mapping_joins_table'],
                db_config['unmapped_fields_table'],
                mapped_field_id
            )
        )
    
    def _update_mapping_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapped_fields_table: str,
        mapping_details_table: str,
        mapping_joins_table: str,
        mapping_id: int,
        concat_strategy: Optional[str],
        concat_separator: Optional[str],
        transformation_updates: Dict[int, str],
        mapping_joins: Optional[List[MappingJoinCreateV2]]
    ) -> Dict[str, Any]:
        """
        Update a mapping with restricted fields (synchronous).
        
        Only updates:
        - concat_strategy and concat_separator in mapped_fields
        - transformation_expr for specified mapping_details (by detail_id)
        - mapping_joins (replaces all existing joins)
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            mapped_fields_table: Fully qualified mapped_fields table name
            mapping_details_table: Fully qualified mapping_details table name
            mapping_joins_table: Fully qualified mapping_joins table name
            mapping_id: ID of the mapping to update
            concat_strategy: New concatenation strategy (or None to keep current)
            concat_separator: New concatenation separator (or None to keep current)
            transformation_updates: Dict mapping detail_id to new transformation_expr
            mapping_joins: New list of joins (or None to keep current)
        
        Returns:
            Dictionary with updated mapping info
        """
        print(f"[Mapping Service V2] Updating mapping ID: {mapping_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            # Start transaction
            cursor = connection.cursor()
            
            # 1. Update mapped_fields if concat strategy/separator provided
            if concat_strategy is not None or concat_separator is not None:
                updates = []
                if concat_strategy is not None:
                    updates.append(f"concat_strategy = '{concat_strategy}'")
                if concat_separator is not None:
                    sep_value = concat_separator.replace("'", "''") if concat_separator else ""
                    updates.append(f"concat_separator = '{sep_value}'")
                
                if updates:
                    update_query = f"""
                    UPDATE {mapped_fields_table}
                    SET {', '.join(updates)}
                    WHERE mapped_field_id = {mapping_id}
                    """
                    print(f"[Mapping Service V2] Updating mapped_fields: {updates}")
                    cursor.execute(update_query)
            
            # 2. Update transformations for specific source fields
            if transformation_updates:
                for detail_id, transformation_expr in transformation_updates.items():
                    expr_escaped = transformation_expr.replace("'", "''") if transformation_expr else ""
                    update_detail_query = f"""
                    UPDATE {mapping_details_table}
                    SET transformations = '{expr_escaped}'
                    WHERE mapping_detail_id = {detail_id} AND mapped_field_id = {mapping_id}
                    """
                    print(f"[Mapping Service V2] Updating transformation for mapping_detail_id {detail_id}")
                    cursor.execute(update_detail_query)
            
            # 3. Replace join conditions if provided
            if mapping_joins is not None:
                # Delete existing joins
                delete_joins_query = f"""
                DELETE FROM {mapping_joins_table}
                WHERE mapped_field_id = {mapping_id}
                """
                print(f"[Mapping Service V2] Deleting existing joins")
                cursor.execute(delete_joins_query)
                
                # Insert new joins
                if mapping_joins:
                    for join in mapping_joins:
                        insert_join_query = f"""
                        INSERT INTO {mapping_joins_table} (
                            mapped_field_id,
                            left_table_name,
                            left_table_physical_name,
                            left_join_column,
                            right_table_name,
                            right_table_physical_name,
                            right_join_column,
                            join_type,
                            join_order
                        ) VALUES (
                            {mapping_id},
                            '{join.left_table_name.replace("'", "''")}',
                            '{join.left_table_physical_name.replace("'", "''")}',
                            '{join.left_join_column.replace("'", "''")}',
                            '{join.right_table_name.replace("'", "''")}',
                            '{join.right_table_physical_name.replace("'", "''")}',
                            '{join.right_join_column.replace("'", "''")}',
                            '{join.join_type}',
                            {join.join_order}
                        )
                        """
                        print(f"[Mapping Service V2] Inserting join: {join.left_table_name}.{join.left_join_column} -> {join.right_table_name}.{join.right_join_column}")
                        cursor.execute(insert_join_query)
            
            # Commit transaction
            connection.commit()
            
            print(f"[Mapping Service V2] Mapping {mapping_id} updated successfully")
            
            return {
                "status": "success",
                "message": f"Mapping {mapping_id} updated successfully",
                "mapping_id": mapping_id,
                "updates": {
                    "concat_strategy_updated": concat_strategy is not None,
                    "transformations_updated": len(transformation_updates),
                    "joins_updated": mapping_joins is not None
                }
            }
            
        except Exception as e:
            print(f"[Mapping Service V2] Error updating mapping: {str(e)}")
            connection.rollback()
            raise
        finally:
            connection.close()
    
    async def update_mapping(
        self,
        mapping_id: int,
        concat_strategy: Optional[str] = None,
        concat_separator: Optional[str] = None,
        transformation_updates: Dict[int, str] = {},
        mapping_joins: Optional[List[MappingJoinCreateV2]] = None
    ) -> Dict[str, Any]:
        """
        Update a mapping with restricted fields (async).
        
        Args:
            mapping_id: ID of the mapping to update
            concat_strategy: New concatenation strategy (or None to keep current)
            concat_separator: New concatenation separator (or None to keep current)
            transformation_updates: Dict mapping detail_id to new transformation_expr
            mapping_joins: New list of joins (or None to keep current)
        
        Returns:
            Dictionary with updated mapping info
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            functools.partial(
                self._update_mapping_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['mapped_fields_table'],
                db_config['mapping_details_table'],
                db_config['mapping_joins_table'],
                mapping_id,
                concat_strategy,
                concat_separator,
                transformation_updates,
                mapping_joins
            )
        )

