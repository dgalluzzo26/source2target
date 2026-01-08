"""
Export Service for generating CSV and SQL exports of mapped fields.

Generates:
- CSV exports of mappings for a project/table
- Databricks SQL INSERT statements for target tables

SQL Generation Strategy:
- Group mappings by source structure (same tables, joins, where clauses)
- Create a CTE for each group containing all columns from that group
- Join CTEs together on the silver table key (SRC_KEY_ID)
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
import csv
import io
import re
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from databricks import sql
from databricks.sdk import WorkspaceClient
from backend.services.config_service import config_service

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=2)


class ExportService:
    """Service for exporting mappings as CSV or SQL."""
    
    def __init__(self):
        self.config_service = config_service  # Use global instance for shared config
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
    
    # =========================================================================
    # SQL GENERATION HELPERS - Grouping and CTE Generation
    # =========================================================================
    
    def _get_structure_signature(self, mapping: Dict[str, Any]) -> str:
        """
        Create a signature for a mapping's source structure.
        Mappings with the same signature can be combined into one CTE.
        
        Uses join_metadata to identify: bronze tables, joins, where clauses
        """
        join_metadata_str = mapping.get('join_metadata', '')
        source_expression = mapping.get('source_expression', '')
        
        if join_metadata_str:
            try:
                jm = json.loads(join_metadata_str) if isinstance(join_metadata_str, str) else join_metadata_str
                
                # Extract key structural elements
                bronze_tables = []
                joins = []
                where_clauses = []
                
                # Handle union branches
                if 'unionBranches' in jm:
                    for branch in jm.get('unionBranches', []):
                        bt = branch.get('bronzeTable', {})
                        if bt.get('physicalName'):
                            bronze_tables.append(bt['physicalName'].upper())
                        for j in branch.get('joins', []):
                            joins.append(f"{j.get('type', '')}:{j.get('toTable', '')}:{j.get('onCondition', '')}")
                        if branch.get('whereClause'):
                            where_clauses.append(branch['whereClause'])
                
                # Single table case
                if 'bronzeTable' in jm and not bronze_tables:
                    bt = jm['bronzeTable']
                    if isinstance(bt, dict) and bt.get('physicalName'):
                        bronze_tables.append(bt['physicalName'].upper())
                    elif isinstance(bt, str):
                        bronze_tables.append(bt.upper())
                
                # Create signature from sorted components
                sig_parts = [
                    'TABLES:' + ','.join(sorted(bronze_tables)),
                    'JOINS:' + '|'.join(sorted(joins)),
                    'WHERE:' + '|'.join(sorted(where_clauses))
                ]
                signature = '::'.join(sig_parts)
                
                # Return hash for cleaner comparison
                return hashlib.md5(signature.encode()).hexdigest()[:12]
                
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Fallback: extract structure from SQL itself
        if source_expression:
            # Normalize and extract FROM/JOIN/WHERE parts
            sql_upper = source_expression.upper()
            
            # Extract FROM table
            from_match = re.search(r'FROM\s+(\S+)', sql_upper)
            from_table = from_match.group(1) if from_match else ''
            
            # Extract JOINs (simplified)
            join_matches = re.findall(r'((?:LEFT|RIGHT|INNER|FULL)?\s*JOIN\s+\S+\s+\w+\s+ON\s+[^WHERE]+)', sql_upper)
            joins_str = '|'.join(sorted(join_matches))
            
            # Extract WHERE
            where_match = re.search(r'WHERE\s+(.+?)(?:GROUP|ORDER|UNION|$)', sql_upper, re.DOTALL)
            where_str = where_match.group(1).strip() if where_match else ''
            
            signature = f"FROM:{from_table}::JOINS:{joins_str}::WHERE:{where_str}"
            return hashlib.md5(signature.encode()).hexdigest()[:12]
        
        # No structure found - each mapping gets unique signature
        return f"unique_{mapping.get('mapped_field_id', 'unknown')}"
    
    def _extract_column_expression(self, source_expression: str, col_physical: str) -> Tuple[str, bool]:
        """
        Extract the column expression from a full SELECT statement.
        
        Returns: (expression, is_complex)
        
        Examples:
        - "SELECT INITCAP(r.NAME) AS NAME FROM ..." -> ("INITCAP(r.NAME)", False)
        - "SELECT t.COL AS COL FROM ..." -> ("t.COL", False)
        - "SELECT ... UNION SELECT ..." -> (full_sql, True)
        """
        if not source_expression:
            return "NULL /* no mapping */", True
        
        sql_str = source_expression.strip()
        
        # Handle UNION - these are complex and need their own CTE
        if 'UNION' in sql_str.upper():
            return sql_str, True
        
        # Try to extract: SELECT [DISTINCT] <expr> AS <alias> FROM ...
        # The expression can contain nested parentheses, so we need a smarter approach
        
        # First, try simple patterns
        patterns = [
            # SELECT DISTINCT expr AS alias FROM
            r'^\s*SELECT\s+DISTINCT\s+(.+?)\s+AS\s+(\w+)\s+FROM\s',
            # SELECT expr AS alias FROM  
            r'^\s*SELECT\s+(.+?)\s+AS\s+(\w+)\s+FROM\s',
            # SELECT DISTINCT expr FROM (without AS)
            r'^\s*SELECT\s+DISTINCT\s+([^\s,]+)\s+FROM\s',
            # SELECT expr FROM (without AS)
            r'^\s*SELECT\s+([^\s,]+)\s+FROM\s',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, sql_str, re.IGNORECASE | re.DOTALL)
            if match:
                expr = match.group(1).strip()
                # Make sure we didn't capture too much (e.g., multiple columns)
                if ',' not in expr or expr.count('(') > expr.count(','):
                    return expr, False
        
        # Try a more flexible approach: find the SELECT and FROM, extract between
        upper_sql = sql_str.upper()
        select_pos = upper_sql.find('SELECT')
        from_pos = upper_sql.find(' FROM ')
        
        if select_pos != -1 and from_pos != -1 and from_pos > select_pos:
            between = sql_str[select_pos + 6:from_pos].strip()
            
            # Remove DISTINCT if present
            if between.upper().startswith('DISTINCT'):
                between = between[8:].strip()
            
            # Check if it's a single expression (might have AS alias at end)
            as_match = re.match(r'^(.+?)\s+AS\s+\w+\s*$', between, re.IGNORECASE | re.DOTALL)
            if as_match:
                expr = as_match.group(1).strip()
                return expr, False
            
            # If no AS, the whole thing might be the expression
            if ',' not in between:
                return between, False
        
        # Complex expression - return the full SQL
        return sql_str, True
    
    def _extract_from_join_where(self, source_expression: str) -> Tuple[str, str, str]:
        """
        Extract FROM clause, JOINs, and WHERE clause from a SELECT statement.
        
        Returns: (from_clause, join_clause, where_clause)
        """
        if not source_expression:
            return "", "", ""
        
        sql_str = source_expression.strip()
        sql_upper = sql_str.upper()
        
        # Skip if UNION (complex)
        if 'UNION' in sql_upper:
            return "", "", ""
        
        # Find FROM position
        from_pos = sql_upper.find(' FROM ')
        if from_pos == -1:
            return "", "", ""
        
        # Get everything after FROM
        after_from = sql_str[from_pos + 6:].strip()
        
        # Find WHERE position
        where_pos = after_from.upper().find(' WHERE ')
        
        if where_pos != -1:
            from_join_part = after_from[:where_pos].strip()
            where_clause = after_from[where_pos + 7:].strip()
        else:
            from_join_part = after_from.strip()
            where_clause = ""
        
        # Split FROM table from JOINs
        join_pos = None
        for join_type in [' LEFT JOIN ', ' RIGHT JOIN ', ' INNER JOIN ', ' FULL JOIN ', ' JOIN ']:
            pos = from_join_part.upper().find(join_type)
            if pos != -1 and (join_pos is None or pos < join_pos):
                join_pos = pos
        
        if join_pos is not None:
            from_clause = from_join_part[:join_pos].strip()
            join_clause = from_join_part[join_pos:].strip()
        else:
            from_clause = from_join_part.strip()
            join_clause = ""
        
        return from_clause, join_clause, where_clause
    
    def _group_mappings_by_structure(self, mappings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group mappings by their source structure.
        
        Returns: Dict mapping signature -> list of mappings
        """
        groups: Dict[str, List[Dict[str, Any]]] = {}
        
        for mapping in mappings:
            sig = self._get_structure_signature(mapping)
            if sig not in groups:
                groups[sig] = []
            groups[sig].append(mapping)
        
        return groups
    
    def _find_silver_key_column(self, mappings: List[Dict[str, Any]]) -> str:
        """
        Find the silver table key column (e.g., SRC_KEY_ID) from mappings.
        
        Looks in join_metadata for the silver table join condition.
        """
        for mapping in mappings:
            jm_str = mapping.get('join_metadata', '')
            if jm_str:
                try:
                    jm = json.loads(jm_str) if isinstance(jm_str, str) else jm_str
                    
                    # Look for silver table join condition
                    for branch in jm.get('unionBranches', [jm]):
                        for join_info in branch.get('joins', []):
                            on_cond = join_info.get('onCondition', '')
                            # Look for pattern like "x.KEY = mf.SRC_KEY_ID"
                            match = re.search(r'=\s*\w+\.(\w+)', on_cond)
                            if match:
                                key = match.group(1).upper()
                                if 'KEY' in key or 'ID' in key:
                                    return key
                except:
                    pass
            
            # Also check source expression for silver table reference
            source_expr = mapping.get('source_expression', '')
            if source_expr and 'silver' in source_expr.lower():
                # Look for mf.SRC_KEY_ID or similar
                match = re.search(r'(\w+)\.(SRC_KEY_ID|MEMBER_ID|MBR_ID)', source_expr, re.IGNORECASE)
                if match:
                    return match.group(2).upper()
        
        return "SRC_KEY_ID"  # Default
    
    def _generate_cte_for_group(
        self,
        group_name: str,
        group_mappings: List[Dict[str, Any]],
        silver_key: str
    ) -> Tuple[str, List[str], bool]:
        """
        Generate a CTE for a group of mappings with the same structure.
        
        Returns: (cte_sql, column_names, has_complex)
        """
        if not group_mappings:
            return "", [], False
        
        # Get structure from first mapping (all should be same)
        first_mapping = group_mappings[0]
        from_clause, join_clause, where_clause = self._extract_from_join_where(
            first_mapping.get('source_expression', '')
        )
        
        # Check for complex (UNION) mappings
        has_complex = False
        complex_mappings = []
        simple_mappings = []
        
        for mapping in group_mappings:
            source_expr = mapping.get('source_expression', '')
            if 'UNION' in source_expr.upper():
                has_complex = True
                complex_mappings.append(mapping)
            else:
                simple_mappings.append(mapping)
        
        # If all complex, handle differently
        if not simple_mappings:
            return self._generate_complex_cte(group_name, complex_mappings, silver_key)
        
        # Build SELECT columns
        select_parts = []
        column_names = []
        
        # Add key column first (from silver table)
        # Try to find the silver table alias
        silver_alias = "mf"  # Default
        if join_clause:
            # Look for silver table alias in joins
            match = re.search(r'silver[^.]*\.(\w+)\s+(\w+)', join_clause, re.IGNORECASE)
            if match:
                silver_alias = match.group(2)
        
        select_parts.append(f"    {silver_alias}.{silver_key}")
        column_names.append(silver_key)
        
        # Add column expressions
        # Track columns that need separate handling
        complex_columns = []
        
        for mapping in simple_mappings:
            col_physical = mapping.get('tgt_column_physical_name', '')
            source_expr = mapping.get('source_expression', '')
            
            expr, is_complex = self._extract_column_expression(source_expr, col_physical)
            
            if is_complex:
                has_complex = True
                # Complex expressions need their original SQL preserved
                # Check if it's a scalar subquery we can inline
                if source_expr.strip().upper().startswith('SELECT') and 'UNION' not in source_expr.upper():
                    # Try to use as scalar subquery
                    select_parts.append(f"    (\n      {source_expr}\n    ) AS {col_physical}")
                else:
                    # Full complex query - needs separate CTE
                    # Add to complex list for separate handling
                    complex_columns.append((col_physical, source_expr))
                    continue  # Don't add to this CTE
            else:
                select_parts.append(f"    {expr} AS {col_physical}")
            
            column_names.append(col_physical)
        
        # Build the CTE
        select_list = ",\n".join(select_parts)
        
        cte_sql = f"{group_name} AS (\n  SELECT DISTINCT\n{select_list}\n  FROM {from_clause}"
        
        if join_clause:
            cte_sql += f"\n  {join_clause}"
        
        if where_clause:
            cte_sql += f"\n  WHERE {where_clause}"
        
        cte_sql += "\n)"
        
        return cte_sql, column_names, has_complex
    
    def _generate_complex_cte(
        self,
        group_name: str,
        mappings: List[Dict[str, Any]],
        silver_key: str
    ) -> Tuple[str, List[str], bool]:
        """
        Generate CTE for complex mappings (UNION, etc).
        
        For UNION queries, we use the original SQL directly - it already
        produces the column we need. We just need to ensure it includes
        the key column for joining.
        """
        column_names = [silver_key]
        cte_parts = []
        
        for mapping in mappings:
            col_physical = mapping.get('tgt_column_physical_name', '')
            source_expr = mapping.get('source_expression', '').strip()
            column_names.append(col_physical)
            
            if not source_expr:
                continue
            
            # The source expression IS the SQL we need
            # For UNION queries, each branch produces key + column
            # We'll use it directly as a subquery
            
            # Check if the SQL already has the silver key
            has_key = silver_key.lower() in source_expr.lower() or 'src_key_id' in source_expr.lower()
            
            if has_key:
                # SQL already includes key, use as-is
                cte_parts.append(f"  -- Column: {col_physical}\n  {source_expr}")
            else:
                # Need to add key - wrap the query
                # Try to find the silver table join to get the key
                cte_parts.append(f"  -- Column: {col_physical} (key may need adjustment)\n  {source_expr}")
        
        # For complex queries, create separate sub-CTEs for each column
        # then join them
        if len(mappings) == 1:
            # Single complex column - use its SQL directly
            source_expr = mappings[0].get('source_expression', '').strip()
            col_physical = mappings[0].get('tgt_column_physical_name', '')
            
            cte_sql = f"""{group_name} AS (
  -- Complex mapping for {col_physical}
  {source_expr}
)"""
        else:
            # Multiple complex columns - each becomes a sub-CTE
            sub_ctes = []
            for i, mapping in enumerate(mappings):
                col_physical = mapping.get('tgt_column_physical_name', '')
                source_expr = mapping.get('source_expression', '').strip()
                sub_name = f"{group_name}_col{i+1}"
                sub_ctes.append(f"{sub_name} AS (\n  -- {col_physical}\n  {source_expr}\n)")
            
            # Join sub-CTEs on the key
            cte_sql = ",\n\n".join(sub_ctes)
        
        return cte_sql, column_names, True
    
    def _generate_insert_sql_with_ctes(
        self,
        mappings: List[Dict[str, Any]],
        target_catalog: str = "${TARGET_CATALOG}",
        target_schema: str = "${TARGET_SCHEMA}"
    ) -> str:
        """
        Generate INSERT statement using grouped CTEs.
        
        Strategy:
        1. Group mappings by source structure
        2. Create CTE per group with all columns from that group
        3. Join CTEs on silver table key
        4. Generate INSERT from joined CTEs (only reference columns from CTEs that have them)
        """
        if not mappings:
            return "-- No mappings found"
        
        # Get table info
        table_physical = mappings[0].get('tgt_table_physical_name', 'unknown_table')
        table_name = mappings[0].get('tgt_table_name', table_physical)
        
        # Find silver key column
        silver_key = self._find_silver_key_column(mappings)
        
        # Group mappings by structure
        groups = self._group_mappings_by_structure(mappings)
        
        print(f"[Export Service] Grouped {len(mappings)} mappings into {len(groups)} structure groups")
        
        # Generate CTEs and track which columns are in which CTE
        ctes = []
        cte_names = []
        cte_columns: Dict[str, List[str]] = {}  # cte_name -> list of columns
        all_columns = [silver_key]  # Key column first
        has_any_complex = False
        
        for i, (sig, group_mappings) in enumerate(groups.items()):
            group_name = f"source_group_{i + 1}"
            cte_sql, columns, has_complex = self._generate_cte_for_group(
                group_name, group_mappings, silver_key
            )
            
            if cte_sql:
                ctes.append(cte_sql)
                cte_names.append(group_name)
                cte_columns[group_name] = columns
                
                # Add columns (skip key since it's already added)
                for col in columns[1:]:
                    if col not in all_columns:
                        all_columns.append(col)
                
                if has_complex:
                    has_any_complex = True
        
        # Build final SQL
        sql_parts = []
        
        # Header
        sql_parts.append(f"""-- ============================================================================
-- Generated INSERT statement for: {table_name}
-- Table: {target_catalog}.{target_schema}.{table_physical}
-- Generated from {len(mappings)} column mappings in {len(groups)} source groups
-- Silver Key Column: {silver_key}
-- ============================================================================
""")
        
        if has_any_complex:
            sql_parts.append("""-- NOTE: Some mappings contain UNION or complex logic
-- The original SQL is preserved in the CTEs
""")
        
        # CTEs
        sql_parts.append("WITH\n")
        sql_parts.append(",\n\n".join(ctes))
        
        # Final INSERT
        column_list = ",\n  ".join(all_columns)
        
        # Build SELECT from joined CTEs
        # Map CTE name to alias
        cte_alias = {name: f"g{i+1}" for i, name in enumerate(cte_names)}
        
        if len(cte_names) == 1:
            # Single CTE - simple select
            alias = cte_alias[cte_names[0]]
            select_cols = ",\n    ".join([f"{alias}.{c}" for c in all_columns])
            from_clause = f"FROM {cte_names[0]} {alias}"
        else:
            # Multiple CTEs - join them
            # For each column, only reference the CTE(s) that actually have it
            select_parts = []
            
            for col in all_columns:
                # Find which CTEs have this column
                ctes_with_col = []
                for cte_name in cte_names:
                    if col in cte_columns.get(cte_name, []):
                        ctes_with_col.append(cte_alias[cte_name])
                
                if len(ctes_with_col) == 0:
                    # Shouldn't happen, but fallback
                    select_parts.append(f"    NULL AS {col}")
                elif len(ctes_with_col) == 1:
                    # Column only in one CTE - no COALESCE needed
                    select_parts.append(f"    {ctes_with_col[0]}.{col}")
                else:
                    # Column in multiple CTEs - use COALESCE
                    coalesce_parts = [f"{alias}.{col}" for alias in ctes_with_col]
                    select_parts.append(f"    COALESCE({', '.join(coalesce_parts)}) AS {col}")
            
            select_cols = ",\n".join(select_parts)
            
            # Build JOIN clause - use the first CTE as the base
            base_alias = cte_alias[cte_names[0]]
            from_clause = f"FROM {cte_names[0]} {base_alias}"
            
            for cte_name in cte_names[1:]:
                alias = cte_alias[cte_name]
                from_clause += f"\n  FULL OUTER JOIN {cte_name} {alias} ON {base_alias}.{silver_key} = {alias}.{silver_key}"
        
        sql_parts.append(f"""

INSERT INTO {target_catalog}.{target_schema}.{table_physical} (
  {column_list}
)
SELECT
{select_cols}
{from_clause}
;
""")
        
        return "".join(sql_parts)
    
    # =========================================================================
    # Legacy FROM clause extraction (kept for compatibility)
    # =========================================================================
    
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
        
        Uses the new CTE-based approach that:
        1. Groups mappings by source structure
        2. Creates a CTE per group
        3. Joins CTEs on silver table key
        
        Args:
            mappings: List of mapping dictionaries (should be for same table)
            target_catalog: Target catalog placeholder or name
            target_schema: Target schema placeholder or name
            
        Returns:
            INSERT INTO ... SELECT ... SQL statement with CTEs
        """
        # Use the new CTE-based generation
        return self._generate_insert_sql_with_ctes(mappings, target_catalog, target_schema)
    
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
                # First, debug - check total mappings for this project
                cursor.execute(f"""
                    SELECT project_id, mapping_status, COUNT(*) as cnt
                    FROM {db_config['mapped_fields_table']}
                    WHERE project_id = {project_id}
                    GROUP BY project_id, mapping_status
                """)
                debug_rows = cursor.fetchall()
                print(f"[Export Service] Mappings for project {project_id}:")
                for row in debug_rows:
                    print(f"  - project_id={row[0]}, status={row[1]}, count={row[2]}")
                
                if not debug_rows:
                    # Check if any mappings exist at all
                    cursor.execute(f"""
                        SELECT project_id, COUNT(*) as cnt
                        FROM {db_config['mapped_fields_table']}
                        GROUP BY project_id
                        LIMIT 10
                    """)
                    all_mappings = cursor.fetchall()
                    print(f"[Export Service] All mappings by project: {all_mappings}")
                
                # Now get the exportable tables
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
                
                print(f"[Export Service] Found {len(rows)} exportable tables for project {project_id}")
                
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            print(f"[Export Service] Error getting mapped tables: {str(e)}")
            raise
        finally:
            connection.close()

