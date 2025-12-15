"""
AI Mapping Service V3 - Hybrid approach with SQL generation.

V3 Changes:
- Uses TWO vector searches in parallel:
  1. semantic_fields - find matching target columns
  2. mapped_fields - find similar historical mappings
- Returns transformation suggestions learned from history
- Generates SQL expressions via LLM based on natural language
- Simplified schema: one row per mapping with source_expression
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import List, Dict, Any, Optional
import json
from databricks import sql
from databricks.sdk import WorkspaceClient
from backend.services.config_service import ConfigService

# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=4)


class AIMappingServiceV3:
    """
    AI Mapping Service V3 with dual vector search and SQL generation.
    
    Key Features:
    - Dual vector search: targets (semantic_fields) + patterns (mapped_fields)
    - Learns transformations from historical mappings
    - Detects multi-table patterns (JOIN, UNION)
    - Generates SQL expressions from natural language
    """
    
    def __init__(self):
        """Initialize the AI mapping service V3."""
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
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "semantic_fields_table": self.config_service.get_fully_qualified_table_name(config.database.semantic_fields_table),
            "mapped_fields_table": self.config_service.get_fully_qualified_table_name(config.database.mapped_fields_table),
            "mapping_feedback_table": self.config_service.get_fully_qualified_table_name(config.database.mapping_feedback_table),
            "unmapped_fields_table": self.config_service.get_fully_qualified_table_name(config.database.unmapped_fields_table)
        }
    
    def _get_vector_search_config(self) -> Dict[str, str]:
        """Get vector search configuration for V3 (three indexes)."""
        config = self.config_service.get_config()
        return {
            "semantic_fields_index": config.vector_search.semantic_fields_index,
            "mapped_fields_index": config.vector_search.mapped_fields_index,
            "unmapped_fields_index": config.vector_search.unmapped_fields_index,
            "endpoint_name": config.vector_search.endpoint_name
        }
    
    def _get_ai_model_config(self) -> Dict[str, str]:
        """Get AI model configuration."""
        config = self.config_service.get_config()
        return {
            "foundation_model_endpoint": config.ai_model.foundation_model_endpoint
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
                print(f"[AI Mapping V3] Could not get OAuth token: {e}")
        
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
    
    def _build_target_query(self, source_fields: List[Dict[str, Any]]) -> str:
        """
        Build query string for searching TARGETS (semantic_fields table).
        
        FORMAT: Must match semantic_fields.semantic_field:
        'DESCRIPTION: ... | TYPE: ... | DOMAIN: ...'
        
        Domain is a soft signal - helps disambiguate similar descriptions.
        Empty string if domain is not provided.
        """
        descriptions = []
        datatypes = []
        domains = []
        
        for field in source_fields:
            desc = field.get('src_comments', '') or field.get('src_column_name', '')
            descriptions.append(desc)
            datatypes.append(field.get('src_physical_datatype', '') or 'STRING')
            domains.append(field.get('domain', '') or '')
        
        combined_desc = ' '.join(descriptions)
        combined_type = datatypes[0] if datatypes else 'STRING'
        # Use first non-empty domain, or empty string
        combined_domain = next((d for d in domains if d), '')
        
        query = f"DESCRIPTION: {combined_desc} | TYPE: {combined_type} | DOMAIN: {combined_domain}"
        
        print(f"[AI Mapping V3] Target query: {query[:150]}...")
        return query
    
    def _build_pattern_query(self, source_fields: List[Dict[str, Any]]) -> str:
        """
        Build query string for searching PATTERNS (mapped_fields table).
        
        FORMAT: Must match mapped_fields.source_semantic_field:
        'DESCRIPTION: ... | TYPE: ... | DOMAIN: ...'
        
        Domain helps find patterns from the same domain.
        Empty string if domain is not provided.
        """
        descriptions = []
        datatypes = []
        domains = []
        
        for field in source_fields:
            desc = field.get('src_comments', '') or field.get('src_column_name', '')
            descriptions.append(desc)
            datatypes.append(field.get('src_physical_datatype', '') or 'STRING')
            domains.append(field.get('domain', '') or '')
        
        combined_desc = ' '.join(descriptions)
        combined_type = datatypes[0] if datatypes else 'STRING'
        # Use first non-empty domain, or empty string
        combined_domain = next((d for d in domains if d), '')
        
        query = f"DESCRIPTION: {combined_desc} | TYPE: {combined_type} | DOMAIN: {combined_domain}"
        
        print(f"[AI Mapping V3] Pattern query: {query[:150]}...")
        return query
    
    # =========================================================================
    # VECTOR SEARCH: SEMANTIC FIELDS (Find matching targets)
    # =========================================================================
    
    # NOTE: No backend filtering - return all results to frontend
    # Frontend applies user-configurable threshold filtering via UI sliders
    # This allows real-time tuning without API calls
    
    def _vector_search_targets_sync(
        self,
        server_hostname: str,
        http_path: str,
        index_name: str,
        query_text: str,
        num_results: int
    ) -> List[Dict[str, Any]]:
        """
        Vector search on semantic_fields to find matching TARGET columns.
        Returns all results - frontend handles filtering via UI sliders.
        """
        print(f"[AI Mapping V3] Vector search TARGETS: {query_text[:100]}...")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                escaped_query = query_text.replace("'", "''")
                
                query = f"""
                SELECT 
                    semantic_field_id,
                    tgt_table_name,
                    tgt_column_name,
                    tgt_table_physical_name,
                    tgt_column_physical_name,
                    tgt_comments,
                    tgt_physical_datatype,
                    domain,
                    search_score
                FROM vector_search(
                    index => '{index_name}',
                    query => '{escaped_query}',
                    num_results => {num_results}
                )
                ORDER BY search_score DESC
                """
                
                cursor.execute(query)
                arrow_table = cursor.fetchall_arrow()
                df = arrow_table.to_pandas()
                all_results = df.to_dict('records')
                
                print(f"[AI Mapping V3] ========== TARGET VECTOR SEARCH ==========")
                print(f"[AI Mapping V3] Query: {query_text[:200]}...")
                print(f"[AI Mapping V3] Raw results: {len(all_results)}")
                
                # Log all results (no backend filtering - frontend handles via sliders)
                print(f"[AI Mapping V3] ALL TARGET SCORES (returning all to frontend):")
                for i, r in enumerate(all_results):
                    score = float(r.get('search_score', 0) or 0)
                    r['search_score'] = score  # Ensure float
                    tgt_table = r.get('tgt_table_physical_name') or r.get('tgt_table_name') or '?'
                    col = r.get('tgt_column_name', 'unknown')
                    desc = (r.get('tgt_comments') or '')[:40]
                    print(f"  {i+1}. {tgt_table}.{col} - score: {score:.6f} - '{desc}'")
                
                # Return all results - frontend filters based on user's threshold slider
                results = all_results
                
                print(f"[AI Mapping V3] Returning {len(results)} targets to frontend")
                print(f"[AI Mapping V3] ========================================")
                
                return results
                
        except Exception as e:
            print(f"[AI Mapping V3] Target vector search failed: {str(e)}")
            return []
        finally:
            connection.close()
    
    # =========================================================================
    # VECTOR SEARCH: MAPPED FIELDS (Find similar historical patterns)
    # =========================================================================
    
    def _vector_search_patterns_sync(
        self,
        server_hostname: str,
        http_path: str,
        index_name: str,
        query_text: str,
        num_results: int
    ) -> List[Dict[str, Any]]:
        """
        Vector search on mapped_fields to find similar HISTORICAL PATTERNS.
        Returns past mappings with their SQL expressions and transformations.
        Returns all results - frontend handles filtering via UI sliders.
        """
        print(f"[AI Mapping V3] Vector search PATTERNS: {query_text[:100]}...")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                escaped_query = query_text.replace("'", "''")
                
                query = f"""
                SELECT 
                    mapped_field_id,
                    tgt_table_name,
                    tgt_column_name,
                    tgt_table_physical_name,
                    tgt_column_physical_name,
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
                    search_score
                FROM vector_search(
                    index => '{index_name}',
                    query => '{escaped_query}',
                    num_results => {num_results}
                )
                ORDER BY search_score DESC
                """
                
                cursor.execute(query)
                arrow_table = cursor.fetchall_arrow()
                df = arrow_table.to_pandas()
                all_results = df.to_dict('records')
                
                print(f"[AI Mapping V3] ========== PATTERN VECTOR SEARCH ==========")
                print(f"[AI Mapping V3] Query: {query_text[:200]}...")
                print(f"[AI Mapping V3] Raw results: {len(all_results)}")
                
                # Log all patterns (no backend filtering - frontend handles via sliders)
                print(f"[AI Mapping V3] ALL PATTERN SCORES (returning all to frontend):")
                for i, r in enumerate(all_results):
                    # Ensure scores are floats
                    if r.get('search_score') is not None:
                        r['search_score'] = float(r['search_score'])
                    else:
                        r['search_score'] = 0.0
                    if r.get('confidence_score') is not None:
                        r['confidence_score'] = float(r['confidence_score'])
                    
                    score = r['search_score']
                    tgt_table = r.get('tgt_table_physical_name') or r.get('tgt_table_name') or '?'
                    tgt_col = r.get('tgt_column_name', 'unknown')
                    src_cols = (r.get('source_columns') or '')[:30]
                    transforms = r.get('transformations_applied') or 'none'
                    has_join_meta = 'YES' if r.get('join_metadata') else 'no'
                    print(f"  {i+1}. {tgt_table}.{tgt_col} <- [{src_cols}] - score: {score:.6f} - transforms: {transforms} - join_metadata: {has_join_meta}")
                
                # Return all results - frontend filters based on user's threshold slider
                results = all_results
                
                print(f"[AI Mapping V3] Returning {len(results)} patterns to frontend")
                print(f"[AI Mapping V3] ==========================================")
                
                return results
                
        except Exception as e:
            print(f"[AI Mapping V3] Pattern vector search failed: {str(e)}")
            return []
        finally:
            connection.close()
    
    # =========================================================================
    # EXACT LOOKUP: REJECTIONS (for top target candidates)
    # =========================================================================
    
    def _fetch_rejections_for_targets_sync(
        self,
        server_hostname: str,
        http_path: str,
        feedback_table: str,
        target_columns: List[str],
        source_columns: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Exact lookup of rejections for specific target columns.
        """
        if not target_columns:
            return []
            
        print(f"[AI Mapping V3] Fetching rejections for {len(target_columns)} targets...")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Build WHERE clause for target columns
                target_conditions = [f"suggested_tgt_column = '{t.replace(chr(39), chr(39)+chr(39))}'" for t in target_columns]
                
                query = f"""
                SELECT 
                    suggested_src_table,
                    suggested_src_column,
                    suggested_tgt_table,
                    suggested_tgt_column,
                    src_comments,
                    user_comments,
                    feedback_ts
                FROM {feedback_table}
                WHERE feedback_action = 'REJECTED'
                AND ({' OR '.join(target_conditions)})
                ORDER BY feedback_ts DESC
                LIMIT 20
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                results = [dict(zip(columns, row)) for row in rows]
                print(f"[AI Mapping V3] Found {len(results)} rejections")
                return results
                
        except Exception as e:
            print(f"[AI Mapping V3] Rejection lookup failed: {str(e)}")
            return []
        finally:
            connection.close()
    
    # =========================================================================
    # LLM: ANALYZE AND SUGGEST
    # =========================================================================
    
    def _call_llm_for_suggestions_sync(
        self,
        endpoint_name: str,
        source_fields: List[Dict[str, Any]],
        target_candidates: List[Dict[str, Any]],
        historical_patterns: List[Dict[str, Any]],
        rejections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Call LLM to analyze all inputs and generate suggestions.
        
        Returns:
            Dict with:
            - suggestions: ranked list with reasoning
            - recommended_expression: suggested SQL expression
            - recommended_transformations: list of transforms to apply
            - detected_pattern: SINGLE, JOIN, or UNION
        """
        print(f"[AI Mapping V3] Calling LLM for analysis...")
        
        try:
            # Build source context with PHYSICAL names for SQL generation
            source_info = []
            current_field_names = []
            current_table_names = []
            
            for field in source_fields:
                # Always use physical names for SQL
                physical_table = field.get('src_table_physical_name', field.get('src_table_name', 'unknown_table'))
                physical_column = field.get('src_column_physical_name', field.get('src_column_name', 'unknown_column'))
                
                current_field_names.append(physical_column)
                current_table_names.append(physical_table)
                
                source_info.append(
                    f"- {physical_table}.{physical_column} "
                    f"({field.get('src_physical_datatype', 'UNKNOWN')}): "
                    f"{field.get('src_comments', 'No description')}"
                )
            
            current_field_names_str = ', '.join(current_field_names)
            
            # Build qualified names for multi-table scenarios
            qualified_field_names = [
                f"{t}.{c}" for t, c in zip(current_table_names, current_field_names)
            ]
            qualified_field_names_str = ', '.join(qualified_field_names)
            
            # First, group historical patterns by target for enrichment
            # Use BOTH full key (table, column) AND normalized versions for matching
            patterns_by_target = {}
            patterns_by_table_col = {}  # Exact match
            patterns_by_physical = {}   # Physical name match
            
            for p in historical_patterns:
                tgt_table = p.get('tgt_table_name', '').lower().strip()
                tgt_col = p.get('tgt_column_name', '').lower().strip()
                tgt_table_phys = p.get('tgt_table_physical_name', tgt_table).lower().strip()
                tgt_col_phys = p.get('tgt_column_physical_name', tgt_col).lower().strip()
                
                # Store by display name
                key1 = (tgt_table, tgt_col)
                if key1 not in patterns_by_table_col:
                    patterns_by_table_col[key1] = []
                patterns_by_table_col[key1].append(p)
                
                # Store by physical name
                key2 = (tgt_table_phys, tgt_col_phys)
                if key2 not in patterns_by_physical:
                    patterns_by_physical[key2] = []
                patterns_by_physical[key2].append(p)
            
            print(f"[AI Mapping V3] Pattern groups (display): {list(patterns_by_table_col.keys())}")
            print(f"[AI Mapping V3] Pattern groups (physical): {list(patterns_by_physical.keys())}")
            
            # Build target candidates context - ENRICHED with pattern support info
            target_info = []
            for i, t in enumerate(target_candidates[:5], 1):
                tgt_table_phys = t.get('tgt_table_physical_name', t.get('tgt_table_name', 'unknown')).lower().strip()
                tgt_column_phys = t.get('tgt_column_physical_name', t.get('tgt_column_name', 'unknown')).lower().strip()
                tgt_table_display = t.get('tgt_table_name', tgt_table_phys).lower().strip()
                tgt_column_display = t.get('tgt_column_name', tgt_column_phys).lower().strip()
                
                # Try multiple matching strategies
                matching_patterns = []
                
                # 1. Try exact display name match
                key1 = (tgt_table_display, tgt_column_display)
                if key1 in patterns_by_table_col:
                    matching_patterns = patterns_by_table_col[key1]
                    print(f"[AI Mapping V3] Display name match for {key1}: {len(matching_patterns)} patterns")
                
                # 2. Try physical name match
                if not matching_patterns:
                    key2 = (tgt_table_phys, tgt_column_phys)
                    if key2 in patterns_by_physical:
                        matching_patterns = patterns_by_physical[key2]
                        print(f"[AI Mapping V3] Physical name match for {key2}: {len(matching_patterns)} patterns")
                
                pattern_count = len(matching_patterns)
                
                # Use original case for display
                tgt_table_out = t.get('tgt_table_physical_name', t.get('tgt_table_name', 'unknown'))
                tgt_column_out = t.get('tgt_column_physical_name', t.get('tgt_column_name', 'unknown'))
                
                pattern_note = ""
                if pattern_count > 0:
                    avg_confidence = sum(p.get('confidence_score', 0) for p in matching_patterns) / pattern_count
                    transforms = matching_patterns[0].get('transformations_applied', 'None')
                    pattern_note = f" [⚡ {pattern_count} HISTORICAL PATTERNS, confidence: {avg_confidence:.0%}, transforms: {transforms}]"
                
                target_info.append(
                    f"{i}. {tgt_table_out}.{tgt_column_out} "
                    f"(Semantic Score: {t.get('search_score', 0):.4f}){pattern_note}\n"
                    f"   Description: {t.get('tgt_comments', 'No description')}"
                )
            
            # Build historical patterns context - GROUPED BY TARGET with counts
            pattern_info = []
            for target_key, patterns in patterns_by_table_col.items():
                pattern_tgt_table, pattern_tgt_col = target_key
                grp_pattern_count = len(patterns)
                grp_avg_confidence = sum(p.get('confidence_score', 0) for p in patterns) / grp_pattern_count
                
                # Get unique transformations across patterns
                all_transforms = set()
                rel_types = set()
                for p in patterns:
                    p_transforms = p.get('transformations_applied', '')
                    if p_transforms:
                        all_transforms.update(tr.strip() for tr in p_transforms.split(','))
                    rel_types.add(p.get('source_relationship_type', 'SINGLE'))
                
                pattern_info.append(
                    f"- Target: {pattern_tgt_col.upper()} (table: {pattern_tgt_table})\n"
                    f"  ★ Pattern Count: {grp_pattern_count} (STRONG historical evidence)\n"
                    f"  ★ Average Confidence: {grp_avg_confidence:.0%}\n"
                    f"  Transformations Used: {', '.join(sorted(all_transforms)) if all_transforms else 'None'}\n"
                    f"  Relationship Types: {', '.join(sorted(rel_types))}"
                )
            
            # Build rejection context
            rejection_info = []
            for r in rejections[:5]:
                rejection_info.append(
                    f"- {r['suggested_src_column']} → {r['suggested_tgt_column']}: "
                    f"{r.get('user_comments', 'No reason given')}"
                )
            
            prompt = f"""You are an expert data mapping assistant. Analyze these inputs and provide mapping recommendations.

CURRENT SOURCE FIELDS TO MAP (use THESE EXACT PHYSICAL names in your SQL):
{chr(10).join(source_info)}

PHYSICAL COLUMN NAMES FOR SQL: {current_field_names_str}
FULLY QUALIFIED NAMES (table.column): {qualified_field_names_str}

TARGET CANDIDATES (from vector search, enriched with pattern info):
{chr(10).join(target_info) if target_info else 'No candidates found'}

HISTORICAL PATTERNS GROUPED BY TARGET:
{chr(10).join(pattern_info) if pattern_info else 'No historical patterns found'}

IMPORTANT - TARGET SELECTION PRIORITY:
1. ⚡ PREFER targets with historical patterns - these represent PROVEN successful mappings
2. A target with 2+ patterns and >80% confidence should be STRONGLY preferred over purely semantic matches
3. Pattern count matters: 3 patterns = very reliable, 1 pattern = somewhat reliable
4. Only choose a pure semantic match (no patterns) if NO pattern-backed targets are available
5. The semantic score is just text similarity - patterns are actual validated mappings!

CRITICAL SQL GENERATION RULES: 
- Use ONLY the PHYSICAL column names listed above in any SQL expressions
- Physical names are: {current_field_names_str}
- For multi-table joins, use qualified names: {qualified_field_names_str}
- Apply transformations from patterns but with the CURRENT PHYSICAL field names

REJECTED MAPPINGS (avoid these):
{chr(10).join(rejection_info) if rejection_info else 'No rejections'}

Based on this analysis, provide:
1. The BEST target field match - PREFER targets with historical patterns over pure semantic matches
2. A SQL expression using ONLY these PHYSICAL field names: {current_field_names_str}
3. Recommended transformations based on historical patterns
4. Whether this should be SINGLE, JOIN, or UNION based on sources

Respond in JSON format:
{{
  "best_target": {{
    "tgt_table_name": "...",
    "tgt_column_name": "...",
    "confidence": 0.0-1.0,
    "reasoning": "..."
  }},
  "recommended_expression": "TRIM(INITCAP({current_field_names[0] if current_field_names else 'field_name'}))",
  "recommended_transformations": ["TRIM", "INITCAP"],
  "detected_pattern": "SINGLE|JOIN|UNION",
  "pattern_reasoning": "...",
  "alternative_targets": [
    {{"tgt_column_name": "...", "reasoning": "..."}}
  ]
}}
"""
            
            from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
            
            response = self.workspace_client.serving_endpoints.query(
                name=endpoint_name,
                messages=[
                    ChatMessage(role=ChatMessageRole.USER, content=prompt)
                ],
                max_tokens=1500
            )
            
            response_text = response.choices[0].message.content
            print(f"[AI Mapping V3] LLM response: {response_text[:500]}...")
            
            # Parse JSON response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(response_text[json_start:json_end])
                # Debug: print parsed best_target
                if 'best_target' in parsed:
                    print(f"[AI Mapping V3] LLM best_target: {parsed['best_target']}")
                return parsed
            
            print(f"[AI Mapping V3] Could not find JSON in response")
            return {"error": "Could not parse LLM response"}
            
        except Exception as e:
            print(f"[AI Mapping V3] LLM call failed: {str(e)}")
            return {"error": str(e)}
    
    # =========================================================================
    # LLM: GENERATE SQL FROM NATURAL LANGUAGE
    # =========================================================================
    
    def _generate_sql_from_description_sync(
        self,
        endpoint_name: str,
        source_fields: List[Dict[str, Any]],
        target_field: Dict[str, Any],
        user_description: str
    ) -> Dict[str, Any]:
        """
        Generate a Databricks SQL expression from natural language description.
        
        Args:
            source_fields: Selected source fields
            target_field: Selected target field
            user_description: Natural language like "uppercase and trim", "join on member_id"
        
        Returns:
            Dict with generated SQL expression and explanation
        """
        print(f"[AI Mapping V3] Generating SQL from: '{user_description}'")
        
        try:
            # Build source context with PHYSICAL names only
            source_info = []
            physical_column_names = []
            physical_table_names = []
            qualified_names = []
            
            for field in source_fields:
                physical_column = field.get('src_column_physical_name', field.get('src_column_name', 'column'))
                physical_table = field.get('src_table_physical_name', field.get('src_table_name', 'table'))
                physical_column_names.append(physical_column)
                physical_table_names.append(physical_table)
                qualified_names.append(f"{physical_table}.{physical_column}")
                source_info.append(
                    f"- {physical_table}.{physical_column} ({field.get('src_physical_datatype', 'STRING')})"
                )
            
            physical_names_str = ', '.join(physical_column_names)
            qualified_names_str = ', '.join(qualified_names)
            
            # Target also uses physical names
            tgt_table = target_field.get('tgt_table_physical_name', target_field.get('tgt_table_name', 'TARGET'))
            tgt_column = target_field.get('tgt_column_physical_name', target_field.get('tgt_column_name', 'COLUMN'))
            
            prompt = f"""Generate a Databricks SQL expression based on the user's request.

SOURCE FIELDS - PHYSICAL DATABASE NAMES (use ONLY these in your SQL):
{chr(10).join(source_info)}

PHYSICAL COLUMN NAMES: {physical_names_str}
FULLY QUALIFIED (table.column): {qualified_names_str}

TARGET FIELD (physical name):
- {tgt_table}.{tgt_column} ({target_field.get('tgt_physical_datatype', 'STRING')})

USER REQUEST: "{user_description}"

Common Databricks SQL transformations:
- TRIM(column) - remove whitespace
- UPPER(column) - uppercase
- LOWER(column) - lowercase
- INITCAP(column) - title case
- CONCAT(col1, ' ', col2) - combine fields
- COALESCE(column, 'default') - handle nulls
- CAST(column AS type) - type conversion
- TO_DATE(column, 'format') - date conversion
- SUBSTR(column, start, length) - substring
- REPLACE(column, 'old', 'new') - replace text
- REGEXP_REPLACE(column, pattern, replacement) - regex replace

CRITICAL: 
- Use ONLY these PHYSICAL column names in your SQL: {physical_names_str}
- For multi-table scenarios, use qualified names: {qualified_names_str}
- Do NOT use logical/display names - only the physical database names above

Generate valid Databricks SQL. Respond in JSON:
{{
  "sql_expression": "TRIM(UPPER({physical_column_names[0] if physical_column_names else 'column'}))",
  "transformations_used": ["TRIM", "UPPER"],
  "explanation": "Applied uppercase and trim as requested"
}}
"""
            
            from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
            
            response = self.workspace_client.serving_endpoints.query(
                name=endpoint_name,
                messages=[
                    ChatMessage(role=ChatMessageRole.USER, content=prompt)
                ],
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content
            
            # Parse JSON response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response_text[json_start:json_end])
            
            return {"error": "Could not parse response", "sql_expression": ""}
            
        except Exception as e:
            print(f"[AI Mapping V3] SQL generation failed: {str(e)}")
            return {"error": str(e), "sql_expression": ""}
    
    # =========================================================================
    # MAIN ENTRY POINT: GENERATE SUGGESTIONS (Hybrid Approach)
    # =========================================================================
    
    async def generate_suggestions(
        self,
        source_fields: List[Dict[str, Any]],
        num_results: int = 10
    ) -> Dict[str, Any]:
        """
        Generate AI-powered mapping suggestions using the Hybrid approach.
        
        STAGE 1 (Parallel):
        - Vector search semantic_fields (find targets)
        - Vector search mapped_fields (find patterns)
        
        STAGE 2 (Sequential):
        - Merge and rank candidates
        - Exact lookup rejections for top candidates
        - LLM analysis with all context
        
        Returns all results - frontend filters based on user's threshold sliders.
        
        Returns:
            Dict with:
            - target_candidates: ranked target fields
            - historical_patterns: similar past mappings
            - recommended_expression: suggested SQL
            - recommended_transformations: transforms to apply
            - detected_pattern: SINGLE/JOIN/UNION
            - rejections_to_avoid: past rejections
        """
        print(f"[AI Mapping V3] === Starting Hybrid AI Flow ===")
        print(f"[AI Mapping V3] Source fields: {len(source_fields)}")
        
        # Load config
        db_config = self._get_db_config()
        vs_config = self._get_vector_search_config()
        ai_config = self._get_ai_model_config()
        
        # Build SEPARATE queries for each index (they have different formats!)
        # Target query matches semantic_fields.semantic_field format
        target_query = self._build_target_query(source_fields)
        # Pattern query matches mapped_fields.source_semantic_field format
        pattern_query = self._build_pattern_query(source_fields)
        
        loop = asyncio.get_event_loop()
        
        # =====================================================================
        # STAGE 1: PARALLEL VECTOR SEARCHES
        # =====================================================================
        print(f"[AI Mapping V3] --- Stage 1: Parallel Discovery ---")
        
        # Vector search targets (using target-specific query format)
        targets_task = loop.run_in_executor(
            executor,
            functools.partial(
                self._vector_search_targets_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                vs_config['semantic_fields_index'],
                target_query,  # Query matches semantic_fields.semantic_field format
                num_results * 2
            )
        )
        
        # Vector search patterns (using pattern-specific query format)
        patterns_task = loop.run_in_executor(
            executor,
            functools.partial(
                self._vector_search_patterns_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                vs_config['mapped_fields_index'],
                pattern_query,  # Query matches mapped_fields.source_semantic_field format
                num_results
            )
        )
        
        # Wait for both
        target_candidates, historical_patterns = await asyncio.gather(
            targets_task, patterns_task
        )
        
        print(f"[AI Mapping V3] Stage 1 results: {len(target_candidates)} targets, {len(historical_patterns)} patterns")
        
        # =====================================================================
        # STAGE 2: TARGETED CONTEXT
        # =====================================================================
        print(f"[AI Mapping V3] --- Stage 2: Targeted Context ---")
        
        # Get top target column names for rejection lookup
        top_targets = [t['tgt_column_name'] for t in target_candidates[:5]]
        source_cols = [f['src_column_name'] for f in source_fields]
        
        # Fetch rejections for top targets
        rejections = await loop.run_in_executor(
            executor,
            functools.partial(
                self._fetch_rejections_for_targets_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['mapping_feedback_table'],
                top_targets,
                source_cols
            )
        )
        
        print(f"[AI Mapping V3] Found {len(rejections)} rejections to avoid")
        
        # =====================================================================
        # STAGE 3: LLM ANALYSIS
        # =====================================================================
        print(f"[AI Mapping V3] --- Stage 3: LLM Analysis ---")
        
        llm_result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._call_llm_for_suggestions_sync,
                ai_config['foundation_model_endpoint'],
                source_fields,
                target_candidates,
                historical_patterns,
                rejections
            )
        )
        
        # =====================================================================
        # BUILD RESPONSE
        # =====================================================================
        response = {
            "target_candidates": target_candidates[:num_results],
            "historical_patterns": historical_patterns,
            "rejections_to_avoid": rejections,
            "llm_analysis": llm_result,
            "recommended_expression": llm_result.get("recommended_expression", ""),
            "recommended_transformations": llm_result.get("recommended_transformations", []),
            "detected_pattern": llm_result.get("detected_pattern", "SINGLE"),
            "best_target": llm_result.get("best_target", {})
        }
        
        print(f"[AI Mapping V3] === Hybrid AI Flow Complete ===")
        return response
    
    # =========================================================================
    # UNMAPPED FIELDS VECTOR SEARCH
    # =========================================================================
    
    def _build_unmapped_query(
        self,
        description: str,
        datatype: str = "STRING",
        domain: str = ""
    ) -> str:
        """
        Build query string for searching UNMAPPED FIELDS.
        
        FORMAT: Must match unmapped_fields.source_semantic_field:
        'DESCRIPTION: ... | TYPE: ... | DOMAIN: ...'
        """
        query = f"DESCRIPTION: {description} | TYPE: {datatype} | DOMAIN: {domain}"
        print(f"[AI Mapping V3] Unmapped query: {query[:100]}...")
        return query
    
    def _vector_search_unmapped_sync(
        self,
        server_hostname: str,
        http_path: str,
        unmapped_index: str,
        query: str,
        num_results: int = 10,
        table_filter: Optional[List[str]] = None,
        user_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Vector search on unmapped_fields for template slot and join key suggestions.
        
        Args:
            server_hostname: Databricks server
            http_path: SQL warehouse path
            unmapped_index: Full index name (catalog.schema.index)
            query: Query string matching source_semantic_field format
            num_results: Max results
            table_filter: Optional list of table names to filter to
            user_filter: Optional uploaded_by user to filter to
            
        Returns:
            List of matching unmapped fields with scores
        """
        print(f"[AI Mapping V3] Vector search unmapped_fields...")
        print(f"[AI Mapping V3]   Query: {query[:80]}...")
        print(f"[AI Mapping V3]   Tables: {table_filter}")
        print(f"[AI Mapping V3]   User: {user_filter}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Escape query for SQL
                escaped_query = query.replace("'", "''")
                
                # Build vector search query - NO filters in VECTOR_SEARCH
                # Filters are applied after fetching results
                # Fetch extra results to account for post-filtering
                fetch_count = num_results * 5  # Fetch more to have enough after filtering
                
                search_query = f"""
                    SELECT 
                        unmapped_field_id,
                        src_table_name,
                        src_table_physical_name,
                        src_column_name,
                        src_column_physical_name,
                        src_physical_datatype,
                        src_comments,
                        domain,
                        mapping_status,
                        uploaded_by,
                        search_score
                    FROM VECTOR_SEARCH(
                        index => '{unmapped_index}',
                        query => '{escaped_query}',
                        num_results => {fetch_count}
                    )
                    ORDER BY search_score DESC
                """
                
                print(f"[AI Mapping V3] Executing unmapped vector search...")
                cursor.execute(search_query)
                
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                print(f"[AI Mapping V3] Vector search returned {len(rows)} raw results, applying filters...")
                
                # Build filter sets for post-filtering
                table_filter_set = None
                if table_filter and len(table_filter) > 0:
                    table_filter_set = set(t.lower() for t in table_filter)
                
                results = []
                for row in rows:
                    result = dict(zip(columns, row))
                    
                    # Apply filters post-fetch
                    # Filter 1: Table filter
                    if table_filter_set:
                        field_table = (result.get('src_table_physical_name') or '').lower()
                        if field_table not in table_filter_set:
                            continue
                    
                    # Filter 2: User filter
                    if user_filter:
                        if result.get('uploaded_by') != user_filter:
                            continue
                    
                    # Filter 3: Status filter (only PENDING and MAPPED)
                    status = result.get('mapping_status') or 'PENDING'
                    if status not in ('PENDING', 'MAPPED'):
                        continue
                    
                    # Rename search_score to match_score for frontend
                    result['match_score'] = result.pop('search_score', 0)
                    results.append(result)
                    
                    # Stop once we have enough results
                    if len(results) >= num_results:
                        break
                
                print(f"[AI Mapping V3] After filtering: {len(results)} results")
                for i, r in enumerate(results[:5]):
                    print(f"  {i+1}. {r.get('src_table_name', '?')}.{r.get('src_column_name', '?')} - score: {r.get('match_score', 0):.4f}")
                
                return results
                
        except Exception as e:
            print(f"[AI Mapping V3] Unmapped vector search error: {e}")
            return []
        finally:
            connection.close()
    
    async def search_unmapped_fields(
        self,
        description: str,
        datatype: str = "STRING",
        domain: str = "",
        table_filter: Optional[List[str]] = None,
        user_email: Optional[str] = None,
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search unmapped fields using vector search for template slot and join key suggestions.
        
        Args:
            description: Description or column name to search for
            datatype: Expected data type (default STRING)
            domain: Optional domain for boosting relevance
            table_filter: Optional list of table names to restrict search to
            user_email: Optional user email to filter by uploaded_by
            num_results: Max results to return
            
        Returns:
            List of matching unmapped fields with match_score
        """
        db_config = self._get_db_config()
        vs_config = self._get_vector_search_config()
        
        # Build query in the format matching source_semantic_field
        query = self._build_unmapped_query(description, datatype, domain)
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            executor,
            functools.partial(
                self._vector_search_unmapped_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                vs_config['unmapped_fields_index'],
                query,
                num_results,
                table_filter,
                user_email
            )
        )
        
        return results
    
    # =========================================================================
    # SQL GENERATION ENDPOINT
    # =========================================================================
    
    async def generate_sql_expression(
        self,
        source_fields: List[Dict[str, Any]],
        target_field: Dict[str, Any],
        user_description: str
    ) -> Dict[str, Any]:
        """
        Generate SQL expression from natural language description.
        
        Args:
            source_fields: Selected source fields
            target_field: Selected target field  
            user_description: Natural language like "uppercase and trim"
        
        Returns:
            Dict with sql_expression, transformations_used, explanation
        """
        ai_config = self._get_ai_model_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._generate_sql_from_description_sync,
                ai_config['foundation_model_endpoint'],
                source_fields,
                target_field,
                user_description
            )
        )
        
        return result

