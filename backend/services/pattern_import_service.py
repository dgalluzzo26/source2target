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
from backend.services.config_service import ConfigService
from backend.services.vector_search_service import VectorSearchService

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
        'confidence_score'
    ]
    
    def __init__(self):
        self.config_service = ConfigService()
        self.vector_search_service = VectorSearchService()
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
        catalog = config.database.catalog
        schema = config.database.schema
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "catalog": catalog,
            "schema": schema,
            "mapped_fields_table": f"{catalog}.{schema}.{config.database.mapped_fields_table}",
            "semantic_fields_table": f"{catalog}.{schema}.{config.database.semantic_fields_table}"
        }
    
    def _get_sql_connection(self, server_hostname: str, http_path: str):
        """Create a SQL connection."""
        return sql.connect(
            server_hostname=server_hostname,
            http_path=http_path
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
            
            # Get preview rows (first 10)
            preview_rows = []
            all_rows = []
            for i, row in enumerate(reader):
                # Clean up values - strip whitespace and handle None
                cleaned_row = {
                    k: (v.strip() if v else '') for k, v in row.items()
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
        source_columns: str
    ) -> Optional[str]:
        """
        Use LLM to parse SQL and generate join_metadata JSON.
        
        Args:
            llm_endpoint: Name of the LLM serving endpoint
            sql_expression: The SQL expression to analyze
            target_column: Target column name
            target_table: Target table name
            source_tables: Pipe-separated source table names
            source_columns: Pipe-separated source column names
            
        Returns:
            JSON string of join_metadata, or None on failure
        """
        if not sql_expression or sql_expression.strip() == "":
            return None
        
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
    {{"role": "join_key|output|filter", "originalColumn": "<column>", "description": "<what user provides>"}}
  ],
  "userTablesToMap": [
    {{"role": "bronze_primary|bronze_secondary", "originalTable": "<table>", "description": "<what user replaces>"}}
  ]
}}

RULES:
1. silverTables = tables from silver_* schemas (CONSTANT, user does NOT replace)
2. bronzeTables/userTablesToMap = tables from bronze_* schemas (user REPLACES with their tables)
3. For UNION, create separate unionBranches for each SELECT
4. If no JOINs/UNIONs, use patternType "SINGLE" and set unionBranches to empty array []
5. Return ONLY the JSON object, no explanation"""

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
                
                # Validate it's valid JSON
                json.loads(json_str)
                return json_str
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
    
    # =========================================================================
    # PROCESS PATTERNS
    # =========================================================================
    
    async def process_patterns(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Process all patterns in a session - generate join_metadata for each.
        
        Args:
            session_id: Import session ID
            
        Returns:
            Status dictionary with progress
        """
        session = self.get_session(session_id)
        if not session:
            return {"status": "error", "error": "Session not found"}
        
        config = self.config_service.get_config()
        llm_endpoint = config.ai_model.foundation_model_endpoint
        
        session["status"] = "PROCESSING"
        processed = []
        errors = []
        
        all_rows = session.get("all_rows", [])
        column_mapping = session.get("column_mapping", {})
        
        for i, row in enumerate(all_rows):
            try:
                # Map CSV columns to pattern fields
                pattern = self._map_row_to_pattern(row, column_mapping)
                
                # Generate join_metadata if SQL expression exists
                sql_expr = pattern.get("source_expression", "")
                if sql_expr:
                    # Generate metadata asynchronously
                    loop = asyncio.get_event_loop()
                    join_metadata = await loop.run_in_executor(
                        executor,
                        functools.partial(
                            self._generate_join_metadata_sync,
                            llm_endpoint,
                            sql_expr,
                            pattern.get("tgt_column_physical_name", ""),
                            pattern.get("tgt_table_physical_name", ""),
                            pattern.get("source_tables_physical", ""),
                            pattern.get("source_columns_physical", "")
                        )
                    )
                    pattern["join_metadata"] = join_metadata
                    
                    # Auto-detect relationship type and transformations
                    if not pattern.get("source_relationship_type"):
                        pattern["source_relationship_type"] = self._determine_relationship_type(
                            sql_expr, 
                            pattern.get("source_columns_physical", "")
                        )
                    
                    if not pattern.get("transformations_applied"):
                        pattern["transformations_applied"] = self._extract_transformations(sql_expr)
                
                pattern["row_index"] = i
                pattern["status"] = "READY"
                processed.append(pattern)
                
            except Exception as e:
                errors.append({
                    "row_index": i,
                    "error": str(e)
                })
            
            # Update progress
            session["processing_progress"] = int((i + 1) / len(all_rows) * 100)
        
        session["processed_patterns"] = processed
        session["errors"] = errors
        session["status"] = "READY_FOR_REVIEW"
        
        return {
            "status": "success",
            "session_id": session_id,
            "processed_count": len(processed),
            "error_count": len(errors)
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
            "total_rows": session.get("total_rows", 0)
        }
    
    # =========================================================================
    # SAVE PATTERNS
    # =========================================================================
    
    def _save_patterns_sync(
        self,
        db_config: Dict[str, str],
        patterns: List[Dict[str, Any]],
        created_by: str
    ) -> Dict[str, Any]:
        """
        Save approved patterns to mapped_fields (synchronous).
        
        Args:
            db_config: Database configuration
            patterns: List of pattern dictionaries to save
            created_by: User email
            
        Returns:
            Status dictionary with saved count
        """
        connection = self._get_sql_connection(
            db_config["server_hostname"],
            db_config["http_path"]
        )
        
        saved_count = 0
        errors = []
        
        try:
            with connection.cursor() as cursor:
                for pattern in patterns:
                    try:
                        # Look up semantic_field_id if possible
                        semantic_field_id = None
                        if pattern.get("tgt_table_physical_name") and pattern.get("tgt_column_physical_name"):
                            cursor.execute(f"""
                                SELECT semantic_field_id 
                                FROM {db_config['semantic_fields_table']}
                                WHERE UPPER(tgt_table_physical_name) = UPPER('{pattern['tgt_table_physical_name']}')
                                  AND UPPER(tgt_column_physical_name) = UPPER('{pattern['tgt_column_physical_name']}')
                                LIMIT 1
                            """)
                            result = cursor.fetchone()
                            if result:
                                semantic_field_id = result[0]
                        
                        # Escape function
                        def esc(val):
                            if val is None:
                                return "NULL"
                            return f"'{str(val).replace(chr(39), chr(39)+chr(39))}'"
                        
                        # Insert pattern
                        cursor.execute(f"""
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
                                is_approved_pattern,
                                pattern_approved_by,
                                pattern_approved_ts
                            ) VALUES (
                                {semantic_field_id if semantic_field_id else 'NULL'},
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
                                true,
                                {esc(created_by)},
                                CURRENT_TIMESTAMP()
                            )
                        """)
                        
                        saved_count += 1
                        
                    except Exception as e:
                        errors.append({
                            "pattern": pattern.get("tgt_column_physical_name", "unknown"),
                            "error": str(e)
                        })
                
                return {
                    "status": "success",
                    "saved_count": saved_count,
                    "error_count": len(errors),
                    "errors": errors
                }
                
        except Exception as e:
            print(f"[Pattern Import] Error saving patterns: {e}")
            raise
        finally:
            connection.close()
    
    async def save_patterns(
        self,
        session_id: str,
        pattern_indices: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Save approved patterns from a session.
        
        Args:
            session_id: Import session ID
            pattern_indices: Optional list of pattern indices to save (all if None)
            
        Returns:
            Status dictionary
        """
        session = self.get_session(session_id)
        if not session:
            return {"status": "error", "error": "Session not found"}
        
        patterns = session.get("processed_patterns", [])
        
        # Filter to specific indices if provided
        if pattern_indices is not None:
            patterns = [p for p in patterns if p.get("row_index") in pattern_indices]
        
        if not patterns:
            return {"status": "error", "error": "No patterns to save"}
        
        db_config = self._get_db_config()
        created_by = session.get("created_by", "unknown")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._save_patterns_sync,
                db_config,
                patterns,
                created_by
            )
        )
        
        # Sync vector search index after save
        if result.get("saved_count", 0) > 0:
            try:
                await self.vector_search_service.sync_mapped_fields_index()
                result["vector_index_synced"] = True
            except Exception as e:
                result["vector_index_synced"] = False
                result["vector_sync_error"] = str(e)
        
        # Update session status
        session["status"] = "COMPLETED"
        
        return result
    
    def delete_session(self, session_id: str) -> bool:
        """Delete an import session."""
        if session_id in self._import_sessions:
            del self._import_sessions[session_id]
            return True
        return False

