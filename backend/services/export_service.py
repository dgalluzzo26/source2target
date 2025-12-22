"""
Export Service for generating CSV and SQL exports of mapped fields.

Generates:
- CSV exports of mappings for a project/table
- Databricks SQL INSERT statements for target tables
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
import csv
import io
import re
from typing import Dict, Any, List, Optional
from databricks import sql
from databricks.sdk import WorkspaceClient
from backend.services.config_service import ConfigService

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=2)


class ExportService:
    """Service for exporting mappings as CSV or SQL."""
    
    def __init__(self):
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self) -> WorkspaceClient:
        """Lazy initialization of workspace client."""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
    
    def _get_db_config(self) -> Dict[str, str]:
        """Get database configuration."""
        config = self.config_service.get_config()
        db = config.database
        return {
            "server_hostname": db.server_hostname,
            "http_path": db.http_path,
            "catalog": db.catalog,
            "schema": db.schema,
            "mapped_fields_table": db.mapped_fields_table
        }
    
    def _get_sql_connection(self, server_hostname: str, http_path: str):
        """Get SQL connection with proper OAuth token handling (matches other services)."""
        # Try to get OAuth token from WorkspaceClient config
        access_token = None
        if self.workspace_client and hasattr(self.workspace_client.config, 'authenticate'):
            try:
                headers = self.workspace_client.config.authenticate()
                if headers and 'Authorization' in headers:
                    access_token = headers['Authorization'].replace('Bearer ', '')
            except Exception as e:
                print(f"[Export Service] Could not get OAuth token: {e}")
        
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
    
    def _get_mappings_sync(
        self,
        db_config: Dict[str, str],
        project_id: int,
        table_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get mappings for export (synchronous).
        
        Args:
            db_config: Database configuration
            project_id: Project ID
            table_name: Optional table physical name filter
            
        Returns:
            List of mapping dictionaries
        """
        connection = self._get_sql_connection(
            db_config["server_hostname"],
            db_config["http_path"]
        )
        
        try:
            with connection.cursor() as cursor:
                table_clause = ""
                if table_name:
                    escaped_table = table_name.replace("'", "''")
                    table_clause = f"AND UPPER(tgt_table_physical_name) = UPPER('{escaped_table}')"
                
                cursor.execute(f"""
                    SELECT 
                        mapped_field_id,
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
                        target_domain,
                        source_relationship_type,
                        transformations_applied,
                        join_metadata,
                        confidence_score,
                        mapping_source,
                        ai_reasoning,
                        mapped_by,
                        mapped_ts
                    FROM {db_config['mapped_fields_table']}
                    WHERE project_id = {project_id}
                      AND mapping_status = 'ACTIVE'
                      {table_clause}
                    ORDER BY tgt_table_physical_name, tgt_column_physical_name
                """)
                
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            print(f"[Export Service] Error getting mappings: {str(e)}")
            raise
        finally:
            connection.close()
    
    def _generate_csv_sync(
        self,
        mappings: List[Dict[str, Any]]
    ) -> str:
        """
        Generate CSV content from mappings.
        
        Args:
            mappings: List of mapping dictionaries
            
        Returns:
            CSV content as string
        """
        if not mappings:
            return ""
        
        # Define columns for export
        export_columns = [
            'tgt_table_name',
            'tgt_table_physical_name',
            'tgt_column_name',
            'tgt_column_physical_name',
            'source_expression',
            'source_tables',
            'source_tables_physical',
            'source_columns',
            'source_columns_physical',
            'source_descriptions',
            'source_datatypes',
            'source_relationship_type',
            'transformations_applied',
            'confidence_score',
            'mapping_source',
            'mapped_by',
            'mapped_ts'
        ]
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=export_columns, extrasaction='ignore')
        writer.writeheader()
        
        for mapping in mappings:
            writer.writerow(mapping)
        
        return output.getvalue()
    
    def _extract_from_clause(
        self,
        mappings: List[Dict[str, Any]]
    ) -> str:
        """
        Extract a common FROM clause from the mapping SQL expressions.
        
        Analyzes the source_expression fields to find common table references
        and build a FROM clause with JOINs.
        
        Args:
            mappings: List of mapping dictionaries
            
        Returns:
            FROM clause string
        """
        # Collect all unique table references
        all_tables = set()
        all_joins = []
        
        for mapping in mappings:
            sql_expr = mapping.get('source_expression', '')
            if not sql_expr:
                continue
            
            # Extract table references from SQL
            # Look for FROM and JOIN clauses
            from_matches = re.findall(r'FROM\s+(\$\{[^}]+\}\.[^}\s]+|\S+)', sql_expr, re.IGNORECASE)
            join_matches = re.findall(r'JOIN\s+(\$\{[^}]+\}\.[^}\s]+|\S+)', sql_expr, re.IGNORECASE)
            
            for table in from_matches + join_matches:
                # Clean up table reference
                table = table.strip().rstrip(',')
                if table:
                    all_tables.add(table)
        
        if not all_tables:
            # Fallback: use source_tables_physical from first mapping
            if mappings and mappings[0].get('source_tables_physical'):
                tables = mappings[0]['source_tables_physical'].split('|')
                return f"FROM {tables[0].strip()}"
            return "FROM <source_table>"
        
        # Build FROM clause - take first table as primary
        tables_list = sorted(all_tables)
        from_clause = f"FROM {tables_list[0]}"
        
        # Note: For complex JOINs, the user may need to adjust this
        # We're providing a starting point
        
        return from_clause
    
    def _generate_insert_sql_sync(
        self,
        mappings: List[Dict[str, Any]],
        target_catalog: str = "${TARGET_CATALOG}",
        target_schema: str = "${TARGET_SCHEMA}"
    ) -> str:
        """
        Generate Databricks SQL INSERT statement for a target table.
        
        Merges all column mappings into a single SELECT statement.
        
        Args:
            mappings: List of mapping dictionaries (should be for same table)
            target_catalog: Target catalog placeholder or name
            target_schema: Target schema placeholder or name
            
        Returns:
            INSERT INTO ... SELECT ... SQL statement
        """
        if not mappings:
            return "-- No mappings found"
        
        # Get table name from first mapping (all should be same table)
        table_physical = mappings[0].get('tgt_table_physical_name', 'unknown_table')
        table_name = mappings[0].get('tgt_table_name', table_physical)
        
        # Build column list and SELECT expressions
        columns = []
        select_expressions = []
        
        for mapping in mappings:
            col_physical = mapping.get('tgt_column_physical_name', '')
            source_expr = mapping.get('source_expression', '')
            
            if not col_physical:
                continue
            
            columns.append(col_physical)
            
            # Clean up source expression
            # If it's a full SELECT statement, extract just the column expression
            if source_expr:
                # Check if it's a simple SELECT
                select_match = re.match(r'^\s*SELECT\s+(.+?)\s+AS\s+\w+\s+FROM', source_expr, re.IGNORECASE | re.DOTALL)
                if select_match:
                    # Extract the expression before AS
                    expr = select_match.group(1).strip()
                    select_expressions.append(f"  {expr} AS {col_physical}")
                else:
                    # Use as-is (might be a complex expression)
                    # Try to extract first SELECT expression
                    simple_match = re.match(r'^\s*SELECT\s+DISTINCT\s+(.+?)\s+AS\s+\w+', source_expr, re.IGNORECASE | re.DOTALL)
                    if simple_match:
                        expr = simple_match.group(1).strip()
                        select_expressions.append(f"  {expr} AS {col_physical}")
                    else:
                        # Use a placeholder for complex expressions
                        select_expressions.append(f"  /* Complex: {col_physical} */ NULL AS {col_physical}")
            else:
                select_expressions.append(f"  NULL AS {col_physical}  -- No mapping defined")
        
        # Build FROM clause
        from_clause = self._extract_from_clause(mappings)
        
        # Generate the INSERT statement
        column_list = ',\n  '.join(columns)
        select_list = ',\n'.join(select_expressions)
        
        sql = f"""-- ============================================================================
-- Generated INSERT statement for: {table_name}
-- Table: {target_catalog}.{target_schema}.{table_physical}
-- Generated from {len(mappings)} column mappings
-- ============================================================================

INSERT INTO {target_catalog}.{target_schema}.{table_physical} (
  {column_list}
)
SELECT
{select_list}
{from_clause}
-- NOTE: Add WHERE clause and JOIN conditions as needed
-- Review complex expressions marked with /* Complex: */ comments
;
"""
        
        return sql
    
    async def export_csv(
        self,
        project_id: int,
        table_name: Optional[str] = None
    ) -> str:
        """
        Export mappings as CSV.
        
        Args:
            project_id: Project ID
            table_name: Optional table filter
            
        Returns:
            CSV content string
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        
        # Get mappings
        mappings = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_mappings_sync,
                db_config,
                project_id,
                table_name
            )
        )
        
        # Generate CSV
        csv_content = self._generate_csv_sync(mappings)
        
        return csv_content
    
    async def export_sql(
        self,
        project_id: int,
        table_name: str,
        target_catalog: str = "${TARGET_CATALOG}",
        target_schema: str = "${TARGET_SCHEMA}"
    ) -> str:
        """
        Export mappings as Databricks SQL INSERT statement.
        
        Args:
            project_id: Project ID
            table_name: Target table physical name
            target_catalog: Target catalog (placeholder or actual)
            target_schema: Target schema (placeholder or actual)
            
        Returns:
            SQL INSERT statement string
        """
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        
        # Get mappings for specific table
        mappings = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_mappings_sync,
                db_config,
                project_id,
                table_name
            )
        )
        
        # Generate SQL
        sql_content = self._generate_insert_sql_sync(
            mappings,
            target_catalog,
            target_schema
        )
        
        return sql_content
    
    async def get_mapped_tables(
        self,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get list of tables with mappings for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of table info dictionaries
        """
        db_config = self._get_db_config()
        
        connection = self._get_sql_connection(
            db_config["server_hostname"],
            db_config["http_path"]
        )
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT 
                        tgt_table_name,
                        tgt_table_physical_name,
                        COUNT(*) as column_count
                    FROM {db_config['mapped_fields_table']}
                    WHERE project_id = {project_id}
                      AND mapping_status = 'ACTIVE'
                    GROUP BY tgt_table_name, tgt_table_physical_name
                    ORDER BY tgt_table_name
                """)
                
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            print(f"[Export Service] Error getting mapped tables: {str(e)}")
            raise
        finally:
            connection.close()

