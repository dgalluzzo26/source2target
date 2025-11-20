"""
Feedback service for V2 mapping.

Manages user feedback on AI mapping suggestions for pattern learning.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import List, Dict, Any, Optional
from databricks import sql
from databricks.sdk import WorkspaceClient
from backend.models.mapping_v2 import MappingFeedbackV2, MappingFeedbackCreateV2
from backend.services.config_service import ConfigService

# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=3)


class FeedbackService:
    """Service for managing mapping feedback (V2 schema)."""
    
    def __init__(self):
        """Initialize the feedback service."""
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self):
        """Lazy initialization of WorkspaceClient."""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
    
    def _get_db_config(self) -> Dict[str, str]:
        """Get database configuration for feedback table."""
        config = self.config_service.get_config()
        return {
            "server_hostname": config.database.server_hostname,
            "http_path": config.database.http_path,
            "mapping_feedback_table": config.database.mapping_feedback_table
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
                print(f"[Feedback Service] Could not get OAuth token: {e}")
        
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
    
    def _create_feedback_sync(
        self,
        server_hostname: str,
        http_path: str,
        mapping_feedback_table: str,
        feedback_data: MappingFeedbackCreateV2
    ) -> Dict[str, Any]:
        """Create feedback record (synchronous)."""
        print(f"[Feedback Service] Creating feedback: {feedback_data.feedback_status}")
        
        connection = self._get_sql_connection(server_hostname, http_path)
        
        try:
            with connection.cursor() as cursor:
                query = f"""
                INSERT INTO {mapping_feedback_table} (
                    src_table_name,
                    src_table_physical_name,
                    src_column_name,
                    src_column_physical_name,
                    suggested_tgt_table_name,
                    suggested_tgt_column_name,
                    feedback_status,
                    user_comment,
                    ai_confidence_score,
                    ai_reasoning,
                    feedback_by
                ) VALUES (
                    '{feedback_data.src_table_name.replace("'", "''")}',
                    '{feedback_data.src_table_physical_name.replace("'", "''")}',
                    '{feedback_data.src_column_name.replace("'", "''")}',
                    '{feedback_data.src_column_physical_name.replace("'", "''")}',
                    '{feedback_data.suggested_tgt_table_name.replace("'", "''")}',
                    '{feedback_data.suggested_tgt_column_name.replace("'", "''")}',
                    '{feedback_data.feedback_status}',
                    {f"'{feedback_data.user_comment.replace("'", "''")}'" if feedback_data.user_comment else 'NULL'},
                    {feedback_data.ai_confidence_score if feedback_data.ai_confidence_score else 'NULL'},
                    {f"'{feedback_data.ai_reasoning.replace("'", "''")}'" if feedback_data.ai_reasoning else 'NULL'},
                    {f"'{feedback_data.feedback_by.replace("'", "''")}'" if feedback_data.feedback_by else 'NULL'}
                )
                """
                
                cursor.execute(query)
                connection.commit()
                
                print(f"[Feedback Service] Feedback created successfully")
                
                return feedback_data.model_dump()
                
        except Exception as e:
            print(f"[Feedback Service] Error creating feedback: {str(e)}")
            raise
        finally:
            connection.close()
    
    async def create_feedback(self, feedback_data: MappingFeedbackCreateV2) -> MappingFeedbackV2:
        """Create feedback record (async)."""
        db_config = self._get_db_config()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(
                self._create_feedback_sync,
                db_config['server_hostname'],
                db_config['http_path'],
                db_config['mapping_feedback_table'],
                feedback_data
            )
        )
        
        return MappingFeedbackV2(**result)

