"""
AI Mapping service for generating semantic mapping suggestions.
Uses Databricks Vector Search + Foundation Model API.
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


class AIMappingService:
    """
    Service for AI-powered mapping suggestions using Databricks Vector Search.
    
    This service generates intelligent mapping suggestions by:
    1. Performing vector similarity search against semantic target fields
    2. Ranking results by confidence score (search_score from vector search)
    3. TODO: Adding LLM-generated reasoning for each suggestion
    
    All database operations are executed asynchronously using ThreadPoolExecutor
    to prevent blocking the FastAPI event loop.
    
    Attributes:
        config_service: ConfigService instance for accessing application configuration
        _workspace_client: Lazy-loaded Databricks WorkspaceClient for OAuth authentication
    """
    
    def __init__(self):
        """
        Initialize the AI mapping service.
        
        Sets up the configuration service and prepares workspace client for lazy loading.
        """
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self):
        """
        Get the Databricks WorkspaceClient with lazy initialization.
        
        Returns:
            WorkspaceClient: Databricks workspace client for API calls and authentication
        """
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
    
    def _get_db_config(self) -> Dict[str, str]:
        """
        Get database configuration from the config service.
        
        Returns:
            Dict[str, str]: Dictionary containing server_hostname, http_path, and semantic_table
        """
        config = self.config_service.get_config()
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "semantic_table": config.database.semantic_table
        }
    
    def _get_vector_search_config(self) -> Dict[str, str]:
        """
        Get vector search configuration from the config service.
        
        Returns:
            Dict[str, str]: Dictionary containing index_name and endpoint_name
        """
        config = self.config_service.get_config()
        return {
            "index_name": config.vector_search.index_name,
            "endpoint_name": config.vector_search.endpoint_name
        }
    
    def _get_ai_model_config(self) -> Dict[str, str]:
        """
        Get AI model configuration from the config service.
        
        Returns:
            Dict[str, str]: Dictionary containing foundation_model_endpoint and previous_mappings_table
        """
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
                print(f"[AI Mapping Service] Could not get OAuth token: {e}")
        
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
    
    def _vector_search_sync(
        self,
        server_hostname: str,
        http_path: str,
        index_name: str,
        query_text: str,
        num_results: int
    ) -> List[Dict[str, Any]]:
        """
        Perform vector search (synchronous, for thread pool).
        Returns results with confidence scores.
        """
        print(f"[AI Mapping Service] Vector search for: {query_text[:100]}...")
        print(f"[AI Mapping Service] Index: {index_name}, num_results: {num_results}")
        
        try:
            connection = self._get_sql_connection(server_hostname, http_path)
            print(f"[AI Mapping Service] Connection established")
        except Exception as e:
            print(f"[AI Mapping Service] Connection failed: {str(e)}")
            raise
        
        try:
            with connection.cursor() as cursor:
                # Escape single quotes
                escaped_query = query_text.replace("'", "''")
                
                # Vector search query - includes search_score for confidence
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
                
                print(f"[AI Mapping Service] Executing vector search...")
                cursor.execute(query)
                
                arrow_table = cursor.fetchall_arrow()
                df = arrow_table.to_pandas()
                results = df.to_dict('records')
                
                print(f"[AI Mapping Service] Vector search returned {len(results)} results")
                return results
        except Exception as e:
            print(f"[AI Mapping Service] Vector search failed: {str(e)}")
            raise
        finally:
            connection.close()
            print(f"[AI Mapping Service] Connection closed")
    
    async def get_vector_search_results(
        self,
        query_text: str,
        num_results: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Get vector search results with confidence scores (async).
        
        Performs semantic similarity search against the vector search index
        to find target fields that are most similar to the query text.
        
        Args:
            query_text: Formatted query string with source field information
            num_results: Maximum number of results to return (default: 25)
            
        Returns:
            List[Dict[str, Any]]: List of search results with confidence scores,
                                  ordered by search_score descending
            
        Raises:
            Exception: If configuration loading or vector search fails
            asyncio.TimeoutError: If search takes longer than 30 seconds
        """
        print(f"[AI Mapping Service] get_vector_search_results called")
        
        try:
            db_config = self._get_db_config()
            vs_config = self._get_vector_search_config()
            
            loop = asyncio.get_event_loop()
            results = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    functools.partial(
                        self._vector_search_sync,
                        db_config['server_hostname'],
                        db_config['http_path'],
                        vs_config['index_name'],
                        query_text,
                        num_results
                    )
                ),
                timeout=30.0
            )
            
            return results
        except asyncio.TimeoutError:
            print("[AI Mapping Service] Vector search timed out after 30 seconds")
            raise Exception("Vector search timed out")
        except Exception as e:
            print(f"[AI Mapping Service] Error in get_vector_search_results: {str(e)}")
            raise
    
    async def generate_ai_suggestions(
        self,
        src_table_name: str,
        src_column_name: str,
        src_datatype: str,
        src_nullable: str,
        src_comments: str,
        num_vector_results: int = 25,
        num_ai_results: int = 10,
        user_feedback: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Generate AI-powered mapping suggestions (async).
        
        Creates mapping suggestions by:
        1. Building a query string from source field metadata
        2. Performing vector similarity search
        3. Ranking results by confidence score
        4. TODO: Adding LLM-generated reasoning for each suggestion
        
        Args:
            src_table_name: Source table name
            src_column_name: Source column name
            src_datatype: Source column data type
            src_nullable: Whether source column is nullable (YES/NO)
            src_comments: Source column description/comments
            num_vector_results: Number of vector search results to retrieve (default: 25)
            num_ai_results: Number of top suggestions to return (default: 10)
            user_feedback: Optional user feedback to refine suggestions (not yet implemented)
            
        Returns:
            List[Dict[str, Any]]: List of suggestion dictionaries, each containing:
                - rank: Suggestion rank (1-N)
                - target_table: Target table logical name
                - target_column: Target column logical name
                - target_table_physical: Target table physical name
                - target_column_physical: Target column physical name
                - semantic_field: Combined semantic field text
                - confidence_score: Similarity score from vector search
                - reasoning: Explanation for the suggestion
        
        Raises:
            Exception: If vector search or configuration loading fails
        """
        print(f"[AI Mapping Service] Generating AI suggestions for {src_table_name}.{src_column_name}")
        
        # Build query text for vector search (same format as original)
        query_text = f"TABLE NAME: {src_table_name}; COLUMN NAME: {src_column_name}; COLUMN DESCRIPTION: {src_comments}; IS COLUMN NULLABLE: {src_nullable}; COLUMN DATATYPE: {src_datatype}"
        
        # Get vector search results with confidence scores
        vector_results = await self.get_vector_search_results(query_text, num_vector_results)
        
        # For now, return top results with confidence scores
        # TODO: Add LLM reasoning in next step
        suggestions = []
        for i, result in enumerate(vector_results[:num_ai_results]):
            suggestions.append({
                "rank": i + 1,
                "target_table": result.get('tgt_table_name', ''),
                "target_column": result.get('tgt_column_name', ''),
                "target_table_physical": result.get('tgt_table_physical_name', ''),
                "target_column_physical": result.get('tgt_column_physical_name', ''),
                "semantic_field": result.get('semantic_field', ''),
                "confidence_score": float(result.get('search_score', 0.0)) if result.get('search_score') is not None else 0.0,
                "reasoning": f"Vector similarity match (score: {result.get('search_score', 0.0):.4f})"
            })
        
        print(f"[AI Mapping Service] Generated {len(suggestions)} AI suggestions")
        return suggestions


# Singleton instance
ai_mapping_service = AIMappingService()

