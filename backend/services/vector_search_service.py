"""
Vector Search Service for managing Databricks Vector Search indexes.

V4 uses only the unmapped_fields index for source field matching during discovery.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import Dict, Any
from databricks.sdk import WorkspaceClient
from backend.services.config_service import config_service

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=2)


class VectorSearchService:
    """Service for managing vector search index synchronization."""
    
    def __init__(self):
        self.config_service = config_service  # Use global instance for shared config
        self._workspace_client = None
    
    @property
    def workspace_client(self) -> WorkspaceClient:
        """Lazy initialization of workspace client."""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
    
    def _sync_index_sync(
        self,
        index_name: str
    ) -> Dict[str, Any]:
        """
        Sync a vector search index (synchronous).
        
        Args:
            index_name: Fully qualified index name (catalog.schema.index_name)
            
        Returns:
            Dictionary with sync status
        """
        print(f"[Vector Search Service] Syncing index: {index_name}")
        
        try:
            # Trigger index sync
            self.workspace_client.vector_search_indexes.sync_index(
                index_name=index_name
            )
            
            print(f"[Vector Search Service] Index sync triggered: {index_name}")
            return {
                "status": "success",
                "index_name": index_name,
                "message": "Index sync triggered"
            }
            
        except Exception as e:
            print(f"[Vector Search Service] Error syncing index {index_name}: {str(e)}")
            return {
                "status": "error",
                "index_name": index_name,
                "error": str(e)
            }
    
    async def sync_index(self, index_name: str) -> Dict[str, Any]:
        """
        Sync a vector search index (async).
        
        Args:
            index_name: Fully qualified index name
            
        Returns:
            Dictionary with sync status
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            functools.partial(self._sync_index_sync, index_name)
        )
        return result
    
    async def sync_unmapped_fields_index(self) -> Dict[str, Any]:
        """
        Sync the unmapped_fields vector search index.
        
        Call this after inserting/updating unmapped_fields records.
        This is the primary index used for V4 discovery workflow.
        """
        config = self.config_service.get_config()
        index_name = config.vector_search.unmapped_fields_index
        return await self.sync_index(index_name)
