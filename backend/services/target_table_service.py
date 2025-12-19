"""
Target table service for V4 target-first workflow.

Manages:
- Getting target tables for a project
- Getting target table details with column info
- Updating target table status
- Starting AI discovery for a table
- Getting suggestions for a table
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import List, Dict, Any, Optional
from datetime import datetime
from databricks import sql
from backend.models.project import (
    TargetTableStatus,
    TargetTableStatusUpdate,
    TargetTableProgress,
    TableMappingStatus
)
from backend.services.config_service import ConfigService

# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=3)


class TargetTableService:
    """Service for managing target tables within projects."""
    
    def __init__(self):
        """Initialize the target table service."""
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self):
        """Lazy initialization of WorkspaceClient."""
        if self._workspace_client is None:
            try:
                from databricks.sdk import WorkspaceClient
                self._workspace_client = WorkspaceClient()
            except Exception as e:
                print(f"[Target Table Service] Could not init WorkspaceClient: {e}")
        return self._workspace_client
    
    def _get_db_config(self) -> Dict[str, str]:
        """Get database configuration."""
        config = self.config_service.get_config()
        catalog = config.database.catalog
        schema = config.database.schema
        
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "projects_table": f"{catalog}.{schema}.mapping_projects",
            "target_table_status_table": f"{catalog}.{schema}.target_table_status",
            "semantic_fields_table": f"{catalog}.{schema}.semantic_fields",
            "mapping_suggestions_table": f"{catalog}.{schema}.mapping_suggestions",
            "mapped_fields_table": f"{catalog}.{schema}.mapped_fields"
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
                print(f"[Target Table Service] Could not get OAuth token: {e}")
        
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
    
    def _escape_sql(self, value: str) -> str:
        """Escape single quotes for SQL strings."""
        if value is None:
            return ""
        return value.replace("'", "''")
    
    # =========================================================================
    # GET TARGET TABLES FOR PROJECT
    # =========================================================================
    
    def _get_target_tables_sync(
        self,
        server_hostname: str,
        http_path: str,
        target_table_status_table: str,
        projects_table: str,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """Get all target tables for a project (synchronous)."""
        print(f"[Target Table Service] Fetching tables for project: {project_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                SELECT 
                    tts.target_table_status_id,
                    tts.project_id,
                    p.project_name,
                    tts.tgt_table_name,
                    tts.tgt_table_physical_name,
                    tts.tgt_table_description,
                    tts.mapping_status,
                    tts.priority,
                    tts.total_columns,
                    tts.columns_with_pattern,
                    tts.columns_mapped,
                    tts.columns_pending_review,
                    tts.columns_no_match,
                    tts.columns_skipped,
                    CASE 
                        WHEN tts.total_columns > 0 
                        THEN ROUND(tts.columns_mapped * 100.0 / tts.total_columns, 1)
                        ELSE 0 
                    END AS progress_percent,
                    tts.total_columns - tts.columns_mapped - tts.columns_skipped AS columns_remaining,
                    tts.avg_confidence,
                    tts.min_confidence,
                    CASE WHEN tts.min_confidence < 0.5 THEN true ELSE false END AS has_low_confidence,
                    CASE WHEN tts.columns_no_match > 0 THEN true ELSE false END AS has_unmatched,
                    tts.ai_job_id,
                    tts.ai_started_ts,
                    tts.ai_completed_ts,
                    tts.ai_error_message,
                    tts.user_notes,
                    tts.display_order,
                    tts.started_ts,
                    tts.completed_ts,
                    tts.updated_ts
                FROM {target_table_status_table} tts
                JOIN {projects_table} p ON tts.project_id = p.project_id
                WHERE tts.project_id = {project_id}
                ORDER BY tts.display_order, tts.tgt_table_name
                """
                
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                tables = []
                for row in rows:
                    table = dict(zip(columns, row))
                    tables.append(table)
                
                print(f"[Target Table Service] Found {len(tables)} tables")
                return tables
                
        except Exception as e:
            print(f"[Target Table Service] Error fetching tables: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_target_tables(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all target tables for a project (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_target_tables_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["target_table_status_table"],
                db_config["projects_table"],
                project_id
            )
        )
        
        return result
    
    # =========================================================================
    # GET TARGET TABLE BY ID
    # =========================================================================
    
    def _get_target_table_by_id_sync(
        self,
        server_hostname: str,
        http_path: str,
        target_table_status_table: str,
        target_table_status_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a target table by ID (synchronous)."""
        print(f"[Target Table Service] Fetching table: {target_table_status_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                SELECT *
                FROM {target_table_status_table}
                WHERE target_table_status_id = {target_table_status_id}
                """
                
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                
                if row:
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            print(f"[Target Table Service] Error fetching table: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_target_table_by_id(self, target_table_status_id: int) -> Optional[Dict[str, Any]]:
        """Get a target table by ID (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_target_table_by_id_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["target_table_status_table"],
                target_table_status_id
            )
        )
        
        return result
    
    # =========================================================================
    # GET TARGET COLUMNS FOR TABLE
    # =========================================================================
    
    def _get_target_columns_sync(
        self,
        server_hostname: str,
        http_path: str,
        semantic_fields_table: str,
        tgt_table_physical_name: str
    ) -> List[Dict[str, Any]]:
        """Get all target columns for a table from semantic_fields (synchronous)."""
        print(f"[Target Table Service] Fetching columns for table: {tgt_table_physical_name}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                SELECT 
                    semantic_field_id,
                    tgt_table_name,
                    tgt_table_physical_name,
                    tgt_column_name,
                    tgt_column_physical_name,
                    tgt_nullable,
                    tgt_physical_datatype,
                    tgt_comments,
                    domain
                FROM {semantic_fields_table}
                WHERE UPPER(tgt_table_physical_name) = UPPER('{self._escape_sql(tgt_table_physical_name)}')
                ORDER BY tgt_column_name
                """
                
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                result = []
                for row in rows:
                    result.append(dict(zip(columns, row)))
                
                print(f"[Target Table Service] Found {len(result)} columns")
                return result
                
        except Exception as e:
            print(f"[Target Table Service] Error fetching columns: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_target_columns(self, tgt_table_physical_name: str) -> List[Dict[str, Any]]:
        """Get all target columns for a table (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_target_columns_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["semantic_fields_table"],
                tgt_table_physical_name
            )
        )
        
        return result
    
    # =========================================================================
    # UPDATE TARGET TABLE STATUS
    # =========================================================================
    
    def _update_target_table_status_sync(
        self,
        server_hostname: str,
        http_path: str,
        target_table_status_table: str,
        target_table_status_id: int,
        data: TargetTableStatusUpdate
    ) -> Dict[str, Any]:
        """Update target table status (synchronous)."""
        print(f"[Target Table Service] Updating table status: {target_table_status_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Build SET clause dynamically
                set_parts = []
                
                if data.mapping_status is not None:
                    set_parts.append(f"mapping_status = '{data.mapping_status.value}'")
                if data.columns_with_pattern is not None:
                    set_parts.append(f"columns_with_pattern = {data.columns_with_pattern}")
                if data.columns_mapped is not None:
                    set_parts.append(f"columns_mapped = {data.columns_mapped}")
                if data.columns_pending_review is not None:
                    set_parts.append(f"columns_pending_review = {data.columns_pending_review}")
                if data.columns_no_match is not None:
                    set_parts.append(f"columns_no_match = {data.columns_no_match}")
                if data.columns_skipped is not None:
                    set_parts.append(f"columns_skipped = {data.columns_skipped}")
                if data.ai_job_id is not None:
                    set_parts.append(f"ai_job_id = '{self._escape_sql(data.ai_job_id)}'")
                if data.ai_started_ts is not None:
                    set_parts.append(f"ai_started_ts = '{data.ai_started_ts.isoformat()}'")
                if data.ai_completed_ts is not None:
                    set_parts.append(f"ai_completed_ts = '{data.ai_completed_ts.isoformat()}'")
                if data.ai_error_message is not None:
                    set_parts.append(f"ai_error_message = '{self._escape_sql(data.ai_error_message)}'")
                if data.avg_confidence is not None:
                    set_parts.append(f"avg_confidence = {data.avg_confidence}")
                if data.min_confidence is not None:
                    set_parts.append(f"min_confidence = {data.min_confidence}")
                if data.user_notes is not None:
                    set_parts.append(f"user_notes = '{self._escape_sql(data.user_notes)}'")
                if data.priority is not None:
                    set_parts.append(f"priority = '{data.priority.value}'")
                if data.started_by is not None:
                    set_parts.append(f"started_by = '{self._escape_sql(data.started_by)}'")
                    set_parts.append("started_ts = CURRENT_TIMESTAMP()")
                if data.completed_by is not None:
                    set_parts.append(f"completed_by = '{self._escape_sql(data.completed_by)}'")
                    set_parts.append("completed_ts = CURRENT_TIMESTAMP()")
                
                set_parts.append("updated_ts = CURRENT_TIMESTAMP()")
                
                query = f"""
                UPDATE {target_table_status_table}
                SET {', '.join(set_parts)}
                WHERE target_table_status_id = {target_table_status_id}
                """
                
                cursor.execute(query)
                
                print(f"[Target Table Service] Updated table status: {target_table_status_id}")
                return {"target_table_status_id": target_table_status_id, "status": "updated"}
                
        except Exception as e:
            print(f"[Target Table Service] Error updating table status: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def update_target_table_status(
        self, 
        target_table_status_id: int, 
        data: TargetTableStatusUpdate
    ) -> Dict[str, Any]:
        """Update target table status (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._update_target_table_status_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["target_table_status_table"],
                target_table_status_id,
                data
            )
        )
        
        return result
    
    # =========================================================================
    # GET PATTERN FOR TARGET COLUMN
    # =========================================================================
    
    def _get_pattern_for_column_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapped_fields_table: str,
        tgt_table_physical_name: str,
        tgt_column_physical_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get past mapping pattern for a target column (synchronous).
        
        Only returns approved patterns (is_approved_pattern = true).
        """
        print(f"[Target Table Service] Finding pattern for: {tgt_table_physical_name}.{tgt_column_physical_name}")
        
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
                    source_tables_physical,
                    source_columns,
                    source_columns_physical,
                    source_descriptions,
                    source_datatypes,
                    source_domain,
                    source_relationship_type,
                    transformations_applied,
                    join_metadata,
                    confidence_score,
                    ai_reasoning
                FROM {mapped_fields_table}
                WHERE UPPER(tgt_table_physical_name) = UPPER('{self._escape_sql(tgt_table_physical_name)}')
                  AND UPPER(tgt_column_physical_name) = UPPER('{self._escape_sql(tgt_column_physical_name)}')
                  AND mapping_status = 'ACTIVE'
                  AND (is_approved_pattern = true OR is_approved_pattern IS NULL)
                ORDER BY confidence_score DESC, mapped_ts DESC
                LIMIT 1
                """
                
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                
                if row:
                    pattern = dict(zip(columns, row))
                    print(f"[Target Table Service] Found pattern: {pattern.get('mapped_field_id')}")
                    return pattern
                
                print(f"[Target Table Service] No pattern found")
                return None
                
        except Exception as e:
            print(f"[Target Table Service] Error finding pattern: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_pattern_for_column(
        self, 
        tgt_table_physical_name: str, 
        tgt_column_physical_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get past mapping pattern for a target column (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_pattern_for_column_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["mapped_fields_table"],
                tgt_table_physical_name,
                tgt_column_physical_name
            )
        )
        
        return result
    
    # =========================================================================
    # RECALCULATE TABLE COUNTERS
    # =========================================================================
    
    def _recalculate_table_counters_sync(
        self,
        server_hostname: str,
        http_path: str,
        target_table_status_table: str,
        mapping_suggestions_table: str,
        target_table_status_id: int
    ) -> Dict[str, Any]:
        """
        Recalculate table counters from suggestion statuses (synchronous).
        
        Called after suggestion status changes.
        """
        print(f"[Target Table Service] Recalculating counters for table: {target_table_status_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Get counts by status
                cursor.execute(f"""
                    SELECT
                        COUNT(CASE WHEN suggestion_status IN ('APPROVED', 'EDITED') THEN 1 END) AS columns_mapped,
                        COUNT(CASE WHEN suggestion_status = 'PENDING' THEN 1 END) AS columns_pending_review,
                        COUNT(CASE WHEN suggestion_status IN ('NO_PATTERN', 'NO_MATCH') THEN 1 END) AS columns_no_match,
                        COUNT(CASE WHEN suggestion_status = 'SKIPPED' THEN 1 END) AS columns_skipped,
                        AVG(CASE WHEN confidence_score IS NOT NULL THEN confidence_score END) AS avg_confidence,
                        MIN(CASE WHEN confidence_score IS NOT NULL THEN confidence_score END) AS min_confidence
                    FROM {mapping_suggestions_table}
                    WHERE target_table_status_id = {target_table_status_id}
                """)
                
                row = cursor.fetchone()
                columns_mapped = row[0] or 0
                columns_pending = row[1] or 0
                columns_no_match = row[2] or 0
                columns_skipped = row[3] or 0
                avg_confidence = row[4]
                min_confidence = row[5]
                
                # Update table status
                cursor.execute(f"""
                    UPDATE {target_table_status_table}
                    SET
                        columns_mapped = {columns_mapped},
                        columns_pending_review = {columns_pending},
                        columns_no_match = {columns_no_match},
                        columns_skipped = {columns_skipped},
                        avg_confidence = {avg_confidence if avg_confidence else 'NULL'},
                        min_confidence = {min_confidence if min_confidence else 'NULL'},
                        updated_ts = CURRENT_TIMESTAMP()
                    WHERE target_table_status_id = {target_table_status_id}
                """)
                
                # Check if table is complete
                cursor.execute(f"""
                    SELECT total_columns FROM {target_table_status_table}
                    WHERE target_table_status_id = {target_table_status_id}
                """)
                total_row = cursor.fetchone()
                total_columns = total_row[0] if total_row else 0
                
                if columns_mapped + columns_skipped >= total_columns and total_columns > 0:
                    cursor.execute(f"""
                        UPDATE {target_table_status_table}
                        SET mapping_status = 'COMPLETE'
                        WHERE target_table_status_id = {target_table_status_id}
                    """)
                
                print(f"[Target Table Service] Updated counters: mapped={columns_mapped}, pending={columns_pending}")
                
                return {
                    "target_table_status_id": target_table_status_id,
                    "columns_mapped": columns_mapped,
                    "columns_pending_review": columns_pending,
                    "columns_no_match": columns_no_match,
                    "columns_skipped": columns_skipped,
                    "status": "counters_updated"
                }
                
        except Exception as e:
            print(f"[Target Table Service] Error recalculating counters: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def recalculate_table_counters(self, target_table_status_id: int) -> Dict[str, Any]:
        """Recalculate table counters (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._recalculate_table_counters_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["target_table_status_table"],
                db_config["mapping_suggestions_table"],
                target_table_status_id
            )
        )
        
        return result

