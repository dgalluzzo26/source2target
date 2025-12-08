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
        """Get vector search configuration for V3 (dual indexes)."""
        config = self.config_service.get_config()
        return {
            "semantic_fields_index": config.vector_search.semantic_fields_index,
            "mapped_fields_index": config.vector_search.mapped_fields_index,
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
    
    def _build_source_query(self, source_fields: List[Dict[str, Any]]) -> str:
        """
        Build a combined query string from source fields for vector search.
        
        Args:
            source_fields: List of source field dictionaries
        
        Returns:
            Formatted query string for vector search
        """
        parts = []
        tables = set()
        columns = []
        descriptions = []
        datatypes = []
        
        for field in source_fields:
            tables.add(field.get('src_table_name', ''))
            columns.append(field.get('src_column_name', ''))
            descriptions.append(field.get('src_comments', '') or 'No description')
            datatypes.append(field.get('src_physical_datatype', '') or 'UNKNOWN')
        
        return (
            f"SOURCE TABLES: {', '.join(tables)} | "
            f"SOURCE COLUMNS: {', '.join(columns)} | "
            f"SOURCE DESCRIPTIONS: {' | '.join(descriptions)} | "
            f"SOURCE TYPES: {', '.join(datatypes)}"
        )
    
    # =========================================================================
    # VECTOR SEARCH: SEMANTIC FIELDS (Find matching targets)
    # =========================================================================
    
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
                results = df.to_dict('records')
                
                print(f"[AI Mapping V3] Found {len(results)} target candidates")
                
                # Debug: print first few results with scores
                if results:
                    print(f"[AI Mapping V3] Sample target results:")
                    for i, r in enumerate(results[:3]):
                        score = r.get('search_score')
                        print(f"  {i+1}. {r.get('tgt_column_name')} - score: {score} (type: {type(score).__name__})")
                
                # Ensure scores are floats (pandas might return numpy types)
                for r in results:
                    if 'search_score' in r and r['search_score'] is not None:
                        r['search_score'] = float(r['search_score'])
                
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
                    source_expression,
                    source_tables,
                    source_columns,
                    source_descriptions,
                    source_relationship_type,
                    transformations_applied,
                    confidence_score,
                    ai_reasoning,
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
                results = df.to_dict('records')
                
                print(f"[AI Mapping V3] Found {len(results)} historical patterns")
                
                # Debug: print first few pattern results
                if results:
                    print(f"[AI Mapping V3] Sample pattern results:")
                    for i, r in enumerate(results[:3]):
                        score = r.get('search_score')
                        print(f"  {i+1}. {r.get('tgt_column_name')} - expr: {r.get('source_expression', '')[:50]} - score: {score}")
                
                # Ensure scores are floats
                for r in results:
                    if 'search_score' in r and r['search_score'] is not None:
                        r['search_score'] = float(r['search_score'])
                    if 'confidence_score' in r and r['confidence_score'] is not None:
                        r['confidence_score'] = float(r['confidence_score'])
                
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
            # Build source context
            source_info = []
            for field in source_fields:
                source_info.append(
                    f"- {field['src_table_name']}.{field['src_column_name']} "
                    f"({field.get('src_physical_datatype', 'UNKNOWN')}): "
                    f"{field.get('src_comments', 'No description')}"
                )
            
            # Build target candidates context
            target_info = []
            for i, t in enumerate(target_candidates[:5], 1):
                target_info.append(
                    f"{i}. {t['tgt_table_name']}.{t['tgt_column_name']} "
                    f"(Score: {t.get('search_score', 0):.4f}) - {t.get('tgt_comments', 'No description')}"
                )
            
            # Build historical patterns context - emphasize TRANSFORMATIONS only
            pattern_info = []
            for p in historical_patterns[:5]:
                transforms = p.get('transformations_applied', 'None')
                rel_type = p.get('source_relationship_type', 'SINGLE')
                pattern_info.append(
                    f"- Target: {p['tgt_column_name']}\n"
                    f"  Transformations Used: {transforms}\n"
                    f"  Relationship Type: {rel_type}\n"
                    f"  (Note: Field names in original were different - only use the transformation pattern)"
                )
            
            # Get current source field names for the LLM to use
            current_field_names = [f.get('src_column_physical_name', f.get('src_column_name', '')) for f in source_fields]
            current_field_names_str = ', '.join(current_field_names)
            
            # Build rejection context
            rejection_info = []
            for r in rejections[:5]:
                rejection_info.append(
                    f"- {r['suggested_src_column']} → {r['suggested_tgt_column']}: "
                    f"{r.get('user_comments', 'No reason given')}"
                )
            
            prompt = f"""You are an expert data mapping assistant. Analyze these inputs and provide mapping recommendations.

CURRENT SOURCE FIELDS TO MAP (use THESE exact field names in your SQL):
{chr(10).join(source_info)}

CURRENT FIELD NAMES TO USE IN SQL: {current_field_names_str}

TARGET CANDIDATES (from vector search):
{chr(10).join(target_info) if target_info else 'No candidates found'}

HISTORICAL PATTERNS (learn TRANSFORMATIONS from these, but use CURRENT field names above):
{chr(10).join(pattern_info) if pattern_info else 'No historical patterns found'}

IMPORTANT: The historical patterns show what transformations (TRIM, UPPER, INITCAP, etc.) were 
typically applied for similar mappings. Apply those same transformations but use the CURRENT 
source field names listed above - NOT the old field names from historical patterns.

REJECTED MAPPINGS (avoid these):
{chr(10).join(rejection_info) if rejection_info else 'No rejections'}

Based on this analysis, provide:
1. The BEST target field match
2. A SQL expression using the CURRENT field names: {current_field_names_str}
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
            # Build source context with physical names
            source_info = []
            field_names = []
            for field in source_fields:
                physical_name = field.get('src_column_physical_name', field.get('src_column_name', 'column'))
                table_name = field.get('src_table_physical_name', field.get('src_table_name', 'table'))
                field_names.append(physical_name)
                source_info.append(
                    f"- {table_name}.{physical_name} ({field.get('src_physical_datatype', 'STRING')})"
                )
            
            field_names_str = ', '.join(field_names)
            
            prompt = f"""Generate a Databricks SQL expression based on the user's request.

SOURCE FIELDS (use these EXACT field names in your SQL):
{chr(10).join(source_info)}

FIELD NAMES TO USE: {field_names_str}

TARGET FIELD:
- {target_field.get('tgt_table_name', 'TARGET')}.{target_field.get('tgt_column_name', 'COLUMN')} ({target_field.get('tgt_physical_datatype', 'STRING')})

USER REQUEST: "{user_description}"

Common transformations:
- TRIM(field) - remove whitespace
- UPPER(field) - uppercase
- LOWER(field) - lowercase
- INITCAP(field) - title case
- CONCAT(field1, ' ', field2) - combine fields
- COALESCE(field, 'default') - handle nulls
- CAST(field AS type) - type conversion
- TO_DATE(field, 'format') - date conversion
- SUBSTR(field, start, length) - substring

IMPORTANT: Use the EXACT field names listed above ({field_names_str}) in your SQL expression.

Generate valid Databricks SQL. Respond in JSON:
{{
  "sql_expression": "TRIM(UPPER({field_names[0] if field_names else 'column'}))",
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
        
        # Build query for vector search
        query_text = self._build_source_query(source_fields)
        print(f"[AI Mapping V3] Query: {query_text[:100]}...")
        
        loop = asyncio.get_event_loop()
        
        # =====================================================================
        # STAGE 1: PARALLEL VECTOR SEARCHES
        # =====================================================================
        print(f"[AI Mapping V3] --- Stage 1: Parallel Discovery ---")
        
        # Vector search targets
        targets_task = loop.run_in_executor(
            executor,
            functools.partial(
                self._vector_search_targets_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                vs_config['semantic_fields_index'],
                query_text,
                num_results * 2
            )
        )
        
        # Vector search patterns
        patterns_task = loop.run_in_executor(
            executor,
            functools.partial(
                self._vector_search_patterns_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                vs_config['mapped_fields_index'],
                query_text,
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

