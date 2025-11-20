"""
AI Mapping service V2 for multi-field mapping suggestions.

V2 Changes:
- Supports multiple source fields → single target field suggestions
- Uses mapping history from mapped_fields table for pattern learning
- LLM recognizes common patterns (e.g., first_name + last_name → full_name)
- Generates intelligent reasoning for multi-field suggestions
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
executor = ThreadPoolExecutor(max_workers=3)


class AIMappingServiceV2:
    """
    Service for AI-powered multi-field mapping suggestions (V2).
    
    Key Features:
    - Multi-field vector search (combines multiple source fields into single query)
    - Pattern learning from historical mappings (mapped_fields table)
    - LLM-powered reasoning for multi-field combinations
    - Confidence scoring based on historical patterns and vector similarity
    """
    
    def __init__(self):
        """Initialize the AI mapping service V2."""
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self):
        """Lazy initialization of WorkspaceClient."""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
    
    def _get_db_config(self) -> Dict[str, str]:
        """Get database configuration for V2 tables."""
        config = self.config_service.get_config()
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "semantic_fields_table": config.database.semantic_fields_table,
            "mapped_fields_table": config.database.mapped_fields_table,
            "mapping_details_table": config.database.mapping_details_table
        }
    
    def _get_vector_search_config(self) -> Dict[str, str]:
        """Get vector search configuration."""
        config = self.config_service.get_config()
        return {
            "index_name": config.vector_search.index_name,
            "endpoint_name": config.vector_search.endpoint_name
        }
    
    def _get_ai_model_config(self) -> Dict[str, str]:
        """Get AI model configuration."""
        config = self.config_service.get_config()
        return {
            "foundation_model_endpoint": config.ai_model.foundation_model_endpoint,
            "previous_mappings_table": config.ai_model.previous_mappings_table_name
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
                print(f"[AI Mapping Service V2] Could not get OAuth token: {e}")
        
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
    
    def _build_multi_field_query(self, source_fields: List[Dict[str, Any]]) -> str:
        """
        Build a combined query string from multiple source fields.
        
        For single field: "Table: T_MEMBER, Column: FIRST_NAME, Type: STRING, Comment: First name"
        For multiple fields: "Combination of: FIRST_NAME (First name) + LAST_NAME (Last name) from T_MEMBER"
        
        Args:
            source_fields: List of source field dictionaries with keys:
                - src_table_name, src_column_name, src_physical_datatype, src_comments
        
        Returns:
            Formatted query string for vector search
        """
        if len(source_fields) == 1:
            # Single field query
            field = source_fields[0]
            return (
                f"Table: {field['src_table_name']}, "
                f"Column: {field['src_column_name']}, "
                f"Type: {field.get('src_physical_datatype', 'UNKNOWN')}, "
                f"Comment: {field.get('src_comments', 'No description')}"
            )
        else:
            # Multi-field query
            table_name = source_fields[0]['src_table_name']
            field_descriptions = []
            for field in source_fields:
                comment = field.get('src_comments', 'No description')
                field_descriptions.append(f"{field['src_column_name']} ({comment})")
            
            combined = " + ".join(field_descriptions)
            return f"Combination of: {combined} from {table_name}"
    
    def _fetch_historical_patterns_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapped_fields_table: str,
        mapping_details_table: str,
        source_fields: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical mapping patterns for similar source fields (synchronous).
        
        Looks for previous mappings where the same source fields (or similar combinations)
        were mapped to target fields. This helps identify common patterns like:
        - first_name + last_name → full_name
        - address_line1 + city + state → full_address
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            mapped_fields_table: Fully qualified mapped_fields table name
            mapping_details_table: Fully qualified mapping_details table name
            source_fields: List of source field dictionaries
        
        Returns:
            List of historical mapping patterns with confidence scores
        """
        print(f"[AI Mapping Service V2] Fetching historical patterns for {len(source_fields)} source fields")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Build WHERE clause to match source fields
                if len(source_fields) == 1:
                    # Single field: exact match
                    field = source_fields[0]
                    table_name = field['src_table_physical_name'].replace("'", "''")
                    column_name = field['src_column_physical_name'].replace("'", "''")
                    where_clause = f"""
                    WHERE md.src_table_physical_name = '{table_name}'
                      AND md.src_column_physical_name = '{column_name}'
                    """
                else:
                    # Multi-field: match combination
                    # Look for mappings where all source fields are present
                    field_conditions = []
                    for field in source_fields:
                        table_name = field['src_table_physical_name'].replace("'", "''")
                        column_name = field['src_column_physical_name'].replace("'", "''")
                        field_conditions.append(
                            f"(md.src_table_physical_name = '{table_name}' "
                            f"AND md.src_column_physical_name = '{column_name}')"
                        )
                    where_clause = f"WHERE ({' OR '.join(field_conditions)})"
                
                # Query historical mappings
                query = f"""
                SELECT 
                    mf.tgt_table_name,
                    mf.tgt_column_name,
                    mf.concat_strategy,
                    mf.mapping_confidence_score,
                    mf.ai_reasoning,
                    COUNT(DISTINCT md.detail_id) as source_field_count
                FROM {mapped_fields_table} mf
                JOIN {mapping_details_table} md ON mf.mapping_id = md.mapping_id
                {where_clause}
                GROUP BY 
                    mf.mapping_id,
                    mf.tgt_table_name,
                    mf.tgt_column_name,
                    mf.concat_strategy,
                    mf.mapping_confidence_score,
                    mf.ai_reasoning
                HAVING COUNT(DISTINCT md.detail_id) >= {len(source_fields)}
                ORDER BY mf.mapped_at DESC
                LIMIT 10
                """
                
                print(f"[AI Mapping Service V2] Executing historical pattern query...")
                cursor.execute(query)
                
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                results = []
                for row in rows:
                    record = dict(zip(columns, row))
                    results.append(record)
                
                print(f"[AI Mapping Service V2] Found {len(results)} historical patterns")
                return results
                
        except Exception as e:
            print(f"[AI Mapping Service V2] Error fetching historical patterns: {str(e)}")
            # Don't fail the entire operation if historical patterns can't be fetched
            return []
        finally:
            connection.close()
    
    def _vector_search_multi_field_sync(
        self,
        server_hostname: str,
        http_path: str,
        index_name: str,
        query_text: str,
        num_results: int
    ) -> List[Dict[str, Any]]:
        """
        Perform vector search with multi-field query (synchronous).
        
        Args:
            server_hostname: Databricks workspace hostname
            http_path: SQL warehouse HTTP path
            index_name: Vector search index name
            query_text: Combined query string from multiple source fields
            num_results: Maximum number of results to return
        
        Returns:
            List of vector search results with search_score
        """
        print(f"[AI Mapping Service V2] Vector search for: {query_text[:150]}...")
        print(f"[AI Mapping Service V2] Index: {index_name}, num_results: {num_results}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                # Escape single quotes
                escaped_query = query_text.replace("'", "''")
                
                # Vector search query
                query = f"""
                SELECT 
                    tgt_table_name,
                    tgt_column_name,
                    tgt_table_physical_name,
                    tgt_column_physical_name,
                    semantic_field,
                    search_score
                FROM vector_search(
                    index => '{index_name}',
                    query => '{escaped_query}',
                    num_results => {num_results}
                )
                ORDER BY search_score DESC
                """
                
                print(f"[AI Mapping Service V2] Executing vector search...")
                cursor.execute(query)
                
                arrow_table = cursor.fetchall_arrow()
                df = arrow_table.to_pandas()
                results = df.to_dict('records')
                
                print(f"[AI Mapping Service V2] Vector search returned {len(results)} results")
                return results
                
        except Exception as e:
            print(f"[AI Mapping Service V2] Vector search failed: {str(e)}")
            raise
        finally:
            connection.close()
    
    def _call_foundation_model_sync(
        self,
        endpoint_name: str,
        source_fields: List[Dict[str, Any]],
        vector_results: List[Dict[str, Any]],
        historical_patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Call Databricks Foundation Model API to generate reasoning for multi-field suggestions (synchronous).
        
        Args:
            endpoint_name: Foundation model endpoint name
            source_fields: List of source field dictionaries
            vector_results: Vector search results
            historical_patterns: Historical mapping patterns
        
        Returns:
            List of enriched suggestions with AI reasoning
        """
        print(f"[AI Mapping Service V2] Calling foundation model: {endpoint_name}")
        print(f"[AI Mapping Service V2] Source fields: {len(source_fields)}, Vector results: {len(vector_results)}")
        
        try:
            # Build prompt for multi-field reasoning
            source_field_names = [f"{field['src_table_name']}.{field['src_column_name']}" for field in source_fields]
            source_field_descriptions = [
                f"- {field['src_column_name']}: {field.get('src_comments', 'No description')} ({field.get('src_physical_datatype', 'UNKNOWN')})"
                for field in source_fields
            ]
            
            # Build historical context
            historical_context = ""
            if historical_patterns:
                historical_context = "\n\nHistorical Patterns:\n"
                for pattern in historical_patterns[:3]:  # Top 3 patterns
                    historical_context += (
                        f"- Previously mapped to: {pattern['tgt_table_name']}.{pattern['tgt_column_name']} "
                        f"(Concat: {pattern.get('concat_strategy', 'UNKNOWN')})\n"
                    )
            
            # Build vector search context (top 5)
            vector_context = "\n\nVector Search Results (Top 5):\n"
            for i, result in enumerate(vector_results[:5], 1):
                vector_context += (
                    f"{i}. {result['tgt_table_name']}.{result['tgt_column_name']} "
                    f"(Score: {result['search_score']:.4f})\n"
                )
            
            prompt = f"""You are a data mapping expert. Analyze the following source fields and suggest the best target field mapping with reasoning.

Source Fields ({len(source_fields)}):
{chr(10).join(source_field_descriptions)}

Task: These source fields will be combined (concatenated) to map to a single target field.{historical_context}{vector_context}

For the TOP 3 vector search results, provide:
1. Match Quality: Rate as "Excellent" (>95%), "Strong" (85-95%), "Good" (70-85%), or "Weak" (<70%)
2. Reasoning: Brief explanation (1-2 sentences) of why this is a good or poor match

Respond in JSON format:
{{
  "suggestions": [
    {{
      "tgt_table_name": "...",
      "tgt_column_name": "...",
      "match_quality": "Excellent|Strong|Good|Weak",
      "reasoning": "..."
    }}
  ]
}}
"""
            
            # Call Foundation Model API
            from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
            
            response = self.workspace_client.serving_endpoints.query(
                name=endpoint_name,
                messages=[
                    ChatMessage(role=ChatMessageRole.USER, content=prompt)
                ],
                max_tokens=1000
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            print(f"[AI Mapping Service V2] LLM Response: {response_text[:200]}...")
            
            # Try to parse JSON from response
            try:
                # Find JSON block in response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    parsed = json.loads(json_str)
                    llm_suggestions = parsed.get('suggestions', [])
                    
                    # Merge LLM reasoning with vector results
                    enriched_results = []
                    for i, result in enumerate(vector_results[:10]):  # Top 10
                        enriched = result.copy()
                        
                        # Find matching LLM suggestion
                        matching_llm = None
                        for llm_sug in llm_suggestions:
                            if (llm_sug.get('tgt_table_name') == result['tgt_table_name'] and
                                llm_sug.get('tgt_column_name') == result['tgt_column_name']):
                                matching_llm = llm_sug
                                break
                        
                        if matching_llm:
                            enriched['match_quality'] = matching_llm.get('match_quality', 'Unknown')
                            enriched['ai_reasoning'] = matching_llm.get('reasoning', '')
                        else:
                            # Default reasoning if LLM didn't provide
                            if i < 3:
                                enriched['match_quality'] = 'Good'
                                enriched['ai_reasoning'] = f"Semantic similarity suggests this is a relevant match for the combined source fields."
                            else:
                                enriched['match_quality'] = 'Weak'
                                enriched['ai_reasoning'] = "Lower semantic similarity; may not be the best match."
                        
                        enriched_results.append(enriched)
                    
                    print(f"[AI Mapping Service V2] Enriched {len(enriched_results)} results with AI reasoning")
                    return enriched_results
                    
            except json.JSONDecodeError as e:
                print(f"[AI Mapping Service V2] Failed to parse LLM JSON response: {e}")
                # Fallback: return vector results with default reasoning
                pass
            
            # Fallback: return vector results with basic reasoning
            enriched_results = []
            for i, result in enumerate(vector_results[:10]):
                enriched = result.copy()
                score = result.get('search_score', 0.0)
                
                if score > 0.04:
                    enriched['match_quality'] = 'Strong'
                    enriched['ai_reasoning'] = "High semantic similarity indicates a strong match."
                elif score > 0.02:
                    enriched['match_quality'] = 'Good'
                    enriched['ai_reasoning'] = "Moderate semantic similarity suggests a reasonable match."
                else:
                    enriched['match_quality'] = 'Weak'
                    enriched['ai_reasoning'] = "Low semantic similarity; may require review."
                
                enriched_results.append(enriched)
            
            return enriched_results
            
        except Exception as e:
            print(f"[AI Mapping Service V2] Foundation model call failed: {str(e)}")
            print(f"[AI Mapping Service V2] Falling back to vector search results only")
            
            # Fallback: return vector results without LLM reasoning
            fallback_results = []
            for result in vector_results[:10]:
                enriched = result.copy()
                enriched['match_quality'] = 'Unknown'
                enriched['ai_reasoning'] = "AI reasoning unavailable; based on vector search similarity only."
                fallback_results.append(enriched)
            
            return fallback_results
    
    async def generate_multi_field_suggestions(
        self,
        source_fields: List[Dict[str, Any]],
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate AI-powered mapping suggestions for multiple source fields (async).
        
        This is the main entry point for V2 multi-field AI suggestions.
        
        Workflow:
        1. Build combined query from source fields
        2. Fetch historical patterns (if available)
        3. Perform vector search
        4. Call LLM for intelligent reasoning
        5. Return ranked suggestions with reasoning
        
        Args:
            source_fields: List of source field dictionaries with keys:
                - src_table_name, src_table_physical_name
                - src_column_name, src_column_physical_name
                - src_physical_datatype, src_comments
            num_results: Maximum number of suggestions to return (default: 10)
        
        Returns:
            List of mapping suggestions with:
                - tgt_table_name, tgt_column_name
                - search_score (from vector search)
                - match_quality (from LLM)
                - ai_reasoning (from LLM)
        
        Raises:
            Exception: If configuration loading or vector search fails
        """
        print(f"[AI Mapping Service V2] Generating suggestions for {len(source_fields)} source fields")
        
        # Load configuration
        db_config = self._get_db_config()
        vector_config = self._get_vector_search_config()
        ai_config = self._get_ai_model_config()
        
        # Build query
        query_text = self._build_multi_field_query(source_fields)
        print(f"[AI Mapping Service V2] Combined query: {query_text}")
        
        loop = asyncio.get_event_loop()
        
        # Step 1: Fetch historical patterns (parallel with vector search)
        historical_patterns_task = loop.run_in_executor(
            executor,
            functools.partial(
                self._fetch_historical_patterns_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['mapped_fields_table'],
                db_config['mapping_details_table'],
                source_fields
            )
        )
        
        # Step 2: Perform vector search
        vector_results_task = loop.run_in_executor(
            executor,
            functools.partial(
                self._vector_search_multi_field_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                vector_config['index_name'],
                query_text,
                num_results * 2  # Get more results for LLM to rank
            )
        )
        
        # Wait for both tasks
        historical_patterns, vector_results = await asyncio.gather(
            historical_patterns_task,
            vector_results_task
        )
        
        # Step 3: Call LLM for reasoning
        enriched_results = await loop.run_in_executor(
            executor,
            functools.partial(
                self._call_foundation_model_sync,
                ai_config['foundation_model_endpoint'],
                source_fields,
                vector_results,
                historical_patterns
            )
        )
        
        # Return top N results
        return enriched_results[:num_results]

