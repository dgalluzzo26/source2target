"""
Project service for V4 target-first workflow.

Manages:
- Creating mapping projects
- Reading project details and dashboard stats
- Updating project status and metadata
- Initializing target tables from semantic_fields
- Deleting projects
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal
from databricks import sql
from backend.models.project import (
    MappingProject,
    MappingProjectCreate,
    MappingProjectUpdate,
    TargetTableStatus,
    TargetTableStatusCreate,
    ProjectDashboard,
    ProjectStatus,
    TableMappingStatus
)
from backend.services.config_service import ConfigService

# Thread pool for blocking database operations
# Use more workers to handle concurrent requests
executor = ThreadPoolExecutor(max_workers=5)


class ProjectService:
    """Service for managing V4 mapping projects."""
    
    def __init__(self):
        """Initialize the project service."""
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
                print(f"[Project Service] Could not init WorkspaceClient: {e}")
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
            "unmapped_fields_table": f"{catalog}.{schema}.unmapped_fields",
            "mapping_suggestions_table": f"{catalog}.{schema}.mapping_suggestions"
        }
    
    def _get_sql_connection(self, server_hostname: str, http_path: str):
        """Get SQL connection with proper OAuth token handling (matches semantic_service)."""
        # Try to get OAuth token from WorkspaceClient config
        access_token = None
        if self.workspace_client and hasattr(self.workspace_client.config, 'authenticate'):
            try:
                headers = self.workspace_client.config.authenticate()
                if headers and 'Authorization' in headers:
                    access_token = headers['Authorization'].replace('Bearer ', '')
                    print(f"[Project Service] Using OAuth token from WorkspaceClient")
            except Exception as e:
                print(f"[Project Service] Could not get OAuth token: {e}")
        
        if access_token:
            return sql.connect(
                server_hostname=server_hostname,
                http_path=http_path,
                access_token=access_token
            )
        else:
            print(f"[Project Service] Using databricks-oauth auth type")
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
    
    def _serialize_row(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database row to JSON-serializable dict."""
        result = {}
        for key, value in row_dict.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, date):
                result[key] = value.isoformat()
            elif isinstance(value, Decimal):
                result[key] = float(value)
            elif value is None:
                result[key] = None
            else:
                result[key] = value
        return result
    
    # =========================================================================
    # CREATE PROJECT
    # =========================================================================
    
    def _create_project_sync(
        self,
        server_hostname: str,
        http_path: str,
        projects_table: str,
        data: MappingProjectCreate
    ) -> Dict[str, Any]:
        """Create a new mapping project (synchronous)."""
        print(f"[Project Service] Creating project: {data.project_name}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                INSERT INTO {projects_table} (
                    project_name,
                    project_description,
                    source_system_name,
                    source_catalogs,
                    source_schemas,
                    target_catalogs,
                    target_schemas,
                    target_domains,
                    project_status,
                    created_by,
                    created_ts
                ) VALUES (
                    '{self._escape_sql(data.project_name)}',
                    {f"'{self._escape_sql(data.project_description)}'" if data.project_description else 'NULL'},
                    {f"'{self._escape_sql(data.source_system_name)}'" if data.source_system_name else 'NULL'},
                    {f"'{self._escape_sql(data.source_catalogs)}'" if data.source_catalogs else 'NULL'},
                    {f"'{self._escape_sql(data.source_schemas)}'" if data.source_schemas else 'NULL'},
                    {f"'{self._escape_sql(data.target_catalogs)}'" if data.target_catalogs else 'NULL'},
                    {f"'{self._escape_sql(data.target_schemas)}'" if data.target_schemas else 'NULL'},
                    {f"'{self._escape_sql(data.target_domains)}'" if data.target_domains else 'NULL'},
                    'NOT_STARTED',
                    {f"'{self._escape_sql(data.created_by)}'" if data.created_by else 'NULL'},
                    CURRENT_TIMESTAMP()
                )
                """
                
                cursor.execute(query)
                
                # Get the created project ID
                cursor.execute(f"""
                    SELECT project_id FROM {projects_table}
                    WHERE project_name = '{self._escape_sql(data.project_name)}'
                    ORDER BY created_ts DESC
                    LIMIT 1
                """)
                
                result = cursor.fetchone()
                project_id = result[0] if result else None
                
                print(f"[Project Service] Created project with ID: {project_id}")
                
                return {
                    "project_id": project_id,
                    "project_name": data.project_name,
                    "status": "created"
                }
                
        except Exception as e:
            print(f"[Project Service] Error creating project: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def create_project(self, data: MappingProjectCreate) -> Dict[str, Any]:
        """Create a new mapping project (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._create_project_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["projects_table"],
                data
            )
        )
        
        return result
    
    # =========================================================================
    # GET PROJECTS (LIST)
    # =========================================================================
    
    def _get_projects_sync(
        self,
        server_hostname: str,
        http_path: str,
        projects_table: str,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all projects (synchronous)."""
        print(f"[Project Service] Fetching projects from {projects_table}...")
        
        try:
            connection = self._get_sql_connection(server_hostname, http_path)
        except Exception as e:
            print(f"[Project Service] Connection error: {str(e)}")
            # Return empty list if connection fails (e.g., local dev without Databricks)
            return []
        
        try:
            with connection.cursor() as cursor:
                # Handle NULL project_status and avoid issues with ARCHIVED filter
                where_clause = "" if include_archived else "WHERE COALESCE(project_status, 'NOT_STARTED') != 'ARCHIVED'"
                
                # Use SELECT * to avoid column name mismatches
                query = f"""
                SELECT *
                FROM {projects_table}
                {where_clause}
                ORDER BY COALESCE(created_ts, CURRENT_TIMESTAMP()) DESC
                """
                
                print(f"[Project Service] Executing query: {query[:200]}...")
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                projects = []
                for row in rows:
                    project = dict(zip(columns, row))
                    # Ensure required fields have defaults
                    project.setdefault('total_target_tables', 0)
                    project.setdefault('tables_complete', 0)
                    project.setdefault('tables_in_progress', 0)
                    project.setdefault('total_target_columns', 0)
                    project.setdefault('columns_mapped', 0)
                    project.setdefault('columns_pending_review', 0)
                    # Serialize to JSON-safe types
                    project = self._serialize_row(project)
                    projects.append(project)
                
                print(f"[Project Service] Found {len(projects)} projects")
                return projects
                
        except Exception as e:
            print(f"[Project Service] Error fetching projects: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            connection.close()
    
    async def get_projects(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get all projects (async wrapper)."""
        db_config = self._get_db_config()
        
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    functools.partial(
                        self._get_projects_sync,
                        db_config["server_hostname"],
                        db_config["http_path"],
                        db_config["projects_table"],
                        include_archived
                    )
                ),
                timeout=60.0  # 60 seconds timeout
            )
            return result
        except asyncio.TimeoutError:
            print("[Project Service] Query timed out after 60 seconds")
            return []  # Return empty list on timeout
    
    # =========================================================================
    # GET PROJECT BY ID
    # =========================================================================
    
    def _get_project_by_id_sync(
        self,
        server_hostname: str,
        http_path: str,
        projects_table: str,
        project_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a project by ID (synchronous)."""
        print(f"[Project Service] Fetching project: {project_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                SELECT 
                    project_id,
                    project_name,
                    project_description,
                    source_system_name,
                    source_catalogs,
                    source_schemas,
                    target_catalogs,
                    target_schemas,
                    target_domains,
                    project_status,
                    total_target_tables,
                    tables_complete,
                    tables_in_progress,
                    total_target_columns,
                    columns_mapped,
                    columns_pending_review,
                    created_by,
                    created_ts,
                    updated_by,
                    updated_ts,
                    completed_by,
                    completed_ts
                FROM {projects_table}
                WHERE project_id = {project_id}
                """
                
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                
                if row:
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            print(f"[Project Service] Error fetching project: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_project_by_id(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get a project by ID (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_project_by_id_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["projects_table"],
                project_id
            )
        )
        
        return result
    
    # =========================================================================
    # UPDATE PROJECT
    # =========================================================================
    
    def _update_project_sync(
        self,
        server_hostname: str,
        http_path: str,
        projects_table: str,
        project_id: int,
        data: MappingProjectUpdate
    ) -> Dict[str, Any]:
        """Update a project (synchronous)."""
        print(f"[Project Service] Updating project: {project_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Build SET clause dynamically
                set_parts = []
                
                if data.project_name is not None:
                    set_parts.append(f"project_name = '{self._escape_sql(data.project_name)}'")
                if data.project_description is not None:
                    set_parts.append(f"project_description = '{self._escape_sql(data.project_description)}'")
                if data.source_system_name is not None:
                    set_parts.append(f"source_system_name = '{self._escape_sql(data.source_system_name)}'")
                if data.source_catalogs is not None:
                    set_parts.append(f"source_catalogs = '{self._escape_sql(data.source_catalogs)}'")
                if data.source_schemas is not None:
                    set_parts.append(f"source_schemas = '{self._escape_sql(data.source_schemas)}'")
                if data.target_catalogs is not None:
                    set_parts.append(f"target_catalogs = '{self._escape_sql(data.target_catalogs)}'")
                if data.target_schemas is not None:
                    set_parts.append(f"target_schemas = '{self._escape_sql(data.target_schemas)}'")
                if data.target_domains is not None:
                    set_parts.append(f"target_domains = '{self._escape_sql(data.target_domains)}'")
                if data.project_status is not None:
                    set_parts.append(f"project_status = '{data.project_status.value}'")
                if data.updated_by is not None:
                    set_parts.append(f"updated_by = '{self._escape_sql(data.updated_by)}'")
                
                set_parts.append("updated_ts = CURRENT_TIMESTAMP()")
                
                if not set_parts:
                    return {"project_id": project_id, "status": "no_changes"}
                
                query = f"""
                UPDATE {projects_table}
                SET {', '.join(set_parts)}
                WHERE project_id = {project_id}
                """
                
                cursor.execute(query)
                
                print(f"[Project Service] Updated project: {project_id}")
                return {"project_id": project_id, "status": "updated"}
                
        except Exception as e:
            print(f"[Project Service] Error updating project: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def update_project(self, project_id: int, data: MappingProjectUpdate) -> Dict[str, Any]:
        """Update a project (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._update_project_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["projects_table"],
                project_id,
                data
            )
        )
        
        return result
    
    # =========================================================================
    # INITIALIZE TARGET TABLES FOR PROJECT
    # =========================================================================
    
    def _initialize_target_tables_sync(
        self,
        server_hostname: str,
        http_path: str,
        projects_table: str,
        target_table_status_table: str,
        semantic_fields_table: str,
        project_id: int,
        domain_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initialize target tables for a project from semantic_fields.
        
        Creates a target_table_status row for each unique target table.
        """
        print(f"[Project Service] Initializing target tables for project: {project_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Build domain filter
                where_clause = ""
                if domain_filter:
                    # Support pipe-separated domains
                    domains = domain_filter.split("|")
                    domain_conditions = [f"domain = '{self._escape_sql(d.strip())}'" for d in domains]
                    where_clause = f"WHERE ({' OR '.join(domain_conditions)})"
                
                # Insert target table status rows grouped by table
                query = f"""
                INSERT INTO {target_table_status_table} (
                    project_id,
                    tgt_table_name,
                    tgt_table_physical_name,
                    tgt_table_description,
                    mapping_status,
                    total_columns,
                    display_order,
                    created_ts
                )
                SELECT 
                    {project_id} AS project_id,
                    tgt_table_name,
                    tgt_table_physical_name,
                    MIN(tgt_comments) AS tgt_table_description,
                    'NOT_STARTED' AS mapping_status,
                    COUNT(*) AS total_columns,
                    ROW_NUMBER() OVER (ORDER BY tgt_table_name) AS display_order,
                    CURRENT_TIMESTAMP() AS created_ts
                FROM {semantic_fields_table}
                {where_clause}
                GROUP BY tgt_table_name, tgt_table_physical_name
                ORDER BY tgt_table_name
                """
                
                cursor.execute(query)
                
                # Get counts
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) AS table_count,
                        SUM(total_columns) AS column_count
                    FROM {target_table_status_table}
                    WHERE project_id = {project_id}
                """)
                
                counts = cursor.fetchone()
                table_count = counts[0] if counts else 0
                column_count = counts[1] if counts else 0
                
                # Update project counters
                cursor.execute(f"""
                    UPDATE {projects_table}
                    SET 
                        total_target_tables = {table_count},
                        total_target_columns = {column_count},
                        project_status = 'IN_PROGRESS',
                        updated_ts = CURRENT_TIMESTAMP()
                    WHERE project_id = {project_id}
                """)
                
                print(f"[Project Service] Initialized {table_count} tables with {column_count} columns")
                
                return {
                    "project_id": project_id,
                    "tables_initialized": table_count,
                    "columns_total": column_count,
                    "status": "initialized"
                }
                
        except Exception as e:
            print(f"[Project Service] Error initializing target tables: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def initialize_target_tables(
        self, 
        project_id: int, 
        domain_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initialize target tables for a project (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._initialize_target_tables_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["projects_table"],
                db_config["target_table_status_table"],
                db_config["semantic_fields_table"],
                project_id,
                domain_filter
            )
        )
        
        return result
    
    # =========================================================================
    # UPDATE PROJECT COUNTERS
    # =========================================================================
    
    def _update_project_counters_sync(
        self,
        server_hostname: str,
        http_path: str,
        projects_table: str,
        target_table_status_table: str,
        project_id: int
    ) -> Dict[str, Any]:
        """
        Recalculate and update project counters from target_table_status.
        
        Called after table status changes.
        """
        print(f"[Project Service] Updating counters for project: {project_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Calculate aggregate stats
                query = f"""
                UPDATE {projects_table}
                SET
                    tables_complete = (
                        SELECT COUNT(*) FROM {target_table_status_table} 
                        WHERE project_id = {project_id} AND mapping_status = 'COMPLETE'
                    ),
                    tables_in_progress = (
                        SELECT COUNT(*) FROM {target_table_status_table} 
                        WHERE project_id = {project_id} AND mapping_status IN ('DISCOVERING', 'SUGGESTIONS_READY', 'IN_PROGRESS')
                    ),
                    columns_mapped = (
                        SELECT COALESCE(SUM(columns_mapped), 0) FROM {target_table_status_table} 
                        WHERE project_id = {project_id}
                    ),
                    columns_pending_review = (
                        SELECT COALESCE(SUM(columns_pending_review), 0) FROM {target_table_status_table} 
                        WHERE project_id = {project_id}
                    ),
                    updated_ts = CURRENT_TIMESTAMP()
                WHERE project_id = {project_id}
                """
                
                cursor.execute(query)
                
                print(f"[Project Service] Updated counters for project: {project_id}")
                return {"project_id": project_id, "status": "counters_updated"}
                
        except Exception as e:
            print(f"[Project Service] Error updating counters: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def update_project_counters(self, project_id: int) -> Dict[str, Any]:
        """Update project counters (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._update_project_counters_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["projects_table"],
                db_config["target_table_status_table"],
                project_id
            )
        )
        
        return result
    
    # =========================================================================
    # DELETE PROJECT
    # =========================================================================
    
    def _delete_project_sync(
        self,
        server_hostname: str,
        http_path: str,
        projects_table: str,
        target_table_status_table: str,
        mapping_suggestions_table: str,
        unmapped_fields_table: str,
        project_id: int
    ) -> Dict[str, Any]:
        """
        Delete a project and all related data.
        
        Deletes: target_table_status, mapping_suggestions
        Updates: unmapped_fields (sets project_id to NULL)
        """
        print(f"[Project Service] Deleting project: {project_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Delete suggestions
                cursor.execute(f"""
                    DELETE FROM {mapping_suggestions_table}
                    WHERE project_id = {project_id}
                """)
                
                # Delete target table status
                cursor.execute(f"""
                    DELETE FROM {target_table_status_table}
                    WHERE project_id = {project_id}
                """)
                
                # Unlink source fields (don't delete, just unlink)
                cursor.execute(f"""
                    UPDATE {unmapped_fields_table}
                    SET project_id = NULL
                    WHERE project_id = {project_id}
                """)
                
                # Delete project
                cursor.execute(f"""
                    DELETE FROM {projects_table}
                    WHERE project_id = {project_id}
                """)
                
                print(f"[Project Service] Deleted project: {project_id}")
                return {"project_id": project_id, "status": "deleted"}
                
        except Exception as e:
            print(f"[Project Service] Error deleting project: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def delete_project(self, project_id: int) -> Dict[str, Any]:
        """Delete a project (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._delete_project_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["projects_table"],
                db_config["target_table_status_table"],
                db_config["mapping_suggestions_table"],
                db_config["unmapped_fields_table"],
                project_id
            )
        )
        
        return result

