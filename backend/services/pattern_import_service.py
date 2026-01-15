"""
Pattern Import Service for bulk loading historical mappings.

Provides functionality to:
- Upload and parse CSV files with historical mapping patterns
- Map CSV columns to mapped_fields table columns
- Generate join_metadata via LLM for each pattern
- Preview and approve patterns before saving
- Save approved patterns to mapped_fields with vector index sync
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
import csv
import io
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
from backend.services.config_service import config_service

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=4)


class PatternImportService:
    """Service for importing historical mapping patterns."""
    
    # Standard mapped_fields columns that can be mapped from CSV
    MAPPABLE_COLUMNS = [
        'tgt_table_name',
        'tgt_table_physical_name',
        'tgt_column_name',
        'tgt_column_physical_name',
        'tgt_comments',
        'source_expression',
        'source_tables',
        'source_tables_physical',
        'source_columns',
        'source_columns_physical',
        'source_descriptions',
        'source_datatypes',
        'source_domain',
        'target_domain',
        'source_relationship_type',
        'transformations_applied',
        'confidence_score',
        'join_column_description'  # NEW: Contains COLUMN:Description|... for join/filter columns
    ]
    
    def __init__(self):
        self.config_service = config_service  # Use global instance for shared config
        self._workspace_client = None
        self._import_sessions: Dict[str, Dict] = {}  # Store import sessions in memory
    
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
            "mapped_fields_table": db.mapped_fields_table,
            "semantic_fields_table": db.semantic_fields_table
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
                    print(f"[Pattern Import] Using OAuth token from WorkspaceClient")
            except Exception as e:
                print(f"[Pattern Import] Could not get OAuth token: {e}")
        
        if access_token:
            return sql.connect(
                server_hostname=server_hostname,
                http_path=http_path,
                access_token=access_token
            )
        else:
            print(f"[Pattern Import] Using databricks-oauth auth type")
            return sql.connect(
                server_hostname=server_hostname,
                http_path=http_path,
                auth_type="databricks-oauth"
            )
    
    # =========================================================================
    # PARSE CSV
    # =========================================================================
    
    def parse_csv(self, csv_content: str) -> Dict[str, Any]:
        """
        Parse CSV content and extract headers and preview data.
        
        Handles:
        - Multi-line fields (quoted with double quotes)
        - Excel-style CSVs
        - Various quote styles
        
        Args:
            csv_content: Raw CSV content string
            
        Returns:
            Dictionary with headers, preview rows, and row count
        """
        try:
            # Try to detect the dialect (handles different CSV formats)
            # Take a sample of the content for dialect detection
            sample = csv_content[:8192]
            
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
            except csv.Error:
                # Fall back to excel dialect if detection fails
                dialect = csv.excel
            
            # Parse CSV with detected dialect
            reader = csv.DictReader(
                io.StringIO(csv_content),
                dialect=dialect,
                quotechar='"',
                doublequote=True  # Handle "" as escaped quote
            )
            headers = reader.fieldnames or []
            
            # Clean headers - strip whitespace
            headers = [h.strip() if h else '' for h in headers]
            
            # Get preview rows (first 10)
            preview_rows = []
            all_rows = []
            for i, row in enumerate(reader):
                # Clean up both keys and values - strip whitespace and handle None
                cleaned_row = {
                    (k.strip() if k else ''): (v.strip() if v else '') for k, v in row.items()
                }
                all_rows.append(cleaned_row)
                if i < 10:
                    preview_rows.append(cleaned_row)
            
            return {
                "status": "success",
                "headers": headers,
                "preview_rows": preview_rows,
                "total_rows": len(all_rows),
                "all_rows": all_rows,
                "mappable_columns": self.MAPPABLE_COLUMNS
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    # =========================================================================
    # CREATE IMPORT SESSION
    # =========================================================================
    
    def create_session(
        self,
        session_id: str,
        csv_data: Dict[str, Any],
        column_mapping: Dict[str, str],
        created_by: str
    ) -> Dict[str, Any]:
        """
        Create an import session to track progress.
        
        Args:
            session_id: Unique session identifier
            csv_data: Parsed CSV data from parse_csv
            column_mapping: Mapping of CSV columns to mapped_fields columns
            created_by: User email creating this session
            
        Returns:
            Session info dictionary
        """
        session = {
            "session_id": session_id,
            "created_by": created_by,
            "created_at": datetime.now().isoformat(),
            "status": "CREATED",
            "csv_headers": csv_data.get("headers", []),
            "column_mapping": column_mapping,
            "total_rows": csv_data.get("total_rows", 0),
            "all_rows": csv_data.get("all_rows", []),
            "processed_patterns": [],
            "processing_progress": 0,
            "errors": []
        }
        
        self._import_sessions[session_id] = session
        
        return {
            "session_id": session_id,
            "status": "CREATED",
            "total_rows": session["total_rows"]
        }
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get an import session by ID."""
        return self._import_sessions.get(session_id)
    
    # =========================================================================
    # GENERATE JOIN METADATA (LLM)
    # =========================================================================
    
    def _generate_join_metadata_sync(
        self,
        llm_endpoint: str,
        sql_expression: str,
        target_column: str,
        target_table: str,
        source_tables: str,
        source_columns: str,
        join_column_description: str = "",
        source_descriptions: str = "",
        tgt_comments: str = ""
    ) -> Optional[str]:
        """
        Use LLM to parse SQL and generate join_metadata JSON.
        
        Post-processes the result to replace LLM-generated descriptions with
        actual descriptions from the CSV when available.
        
        Args:
            llm_endpoint: Name of the LLM serving endpoint
            sql_expression: The SQL expression to analyze
            target_column: Target column name
            target_table: Target table name
            source_tables: Pipe-separated source table names
            source_columns: Pipe-separated source column names
            join_column_description: Pipe-delimited COLUMN:Description pairs
            source_descriptions: Pipe-separated source descriptions
            tgt_comments: Target column comments
            
        Returns:
            JSON string of join_metadata, or None on failure
        """
        if not sql_expression or sql_expression.strip() == "":
            return None
        
        # Parse available descriptions for post-processing
        join_desc_dict = self._parse_column_descriptions(join_column_description)
        
        prompt = f"""Parse this SQL expression and generate a JSON metadata object for a data mapping tool.

SQL EXPRESSION:
```sql
{sql_expression}
```

CONTEXT:
- Target Column: {target_column}
- Target Table: {target_table}
- Source Tables: {source_tables}
- Source Columns: {source_columns}

Generate a JSON object with this EXACT structure:
{{
  "patternType": "SINGLE|JOIN|UNION|UNION_JOIN|CONCAT",
  "outputColumn": "<the column being selected>",
  "description": "<brief description of what this mapping does>",
  "silverTables": [
    {{"alias": "<alias>", "physicalName": "<full table name>", "isConstant": true, "description": "<table purpose>"}}
  ],
  "unionBranches": [
    {{
      "branchId": 1,
      "description": "<what this branch does>",
      "bronzeTable": {{"alias": "<alias>", "physicalName": "<table>", "isConstant": false}},
      "joins": [
        {{"type": "INNER|LEFT", "toTable": "<alias>", "onCondition": "<condition>"}}
      ],
      "whereClause": "<where clause if any>"
    }}
  ],
  "userColumnsToMap": [
    {{"role": "output|join_key|filter", "originalColumn": "<column_name>", "description": "<semantic description>"}}
  ],
  "userTablesToMap": [
    {{"role": "bronze_primary|bronze_secondary", "originalTable": "<table>", "description": "<what user replaces>"}}
  ]
}}

CRITICAL - userColumnsToMap MUST include ALL columns from bronze tables:
- role="output": Columns in SELECT clause that produce the output value
- role="join_key": Columns used in JOIN ON conditions from bronze tables (e.g., SAK_RECIP, CDE_COUNTY)
- role="filter": Columns used in WHERE clauses from bronze tables (e.g., CURR_REC_IND, CDE_ADDR_USAGE)

IMPORTANT: Extract EVERY bronze column referenced in the SQL, not just the output column!
For example, if SQL has: "b.SAK_RECIP = mf.SRC_KEY_ID AND b.CURR_REC_IND=1"
Then userColumnsToMap MUST include:
- {{"role": "join_key", "originalColumn": "SAK_RECIP", "description": "Recipient key for joining to member foundation"}}
- {{"role": "filter", "originalColumn": "CURR_REC_IND", "description": "Current record indicator flag"}}

RULES:
1. silverTables = tables from silver_* schemas (CONSTANT, user does NOT replace)
2. bronzeTables/userTablesToMap = tables from bronze_* schemas (user REPLACES with their tables)
3. For UNION, create separate unionBranches for each SELECT
4. If no JOINs/UNIONs, use patternType "SINGLE" and set unionBranches to empty array []
5. userColumnsToMap must include ALL bronze columns: output columns, join key columns, AND filter columns
6. Return ONLY the JSON object, no explanation"""

        try:
            response = self.workspace_client.serving_endpoints.query(
                name=llm_endpoint,
                messages=[
                    ChatMessage(role=ChatMessageRole.USER, content=prompt)
                ],
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                
                # Clean control characters
                json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json_str)
                
                # Parse and post-process to replace LLM descriptions with actual ones
                metadata = json.loads(json_str)
                
                # Post-process userColumnsToMap descriptions
                if "userColumnsToMap" in metadata:
                    replaced_count = 0
                    for col_entry in metadata["userColumnsToMap"]:
                        col_name = col_entry.get("originalColumn", "")
                        if col_name:
                            # Try to find actual description
                            actual_desc = self._find_column_description(
                                col_name,
                                join_desc_dict,
                                source_descriptions,
                                source_columns,
                                tgt_comments
                            )
                            if actual_desc:
                                col_entry["description"] = actual_desc
                                replaced_count += 1
                    
                    if replaced_count > 0:
                        print(f"[Pattern Import] Replaced {replaced_count} LLM descriptions with actual ones")
                
                return json.dumps(metadata)
            else:
                return None
                
        except json.JSONDecodeError as e:
            print(f"[Pattern Import] Failed to parse JSON: {e}")
            return None
        except Exception as e:
            print(f"[Pattern Import] LLM error: {e}")
            return None
    
    def _determine_relationship_type(self, sql: str, source_columns: str) -> str:
        """Determine the source relationship type from SQL."""
        if not sql:
            return "SINGLE"
        
        sql_upper = sql.upper()
        
        if "UNION" in sql_upper and "JOIN" in sql_upper:
            return "UNION_JOIN"
        elif "UNION" in sql_upper:
            return "UNION"
        elif "JOIN" in sql_upper:
            return "JOIN"
        elif source_columns and "|" in source_columns:
            return "CONCAT"
        else:
            return "SINGLE"
    
    def _extract_transformations(self, sql: str) -> Optional[str]:
        """Extract transformation functions used in SQL."""
        if not sql:
            return None
        
        sql_upper = sql.upper()
        transforms = []
        
        transform_funcs = [
            'TRIM', 'UPPER', 'LOWER', 'INITCAP', 'CONCAT', 'SUBSTRING', 'SUBSTR',
            'REPLACE', 'COALESCE', 'NVL', 'IFNULL', 'NULLIF', 'CAST', 'CONVERT',
            'TO_DATE', 'TO_TIMESTAMP', 'DATE_FORMAT', 'LPAD', 'RPAD', 'LEFT', 'RIGHT',
            'CASE', 'DECODE', 'IIF', 'SPLIT_PART', 'REGEXP_REPLACE', 'REGEXP_EXTRACT'
        ]
        
        for func in transform_funcs:
            if func in sql_upper:
                transforms.append(func)
        
        return ", ".join(transforms) if transforms else None
    
    def _parse_column_descriptions(self, description_str: str) -> Dict[str, str]:
        """
        Parse pipe-delimited column descriptions.
        
        Format: "COLUMN1:Description for column 1|COLUMN2:Description for column 2|..."
        
        Args:
            description_str: Pipe-delimited string of COLUMN:Description pairs
            
        Returns:
            Dictionary mapping column names (uppercase) to descriptions
        """
        result = {}
        if not description_str or not description_str.strip():
            return result
        
        # Split by pipe
        parts = description_str.split('|')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Find first colon (column name can't have colon, but description might)
            colon_idx = part.find(':')
            if colon_idx > 0:
                column_name = part[:colon_idx].strip().upper()
                description = part[colon_idx + 1:].strip()
                if column_name and description:
                    result[column_name] = description
        
        return result
    
    def _find_column_description(
        self,
        column_name: str,
        join_col_desc: Dict[str, str],
        source_descriptions: str,
        source_columns: str,
        tgt_comments: str
    ) -> Optional[str]:
        """
        Find description for a column using priority lookup.
        
        Priority:
        1. join_column_description (parsed dict)
        2. source_descriptions (matched by position with source_columns)
        3. tgt_comments (target column description)
        
        Args:
            column_name: Column name to find description for
            join_col_desc: Parsed join_column_description dict
            source_descriptions: Pipe-separated source descriptions
            source_columns: Pipe-separated source columns (for positional match)
            tgt_comments: Target column comments
            
        Returns:
            Description if found, None otherwise
        """
        col_upper = column_name.upper().strip()
        
        # Priority 1: join_column_description (exact match)
        if col_upper in join_col_desc:
            return join_col_desc[col_upper]
        
        # Priority 2: source_descriptions (positional match with source_columns)
        if source_descriptions and source_columns:
            src_cols = [c.strip().upper() for c in source_columns.split('|')]
            src_descs = [d.strip() for d in source_descriptions.split('|')]
            
            for i, col in enumerate(src_cols):
                if col == col_upper and i < len(src_descs) and src_descs[i]:
                    return src_descs[i]
        
        # Priority 3: tgt_comments (only if it seems relevant - contains column name)
        if tgt_comments and col_upper.lower() in tgt_comments.lower():
            return tgt_comments
        
        return None
    
    def _detect_special_case(self, sql_expr: str) -> Dict[str, Any]:
        """
        Detect special case patterns in source expression.
        
        Returns:
            Dict with:
            - special_case_type: 'AUTO_GENERATED' | 'HARDCODED' | 'NOT_APPLICABLE' | None
            - hardcoded_value: The value to hardcode (for HARDCODED type)
            - generated_sql: Pre-generated SQL for special cases
        """
        if not sql_expr:
            return {"special_case_type": None}
        
        sql_clean = sql_expr.strip()
        sql_upper = sql_clean.upper()
        
        # Check for AUTO GENERATED patterns (case insensitive)
        auto_gen_patterns = [
            "AUTO GENERATED",
            "AUTO-GENERATED", 
            "AUTOGENERATED",
            "AUTO_GENERATED",
            "GENERATED ON INSERT",
            "IDENTITY COLUMN",
            "AUTO INCREMENT"
        ]
        
        for pattern in auto_gen_patterns:
            if pattern in sql_upper:
                print(f"[Pattern Import] Detected AUTO_GENERATED: '{sql_clean}'")
                return {
                    "special_case_type": "AUTO_GENERATED",
                    "hardcoded_value": None,
                    "generated_sql": None,  # No SQL needed, auto-mapped
                    "mapping_action": "AUTO_MAP"
                }
        
        # Check for NA / Not Applicable patterns
        na_patterns = [
            "N/A",
            "NA",
            "NOT APPLICABLE",
            "NOT USED",
            "UNUSED",
            "NOT IN USE",
            "DEPRECATED",
            "DO NOT MAP"
        ]
        
        # Only match if it's primarily just the NA text (not part of larger SQL)
        sql_stripped = sql_clean.strip().upper()
        if sql_stripped in na_patterns or (len(sql_stripped) < 30 and any(p in sql_upper for p in na_patterns)):
            print(f"[Pattern Import] Detected NOT_APPLICABLE: '{sql_clean}'")
            return {
                "special_case_type": "NOT_APPLICABLE",
                "hardcoded_value": None,
                "generated_sql": None,
                "mapping_action": "SKIP"
            }
        
        # Check for HARD CODED patterns
        # Match patterns like: "Hard coded as NULL", "Hard code as 'Y'", "Hardcoded: 0"
        hardcode_patterns = [
            r"HARD\s*CODE[D]?\s*(?:AS|:)?\s*(.+)",
            r"HARDCODE[D]?\s*(?:AS|:)?\s*(.+)",
            r"CONSTANT\s*(?:VALUE)?[:=]?\s*(.+)",
            r"STATIC\s*(?:VALUE)?[:=]?\s*(.+)",
            r"ALWAYS\s+(.+)"
        ]
        
        for pattern in hardcode_patterns:
            match = re.search(pattern, sql_upper)
            if match:
                # Extract the hardcoded value
                raw_value = match.group(1).strip()
                
                # Clean up the value
                # Remove trailing punctuation, quotes for parsing
                raw_value_clean = raw_value.strip("'\"` ")
                
                # Determine the SQL value representation
                if raw_value_clean.upper() == "NULL":
                    sql_value = "NULL"
                elif raw_value_clean.upper() in ("TRUE", "FALSE"):
                    sql_value = raw_value_clean.upper()
                elif raw_value_clean.isdigit() or (raw_value_clean.startswith('-') and raw_value_clean[1:].isdigit()):
                    sql_value = raw_value_clean
                else:
                    # String value - wrap in quotes
                    sql_value = f"'{raw_value_clean}'"
                
                print(f"[Pattern Import] Detected HARDCODED: '{sql_clean}' -> {sql_value}")
                return {
                    "special_case_type": "HARDCODED",
                    "hardcoded_value": raw_value_clean,
                    "generated_sql": sql_value,  # Will be used as: SELECT {sql_value} AS {column}
                    "mapping_action": "HARDCODE"
                }
        
        # No special case detected
        return {"special_case_type": None}
    
    # =========================================================================
    # PROCESS PATTERNS
    # =========================================================================
    
    async def process_patterns(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process patterns in a session - generate join_metadata for each.
        
        Args:
            session_id: Import session ID
            limit: Optional limit on number of patterns to process
            
        Returns:
            Status dictionary with progress
        """
        print(f"[Pattern Import] Starting process_patterns for session: {session_id}")
        print(f"[Pattern Import] Limit: {limit}")
        
        session = self.get_session(session_id)
        if not session:
            print(f"[Pattern Import] Session not found: {session_id}")
            return {"status": "error", "error": "Session not found"}
        
        config = self.config_service.get_config()
        llm_endpoint = config.ai_model.foundation_model_endpoint
        print(f"[Pattern Import] Using LLM endpoint: {llm_endpoint}")
        
        session["status"] = "PROCESSING"
        session["processed_patterns"] = []  # Initialize empty - will update incrementally
        session["errors"] = []
        session["processed_count"] = 0
        session["total_to_process"] = 0
        
        all_rows = session.get("all_rows", [])
        column_mapping = session.get("column_mapping", {})
        
        # Apply limit if specified
        rows_to_process = all_rows[:limit] if limit else all_rows
        total_rows = len(rows_to_process)
        session["total_to_process"] = total_rows
        
        print(f"[Pattern Import] Processing {total_rows} rows (out of {len(all_rows)} total)")
        
        # Get database config for semantic_field_id lookup
        db_config = self._get_db_config()
        
        # Debug: Log the column mapping being used
        print(f"[Pattern Import] Column mapping: {column_mapping}")
        
        # BATCH LOOKUP: Get all semantic fields at once to avoid connection timeout issues
        semantic_field_cache = {}
        try:
            print(f"[Pattern Import] Loading all semantic fields for batch lookup...")
            lookup_connection = self._get_sql_connection(db_config["server_hostname"], db_config["http_path"])
            with lookup_connection.cursor() as lookup_cursor:
                lookup_cursor.execute(f"""
                    SELECT 
                        semantic_field_id,
                        UPPER(TRIM(COALESCE(tgt_table_physical_name, ''))),
                        UPPER(TRIM(COALESCE(tgt_column_physical_name, ''))),
                        UPPER(TRIM(COALESCE(tgt_table_name, ''))),
                        UPPER(TRIM(COALESCE(tgt_column_name, '')))
                    FROM {db_config['semantic_fields_table']}
                """)
                for row in lookup_cursor.fetchall():
                    sf_id, table_phys, col_phys, table_log, col_log = row
                    # Index by both physical and logical names
                    if table_phys and col_phys:
                        semantic_field_cache[(table_phys, col_phys)] = sf_id
                    if table_log and col_log:
                        semantic_field_cache[(table_log, col_log)] = sf_id
                    # Also cross-reference physical table with logical column and vice versa
                    if table_phys and col_log:
                        semantic_field_cache[(table_phys, col_log)] = sf_id
                    if table_log and col_phys:
                        semantic_field_cache[(table_log, col_phys)] = sf_id
            lookup_connection.close()
            print(f"[Pattern Import] Loaded {len(semantic_field_cache)} semantic field mappings into cache")
        except Exception as e:
            print(f"[Pattern Import] Error loading semantic fields: {e}")
            semantic_field_cache = {}
        
        # =====================================================================
        # PHASE 1: Fast pre-processing (no LLM calls)
        # =====================================================================
        print(f"[Pattern Import] Phase 1: Pre-processing {total_rows} rows...")
        
        patterns_needing_llm = []  # List of (index, pattern) tuples that need LLM
        completed_count = 0  # Track patterns that are fully done
        
        for i, row in enumerate(rows_to_process):
            try:
                # Map CSV columns to pattern fields
                pattern = self._map_row_to_pattern(row, column_mapping)
                
                target_col = pattern.get("tgt_column_physical_name", "").strip() if pattern.get("tgt_column_physical_name") else ""
                target_table = pattern.get("tgt_table_physical_name", "").strip() if pattern.get("tgt_table_physical_name") else ""
                
                # Fallback to logical names if physical not provided
                if not target_table:
                    target_table = pattern.get("tgt_table_name", "").strip() if pattern.get("tgt_table_name") else ""
                if not target_col:
                    target_col = pattern.get("tgt_column_name", "").strip() if pattern.get("tgt_column_name") else ""
                
                # Look up semantic_field_id from cache
                semantic_field_id = None
                semantic_field_warning = None
                
                if target_table and target_col:
                    lookup_key = (target_table.upper().strip(), target_col.upper().strip())
                    semantic_field_id = semantic_field_cache.get(lookup_key)
                    if not semantic_field_id:
                        semantic_field_warning = f"No matching semantic field found for {target_table}.{target_col}"
                else:
                    semantic_field_warning = "Missing target table or column name"
                
                pattern["semantic_field_id"] = semantic_field_id
                pattern["semantic_field_warning"] = semantic_field_warning
                pattern["row_index"] = i
                
                # Check for special cases (auto-generated, hardcoded, N/A)
                sql_expr = pattern.get("source_expression", "")
                special_case = self._detect_special_case(sql_expr)
                
                if special_case.get("special_case_type"):
                    # Special case - no LLM needed, fully complete
                    sc_type = special_case["special_case_type"]
                    pattern["special_case_type"] = sc_type
                    pattern["mapping_action"] = special_case.get("mapping_action")
                    pattern["status"] = "READY"
                    
                    target_col_name = pattern.get("tgt_column_physical_name", "UNKNOWN")
                    
                    if sc_type == "AUTO_GENERATED":
                        pattern["join_metadata"] = json.dumps({
                            "patternType": "AUTO_GENERATED",
                            "outputColumn": target_col_name,
                            "description": "Column is auto-generated on insert",
                            "mappingAction": "AUTO_MAP",
                            "silverTables": [], "unionBranches": [], "userColumnsToMap": [], "userTablesToMap": []
                        })
                        pattern["source_relationship_type"] = "AUTO_GENERATED"
                    elif sc_type == "HARDCODED":
                        hardcode_val = special_case.get("generated_sql", "NULL")
                        pattern["join_metadata"] = json.dumps({
                            "patternType": "HARDCODED",
                            "outputColumn": target_col_name,
                            "description": f"Hardcoded to: {hardcode_val}",
                            "hardcodedValue": special_case.get("hardcoded_value"),
                            "generatedSql": f"SELECT {hardcode_val} AS {target_col_name}",
                            "mappingAction": "HARDCODE",
                            "silverTables": [], "unionBranches": [], "userColumnsToMap": [], "userTablesToMap": []
                        })
                        pattern["source_relationship_type"] = "HARDCODED"
                    elif sc_type == "NOT_APPLICABLE":
                        pattern["join_metadata"] = json.dumps({
                            "patternType": "NOT_APPLICABLE",
                            "outputColumn": target_col_name,
                            "description": "Column is not applicable - suggest skip",
                            "mappingAction": "SKIP",
                            "silverTables": [], "unionBranches": [], "userColumnsToMap": [], "userTablesToMap": []
                        })
                        pattern["source_relationship_type"] = "NOT_APPLICABLE"
                        
                    session["processed_patterns"].append(pattern)
                    completed_count += 1
                    session["processed_count"] = completed_count
                        
                elif sql_expr:
                    # Needs LLM call - queue it for parallel processing (don't add to processed yet)
                    pattern["status"] = "PENDING_LLM"
                    # Auto-detect relationship type and transformations now
                    pattern["source_relationship_type"] = self._determine_relationship_type(
                        sql_expr, pattern.get("source_columns_physical", "")
                    )
                    pattern["transformations_applied"] = self._extract_transformations(sql_expr)
                    patterns_needing_llm.append((i, pattern))
                else:
                    # No SQL expression - complete
                    pattern["status"] = "READY"
                    pattern["join_metadata"] = None
                    session["processed_patterns"].append(pattern)
                    completed_count += 1
                    session["processed_count"] = completed_count
                    
            except Exception as e:
                print(f"[Pattern Import] Row {i+1}: Exception: {e}")
                error_pattern = self._map_row_to_pattern(row, column_mapping)
                error_pattern["row_index"] = i
                error_pattern["status"] = "ERROR"
                error_pattern["error"] = str(e)
                session["processed_patterns"].append(error_pattern)
                session["errors"].append({"row_index": i, "error": str(e)})
                completed_count += 1
                session["processed_count"] = completed_count
            
            # Update progress based on phase 1 completion
            session["processing_progress"] = int((i + 1) / total_rows * 50)  # 0-50% for phase 1
        
        print(f"[Pattern Import] Phase 1 complete. {completed_count} done, {len(patterns_needing_llm)} need LLM calls.")
        
        # =====================================================================
        # PHASE 2: Parallel LLM calls (the slow part - now parallelized!)
        # =====================================================================
        if patterns_needing_llm:
            print(f"[Pattern Import] Phase 2: Running {len(patterns_needing_llm)} LLM calls in parallel...")
            
            # Create async tasks for all LLM calls
            async def call_llm_for_pattern(idx: int, pattern: dict) -> tuple:
                """Wrapper to call LLM and return (index, pattern, result, error)"""
                sql_expr = pattern.get("source_expression", "")
                try:
                    loop = asyncio.get_event_loop()
                    join_metadata = await asyncio.wait_for(
                        loop.run_in_executor(
                            executor,
                            functools.partial(
                                self._generate_join_metadata_sync,
                                llm_endpoint,
                                sql_expr,
                                pattern.get("tgt_column_physical_name", ""),
                                pattern.get("tgt_table_physical_name", ""),
                                pattern.get("source_tables_physical", ""),
                                pattern.get("source_columns_physical", ""),
                                pattern.get("join_column_description", ""),  # NEW
                                pattern.get("source_descriptions", ""),      # NEW
                                pattern.get("tgt_comments", "")              # NEW
                            )
                        ),
                        timeout=90.0  # 90 second timeout per LLM call
                    )
                    return (idx, pattern, join_metadata, None)
                except asyncio.TimeoutError:
                    return (idx, pattern, None, "LLM call timed out after 90 seconds")
                except Exception as e:
                    return (idx, pattern, None, str(e))
            
            # Run all LLM calls in parallel (batched to avoid overwhelming the API)
            BATCH_SIZE = 10  # Process 10 LLM calls at a time
            llm_completed = 0
            
            for batch_start in range(0, len(patterns_needing_llm), BATCH_SIZE):
                batch = patterns_needing_llm[batch_start:batch_start + BATCH_SIZE]
                batch_num = batch_start // BATCH_SIZE + 1
                total_batches = (len(patterns_needing_llm) + BATCH_SIZE - 1) // BATCH_SIZE
                
                print(f"[Pattern Import] LLM batch {batch_num}/{total_batches} ({len(batch)} calls)...")
                
                # Create tasks for this batch
                tasks = [call_llm_for_pattern(idx, pattern) for idx, pattern in batch]
                
                # Run batch in parallel
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results - add completed patterns to session
                for result in results:
                    if isinstance(result, Exception):
                        print(f"[Pattern Import] Unexpected exception: {result}")
                        continue
                    
                    idx, pattern, join_metadata, error = result
                    
                    if error:
                        pattern["status"] = "ERROR"
                        pattern["error"] = error
                        pattern["join_metadata"] = None
                        session["errors"].append({
                            "row_index": idx,
                            "column": pattern.get("tgt_column_physical_name", ""),
                            "error": error
                        })
                else:
                    pattern["status"] = "READY"
                        pattern["join_metadata"] = join_metadata
                    
                    # NOW add to processed patterns (after LLM is done)
                session["processed_patterns"].append(pattern)
                    completed_count += 1
                    llm_completed += 1
                    session["processed_count"] = completed_count
                
                # Update progress (50-100% for phase 2)
                progress = 50 + int(llm_completed / len(patterns_needing_llm) * 50)
                session["processing_progress"] = min(progress, 100)
            
            print(f"[Pattern Import] Phase 2 complete. All LLM calls finished.")
        
        session["processing_progress"] = 100
        
        session["status"] = "READY_FOR_REVIEW"
        
        successful = len([p for p in session["processed_patterns"] if p.get("status") == "READY"])
        failed = len([p for p in session["processed_patterns"] if p.get("status") == "ERROR"])
        missing_semantic = len([p for p in session["processed_patterns"] if p.get("semantic_field_warning")])
        
        print(f"[Pattern Import] Complete: {successful} successful, {failed} failed, {missing_semantic} missing semantic field")
        
        return {
            "status": "success",
            "session_id": session_id,
            "processed_count": successful,
            "error_count": failed,
            "total": total_rows
        }
    
    def _map_row_to_pattern(
        self,
        row: Dict[str, str],
        column_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Map a CSV row to a pattern dictionary using column mapping.
        
        Args:
            row: CSV row dictionary
            column_mapping: Mapping of mapped_fields columns to CSV columns
            
        Returns:
            Pattern dictionary
        """
        pattern = {}
        
        for target_col, csv_col in column_mapping.items():
            if csv_col and csv_col in row:
                value = row[csv_col]
                # Convert confidence_score to float
                if target_col == "confidence_score" and value:
                    try:
                        pattern[target_col] = float(value)
                    except:
                        pattern[target_col] = 0.9
                else:
                    pattern[target_col] = value
        
        return pattern
    
    # =========================================================================
    # GET PREVIEW
    # =========================================================================
    
    def get_preview(self, session_id: str) -> Dict[str, Any]:
        """
        Get preview of processed patterns for review.
        
        Args:
            session_id: Import session ID
            
        Returns:
            Preview data dictionary
        """
        session = self.get_session(session_id)
        if not session:
            return {"status": "error", "error": "Session not found"}
        
        return {
            "status": "success",
            "session_status": session.get("status"),
            "processing_progress": session.get("processing_progress", 0),
            "patterns": session.get("processed_patterns", []),
            "errors": session.get("errors", []),
            "total_rows": session.get("total_rows", 0),
            # Save progress tracking
            "save_status": session.get("save_status"),  # None, SAVING, COMPLETE, FAILED
            "save_progress": session.get("save_progress", 0),
            "save_total": session.get("save_total", 0),
            "save_current": session.get("save_current", 0),
            "save_current_pattern": session.get("save_current_pattern"),
            "save_errors": session.get("save_errors", [])
        }
    
    # =========================================================================
    # SAVE PATTERNS
    # =========================================================================
    
    def _save_patterns_sync(
        self,
        db_config: Dict[str, str],
        patterns: List[Dict[str, Any]],
        created_by: str,
        session: Optional[Dict[str, Any]] = None,
        project_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save approved patterns to mapped_fields (synchronous).
        
        Args:
            db_config: Database configuration
            patterns: List of pattern dictionaries to save
            created_by: User email
            session: Optional session dict for progress tracking
            project_type: Project type for pattern filtering (required for new imports)
            
        Returns:
            Status dictionary with saved count
        """
        print(f"[Pattern Import Sync] Starting save of {len(patterns)} patterns")
        print(f"[Pattern Import Sync] DB config: {db_config.get('mapped_fields_table')}")
        
        # Initialize save progress tracking
        if session:
            session["save_status"] = "SAVING"
            session["save_progress"] = 0
            session["save_total"] = len(patterns)
            session["save_current"] = 0
            session["save_errors"] = []
        
        connection = self._get_sql_connection(
            db_config["server_hostname"],
            db_config["http_path"]
        )
        print(f"[Pattern Import Sync] Database connection established")
        
        saved_count = 0
        errors = []
        
        # Escape function for SQL values
        def esc(val):
            if val is None:
                return "NULL"
            return f"'{str(val).replace(chr(39), chr(39)+chr(39))}'"
        
        try:
            with connection.cursor() as cursor:
                # Build list of valid patterns and their VALUES tuples
                values_list = []
                
                for i, pattern in enumerate(patterns):
                    print(f"[Pattern Import Sync] Processing pattern {i+1}/{len(patterns)}: {pattern.get('tgt_column_physical_name')}")
                    
                    # Update progress in session for polling
                    if session:
                        session["save_current"] = i + 1
                        session["save_progress"] = int((i + 1) / len(patterns) * 50)  # 0-50% for building
                        session["save_current_pattern"] = pattern.get('tgt_column_physical_name', 'unknown')
                    
                    # Use cached semantic_field_id from processing phase
                    semantic_field_id = pattern.get("semantic_field_id")
                    
                    # Get values for logging
                    tgt_table = pattern.get("tgt_table_physical_name", "").strip() if pattern.get("tgt_table_physical_name") else ""
                    tgt_column = pattern.get("tgt_column_physical_name", "").strip() if pattern.get("tgt_column_physical_name") else ""
                    
                    # Fallback to logical names if physical not provided
                    if not tgt_table:
                        tgt_table = pattern.get("tgt_table_name", "").strip() if pattern.get("tgt_table_name") else ""
                    if not tgt_column:
                        tgt_column = pattern.get("tgt_column_name", "").strip() if pattern.get("tgt_column_name") else ""
                    
                    # Skip patterns without matching semantic field (required for FK constraint)
                    if not semantic_field_id:
                        print(f"[Pattern Import Sync] Skipping pattern - no semantic field found for {tgt_table}.{tgt_column}")
                        errors.append({
                            "pattern": f"{tgt_table}.{tgt_column}",
                            "error": f"No matching semantic field found for {tgt_table}.{tgt_column}. Ensure target field exists in semantic_fields table."
                        })
                        continue
                    
                    # Build VALUES tuple for this pattern
                    values_tuple = f"""(
                        {semantic_field_id},
                        {esc(pattern.get('tgt_table_name'))},
                        {esc(pattern.get('tgt_table_physical_name'))},
                        {esc(pattern.get('tgt_column_name'))},
                        {esc(pattern.get('tgt_column_physical_name'))},
                        {esc(pattern.get('tgt_comments'))},
                        {esc(pattern.get('source_expression'))},
                        {esc(pattern.get('source_tables'))},
                        {esc(pattern.get('source_tables_physical'))},
                        {esc(pattern.get('source_columns'))},
                        {esc(pattern.get('source_columns_physical'))},
                        {esc(pattern.get('source_descriptions'))},
                        {esc(pattern.get('source_datatypes'))},
                        {esc(pattern.get('source_domain'))},
                        {esc(pattern.get('target_domain'))},
                        {esc(pattern.get('source_relationship_type', 'SINGLE'))},
                        {esc(pattern.get('transformations_applied'))},
                        {esc(pattern.get('join_metadata'))},
                        {pattern.get('confidence_score', 0.9)},
                        'BULK_UPLOAD',
                        false,
                        'ACTIVE',
                        {esc(created_by)},
                        CURRENT_TIMESTAMP(),
                        NULL,
                        {esc(project_type) if project_type else 'NULL'},
                        true,
                        {esc(created_by)},
                        CURRENT_TIMESTAMP()
                    )"""
                    values_list.append(values_tuple)
                
                # Execute batch INSERT if we have valid patterns
                if values_list:
                    print(f"[Pattern Import Sync] Executing batch INSERT for {len(values_list)} patterns...")
                    
                    if session:
                        session["save_progress"] = 60
                        session["save_current_pattern"] = "Batch inserting..."
                    
                    # Join all VALUES tuples and execute single INSERT
                    batch_sql = f"""
                            INSERT INTO {db_config['mapped_fields_table']} (
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
                                target_domain,
                                source_relationship_type,
                                transformations_applied,
                                join_metadata,
                                confidence_score,
                                mapping_source,
                                ai_generated,
                                mapping_status,
                                mapped_by,
                                mapped_ts,
                                project_id,
                            project_type,
                                is_approved_pattern,
                                pattern_approved_by,
                                pattern_approved_ts
                        ) VALUES {', '.join(values_list)}
                    """
                    
                    cursor.execute(batch_sql)
                    saved_count = len(values_list)
                    print(f"[Pattern Import Sync] Batch INSERT successful: {saved_count} patterns saved")
                else:
                    print(f"[Pattern Import Sync] No valid patterns to insert")
                
                print(f"[Pattern Import Sync] Complete: {saved_count} saved, {len(errors)} errors")
                
                # Mark save as complete in session
                if session:
                    session["save_status"] = "COMPLETE"
                    session["save_progress"] = 100
                    session["save_errors"] = errors
                
                return {
                    "status": "success",
                    "saved_count": saved_count,
                    "error_count": len(errors),
                    "errors": errors
                }
                
        except Exception as e:
            print(f"[Pattern Import Sync] Fatal error saving patterns: {e}")
            import traceback
            traceback.print_exc()
            
            # Mark save as failed in session
            if session:
                session["save_status"] = "FAILED"
                session["save_errors"] = [{"error": str(e)}]
            
            raise
        finally:
            connection.close()
    
    async def save_patterns(
        self,
        session_id: str,
        pattern_indices: Optional[List[int]] = None,
        project_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save approved patterns from a session.
        
        Args:
            session_id: Import session ID
            pattern_indices: Optional list of pattern indices to save (all if None)
            project_type: Project type for pattern filtering (required for new imports)
            
        Returns:
            Status dictionary
        """
        print(f"[Pattern Import] save_patterns called for session: {session_id}")
        print(f"[Pattern Import] Pattern indices: {pattern_indices}")
        
        session = self.get_session(session_id)
        if not session:
            print(f"[Pattern Import] Session not found: {session_id}")
            return {"status": "error", "error": "Session not found"}
        
        print(f"[Pattern Import] Session found, status: {session.get('status')}")
        patterns = session.get("processed_patterns", [])
        print(f"[Pattern Import] Total processed patterns in session: {len(patterns)}")
        
        # Filter to specific indices if provided
        if pattern_indices is not None:
            patterns = [p for p in patterns if p.get("row_index") in pattern_indices]
            print(f"[Pattern Import] Filtered to {len(patterns)} patterns by indices")
        
        if not patterns:
            print(f"[Pattern Import] No patterns to save after filtering")
            return {"status": "error", "error": "No patterns to save"}
        
        # Filter to only READY patterns
        ready_patterns = [p for p in patterns if p.get("status") == "READY"]
        print(f"[Pattern Import] {len(ready_patterns)} patterns with READY status")
        
        if not ready_patterns:
            print(f"[Pattern Import] No READY patterns to save")
            return {"status": "error", "error": "No READY patterns to save"}
        
        db_config = self._get_db_config()
        created_by = session.get("created_by", "unknown")
        # Use project_type from parameter, or fall back to session
        effective_project_type = project_type or session.get("project_type")
        print(f"[Pattern Import] Created by: {created_by}, project_type: {effective_project_type}")
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                functools.partial(
                    self._save_patterns_sync,
                    db_config,
                    ready_patterns,
                    created_by,
                    session,  # Pass session for progress tracking
                    effective_project_type  # Pass project_type
                )
            )
            
            print(f"[Pattern Import] Save result: {result}")
            
            # Update session status
            session["status"] = "COMPLETED"
            
            return result
        except Exception as e:
            print(f"[Pattern Import] Error in save_patterns: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}
    
    def delete_session(self, session_id: str) -> bool:
        """Delete an import session."""
        if session_id in self._import_sessions:
            del self._import_sessions[session_id]
            return True
        return False

