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
from backend.services.vector_search_service import VectorSearchService
from backend.services.pattern_service import PatternService

# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=4)

import re

def clean_llm_json(text: str) -> str:
    """
    Clean LLM response text to extract valid JSON.
    
    Handles common issues:
    - Control characters (null bytes, form feeds, etc.)
    - Windows line endings
    - Trailing commas in JSON
    - Markdown code blocks
    - Literal newlines inside JSON string values (must be escaped as \\n)
    """
    if not text:
        return ""
    
    # Extract JSON from markdown code blocks if present
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if code_block_match:
        text = code_block_match.group(1).strip()
    
    # Find the JSON object
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    
    if json_start < 0 or json_end <= json_start:
        return ""
    
    json_str = text[json_start:json_end]
    
    # Remove control characters (except newlines and tabs)
    # \x00-\x08: null through backspace
    # \x0b: vertical tab
    # \x0c: form feed
    # \x0e-\x1f: shift out through unit separator
    # \x7f: DEL
    json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json_str)
    
    # Normalize line endings
    json_str = json_str.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove trailing commas before closing braces/brackets (common LLM mistake)
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    
    # Fix literal newlines inside JSON string values
    # This is the tricky part - LLMs often put actual newlines in SQL strings
    # We need to escape them as \n for valid JSON
    # Strategy: Replace newlines that appear to be inside string values
    
    # Approach: Process character by character to handle strings properly
    result = []
    in_string = False
    escape_next = False
    
    for char in json_str:
        if escape_next:
            result.append(char)
            escape_next = False
            continue
            
        if char == '\\':
            result.append(char)
            escape_next = True
            continue
            
        if char == '"' and not escape_next:
            in_string = not in_string
            result.append(char)
            continue
        
        # If we're inside a string and hit a newline, escape it
        if in_string and char == '\n':
            result.append('\\n')
            continue
        
        # If we're inside a string and hit a tab, escape it  
        if in_string and char == '\t':
            result.append('\\t')
            continue
            
        result.append(char)
    
    return ''.join(result)


def filter_false_positive_warnings(warnings: List[str], changes: List[Dict[str, Any]]) -> List[str]:
    """
    Filter out warnings that mention columns which were actually successfully replaced.
    
    LLMs sometimes incorrectly list columns as "not found" even though they appear
    in the changes array as successfully replaced. This filters those out.
    
    Args:
        warnings: List of warning strings from LLM
        changes: List of change objects with 'original', 'new', 'type' fields
        
    Returns:
        Filtered list of warnings
    """
    if not warnings or not changes:
        return warnings
    
    # Build set of column names that were successfully replaced (case-insensitive)
    replaced_columns = set()
    for change in changes:
        if change.get("type") == "column_replace" or change.get("new"):
            original = change.get("original", "")
            # Extract just the column name (handle TABLE.COLUMN format)
            if "." in original:
                original = original.split(".")[-1]
            if original:
                replaced_columns.add(original.upper())
    
    if not replaced_columns:
        return warnings
    
    # Filter out warnings that mention successfully replaced columns
    filtered_warnings = []
    for warning in warnings:
        warning_upper = warning.upper()
        # Check if any replaced column is mentioned in this warning
        is_false_positive = False
        for col in replaced_columns:
            # Check various patterns: column name alone or with table prefix
            if col in warning_upper:
                # Make sure it's a word boundary match (not part of another word)
                import re
                pattern = r'\b' + re.escape(col) + r'\b'
                if re.search(pattern, warning_upper):
                    is_false_positive = True
                    break
        
        if not is_false_positive:
            filtered_warnings.append(warning)
    
    if len(warnings) != len(filtered_warnings):
        print(f"[Suggestion Service] Filtered {len(warnings) - len(filtered_warnings)} false positive warnings")
    
    return filtered_warnings


class SuggestionService:
    """Service for generating and managing AI mapping suggestions."""
    
    def __init__(self):
        """Initialize the suggestion service."""
        self.config_service = ConfigService()
        self.vector_search_service = VectorSearchService()
        self.pattern_service = PatternService()
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
        db = config.database
        
        return {
            "server_hostname": db.server_hostname,
            "http_path": db.http_path,
            "projects_table": db.mapping_projects_table,
            "target_table_status_table": db.target_table_status_table,
            "semantic_fields_table": db.semantic_fields_table,
            "mapping_suggestions_table": db.mapping_suggestions_table,
            "mapped_fields_table": db.mapped_fields_table,
            "unmapped_fields_table": db.unmapped_fields_table,
            "mapping_feedback_table": db.mapping_feedback_table
        }
    
    def _get_vector_search_config(self) -> Dict[str, str]:
        """Get vector search configuration."""
        config = self.config_service.get_config()
        return {
            "endpoint_name": config.vector_search.endpoint_name,
            "unmapped_fields_index": config.vector_search.unmapped_fields_index
        }
    
    def _get_llm_config(self) -> Dict[str, str]:
        """Get LLM configuration."""
        config = self.config_service.get_config()
        return {
            "endpoint_name": config.ai_model.foundation_model_endpoint
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
                print(f"[Suggestion Service] Could not get OAuth token: {e}")
        
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
    # VECTOR SEARCH: Find matching source fields
    # =========================================================================
    
    def _build_vs_query(self, description: str, project_id: int, column_name: str = "") -> str:
        """
        Build a vector search query string with project context.
        
        Format: PROJECT: {id} | DESCRIPTION: {desc} | COLUMN: {name}
        This format matches the indexed source_semantic_field for better similarity.
        """
        parts = [f"PROJECT: {project_id}"]
        if description:
            parts.append(f"DESCRIPTION: {description}")
        if column_name:
            parts.append(f"COLUMN: {column_name}")
        return " | ".join(parts)
    
    def _vector_search_single_query_sync(
        self,
        index_name: str,
        query_text: str,
        project_id: int,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Execute a single vector search query (synchronous).
        
        Returns matches filtered by project_id.
        
        Note: We over-fetch significantly because with many projects having similar
        columns, the top results may be spread across projects. The PROJECT prefix
        in the query boosts same-project results, but we still filter to be certain.
        """
        # Over-fetch multiplier: With N projects having similar columns,
        # we need to fetch N * num_results to ensure we get enough from target project.
        # Using 10x as a safe default for up to ~10 similar projects.
        OVER_FETCH_MULTIPLIER = 10
        
        try:
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
                    "source_semantic_field",
                    "project_id"
                ],
                query_text=query_text,
                num_results=num_results * OVER_FETCH_MULTIPLIER  # Fetch 10x to ensure coverage across many projects
            )
            
            matches = []
            total_raw = 0
            other_projects = 0
            
            for item in results.result.data_array:
                if len(item) >= 10:
                    total_raw += 1
                    item_project_id = item[9]
                    score = item[-1] if isinstance(item[-1], (int, float)) else 0.0
                    
                    # Filter by project_id
                    if project_id is not None and item_project_id != project_id:
                        other_projects += 1
                        continue
                    
                    match = {
                        "unmapped_field_id": item[0],
                        "src_table_name": item[1],
                        "src_table_physical_name": item[2],
                        "src_column_name": item[3],
                        "src_column_physical_name": item[4],
                        "src_comments": item[5],
                        "src_physical_datatype": item[6],
                        "domain": item[7],
                        "project_id": item[9],
                        "score": score
                    }
                    matches.append(match)
                    
                    if len(matches) >= num_results:
                        break
            
            # Log filter efficiency
            if other_projects > 0:
                print(f"[VS Single] Raw: {total_raw}, filtered out {other_projects} from other projects, kept {len(matches)} for project {project_id}")
            
            return matches
            
        except Exception as e:
            print(f"[VS] Single query error: {e}")
            return []
    
    def _vector_search_parallel_sync(
        self,
        index_name: str,
        columns_to_search: List[Dict[str, str]],
        project_id: int,
        num_results_per_column: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Execute parallel vector searches for multiple columns.
        
        Args:
            index_name: Vector search index name
            columns_to_search: List of {description, column_name, role} dicts
            project_id: Project ID to filter results
            num_results_per_column: Results per search
            
        Returns:
            Merged and deduplicated list of matches
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        print(f"[VS Parallel] Starting {len(columns_to_search)} parallel searches for project {project_id}")
        
        all_matches = []
        seen_ids = set()
        
        # Store for debugging
        self._last_parallel_searches = []
        
        def search_column(col_info: Dict[str, str]) -> List[Dict[str, Any]]:
            """Search for a single column."""
            query = self._build_vs_query(
                col_info.get('description', ''),
                project_id,
                col_info.get('column_name', '')
            )
            results = self._vector_search_single_query_sync(
                index_name, query, project_id, num_results_per_column
            )
            return {
                "query": query,
                "role": col_info.get('role', 'unknown'),
                "results": results
            }
        
        # Execute searches in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(len(columns_to_search), 5)) as executor:
            futures = {executor.submit(search_column, col): col for col in columns_to_search}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    self._last_parallel_searches.append({
                        "query": result["query"],
                        "role": result["role"],
                        "count": len(result["results"]),
                        "columns": [f"{r['src_table_physical_name']}.{r['src_column_physical_name']}" for r in result["results"][:3]]
                    })
                    
                    # Merge results, avoiding duplicates
                    for match in result["results"]:
                        field_id = match["unmapped_field_id"]
                        if field_id not in seen_ids:
                            seen_ids.add(field_id)
                            all_matches.append(match)
                            
                except Exception as e:
                    print(f"[VS Parallel] Search error: {e}")
        
        # Sort by score descending
        all_matches.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        print(f"[VS Parallel] Completed: {len(all_matches)} unique matches from {len(columns_to_search)} searches")
        for search_result in self._last_parallel_searches:
            print(f"[VS Parallel]   {search_result['role']}: {search_result['count']} results - {search_result['columns']}")
        
        return all_matches
    
    def _vector_search_source_fields_sync(
        self,
        endpoint_name: str,
        index_name: str,
        query_text: str,
        project_id: int,
        num_results: int = 5,
        columns_to_map: List[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Vector search for matching source fields (synchronous).
        
        If columns_to_map is provided, uses parallel searches for each column.
        Otherwise, falls back to single combined search.
        
        Args:
            endpoint_name: Vector search endpoint
            index_name: Index to search
            query_text: Combined query text (used if columns_to_map not provided)
            project_id: Project ID to filter results
            num_results: Number of results to return
            columns_to_map: Optional list of columns from join_metadata for parallel search
        """
        # If we have specific columns to search, use parallel search
        if columns_to_map and len(columns_to_map) > 0:
            print(f"[VS] Using parallel search for {len(columns_to_map)} columns")
            return self._vector_search_parallel_sync(
                index_name,
                columns_to_map,
                project_id,
                num_results_per_column=5
            )
        
        # Fall back to single combined search
        # Build query with project context
        query_with_project = self._build_vs_query(query_text, project_id)
        
        # Store for debugging
        self._last_vector_search = {
            "query_text": query_with_project,
            "original_query": query_text,
            "project_id": project_id,
            "num_results": num_results,
            "raw_results": [],
            "filtered_results": []
        }
        
        # Over-fetch multiplier for many projects with similar columns
        OVER_FETCH_MULTIPLIER = 10
        
        print(f"[VS Debug] Query: {query_with_project[:200]}...")
        print(f"[VS Debug] Requesting {num_results * OVER_FETCH_MULTIPLIER} results, filtering to project {project_id}")
        
        # Log equivalent Databricks SQL for debugging
        escaped_query = query_with_project.replace("'", "''")[:500]
        sql_equivalent = f"""
-- Databricks SQL equivalent for vector search debugging:
SELECT * FROM VECTOR_SEARCH(
    index => '{index_name}',
    query => '{escaped_query}',
    num_results => {num_results * 3}
)
WHERE project_id = {project_id}
ORDER BY score DESC
LIMIT {num_results};
"""
        self._last_vector_search["sql_equivalent"] = sql_equivalent
        
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
                    "source_semantic_field",
                    "project_id"
                ],
                query_text=query_with_project,
                num_results=num_results * OVER_FETCH_MULTIPLIER  # Fetch 10x to ensure coverage across many projects
            )
            
            print(f"[VS Debug] Raw results count: {len(results.result.data_array) if results.result.data_array else 0}")
            
            matches = []
            all_raw = []
            
            for item in results.result.data_array:
                # Parse the result based on column order
                if len(item) >= 10:
                    item_project_id = item[9]
                    score = item[-1] if isinstance(item[-1], (int, float)) else 0.0
                    
                    raw_match = {
                        "column": f"{item[2]}.{item[4]}",
                        "description": str(item[5])[:50] if item[5] else "",
                        "project_id": item_project_id,
                        "score": score
                    }
                    all_raw.append(raw_match)
                    
                    # Filter by project_id after getting results
                    if project_id is not None and item_project_id != project_id:
                        continue
                    
                    match = {
                        "unmapped_field_id": item[0],
                        "src_table_name": item[1],
                        "src_table_physical_name": item[2],
                        "src_column_name": item[3],
                        "src_column_physical_name": item[4],
                        "src_comments": item[5],
                        "src_physical_datatype": item[6],
                        "domain": item[7],
                        "project_id": item[9],
                        "score": score
                    }
                    matches.append(match)
                    
                    # Stop once we have enough matches
                    if len(matches) >= num_results:
                        break
            
            self._last_vector_search["raw_results"] = all_raw
            
            # Log what columns we found
            print(f"[VS Debug] All raw results:")
            for r in all_raw[:20]:
                print(f"[VS Debug]   {r['column']} (proj={r['project_id']}, score={r['score']:.3f}): {r['description']}")
            
            # Take top N results (in case we got more)
            matches = matches[:num_results]
            self._last_vector_search["filtered_results"] = [
                {"column": f"{m['src_table_physical_name']}.{m['src_column_physical_name']}", "score": m['score']}
                for m in matches
            ]
            
            print(f"[VS Debug] After project filter: {len(matches)} matches")
            
            return matches
            
        except Exception as e:
            print(f"[Suggestion Service] Vector search error: {str(e)}")
            import traceback
            traceback.print_exc()
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
                  AND mapping_status IN ('PENDING', 'UNMAPPED')
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
            f"- {t.get('physicalName', 'silver.*')} AS {t.get('alias', '')} (DO NOT CHANGE)"
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
1. Tables containing "silver" in their path are CONSTANT - DO NOT modify ANY columns from silver tables
2. Only replace columns from bronze/source tables (tables NOT containing "silver" in their path)
3. Replace bronze table names with user's source tables
4. Replace bronze column names with user's source columns based on description matching
5. Keep all JOINs, WHERE clauses, UNION structure intact
6. Keep all transformations (TRIM, INITCAP, CONCAT, etc.)

WARNINGS RULES:
- ONLY warn about PATTERN columns (columns in the original SQL template) that you could NOT find a matching source column for
- Do NOT warn about extra source columns that were provided but not needed
- NEVER warn about silver table columns (any table with "silver" in the path)
- Pattern columns to match are ONLY those from bronze tables in the original SQL, NOT the source columns provided

Return ONLY valid JSON with this structure:
{{
  "rewritten_sql": "<the complete rewritten SQL>",
  "changes": [
    {{"type": "table_replace", "original": "<old>", "new": "<new>"}},
    {{"type": "column_replace", "original": "<old>", "new": "<new>"}}
  ],
  "warnings": ["<only unmatched columns from bronze/source tables>"],
  "confidence": 0.0-1.0,
  "reasoning": "<brief explanation of changes made>"
}}"""

        # Store prompt for debugging (can be retrieved via API)
        self._last_llm_prompt = {
            "target_column": target_column,
            "pattern_sql": pattern_sql,
            "pattern_descriptions": pattern_descriptions,
            "join_metadata_raw": join_metadata,  # Raw value to debug
            "join_metadata_parsed": metadata,    # Parsed dict
            "matched_sources": [
                {
                    "table": src.get('src_table_physical_name', '?'),
                    "column": src.get('src_column_physical_name', '?'),
                    "description": src.get('src_comments', 'N/A')
                }
                for src in matched_sources
            ],
            "silver_tables": silver_text,
            "full_prompt": prompt
        }
        
        # Brief log (full details available via debug endpoint)
        print(f"[LLM] Rewriting for {target_column} with {len(matched_sources)} source columns")

        try:
            response = self.workspace_client.serving_endpoints.query(
                name=llm_endpoint,
                messages=[
                    ChatMessage(role=ChatMessageRole.USER, content=prompt)
                ],
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content
            
            # Clean and extract JSON using helper
            json_str = clean_llm_json(response_text)
            
            if json_str:
                try:
                    result = json.loads(json_str)
                    print(f"[Suggestion Service] SQL rewritten with confidence: {result.get('confidence', 0)}")
                    return result
                except json.JSONDecodeError as je:
                    print(f"[Suggestion Service] JSON parse error: {str(je)}")
                    print(f"[Suggestion Service] Raw JSON (first 500 chars): {json_str[:500]}")
                    
                    # Try even more aggressive cleanup - replace all control chars with spaces
                    json_str_clean = re.sub(r'[\x00-\x1f\x7f]', ' ', json_str)
                    # Also try to fix unescaped newlines in string values
                    json_str_clean = re.sub(r'(?<!\\)\n', ' ', json_str_clean)
                    try:
                        result = json.loads(json_str_clean)
                        print(f"[Suggestion Service] SQL rewritten after aggressive cleanup with confidence: {result.get('confidence', 0)}")
                        return result
                    except json.JSONDecodeError as je2:
                        print(f"[Suggestion Service] JSON parse still failed after cleanup: {str(je2)}")
                        return {
                            "rewritten_sql": pattern_sql,
                            "changes": [],
                            "warnings": [f"JSON parse error: {str(je)}"],
                            "confidence": 0.3,
                            "reasoning": "LLM response contained invalid JSON"
                        }
            else:
                return {
                    "rewritten_sql": pattern_sql,
                    "changes": [],
                    "warnings": ["Failed to parse LLM response - no JSON found"],
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
    # GENERATE JOIN METADATA FROM SQL
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
            sql_expression: The final SQL expression to analyze
            target_column: Target column physical name
            target_table: Target table physical name
            source_tables: Pipe-separated source table names
            source_columns: Pipe-separated source column names
            
        Returns:
            JSON string of join_metadata, or None on failure
        """
        if not sql_expression or sql_expression.strip() == "":
            return None
        
        print(f"[Suggestion Service] Generating join_metadata for: {target_column}")
        
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
            
            # Clean and extract JSON using helper
            json_str = clean_llm_json(response_text)
            
            if json_str:
                try:
                    # Validate it's valid JSON
                    json.loads(json_str)
                    print(f"[Suggestion Service] Generated join_metadata successfully")
                    return json_str
                except json.JSONDecodeError as e:
                    print(f"[Suggestion Service] Failed to parse join_metadata JSON: {e}")
                    # Try aggressive cleanup
                    json_str_clean = re.sub(r'[\x00-\x1f\x7f]', ' ', json_str)
                    json_str_clean = re.sub(r'(?<!\\)\n', ' ', json_str_clean)
                    try:
                        json.loads(json_str_clean)
                        print(f"[Suggestion Service] Generated join_metadata after cleanup")
                        return json_str_clean
                    except:
                        return None
            else:
                print(f"[Suggestion Service] No JSON found in LLM response for join_metadata")
                return None
        except Exception as e:
            print(f"[Suggestion Service] LLM error generating join_metadata: {str(e)}")
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
        
        # Common transformation functions
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
                # Clear existing suggestions for this table (allows re-discovery)
                cursor.execute(f"""
                    DELETE FROM {db_config['mapping_suggestions_table']}
                    WHERE target_table_status_id = {target_table_status_id}
                """)
                print(f"[Suggestion Service] Cleared existing suggestions for table {target_table_status_id}")
                
                # Update table status to DISCOVERING
                cursor.execute(f"""
                    UPDATE {db_config['target_table_status_table']}
                    SET 
                        mapping_status = 'DISCOVERING',
                        ai_started_ts = CURRENT_TIMESTAMP(),
                        ai_completed_ts = NULL,
                        ai_error_message = NULL,
                        columns_with_pattern = 0,
                        columns_pending_review = 0,
                        columns_no_match = 0
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
                
                # Fetch ALL patterns for this table in ONE query (much faster)
                print(f"[Suggestion Service] Pre-fetching patterns for table: {tgt_table_physical_name}")
                import time
                start_time = time.time()
                patterns_cache = self.pattern_service.get_all_patterns_for_table(tgt_table_physical_name)
                print(f"[Suggestion Service] Pattern cache loaded in {time.time() - start_time:.2f}s, columns with patterns: {len(patterns_cache)}")
                
                col_idx = 0
                total_cols = len(target_columns)
                
                for target_col in target_columns:
                    col_idx += 1
                    col_start = time.time()
                    semantic_field_id = target_col["semantic_field_id"]
                    tgt_column_physical = target_col["tgt_column_physical_name"]
                    tgt_comments = target_col.get("tgt_comments", "")
                    
                    print(f"[Suggestion Service] Processing column {col_idx}/{total_cols}: {tgt_column_physical}")
                    
                    # Find best pattern from cache (no additional DB queries)
                    pattern_result = self.pattern_service.get_best_pattern_from_cache(
                        patterns_cache,
                        tgt_column_physical
                    )
                    print(f"[Suggestion Service]   -> Pattern lookup: {time.time() - col_start:.2f}s")
                    
                    best_pattern = pattern_result.get("pattern")
                    alternatives_count = len(pattern_result.get("alternatives", []))
                    
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
                        "pattern_signature": None,
                        "pattern_description": None,
                        "alternative_patterns_count": alternatives_count,
                        "matched_source_fields": "[]",
                        "suggested_sql": None,
                        "sql_changes": "[]",
                        "confidence_score": None,
                        "ai_reasoning": None,
                        "warnings": "[]",
                        "suggestion_status": "NO_PATTERN"
                    }
                    
                    if best_pattern:
                        patterns_found += 1
                        pattern = best_pattern
                        
                        suggestion_data["pattern_mapped_field_id"] = pattern["mapped_field_id"]
                        suggestion_data["pattern_type"] = pattern.get("source_relationship_type")
                        suggestion_data["pattern_sql"] = pattern.get("source_expression")
                        suggestion_data["pattern_signature"] = pattern.get("_signature")
                        suggestion_data["pattern_description"] = pattern.get("_signature_description")
                        
                        print(f"[Suggestion Service] Found pattern (usage: {pattern.get('_selected_from_count', 1)}, alternatives: {alternatives_count})")
                        
                        # Check for special case patterns (auto-generated, hardcoded, N/A)
                        is_special_case = False
                        join_metadata_str = pattern.get('join_metadata')
                        if join_metadata_str:
                            try:
                                jm = json.loads(join_metadata_str) if isinstance(join_metadata_str, str) else join_metadata_str
                                pattern_type = jm.get('patternType', '')
                                mapping_action = jm.get('mappingAction', '')
                                
                                if pattern_type == 'AUTO_GENERATED':
                                    is_special_case = True
                                    print(f"[Suggestion Service] Special case: AUTO_GENERATED - auto-mapping (no SQL needed)")
                                    suggestion_data["suggested_sql"] = None  # No SQL needed - field auto-populates on INSERT
                                    suggestion_data["sql_changes"] = json.dumps([{"type": "auto_generated", "description": "Column auto-populated on insert - no mapping required"}])
                                    suggestion_data["confidence_score"] = 1.0
                                    suggestion_data["ai_reasoning"] = "AUTO-GENERATED FIELD: This column is automatically populated by the database on INSERT (identity, sequence, timestamp, or computed column). No source mapping or SQL is required."
                                    suggestion_data["warnings"] = json.dumps([])
                                    suggestion_data["suggestion_status"] = "AUTO_MAPPED"  # Special status for auto-generated
                                    suggestion_data["matched_source_fields"] = json.dumps([])
                                    
                                elif pattern_type == 'HARDCODED':
                                    is_special_case = True
                                    hardcoded_value = jm.get('hardcodedValue', 'NULL')
                                    generated_sql = jm.get('generatedSql', f"SELECT {hardcoded_value} AS {tgt_column_physical}")
                                    print(f"[Suggestion Service] Special case: HARDCODED = {hardcoded_value}")
                                    suggestion_data["suggested_sql"] = generated_sql
                                    suggestion_data["sql_changes"] = json.dumps([{"type": "hardcoded", "value": hardcoded_value}])
                                    suggestion_data["confidence_score"] = 1.0
                                    suggestion_data["ai_reasoning"] = f"This column is hardcoded to a constant value: {hardcoded_value}. No source column mapping needed."
                                    suggestion_data["warnings"] = json.dumps([])
                                    suggestion_data["suggestion_status"] = "PENDING"
                                    suggestion_data["matched_source_fields"] = json.dumps([])
                                    
                                elif pattern_type == 'NOT_APPLICABLE':
                                    is_special_case = True
                                    print(f"[Suggestion Service] Special case: NOT_APPLICABLE - suggesting skip")
                                    suggestion_data["suggested_sql"] = None
                                    suggestion_data["sql_changes"] = json.dumps([])
                                    suggestion_data["confidence_score"] = 1.0
                                    suggestion_data["ai_reasoning"] = "This column is marked as Not Applicable / Not In Use in the historical pattern. Recommended action: SKIP this column."
                                    suggestion_data["warnings"] = json.dumps(["Column not applicable - consider skipping"])
                                    suggestion_data["suggestion_status"] = "PENDING"
                                    suggestion_data["matched_source_fields"] = json.dumps([])
                                    
                            except Exception as e:
                                print(f"[Suggestion Service] Could not check for special case: {e}")
                        
                        # For special cases (AUTO_GENERATED, HARDCODED, NOT_APPLICABLE),
                        # suggestion_data is already populated - skip vector search and LLM
                        if not is_special_case:
                            # Extract columns to map from join_metadata for PARALLEL vector search
                            columns_to_map = []
                            search_terms = [tgt_comments, pattern.get('source_descriptions', '')]
                            
                            join_metadata_str = pattern.get('join_metadata')
                            print(f"[Suggestion Service] join_metadata type: {type(join_metadata_str)}, value: {str(join_metadata_str)[:200] if join_metadata_str else 'None'}")
                            
                            if join_metadata_str:
                                try:
                                    jm = json.loads(join_metadata_str) if isinstance(join_metadata_str, str) else join_metadata_str
                                    print(f"[Suggestion Service] Parsed join_metadata keys: {list(jm.keys()) if isinstance(jm, dict) else 'not a dict'}")
                                    
                                    # Get columns to map from userColumnsToMap for parallel search
                                    user_cols = jm.get('userColumnsToMap', [])
                                    print(f"[Suggestion Service] userColumnsToMap has {len(user_cols)} entries")
                                    
                                    for col in user_cols:
                                        desc = col.get('description', '')
                                        orig_col = col.get('originalColumn', '')
                                        role = col.get('role', '')
                                        print(f"[Suggestion Service]   -> {role}: {orig_col} - {desc}")
                                        
                                        # Build columns_to_map for parallel vector search
                                        columns_to_map.append({
                                            'description': desc if desc else orig_col,
                                            'column_name': orig_col,
                                            'role': role
                                        })
                                        
                                        # Also build combined search_terms for fallback
                                        if desc:
                                            search_terms.append(desc)
                                        if orig_col:
                                            search_terms.append(orig_col)
                                            
                                except Exception as e:
                                    print(f"[Suggestion Service] Could not parse join_metadata: {e}")
                                    import traceback
                                    traceback.print_exc()
                            
                            # Add the output column itself as a search target
                            if tgt_comments:
                                columns_to_map.insert(0, {
                                    'description': tgt_comments,
                                    'column_name': tgt_column_physical,
                                    'role': 'output'
                                })
                            
                            search_query = " ".join([t for t in search_terms if t])
                            print(f"[Suggestion Service] Search query: {search_query[:200]}...")
                            print(f"[Suggestion Service] Columns to parallel search: {len(columns_to_map)}")
                            
                            # Vector search for matching source fields
                            # Use parallel search if we have columns_to_map
                            vs_start = time.time()
                            matched_sources = self._vector_search_source_fields_sync(
                                vs_config["endpoint_name"],
                                vs_config["unmapped_fields_index"],
                                search_query,
                                project_id,
                                num_results=15,
                                columns_to_map=columns_to_map if columns_to_map else None
                            )
                            print(f"[Suggestion Service]   -> Vector search: {time.time() - vs_start:.2f}s, found {len(matched_sources) if matched_sources else 0}")
                            
                            # Fallback to SQL search if vector search returns nothing
                            if not matched_sources:
                                sql_start = time.time()
                                matched_sources = self._sql_search_source_fields_sync(
                                    db_config["server_hostname"],
                                    db_config["http_path"],
                                    db_config["unmapped_fields_table"],
                                    search_query,
                                    project_id,
                                    num_results=5
                                )
                                print(f"[Suggestion Service]   -> SQL fallback: {time.time() - sql_start:.2f}s, found {len(matched_sources) if matched_sources else 0}")
                            
                            # Supplementary: Search for columns by name pattern from join_metadata
                            # This catches columns that vector search might miss due to semantic distance
                            if join_metadata_str and matched_sources:
                                try:
                                    jm = json.loads(join_metadata_str) if isinstance(join_metadata_str, str) else join_metadata_str
                                    pattern_columns = [col.get('originalColumn', '') for col in jm.get('userColumnsToMap', [])]
                                    matched_col_names = {m.get('src_column_physical_name', '').upper() for m in matched_sources}
                                    
                                    # Find pattern columns not yet matched
                                    missing_patterns = [pc for pc in pattern_columns if pc and pc.upper() not in matched_col_names]
                                    
                                    if missing_patterns:
                                        print(f"[Suggestion Service]   -> Pattern columns not matched: {missing_patterns}")
                                        # Do targeted SQL search for similar column names
                                        for pattern_col in missing_patterns[:5]:  # Limit to 5
                                            extra_matches = self._sql_search_source_fields_sync(
                                                db_config["server_hostname"],
                                                db_config["http_path"],
                                                db_config["unmapped_fields_table"],
                                                pattern_col,  # Search by column name
                                                project_id,
                                                num_results=3
                                            )
                                            if extra_matches:
                                                # Add new matches that aren't already present
                                                for em in extra_matches:
                                                    em_col = em.get('src_column_physical_name', '').upper()
                                                    if em_col not in matched_col_names:
                                                        matched_sources.append(em)
                                                        matched_col_names.add(em_col)
                                                        print(f"[Suggestion Service]   -> Added: {em.get('src_table_physical_name')}.{em_col} for pattern col {pattern_col}")
                                except Exception as e:
                                    print(f"[Suggestion Service] Error in supplementary search: {e}")
                            
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
                                llm_start = time.time()
                                rewrite_result = self._rewrite_sql_with_llm_sync(
                                    llm_config["endpoint_name"],
                                    pattern["source_expression"],
                                    pattern.get("join_metadata"),
                                    pattern.get("source_descriptions", ""),
                                    matched_sources,
                                    tgt_column_physical
                                )
                                print(f"[Suggestion Service]   -> LLM rewrite: {time.time() - llm_start:.2f}s")
                                
                                # Filter out false positive warnings (columns listed as missing but actually replaced)
                                changes = rewrite_result.get("changes", [])
                                raw_warnings = rewrite_result.get("warnings", [])
                                filtered_warnings = filter_false_positive_warnings(raw_warnings, changes)
                                
                                suggestion_data["suggested_sql"] = rewrite_result.get("rewritten_sql")
                                suggestion_data["sql_changes"] = json.dumps(changes)
                                suggestion_data["confidence_score"] = rewrite_result.get("confidence", 0.5)
                                suggestion_data["ai_reasoning"] = rewrite_result.get("reasoning", "")
                                suggestion_data["warnings"] = json.dumps(filtered_warnings)
                                suggestion_data["suggestion_status"] = "PENDING"
                            else:
                                # Pattern found but no matching sources
                                no_match += 1
                                suggestion_data["suggestion_status"] = "NO_MATCH"
                                suggestion_data["warnings"] = json.dumps(["No matching source fields found for this pattern"])
                        # else: is_special_case is True - suggestion_data already populated
                    else:
                        # No pattern found
                        no_pattern += 1
                        suggestion_data["suggestion_status"] = "NO_PATTERN"
                    
                    # Insert suggestion
                    print(f"[Suggestion Service]   -> Total column time: {time.time() - col_start:.2f}s, status: {suggestion_data['suggestion_status']}")
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
                    
                    # Track status for final counts
                    status = suggestion_data['suggestion_status']
                    if status == 'AUTO_MAPPED':
                        # AUTO_MAPPED counts as mapped
                        pass
                    elif status == 'NO_MATCH':
                        pass  # already counted above
                    elif status == 'NO_PATTERN':
                        pass  # already counted above
                    
                    # Incremental progress update (every column)
                    current_pending = suggestions_created - no_pattern - no_match
                    cursor.execute(f"""
                        UPDATE {db_config['target_table_status_table']}
                        SET 
                            columns_with_pattern = {patterns_found},
                            columns_pending_review = {current_pending},
                            columns_no_match = {no_match}
                        WHERE target_table_status_id = {target_table_status_id}
                    """)
                
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
    # REGENERATE SINGLE SUGGESTION
    # =========================================================================
    
    def _regenerate_single_suggestion_sync(
        self,
        db_config: Dict[str, str],
        vs_config: Dict[str, str],
        llm_config: Dict[str, str],
        suggestion_id: int,
        pattern_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Regenerate AI suggestion for a single column.
        
        Args:
            suggestion_id: The suggestion to regenerate
            pattern_id: Optional specific pattern to use (for alternative pattern selection)
        
        Useful when user has added new source fields and wants to re-run
        discovery for just one column without rediscovering the entire table.
        """
        print(f"[Suggestion Service] Regenerating suggestion: {suggestion_id}, pattern_id: {pattern_id}")
        
        connection = self._get_sql_connection(
            db_config["server_hostname"],
            db_config["http_path"]
        )
        
        try:
            with connection.cursor() as cursor:
                # Get the existing suggestion details
                cursor.execute(f"""
                    SELECT 
                        s.suggestion_id,
                        s.project_id,
                        s.target_table_status_id,
                        s.semantic_field_id,
                        s.tgt_table_name,
                        s.tgt_table_physical_name,
                        s.tgt_column_name,
                        s.tgt_column_physical_name,
                        s.tgt_comments,
                        s.tgt_physical_datatype,
                        sf.domain
                    FROM {db_config['mapping_suggestions_table']} s
                    LEFT JOIN {db_config['semantic_fields_table']} sf 
                        ON s.semantic_field_id = sf.semantic_field_id
                    WHERE s.suggestion_id = {suggestion_id}
                """)
                
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                
                if not row:
                    return {"error": f"Suggestion {suggestion_id} not found", "status": "error"}
                
                suggestion = dict(zip(columns, row))
                project_id = suggestion["project_id"]
                target_table_status_id = suggestion["target_table_status_id"]
                tgt_column_physical = suggestion["tgt_column_physical_name"]
                tgt_table_physical = suggestion["tgt_table_physical_name"]
                tgt_comments = suggestion.get("tgt_comments", "")
                
                print(f"[Suggestion Service] Regenerating for column: {tgt_column_physical}")
                
                # Step 1: Find pattern for this target column
                # If pattern_id is provided, use that specific pattern
                # Otherwise, use PatternService to find the best pattern
                pattern = None
                alternatives_count = 0
                
                if pattern_id:
                    # User selected a specific alternative pattern
                    pattern = self.pattern_service.get_pattern_by_id(pattern_id)
                    if pattern:
                        print(f"[Suggestion Service] Using specified pattern: {pattern_id}")
                else:
                    # Use best pattern from PatternService
                    pattern_result = self.pattern_service.get_best_pattern_with_alternatives(
                        tgt_table_physical,
                        tgt_column_physical
                    )
                    pattern = pattern_result.get("pattern")
                    alternatives_count = len(pattern_result.get("alternatives", []))
                    if pattern:
                        print(f"[Suggestion Service] Using best pattern (usage: {pattern.get('_selected_from_count', 1)}, alternatives: {alternatives_count})")
                
                # Build suggestion data
                new_suggestion_data = {
                    "project_id": project_id,
                    "target_table_status_id": target_table_status_id,
                    "semantic_field_id": suggestion["semantic_field_id"],
                    "tgt_table_name": suggestion["tgt_table_name"],
                    "tgt_table_physical_name": tgt_table_physical,
                    "tgt_column_name": suggestion["tgt_column_name"],
                    "tgt_column_physical_name": tgt_column_physical,
                    "tgt_comments": tgt_comments,
                    "tgt_physical_datatype": suggestion.get("tgt_physical_datatype"),
                    "pattern_mapped_field_id": None,
                    "pattern_type": None,
                    "pattern_sql": None,
                    "pattern_signature": None,
                    "pattern_description": None,
                    "alternative_patterns_count": alternatives_count,
                    "matched_source_fields": "[]",
                    "suggested_sql": None,
                    "sql_changes": "[]",
                    "confidence_score": None,
                    "ai_reasoning": None,
                    "warnings": "[]",
                    "suggestion_status": "NO_PATTERN"
                }
                
                if pattern:
                    new_suggestion_data["pattern_mapped_field_id"] = pattern["mapped_field_id"]
                    new_suggestion_data["pattern_type"] = pattern.get("source_relationship_type", "SINGLE")
                    new_suggestion_data["pattern_sql"] = pattern.get("source_expression")
                    new_suggestion_data["pattern_signature"] = pattern.get("_signature")
                    new_suggestion_data["pattern_description"] = pattern.get("_signature_description")
                    
                    # Check for special case patterns (auto-generated, hardcoded, N/A)
                    is_special_case = False
                    join_metadata_str = pattern.get('join_metadata')
                    if join_metadata_str:
                        try:
                            jm = json.loads(join_metadata_str) if isinstance(join_metadata_str, str) else join_metadata_str
                            pattern_type = jm.get('patternType', '')
                            
                            if pattern_type == 'AUTO_GENERATED':
                                is_special_case = True
                                print(f"[Suggestion Service] Special case: AUTO_GENERATED - auto-mapping (no SQL needed)")
                                new_suggestion_data["suggested_sql"] = None  # No SQL needed - field auto-populates on INSERT
                                new_suggestion_data["sql_changes"] = json.dumps([{"type": "auto_generated", "description": "Column auto-populated on insert - no mapping required"}])
                                new_suggestion_data["confidence_score"] = 1.0
                                new_suggestion_data["ai_reasoning"] = "AUTO-GENERATED FIELD: This column is automatically populated by the database on INSERT (identity, sequence, timestamp, or computed column). No source mapping or SQL is required."
                                new_suggestion_data["warnings"] = json.dumps([])
                                new_suggestion_data["suggestion_status"] = "AUTO_MAPPED"  # Special status for auto-generated
                                new_suggestion_data["matched_source_fields"] = json.dumps([])
                                
                            elif pattern_type == 'HARDCODED':
                                is_special_case = True
                                hardcoded_value = jm.get('hardcodedValue', 'NULL')
                                generated_sql = jm.get('generatedSql', f"SELECT {hardcoded_value} AS {tgt_column_physical}")
                                print(f"[Suggestion Service] Special case: HARDCODED = {hardcoded_value}")
                                new_suggestion_data["suggested_sql"] = generated_sql
                                new_suggestion_data["sql_changes"] = json.dumps([{"type": "hardcoded", "value": hardcoded_value}])
                                new_suggestion_data["confidence_score"] = 1.0
                                new_suggestion_data["ai_reasoning"] = f"This column is hardcoded to a constant value: {hardcoded_value}. No source column mapping needed."
                                new_suggestion_data["warnings"] = json.dumps([])
                                new_suggestion_data["suggestion_status"] = "PENDING"
                                new_suggestion_data["matched_source_fields"] = json.dumps([])
                                
                            elif pattern_type == 'NOT_APPLICABLE':
                                is_special_case = True
                                print(f"[Suggestion Service] Special case: NOT_APPLICABLE - suggesting skip")
                                new_suggestion_data["suggested_sql"] = None
                                new_suggestion_data["sql_changes"] = json.dumps([])
                                new_suggestion_data["confidence_score"] = 1.0
                                new_suggestion_data["ai_reasoning"] = "This column is marked as Not Applicable / Not In Use in the historical pattern. Recommended action: SKIP this column."
                                new_suggestion_data["warnings"] = json.dumps(["Column not applicable - consider skipping"])
                                new_suggestion_data["suggestion_status"] = "PENDING"
                                new_suggestion_data["matched_source_fields"] = json.dumps([])
                        except Exception as e:
                            print(f"[Suggestion Service] Could not check for special case: {e}")
                    
                    if not is_special_case:
                        # Step 2: Find matching source columns (only for regular patterns)
                        # Extract columns to map for PARALLEL vector search
                        columns_to_map = []
                        search_terms = [tgt_comments, pattern.get('source_descriptions', '')]
                        
                        # Extract column descriptions from join_metadata for parallel search
                        if join_metadata_str:
                            try:
                                jm = json.loads(join_metadata_str) if isinstance(join_metadata_str, str) else join_metadata_str
                                for col in jm.get('userColumnsToMap', []):
                                    desc = col.get('description', '')
                                    orig_col = col.get('originalColumn', '')
                                    role = col.get('role', '')
                                    
                                    # Build columns_to_map for parallel vector search
                                    columns_to_map.append({
                                        'description': desc if desc else orig_col,
                                        'column_name': orig_col,
                                        'role': role
                                    })
                                    
                                    # Also build combined search_terms for fallback
                                    if desc:
                                        search_terms.append(desc)
                                    if orig_col:
                                        search_terms.append(orig_col)
                            except Exception as e:
                                print(f"[Suggestion Service] Could not parse join_metadata: {e}")
                        
                        # Add the output column itself as a search target
                        if tgt_comments:
                            columns_to_map.insert(0, {
                                'description': tgt_comments,
                                'column_name': tgt_column_physical,
                                'role': 'output'
                            })
                        
                        search_query = " ".join([t for t in search_terms if t])
                        print(f"[Suggestion Service] Regenerate search query: {search_query[:150]}...")
                        print(f"[Suggestion Service] Columns to parallel search: {len(columns_to_map)}")
                    
                        # Vector search - use parallel search for better coverage
                        matched_sources = self._vector_search_source_fields_sync(
                            vs_config["endpoint_name"],
                            vs_config["unmapped_fields_index"],
                            search_query,
                            project_id,
                            num_results=15,
                            columns_to_map=columns_to_map if columns_to_map else None
                        )
                        
                        # Fallback to SQL search
                        if not matched_sources:
                            matched_sources = self._sql_search_source_fields_sync(
                                db_config["server_hostname"],
                                db_config["http_path"],
                                db_config["unmapped_fields_table"],
                                search_query,
                                project_id,
                                num_results=15
                            )
                        
                        if matched_sources:
                            # Store matched sources
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
                            new_suggestion_data["matched_source_fields"] = matched_fields_json
                            
                            # Step 3: Rewrite SQL with LLM
                            rewrite_result = self._rewrite_sql_with_llm_sync(
                                llm_config["endpoint_name"],
                                pattern["source_expression"],
                                pattern.get("join_metadata"),
                                pattern.get("source_descriptions", ""),
                                matched_sources,
                                tgt_column_physical
                            )
                            
                            # Filter out false positive warnings (columns listed as missing but actually replaced)
                            changes = rewrite_result.get("changes", [])
                            raw_warnings = rewrite_result.get("warnings", [])
                            filtered_warnings = filter_false_positive_warnings(raw_warnings, changes)
                            
                            new_suggestion_data["suggested_sql"] = rewrite_result.get("rewritten_sql")
                            new_suggestion_data["sql_changes"] = json.dumps(changes)
                            new_suggestion_data["confidence_score"] = rewrite_result.get("confidence", 0.5)
                            new_suggestion_data["ai_reasoning"] = rewrite_result.get("reasoning", "")
                            new_suggestion_data["warnings"] = json.dumps(filtered_warnings)
                            new_suggestion_data["suggestion_status"] = "PENDING"
                        else:
                            new_suggestion_data["suggestion_status"] = "NO_MATCH"
                            new_suggestion_data["warnings"] = json.dumps(["No matching source fields found for this pattern"])
                
                # Step 4: Update the existing suggestion
                cursor.execute(f"""
                    UPDATE {db_config['mapping_suggestions_table']}
                    SET
                        pattern_mapped_field_id = {new_suggestion_data['pattern_mapped_field_id'] if new_suggestion_data['pattern_mapped_field_id'] else 'NULL'},
                        pattern_type = {f"'{new_suggestion_data['pattern_type']}'" if new_suggestion_data['pattern_type'] else 'NULL'},
                        pattern_sql = {f"'{self._escape_sql(new_suggestion_data['pattern_sql'])}'" if new_suggestion_data['pattern_sql'] else 'NULL'},
                        matched_source_fields = '{self._escape_sql(new_suggestion_data['matched_source_fields'])}',
                        suggested_sql = {f"'{self._escape_sql(new_suggestion_data['suggested_sql'])}'" if new_suggestion_data['suggested_sql'] else 'NULL'},
                        sql_changes = '{self._escape_sql(new_suggestion_data['sql_changes'])}',
                        confidence_score = {new_suggestion_data['confidence_score'] if new_suggestion_data['confidence_score'] else 'NULL'},
                        ai_reasoning = {f"'{self._escape_sql(new_suggestion_data['ai_reasoning'])}'" if new_suggestion_data['ai_reasoning'] else 'NULL'},
                        warnings = '{self._escape_sql(new_suggestion_data['warnings'])}',
                        suggestion_status = '{new_suggestion_data['suggestion_status']}',
                        edited_sql = NULL,
                        edited_source_fields = NULL,
                        edit_notes = NULL,
                        rejection_reason = NULL,
                        reviewed_by = NULL,
                        reviewed_ts = NULL
                    WHERE suggestion_id = {suggestion_id}
                """)
                
                print(f"[Suggestion Service] Regenerated suggestion {suggestion_id} with status: {new_suggestion_data['suggestion_status']}")
                
                return {
                    "suggestion_id": suggestion_id,
                    "status": new_suggestion_data["suggestion_status"],
                    "confidence_score": new_suggestion_data.get("confidence_score"),
                    "message": "Suggestion regenerated successfully"
                }
                
        except Exception as e:
            print(f"[Suggestion Service] Error regenerating suggestion: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def regenerate_single_suggestion(
        self, 
        suggestion_id: int,
        pattern_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Regenerate AI suggestion for a single column (async wrapper).
        
        Args:
            suggestion_id: The suggestion to regenerate
            pattern_id: Optional specific pattern to use (for alternative pattern selection)
        """
        db_config = self._get_db_config()
        vs_config = self._get_vector_search_config()
        llm_config = self._get_llm_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._regenerate_single_suggestion_sync,
                db_config,
                vs_config,
                llm_config,
                suggestion_id,
                pattern_id
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
                
                # Get join_metadata, transformations, and domains from the original pattern
                pattern_join_metadata = None
                pattern_transformations = None
                source_domain = None
                target_domain = None
                
                if suggestion.get("pattern_mapped_field_id"):
                    cursor.execute(f"""
                        SELECT join_metadata, transformations_applied, source_domain, target_domain
                        FROM {db_config['mapped_fields_table']}
                        WHERE mapped_field_id = {suggestion['pattern_mapped_field_id']}
                    """)
                    pattern_row = cursor.fetchone()
                    if pattern_row:
                        pattern_join_metadata = pattern_row[0]
                        pattern_transformations = pattern_row[1]
                        source_domain = pattern_row[2]
                        target_domain = pattern_row[3]
                
                # Get target domain from semantic_fields if not from pattern
                if not target_domain and suggestion.get('semantic_field_id'):
                    cursor.execute(f"""
                        SELECT domain FROM {db_config['semantic_fields_table']}
                        WHERE semantic_field_id = {suggestion['semantic_field_id']}
                    """)
                    domain_row = cursor.fetchone()
                    if domain_row:
                        target_domain = domain_row[0]
                
                # Generate fresh join_metadata from the final SQL expression
                # This handles cases where user edited the SQL
                config = self.config_service.get_config()
                generated_join_metadata = self._generate_join_metadata_sync(
                    config.ai_model.foundation_model_endpoint,
                    final_sql,
                    suggestion.get('tgt_column_physical_name', ''),
                    suggestion.get('tgt_table_physical_name', ''),
                    source_tables_physical,
                    source_columns_physical
                )
                
                # Use generated metadata, fall back to pattern if generation failed
                final_join_metadata = generated_join_metadata or pattern_join_metadata
                
                # Determine relationship type from the final SQL
                relationship_type = self._determine_relationship_type(final_sql, source_columns_physical)
                
                # Extract transformations from the final SQL
                final_transformations = self._extract_transformations(final_sql) or pattern_transformations
                
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
                        source_domain,
                        target_domain,
                        source_relationship_type,
                        transformations_applied,
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
                        {f"'{self._escape_sql(source_domain)}'" if source_domain else 'NULL'},
                        {f"'{self._escape_sql(target_domain)}'" if target_domain else 'NULL'},
                        '{relationship_type}',
                        {f"'{self._escape_sql(final_transformations)}'" if final_transformations else 'NULL'},
                        {f"'{self._escape_sql(final_join_metadata)}'" if final_join_metadata else 'NULL'},
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

    # =========================================================================
    # AI SQL ASSISTANT
    # =========================================================================
    
    def _ai_sql_assist_sync(
        self,
        prompt: str,
        current_sql: str,
        target_column: Optional[str] = None,
        target_table: Optional[str] = None,
        available_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to modify SQL based on natural language prompt.
        
        Args:
            prompt: User's natural language instruction (e.g., "Replace CDE_COUNTY with COUNTY_CD")
            current_sql: The current SQL expression to modify
            target_column: Optional target column name for context
            target_table: Optional target table name for context
            available_columns: Optional list of available source columns
            
        Returns:
            Dict with 'sql', 'explanation', 'success'
        """
        try:
            config = self.config_service.get_config()
            
            # Build context section
            context_parts = []
            if target_table and target_column:
                context_parts.append(f"Target: {target_table}.{target_column}")
            if available_columns:
                context_parts.append(f"Available source columns: {', '.join(available_columns[:20])}")
            
            context_str = "\n".join(context_parts) if context_parts else "No additional context provided."
            
            system_prompt = """You are an expert SQL assistant helping to modify data mapping expressions.

Your job is to take a user's natural language request and modify the SQL expression accordingly.

RULES:
1. Only output the modified SQL - no explanations unless asked
2. Preserve the overall structure and intent of the original SQL
3. Be precise with column/table name replacements
4. Keep SQL formatting clean and readable
5. If the request is unclear, make a reasonable interpretation

OUTPUT FORMAT:
Return a JSON object with:
{
  "sql": "the modified SQL expression",
  "explanation": "brief explanation of what was changed"
}"""

            user_prompt = f"""CONTEXT:
{context_str}

CURRENT SQL:
```sql
{current_sql}
```

USER REQUEST:
{prompt}

Modify the SQL according to the user's request and return JSON with the result."""

            print(f"[AI Assist] Calling LLM with prompt: {prompt[:100]}...")
            
            response = self.workspace_client.serving_endpoints.query(
                name=config.ai_model.foundation_model_endpoint,
                messages=[
                    ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt),
                    ChatMessage(role=ChatMessageRole.USER, content=user_prompt)
                ],
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content
            print(f"[AI Assist] LLM response: {response_text[:200]}...")
            
            # Parse JSON from response
            import re
            
            print(f"[AI Assist] Raw LLM response: {response_text[:500]}...")
            
            # Remove markdown code blocks if present (```json ... ``` or ``` ... ```)
            clean_response = response_text
            json_block_match = re.search(r'```(?:json)?\s*(.*?)\s*```', clean_response, re.DOTALL)
            if json_block_match:
                clean_response = json_block_match.group(1).strip()
            
            # Try to extract SQL directly from the "sql" field
            # This handles cases where JSON has literal newlines in string values (invalid JSON)
            sql_start_match = re.search(r'"sql"\s*:\s*"', clean_response)
            if sql_start_match:
                sql_start = sql_start_match.end()
                # Find the closing quote - look for " followed by , or } or "explanation"
                # But we need to handle escaped quotes \"
                remaining = clean_response[sql_start:]
                
                # Find the end of the SQL string value
                sql_end = None
                i = 0
                while i < len(remaining):
                    if remaining[i] == '"' and (i == 0 or remaining[i-1] != '\\'):
                        sql_end = i
                        break
                    i += 1
                
                if sql_end:
                    extracted_sql = remaining[:sql_end]
                    # Unescape any escaped characters
                    extracted_sql = extracted_sql.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                    print(f"[AI Assist] Extracted SQL: {extracted_sql[:100]}...")
                    
                    # Try to get explanation too
                    explanation = "SQL modified by AI"
                    expl_match = re.search(r'"explanation"\s*:\s*"([^"]*)"', clean_response)
                    if expl_match:
                        explanation = expl_match.group(1)
                    
                    return {
                        "sql": extracted_sql.strip(),
                        "explanation": explanation,
                        "success": True
                    }
            
            # Fallback: try standard JSON parsing
            # Strip control characters first
            clean_response = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', clean_response)
            
            # Find JSON object in response
            json_start = clean_response.find('{')
            json_end = clean_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = clean_response[json_start:json_end]
                try:
                    result = json.loads(json_str)
                    return {
                        "sql": result.get("sql", current_sql),
                        "explanation": result.get("explanation", "SQL modified"),
                        "success": True
                    }
                except json.JSONDecodeError as e:
                    print(f"[AI Assist] JSON parse error: {e}")
                    print(f"[AI Assist] JSON string was: {json_str[:200]}...")
            
            # Try to extract SQL directly from code block in original response
            sql_match = re.search(r'```sql\s*(.*?)\s*```', response_text, re.DOTALL)
            if sql_match:
                return {
                    "sql": sql_match.group(1).strip(),
                    "explanation": "SQL extracted from response",
                    "success": True
                }
            
            # Last resort - if response looks like SQL (no JSON), use it directly
            if clean_response.strip() and not clean_response.strip().startswith('{'):
                # Check if it looks like SQL (contains common SQL keywords)
                sql_keywords = ['SELECT', 'COALESCE', 'CASE', 'WHEN', 'FROM', 'JOIN', 'CONCAT', 'TRIM', 'UPPER', 'LOWER']
                if any(kw in clean_response.upper() for kw in sql_keywords):
                    print(f"[AI Assist] Response appears to be raw SQL, using directly")
                    return {
                        "sql": clean_response.strip(),
                        "explanation": "SQL from LLM response",
                        "success": True
                    }
            
            # Fallback - return original
            print(f"[AI Assist] Could not parse response: {response_text[:300]}...")
            return {
                "sql": current_sql,
                "explanation": "Could not parse LLM response - try rephrasing your request",
                "success": False
            }
            
        except Exception as e:
            print(f"[AI Assist] Error: {str(e)}")
            return {
                "sql": current_sql,
                "explanation": f"Error: {str(e)}",
                "success": False
            }
    
    async def ai_sql_assist(
        self,
        prompt: str,
        current_sql: str,
        target_column: Optional[str] = None,
        target_table: Optional[str] = None,
        available_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """AI SQL assistant (async wrapper)."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._ai_sql_assist_sync,
                prompt,
                current_sql,
                target_column,
                target_table,
                available_columns
            )
        )
        return result

