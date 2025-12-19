"""
Suggestion service for V4 target-first workflow.

Core AI logic for:
- Generating suggestions for all columns in a target table
- Finding matching source fields via vector search
- Rewriting SQL patterns with user's source columns via LLM
- Approving, editing, rejecting suggestions
- Creating mappings from approved suggestions

This is the heart of the target-first workflow.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
from backend.models.suggestion import (
    MappingSuggestion,
    MappingSuggestionCreate,
    SuggestionApproveRequest,
    SuggestionEditRequest,
    SuggestionRejectRequest,
    SuggestionStatus,
    MatchedSourceField,
    SQLChange,
    SuggestionWarning
)
from backend.models.project import TableMappingStatus
from backend.services.config_service import ConfigService

# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=4)


class SuggestionService:
    """Service for generating and managing AI mapping suggestions."""
    
    def __init__(self):
        """Initialize the suggestion service."""
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
        catalog = config.database.catalog
        schema = config.database.schema
        
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "projects_table": f"{catalog}.{schema}.mapping_projects",
            "target_table_status_table": f"{catalog}.{schema}.target_table_status",
            "semantic_fields_table": f"{catalog}.{schema}.semantic_fields",
            "mapping_suggestions_table": f"{catalog}.{schema}.mapping_suggestions",
            "mapped_fields_table": f"{catalog}.{schema}.mapped_fields",
            "unmapped_fields_table": f"{catalog}.{schema}.unmapped_fields",
            "mapping_feedback_table": f"{catalog}.{schema}.mapping_feedback"
        }
    
    def _get_vector_search_config(self) -> Dict[str, str]:
        """Get vector search configuration."""
        config = self.config_service.get_config()
        return {
            "endpoint_name": config.vector_search.endpoint_name,
            "unmapped_fields_index": config.vector_search.unmapped_fields_index,
            "mapped_fields_index": config.vector_search.mapped_fields_index
        }
    
    def _get_llm_config(self) -> Dict[str, str]:
        """Get LLM configuration."""
        config = self.config_service.get_config()
        return {
            "endpoint_name": config.ai_model.foundation_model_endpoint
        }
    
    def _get_sql_connection(self, server_hostname: str, http_path: str):
        """Get SQL connection using OAuth."""
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
    # VECTOR SEARCH: Find matching source fields
    # =========================================================================
    
    def _vector_search_source_fields_sync(
        self,
        endpoint_name: str,
        index_name: str,
        query_text: str,
        project_id: int,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Vector search for matching source fields (synchronous).
        
        Searches unmapped_fields for fields matching the query description.
        Filters by project_id to only return user's source fields.
        """
        print(f"[Suggestion Service] Vector search for: {query_text[:50]}...")
        
        try:
            # Use vector search to find similar source fields
            results = self.workspace_client.vector_search_indexes.query_index(
                index_name=index_name,
                columns=[
                    "unmapped_field_id",
                    "src_table_name",
                    "src_table_physical_name", 
                    "src_column_name",
                    "src_column_physical_name",
                    "src_comments",
                    "src_physical_datatype",
                    "domain",
                    "source_semantic_field"
                ],
                query_text=query_text,
                num_results=num_results * 2,  # Get extra to filter by project
                filters={"project_id": project_id}  # Filter by project
            )
            
            matches = []
            for item in results.result.data_array:
                # Parse the result based on column order
                if len(item) >= 9:
                    match = {
                        "unmapped_field_id": item[0],
                        "src_table_name": item[1],
                        "src_table_physical_name": item[2],
                        "src_column_name": item[3],
                        "src_column_physical_name": item[4],
                        "src_comments": item[5],
                        "src_physical_datatype": item[6],
                        "domain": item[7],
                        "score": item[-1] if isinstance(item[-1], (int, float)) else 0.0
                    }
                    matches.append(match)
            
            # Take top N results
            matches = matches[:num_results]
            print(f"[Suggestion Service] Found {len(matches)} matching source fields")
            
            return matches
            
        except Exception as e:
            print(f"[Suggestion Service] Vector search error: {str(e)}")
            # Fall back to SQL-based search if vector search fails
            return []
    
    def _sql_search_source_fields_sync(
        self,
        server_hostname: str,
        http_path: str,
        unmapped_fields_table: str,
        search_description: str,
        project_id: int,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        SQL-based fallback search for source fields (synchronous).
        
        Uses LIKE matching on description when vector search is unavailable.
        """
        print(f"[Suggestion Service] SQL fallback search for: {search_description[:50]}...")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Extract keywords from description
                keywords = search_description.lower().split()[:5]
                like_conditions = " OR ".join([
                    f"LOWER(src_comments) LIKE '%{self._escape_sql(kw)}%'"
                    for kw in keywords if len(kw) > 3
                ])
                
                if not like_conditions:
                    like_conditions = "1=1"
                
                query = f"""
                SELECT 
                    unmapped_field_id,
                    src_table_name,
                    src_table_physical_name,
                    src_column_name,
                    src_column_physical_name,
                    src_comments,
                    src_physical_datatype,
                    domain
                FROM {unmapped_fields_table}
                WHERE project_id = {project_id}
                  AND mapping_status = 'PENDING'
                  AND ({like_conditions})
                LIMIT {num_results}
                """
                
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                matches = []
                for row in rows:
                    match = dict(zip(columns, row))
                    match["score"] = 0.5  # Default score for SQL search
                    matches.append(match)
                
                print(f"[Suggestion Service] SQL search found {len(matches)} fields")
                return matches
                
        except Exception as e:
            print(f"[Suggestion Service] SQL search error: {str(e)}")
            return []
        finally:
            connection.close()
    
    # =========================================================================
    # LLM: Rewrite SQL with user's source columns
    # =========================================================================
    
    def _rewrite_sql_with_llm_sync(
        self,
        llm_endpoint: str,
        pattern_sql: str,
        join_metadata: Optional[str],
        pattern_descriptions: str,
        matched_sources: List[Dict[str, Any]],
        target_column: str
    ) -> Dict[str, Any]:
        """
        Use LLM to rewrite pattern SQL with user's source columns.
        
        Returns rewritten SQL, changes made, and confidence.
        """
        print(f"[Suggestion Service] Rewriting SQL for: {target_column}")
        
        # Parse join_metadata if available
        metadata = {}
        if join_metadata:
            try:
                metadata = json.loads(join_metadata)
            except:
                pass
        
        # Build matched sources description
        source_info = []
        for src in matched_sources:
            source_info.append(
                f"- {src.get('src_table_physical_name', 'UNKNOWN')}.{src.get('src_column_physical_name', 'UNKNOWN')}"
                f"\n  Description: {src.get('src_comments', 'N/A')}"
                f"\n  Type: {src.get('src_physical_datatype', 'STRING')}"
            )
        
        sources_text = "\n".join(source_info) if source_info else "No matching sources found"
        
        # Identify silver tables (constant) from metadata or SQL
        silver_tables = metadata.get("silverTables", [])
        silver_text = "\n".join([
            f"- {t.get('schema', 'silver')}.{t.get('name', '')} AS {t.get('alias', '')} (DO NOT CHANGE)"
            for t in silver_tables
        ]) if silver_tables else "Silver tables: Keep any tables from 'silver_*' schemas unchanged"
        
        prompt = f"""You are rewriting a SQL mapping template by replacing source columns with the user's columns.

TARGET COLUMN: {target_column}

ORIGINAL SQL TEMPLATE:
```sql
{pattern_sql}
```

ORIGINAL COLUMN DESCRIPTIONS FROM PATTERN:
{pattern_descriptions}

USER'S MATCHING SOURCE COLUMNS:
{sources_text}

SILVER TABLES (CONSTANT - DO NOT MODIFY):
{silver_text}

RULES:
1. Silver tables (from silver_* schemas) and their columns stay EXACTLY as-is
2. Replace bronze table names with user's source tables
3. Replace bronze column names with user's source columns based on description matching
4. Keep all JOINs, WHERE clauses, UNION structure intact
5. Keep all transformations (TRIM, INITCAP, CONCAT, etc.)
6. If you cannot find a matching source column, note it in warnings

Return ONLY valid JSON with this structure:
{{
  "rewritten_sql": "<the complete rewritten SQL>",
  "changes": [
    {{"type": "table_replace", "original": "<old>", "new": "<new>"}},
    {{"type": "column_replace", "original": "<old>", "new": "<new>"}}
  ],
  "warnings": ["<any issues or unmatched columns>"],
  "confidence": 0.0-1.0,
  "reasoning": "<brief explanation of changes made>"
}}"""

        try:
            response = self.workspace_client.serving_endpoints.query(
                name=llm_endpoint,
                messages=[
                    ChatMessage(role=ChatMessageRole.USER, content=prompt)
                ],
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content
            
            # Parse JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
                print(f"[Suggestion Service] SQL rewritten with confidence: {result.get('confidence', 0)}")
                return result
            else:
                return {
                    "rewritten_sql": pattern_sql,
                    "changes": [],
                    "warnings": ["Failed to parse LLM response"],
                    "confidence": 0.3,
                    "reasoning": "LLM response could not be parsed"
                }
                
        except Exception as e:
            print(f"[Suggestion Service] LLM error: {str(e)}")
            return {
                "rewritten_sql": pattern_sql,
                "changes": [],
                "warnings": [f"LLM error: {str(e)}"],
                "confidence": 0.2,
                "reasoning": "LLM call failed"
            }
    
    # =========================================================================
    # GENERATE SUGGESTIONS FOR TABLE
    # =========================================================================
    
    def _generate_suggestions_for_table_sync(
        self,
        db_config: Dict[str, str],
        vs_config: Dict[str, str],
        llm_config: Dict[str, str],
        project_id: int,
        target_table_status_id: int,
        tgt_table_physical_name: str
    ) -> Dict[str, Any]:
        """
        Generate suggestions for all columns in a target table (synchronous).
        
        This is the main AI discovery process:
        1. Get all target columns from semantic_fields
        2. For each column, find past pattern from mapped_fields
        3. Vector search for matching source fields
        4. LLM rewrites SQL with user's sources
        5. Store suggestions in mapping_suggestions
        """
        print(f"[Suggestion Service] Generating suggestions for table: {tgt_table_physical_name}")
        
        connection = self._get_sql_connection(
            db_config["server_hostname"],
            db_config["http_path"]
        )
        
        try:
            with connection.cursor() as cursor:
                # Update table status to DISCOVERING
                cursor.execute(f"""
                    UPDATE {db_config['target_table_status_table']}
                    SET 
                        mapping_status = 'DISCOVERING',
                        ai_started_ts = CURRENT_TIMESTAMP()
                    WHERE target_table_status_id = {target_table_status_id}
                """)
                
                # Get all target columns for this table
                cursor.execute(f"""
                    SELECT 
                        semantic_field_id,
                        tgt_table_name,
                        tgt_table_physical_name,
                        tgt_column_name,
                        tgt_column_physical_name,
                        tgt_comments,
                        tgt_physical_datatype,
                        domain
                    FROM {db_config['semantic_fields_table']}
                    WHERE UPPER(tgt_table_physical_name) = UPPER('{self._escape_sql(tgt_table_physical_name)}')
                    ORDER BY tgt_column_name
                """)
                
                columns = [desc[0] for desc in cursor.description]
                target_columns = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                print(f"[Suggestion Service] Processing {len(target_columns)} target columns")
                
                suggestions_created = 0
                patterns_found = 0
                no_pattern = 0
                no_match = 0
                
                for target_col in target_columns:
                    semantic_field_id = target_col["semantic_field_id"]
                    tgt_column_physical = target_col["tgt_column_physical_name"]
                    tgt_comments = target_col.get("tgt_comments", "")
                    
                    print(f"[Suggestion Service] Processing column: {tgt_column_physical}")
                    
                    # Find past pattern for this column
                    cursor.execute(f"""
                        SELECT 
                            mapped_field_id,
                            source_expression,
                            source_tables,
                            source_columns,
                            source_descriptions,
                            source_relationship_type,
                            join_metadata,
                            ai_reasoning,
                            confidence_score
                        FROM {db_config['mapped_fields_table']}
                        WHERE UPPER(tgt_table_physical_name) = UPPER('{self._escape_sql(tgt_table_physical_name)}')
                          AND UPPER(tgt_column_physical_name) = UPPER('{self._escape_sql(tgt_column_physical)}')
                          AND mapping_status = 'ACTIVE'
                          AND (is_approved_pattern = true OR is_approved_pattern IS NULL)
                        ORDER BY confidence_score DESC
                        LIMIT 1
                    """)
                    
                    pattern_row = cursor.fetchone()
                    
                    # Initialize suggestion data
                    suggestion_data = {
                        "project_id": project_id,
                        "target_table_status_id": target_table_status_id,
                        "semantic_field_id": semantic_field_id,
                        "tgt_table_name": target_col["tgt_table_name"],
                        "tgt_table_physical_name": target_col["tgt_table_physical_name"],
                        "tgt_column_name": target_col["tgt_column_name"],
                        "tgt_column_physical_name": tgt_column_physical,
                        "tgt_comments": tgt_comments,
                        "tgt_physical_datatype": target_col.get("tgt_physical_datatype"),
                        "pattern_mapped_field_id": None,
                        "pattern_type": None,
                        "pattern_sql": None,
                        "matched_source_fields": "[]",
                        "suggested_sql": None,
                        "sql_changes": "[]",
                        "confidence_score": None,
                        "ai_reasoning": None,
                        "warnings": "[]",
                        "suggestion_status": "NO_PATTERN"
                    }
                    
                    if pattern_row:
                        patterns_found += 1
                        pattern_cols = ["mapped_field_id", "source_expression", "source_tables", 
                                       "source_columns", "source_descriptions", "source_relationship_type",
                                       "join_metadata", "ai_reasoning", "confidence_score"]
                        pattern = dict(zip(pattern_cols, pattern_row))
                        
                        suggestion_data["pattern_mapped_field_id"] = pattern["mapped_field_id"]
                        suggestion_data["pattern_type"] = pattern["source_relationship_type"]
                        suggestion_data["pattern_sql"] = pattern["source_expression"]
                        
                        # Build search query from target description + pattern descriptions
                        search_query = f"{tgt_comments} {pattern.get('source_descriptions', '')}"
                        
                        # Vector search for matching source fields
                        matched_sources = self._vector_search_source_fields_sync(
                            vs_config["endpoint_name"],
                            vs_config["unmapped_fields_index"],
                            search_query,
                            project_id,
                            num_results=5
                        )
                        
                        # Fallback to SQL search if vector search returns nothing
                        if not matched_sources:
                            matched_sources = self._sql_search_source_fields_sync(
                                db_config["server_hostname"],
                                db_config["http_path"],
                                db_config["unmapped_fields_table"],
                                search_query,
                                project_id,
                                num_results=5
                            )
                        
                        if matched_sources:
                            # Store matched source fields
                            matched_fields_json = json.dumps([
                                {
                                    "unmapped_field_id": m["unmapped_field_id"],
                                    "src_table_name": m.get("src_table_name", ""),
                                    "src_table_physical_name": m.get("src_table_physical_name", ""),
                                    "src_column_name": m.get("src_column_name", ""),
                                    "src_column_physical_name": m.get("src_column_physical_name", ""),
                                    "src_comments": m.get("src_comments", ""),
                                    "src_physical_datatype": m.get("src_physical_datatype", ""),
                                    "match_score": m.get("score", 0.5)
                                }
                                for m in matched_sources
                            ])
                            suggestion_data["matched_source_fields"] = matched_fields_json
                            
                            # Rewrite SQL with LLM
                            rewrite_result = self._rewrite_sql_with_llm_sync(
                                llm_config["endpoint_name"],
                                pattern["source_expression"],
                                pattern.get("join_metadata"),
                                pattern.get("source_descriptions", ""),
                                matched_sources,
                                tgt_column_physical
                            )
                            
                            suggestion_data["suggested_sql"] = rewrite_result.get("rewritten_sql")
                            suggestion_data["sql_changes"] = json.dumps(rewrite_result.get("changes", []))
                            suggestion_data["confidence_score"] = rewrite_result.get("confidence", 0.5)
                            suggestion_data["ai_reasoning"] = rewrite_result.get("reasoning", "")
                            suggestion_data["warnings"] = json.dumps(rewrite_result.get("warnings", []))
                            suggestion_data["suggestion_status"] = "PENDING"
                        else:
                            # Pattern found but no matching sources
                            no_match += 1
                            suggestion_data["suggestion_status"] = "NO_MATCH"
                            suggestion_data["warnings"] = json.dumps(["No matching source fields found for this pattern"])
                    else:
                        # No pattern found
                        no_pattern += 1
                        suggestion_data["suggestion_status"] = "NO_PATTERN"
                    
                    # Insert suggestion
                    cursor.execute(f"""
                        INSERT INTO {db_config['mapping_suggestions_table']} (
                            project_id,
                            target_table_status_id,
                            semantic_field_id,
                            tgt_table_name,
                            tgt_table_physical_name,
                            tgt_column_name,
                            tgt_column_physical_name,
                            tgt_comments,
                            tgt_physical_datatype,
                            pattern_mapped_field_id,
                            pattern_type,
                            pattern_sql,
                            matched_source_fields,
                            suggested_sql,
                            sql_changes,
                            confidence_score,
                            ai_reasoning,
                            warnings,
                            suggestion_status,
                            created_ts
                        ) VALUES (
                            {suggestion_data['project_id']},
                            {suggestion_data['target_table_status_id']},
                            {suggestion_data['semantic_field_id']},
                            '{self._escape_sql(suggestion_data['tgt_table_name'])}',
                            '{self._escape_sql(suggestion_data['tgt_table_physical_name'])}',
                            '{self._escape_sql(suggestion_data['tgt_column_name'])}',
                            '{self._escape_sql(suggestion_data['tgt_column_physical_name'])}',
                            {f"'{self._escape_sql(suggestion_data['tgt_comments'])}'" if suggestion_data['tgt_comments'] else 'NULL'},
                            {f"'{self._escape_sql(suggestion_data['tgt_physical_datatype'])}'" if suggestion_data['tgt_physical_datatype'] else 'NULL'},
                            {suggestion_data['pattern_mapped_field_id'] if suggestion_data['pattern_mapped_field_id'] else 'NULL'},
                            {f"'{suggestion_data['pattern_type']}'" if suggestion_data['pattern_type'] else 'NULL'},
                            {f"'{self._escape_sql(suggestion_data['pattern_sql'])}'" if suggestion_data['pattern_sql'] else 'NULL'},
                            '{self._escape_sql(suggestion_data['matched_source_fields'])}',
                            {f"'{self._escape_sql(suggestion_data['suggested_sql'])}'" if suggestion_data['suggested_sql'] else 'NULL'},
                            '{self._escape_sql(suggestion_data['sql_changes'])}',
                            {suggestion_data['confidence_score'] if suggestion_data['confidence_score'] else 'NULL'},
                            {f"'{self._escape_sql(suggestion_data['ai_reasoning'])}'" if suggestion_data['ai_reasoning'] else 'NULL'},
                            '{self._escape_sql(suggestion_data['warnings'])}',
                            '{suggestion_data['suggestion_status']}',
                            CURRENT_TIMESTAMP()
                        )
                    """)
                    
                    suggestions_created += 1
                
                # Update table status
                pending_count = suggestions_created - no_pattern - no_match
                
                cursor.execute(f"""
                    UPDATE {db_config['target_table_status_table']}
                    SET 
                        mapping_status = 'SUGGESTIONS_READY',
                        ai_completed_ts = CURRENT_TIMESTAMP(),
                        columns_with_pattern = {patterns_found},
                        columns_pending_review = {pending_count},
                        columns_no_match = {no_match}
                    WHERE target_table_status_id = {target_table_status_id}
                """)
                
                print(f"[Suggestion Service] Generated {suggestions_created} suggestions")
                print(f"  Patterns found: {patterns_found}, No pattern: {no_pattern}, No match: {no_match}")
                
                return {
                    "target_table_status_id": target_table_status_id,
                    "suggestions_created": suggestions_created,
                    "patterns_found": patterns_found,
                    "no_pattern": no_pattern,
                    "no_match": no_match,
                    "pending_review": pending_count,
                    "status": "completed"
                }
                
        except Exception as e:
            print(f"[Suggestion Service] Error generating suggestions: {str(e)}")
            
            # Update table status with error
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"""
                        UPDATE {db_config['target_table_status_table']}
                        SET 
                            mapping_status = 'NOT_STARTED',
                            ai_error_message = '{self._escape_sql(str(e)[:500])}'
                        WHERE target_table_status_id = {target_table_status_id}
                    """)
            except:
                pass
            
            raise
        finally:
            connection.close()
    
    async def generate_suggestions_for_table(
        self,
        project_id: int,
        target_table_status_id: int,
        tgt_table_physical_name: str
    ) -> Dict[str, Any]:
        """Generate suggestions for a target table (async wrapper)."""
        db_config = self._get_db_config()
        vs_config = self._get_vector_search_config()
        llm_config = self._get_llm_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._generate_suggestions_for_table_sync,
                db_config,
                vs_config,
                llm_config,
                project_id,
                target_table_status_id,
                tgt_table_physical_name
            )
        )
        
        return result
    
    # =========================================================================
    # GET SUGGESTIONS FOR TABLE
    # =========================================================================
    
    def _get_suggestions_for_table_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapping_suggestions_table: str,
        target_table_status_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all suggestions for a target table (synchronous)."""
        print(f"[Suggestion Service] Fetching suggestions for table: {target_table_status_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                status_clause = ""
                if status_filter:
                    status_clause = f"AND suggestion_status = '{status_filter}'"
                
                query = f"""
                SELECT 
                    suggestion_id,
                    project_id,
                    target_table_status_id,
                    semantic_field_id,
                    tgt_table_name,
                    tgt_table_physical_name,
                    tgt_column_name,
                    tgt_column_physical_name,
                    tgt_comments,
                    tgt_physical_datatype,
                    pattern_mapped_field_id,
                    pattern_type,
                    pattern_sql,
                    matched_source_fields,
                    suggested_sql,
                    sql_changes,
                    confidence_score,
                    ai_reasoning,
                    warnings,
                    suggestion_status,
                    edited_sql,
                    edited_source_fields,
                    edit_notes,
                    rejection_reason,
                    created_mapped_field_id,
                    created_ts,
                    reviewed_by,
                    reviewed_ts
                FROM {mapping_suggestions_table}
                WHERE target_table_status_id = {target_table_status_id}
                {status_clause}
                ORDER BY 
                    CASE suggestion_status 
                        WHEN 'PENDING' THEN 1 
                        WHEN 'NO_MATCH' THEN 2
                        WHEN 'NO_PATTERN' THEN 3
                        ELSE 4 
                    END,
                    confidence_score DESC,
                    tgt_column_name
                """
                
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                suggestions = []
                for row in rows:
                    suggestion = dict(zip(columns, row))
                    suggestions.append(suggestion)
                
                print(f"[Suggestion Service] Found {len(suggestions)} suggestions")
                return suggestions
                
        except Exception as e:
            print(f"[Suggestion Service] Error fetching suggestions: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_suggestions_for_table(
        self, 
        target_table_status_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all suggestions for a target table (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_suggestions_for_table_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["mapping_suggestions_table"],
                target_table_status_id,
                status_filter
            )
        )
        
        return result
    
    # =========================================================================
    # GET SUGGESTION BY ID
    # =========================================================================
    
    def _get_suggestion_by_id_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapping_suggestions_table: str,
        suggestion_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a suggestion by ID (synchronous)."""
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                SELECT *
                FROM {mapping_suggestions_table}
                WHERE suggestion_id = {suggestion_id}
                """
                
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                
                if row:
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            print(f"[Suggestion Service] Error fetching suggestion: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def get_suggestion_by_id(self, suggestion_id: int) -> Optional[Dict[str, Any]]:
        """Get a suggestion by ID (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._get_suggestion_by_id_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["mapping_suggestions_table"],
                suggestion_id
            )
        )
        
        return result
    
    # =========================================================================
    # APPROVE SUGGESTION
    # =========================================================================
    
    def _approve_suggestion_sync(
        self,
        db_config: Dict[str, str],
        suggestion_id: int,
        reviewed_by: str,
        edited_sql: Optional[str] = None,
        edit_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve a suggestion and create a mapping (synchronous).
        
        If edited_sql is provided, uses that instead of suggested_sql.
        Creates a new row in mapped_fields.
        """
        print(f"[Suggestion Service] Approving suggestion: {suggestion_id}")
        
        connection = self._get_sql_connection(
            db_config["server_hostname"],
            db_config["http_path"]
        )
        
        try:
            with connection.cursor() as cursor:
                # Get the suggestion
                cursor.execute(f"""
                    SELECT *
                    FROM {db_config['mapping_suggestions_table']}
                    WHERE suggestion_id = {suggestion_id}
                """)
                
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                
                if not row:
                    return {"error": "Suggestion not found", "suggestion_id": suggestion_id}
                
                suggestion = dict(zip(columns, row))
                
                # Determine which SQL to use
                final_sql = edited_sql if edited_sql else suggestion.get("suggested_sql", "")
                status = "EDITED" if edited_sql else "APPROVED"
                
                # Parse matched source fields for metadata
                matched_sources = []
                if suggestion.get("matched_source_fields"):
                    try:
                        matched_sources = json.loads(suggestion["matched_source_fields"])
                    except:
                        pass
                
                # Build source metadata from matched fields
                source_tables = "|".join([m.get("src_table_name", "") for m in matched_sources[:3]])
                source_tables_physical = "|".join([m.get("src_table_physical_name", "") for m in matched_sources[:3]])
                source_columns = "|".join([m.get("src_column_name", "") for m in matched_sources[:3]])
                source_columns_physical = "|".join([m.get("src_column_physical_name", "") for m in matched_sources[:3]])
                source_descriptions = "|".join([m.get("src_comments", "") for m in matched_sources[:3]])
                source_datatypes = "|".join([m.get("src_physical_datatype", "") for m in matched_sources[:3]])
                
                # Create mapping in mapped_fields
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
                        source_relationship_type,
                        join_metadata,
                        confidence_score,
                        mapping_source,
                        ai_reasoning,
                        ai_generated,
                        mapping_status,
                        mapped_by,
                        mapped_ts,
                        project_id,
                        is_approved_pattern
                    ) VALUES (
                        {suggestion['semantic_field_id']},
                        '{self._escape_sql(suggestion['tgt_table_name'])}',
                        '{self._escape_sql(suggestion['tgt_table_physical_name'])}',
                        '{self._escape_sql(suggestion['tgt_column_name'])}',
                        '{self._escape_sql(suggestion['tgt_column_physical_name'])}',
                        {f"'{self._escape_sql(suggestion['tgt_comments'])}'" if suggestion.get('tgt_comments') else 'NULL'},
                        '{self._escape_sql(final_sql)}',
                        '{self._escape_sql(source_tables)}',
                        '{self._escape_sql(source_tables_physical)}',
                        '{self._escape_sql(source_columns)}',
                        '{self._escape_sql(source_columns_physical)}',
                        '{self._escape_sql(source_descriptions)}',
                        '{self._escape_sql(source_datatypes)}',
                        '{suggestion.get('pattern_type', 'SINGLE')}',
                        {f"'{self._escape_sql(str(suggestion.get('pattern_sql', '')))}'" if suggestion.get('pattern_sql') else 'NULL'},
                        {suggestion.get('confidence_score', 0.8)},
                        'AI',
                        {f"'{self._escape_sql(suggestion.get('ai_reasoning', ''))}'" if suggestion.get('ai_reasoning') else 'NULL'},
                        true,
                        'ACTIVE',
                        '{self._escape_sql(reviewed_by)}',
                        CURRENT_TIMESTAMP(),
                        {suggestion['project_id']},
                        false
                    )
                """)
                
                # Get the created mapping ID
                cursor.execute(f"""
                    SELECT mapped_field_id 
                    FROM {db_config['mapped_fields_table']}
                    WHERE semantic_field_id = {suggestion['semantic_field_id']}
                      AND project_id = {suggestion['project_id']}
                    ORDER BY mapped_ts DESC
                    LIMIT 1
                """)
                mapping_row = cursor.fetchone()
                mapped_field_id = mapping_row[0] if mapping_row else None
                
                # Update suggestion status
                cursor.execute(f"""
                    UPDATE {db_config['mapping_suggestions_table']}
                    SET 
                        suggestion_status = '{status}',
                        edited_sql = {f"'{self._escape_sql(edited_sql)}'" if edited_sql else 'NULL'},
                        edit_notes = {f"'{self._escape_sql(edit_notes)}'" if edit_notes else 'NULL'},
                        created_mapped_field_id = {mapped_field_id if mapped_field_id else 'NULL'},
                        reviewed_by = '{self._escape_sql(reviewed_by)}',
                        reviewed_ts = CURRENT_TIMESTAMP()
                    WHERE suggestion_id = {suggestion_id}
                """)
                
                # Update source field status to MAPPED
                for src in matched_sources:
                    if src.get("unmapped_field_id"):
                        cursor.execute(f"""
                            UPDATE {db_config['unmapped_fields_table']}
                            SET 
                                mapping_status = 'MAPPED',
                                mapped_field_id = {mapped_field_id if mapped_field_id else 'NULL'}
                            WHERE unmapped_field_id = {src['unmapped_field_id']}
                        """)
                
                print(f"[Suggestion Service] Approved suggestion {suggestion_id}, created mapping {mapped_field_id}")
                
                return {
                    "suggestion_id": suggestion_id,
                    "mapped_field_id": mapped_field_id,
                    "status": status,
                    "target_table_status_id": suggestion["target_table_status_id"]
                }
                
        except Exception as e:
            print(f"[Suggestion Service] Error approving suggestion: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def approve_suggestion(
        self, 
        suggestion_id: int, 
        request: SuggestionApproveRequest
    ) -> Dict[str, Any]:
        """Approve a suggestion (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._approve_suggestion_sync,
                db_config,
                suggestion_id,
                request.reviewed_by
            )
        )
        
        return result
    
    async def edit_and_approve_suggestion(
        self, 
        suggestion_id: int, 
        request: SuggestionEditRequest
    ) -> Dict[str, Any]:
        """Edit and approve a suggestion (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._approve_suggestion_sync,
                db_config,
                suggestion_id,
                request.reviewed_by,
                request.edited_sql,
                request.edit_notes
            )
        )
        
        return result
    
    # =========================================================================
    # REJECT SUGGESTION
    # =========================================================================
    
    def _reject_suggestion_sync(
        self,
        db_config: Dict[str, str],
        suggestion_id: int,
        reviewed_by: str,
        rejection_reason: str
    ) -> Dict[str, Any]:
        """
        Reject a suggestion and record feedback (synchronous).
        
        Records rejection in mapping_feedback for AI learning.
        """
        print(f"[Suggestion Service] Rejecting suggestion: {suggestion_id}")
        
        connection = self._get_sql_connection(
            db_config["server_hostname"],
            db_config["http_path"]
        )
        
        try:
            with connection.cursor() as cursor:
                # Get the suggestion
                cursor.execute(f"""
                    SELECT *
                    FROM {db_config['mapping_suggestions_table']}
                    WHERE suggestion_id = {suggestion_id}
                """)
                
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                
                if not row:
                    return {"error": "Suggestion not found"}
                
                suggestion = dict(zip(columns, row))
                
                # Update suggestion status
                cursor.execute(f"""
                    UPDATE {db_config['mapping_suggestions_table']}
                    SET 
                        suggestion_status = 'REJECTED',
                        rejection_reason = '{self._escape_sql(rejection_reason)}',
                        reviewed_by = '{self._escape_sql(reviewed_by)}',
                        reviewed_ts = CURRENT_TIMESTAMP()
                    WHERE suggestion_id = {suggestion_id}
                """)
                
                # Record in mapping_feedback for AI learning
                matched_sources = []
                if suggestion.get("matched_source_fields"):
                    try:
                        matched_sources = json.loads(suggestion["matched_source_fields"])
                    except:
                        pass
                
                if matched_sources:
                    src = matched_sources[0]  # Primary matched source
                    cursor.execute(f"""
                        INSERT INTO {db_config['mapping_feedback_table']} (
                            suggested_src_table,
                            suggested_src_column,
                            suggested_tgt_table,
                            suggested_tgt_column,
                            src_comments,
                            src_datatype,
                            tgt_comments,
                            ai_confidence_score,
                            ai_reasoning,
                            feedback_action,
                            user_comments,
                            domain,
                            feedback_by,
                            feedback_ts
                        ) VALUES (
                            '{self._escape_sql(src.get('src_table_physical_name', ''))}',
                            '{self._escape_sql(src.get('src_column_physical_name', ''))}',
                            '{self._escape_sql(suggestion['tgt_table_physical_name'])}',
                            '{self._escape_sql(suggestion['tgt_column_physical_name'])}',
                            {f"'{self._escape_sql(src.get('src_comments', ''))}'" if src.get('src_comments') else 'NULL'},
                            {f"'{self._escape_sql(src.get('src_physical_datatype', ''))}'" if src.get('src_physical_datatype') else 'NULL'},
                            {f"'{self._escape_sql(suggestion.get('tgt_comments', ''))}'" if suggestion.get('tgt_comments') else 'NULL'},
                            {suggestion.get('confidence_score') if suggestion.get('confidence_score') else 'NULL'},
                            {f"'{self._escape_sql(suggestion.get('ai_reasoning', ''))}'" if suggestion.get('ai_reasoning') else 'NULL'},
                            'REJECTED',
                            '{self._escape_sql(rejection_reason)}',
                            NULL,
                            '{self._escape_sql(reviewed_by)}',
                            CURRENT_TIMESTAMP()
                        )
                    """)
                
                print(f"[Suggestion Service] Rejected suggestion: {suggestion_id}")
                
                return {
                    "suggestion_id": suggestion_id,
                    "status": "REJECTED",
                    "target_table_status_id": suggestion["target_table_status_id"]
                }
                
        except Exception as e:
            print(f"[Suggestion Service] Error rejecting suggestion: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def reject_suggestion(
        self, 
        suggestion_id: int, 
        request: SuggestionRejectRequest
    ) -> Dict[str, Any]:
        """Reject a suggestion (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._reject_suggestion_sync,
                db_config,
                suggestion_id,
                request.reviewed_by,
                request.rejection_reason
            )
        )
        
        return result
    
    # =========================================================================
    # SKIP SUGGESTION
    # =========================================================================
    
    def _skip_suggestion_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapping_suggestions_table: str,
        suggestion_id: int,
        reviewed_by: str
    ) -> Dict[str, Any]:
        """Skip a suggestion (synchronous)."""
        print(f"[Suggestion Service] Skipping suggestion: {suggestion_id}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Get target_table_status_id before updating
                cursor.execute(f"""
                    SELECT target_table_status_id
                    FROM {mapping_suggestions_table}
                    WHERE suggestion_id = {suggestion_id}
                """)
                row = cursor.fetchone()
                target_table_status_id = row[0] if row else None
                
                cursor.execute(f"""
                    UPDATE {mapping_suggestions_table}
                    SET 
                        suggestion_status = 'SKIPPED',
                        reviewed_by = '{self._escape_sql(reviewed_by)}',
                        reviewed_ts = CURRENT_TIMESTAMP()
                    WHERE suggestion_id = {suggestion_id}
                """)
                
                return {
                    "suggestion_id": suggestion_id,
                    "status": "SKIPPED",
                    "target_table_status_id": target_table_status_id
                }
                
        except Exception as e:
            print(f"[Suggestion Service] Error skipping suggestion: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def skip_suggestion(
        self, 
        suggestion_id: int, 
        request: SuggestionRejectRequest
    ) -> Dict[str, Any]:
        """Skip a suggestion (async wrapper)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._skip_suggestion_sync,
                db_config["server_hostname"],
                db_config["http_path"],
                db_config["mapping_suggestions_table"],
                suggestion_id,
                request.reviewed_by
            )
        )
        
        return result

