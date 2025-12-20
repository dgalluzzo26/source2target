"""
Vector Search Service for managing Databricks Vector Search indexes.

Provides utilities for syncing vector search indexes after data changes
to mapped_fields and unmapped_fields tables.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import Dict, Any, Optional
from databricks.sdk import WorkspaceClient
from backend.services.config_service import ConfigService

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=2)


class VectorSearchService:
    """Service for managing vector search index synchronization."""
    
    def __init__(self):
        self.config_service = ConfigService()
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
    
    async def sync_mapped_fields_index(self) -> Dict[str, Any]:
        """
        Sync the mapped_fields vector search index.
        
        Call this after inserting/updating mapped_fields records.
        """
        config = self.config_service.get_config()
        index_name = config.vector_search.mapped_fields_index
        return await self.sync_index(index_name)
    
    async def sync_unmapped_fields_index(self) -> Dict[str, Any]:
        """
        Sync the unmapped_fields vector search index.
        
        Call this after inserting/updating unmapped_fields records.
        """
        config = self.config_service.get_config()
        index_name = config.vector_search.unmapped_fields_index
        return await self.sync_index(index_name)
    
    async def sync_semantic_fields_index(self) -> Dict[str, Any]:
        """
        Sync the semantic_fields vector search index.
        
        Call this after inserting/updating semantic_fields records.
        """
        config = self.config_service.get_config()
        index_name = config.vector_search.semantic_fields_index
        return await self.sync_index(index_name)
    
    async def sync_all_indexes(self) -> Dict[str, Any]:
        """
        Sync all vector search indexes.
        
        Returns:
            Dictionary with results for each index
        """
        results = {}
        
        # Sync all indexes in parallel
        mapped_task = self.sync_mapped_fields_index()
        unmapped_task = self.sync_unmapped_fields_index()
        semantic_task = self.sync_semantic_fields_index()
        
        results["mapped_fields"] = await mapped_task
        results["unmapped_fields"] = await unmapped_task
        results["semantic_fields"] = await semantic_task
        
        return results

