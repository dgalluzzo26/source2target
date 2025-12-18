"""
FastAPI router for V4 target table endpoints.

V4 Target-First Workflow:
- Get target tables for a project with progress
- Start AI discovery for a table
- Get target columns for a table
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from backend.services.target_table_service import TargetTableService
from backend.services.suggestion_service import SuggestionService
from backend.services.project_service import ProjectService
from backend.models.project import (
    TargetTableStatus,
    TargetTableStatusUpdate,
    TargetTableProgress,
    TableMappingStatus,
    TablePriority
)

router = APIRouter(prefix="/api/v4/projects/{project_id}/target-tables", tags=["V4 Target Tables"])

# Service instances
target_table_service = TargetTableService()
suggestion_service = SuggestionService()
project_service = ProjectService()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class StartDiscoveryRequest(BaseModel):
    """Request to start AI discovery for a table."""
    started_by: str


class StartDiscoveryResponse(BaseModel):
    """Response for start discovery."""
    target_table_status_id: int
    tgt_table_physical_name: str
    status: str
    message: str


class DiscoveryCompleteResponse(BaseModel):
    """Response when discovery completes."""
    target_table_status_id: int
    suggestions_created: int
    patterns_found: int
    no_pattern: int
    no_match: int
    pending_review: int
    status: str


class UpdateTableStatusRequest(BaseModel):
    """Request to update table status."""
    priority: Optional[TablePriority] = None
    user_notes: Optional[str] = None


# =============================================================================
# TARGET TABLE ENDPOINTS
# =============================================================================

@router.get("/", response_model=List[dict])
async def get_target_tables(project_id: int):
    """
    Get all target tables for a project with progress stats.
    
    Returns tables with:
    - Column counts (total, mapped, pending, etc.)
    - Progress percentage
    - AI processing status
    - Confidence summary
    """
    try:
        tables = await target_table_service.get_target_tables(project_id)
        return tables
    except Exception as e:
        print(f"[Target Tables Router] Error getting tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{target_table_status_id}", response_model=dict)
async def get_target_table(project_id: int, target_table_status_id: int):
    """
    Get a single target table with full details.
    """
    try:
        table = await target_table_service.get_target_table_by_id(target_table_status_id)
        if not table:
            raise HTTPException(status_code=404, detail="Target table not found")
        
        # Verify it belongs to the project
        if table.get("project_id") != project_id:
            raise HTTPException(status_code=404, detail="Target table not found in this project")
        
        return table
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Target Tables Router] Error getting table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{target_table_status_id}/columns", response_model=List[dict])
async def get_target_columns(project_id: int, target_table_status_id: int):
    """
    Get all target columns for a table from semantic_fields.
    
    Returns column definitions with descriptions and data types.
    """
    try:
        # Get the table to find physical name
        table = await target_table_service.get_target_table_by_id(target_table_status_id)
        if not table:
            raise HTTPException(status_code=404, detail="Target table not found")
        
        columns = await target_table_service.get_target_columns(
            table["tgt_table_physical_name"]
        )
        return columns
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Target Tables Router] Error getting columns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{target_table_status_id}", response_model=dict)
async def update_target_table(
    project_id: int,
    target_table_status_id: int,
    data: UpdateTableStatusRequest
):
    """
    Update target table priority or notes.
    """
    try:
        update_data = TargetTableStatusUpdate(
            priority=data.priority,
            user_notes=data.user_notes
        )
        result = await target_table_service.update_target_table_status(
            target_table_status_id, 
            update_data
        )
        return result
    except Exception as e:
        print(f"[Target Tables Router] Error updating table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AI DISCOVERY ENDPOINTS
# =============================================================================

@router.post("/{target_table_status_id}/discover", response_model=StartDiscoveryResponse)
async def start_discovery(
    project_id: int,
    target_table_status_id: int,
    request: StartDiscoveryRequest,
    background_tasks: BackgroundTasks
):
    """
    Start AI discovery for a target table.
    
    This runs asynchronously in the background:
    1. Gets all target columns from semantic_fields
    2. For each column, finds past mapping patterns
    3. Vector searches for matching source fields
    4. LLM rewrites SQL with user's columns
    5. Stores suggestions in mapping_suggestions
    
    Poll GET /suggestions or use webhooks to know when complete.
    """
    try:
        # Get the table
        table = await target_table_service.get_target_table_by_id(target_table_status_id)
        if not table:
            raise HTTPException(status_code=404, detail="Target table not found")
        
        # Check if already discovering
        if table.get("mapping_status") == "DISCOVERING":
            return StartDiscoveryResponse(
                target_table_status_id=target_table_status_id,
                tgt_table_physical_name=table["tgt_table_physical_name"],
                status="already_running",
                message="Discovery is already in progress for this table"
            )
        
        # Update status to indicate started
        update_data = TargetTableStatusUpdate(
            mapping_status=TableMappingStatus.DISCOVERING,
            started_by=request.started_by
        )
        await target_table_service.update_target_table_status(target_table_status_id, update_data)
        
        # Run discovery in background
        async def run_discovery():
            try:
                await suggestion_service.generate_suggestions_for_table(
                    project_id,
                    target_table_status_id,
                    table["tgt_table_physical_name"]
                )
                # Update project counters
                await project_service.update_project_counters(project_id)
            except Exception as e:
                print(f"[Target Tables Router] Background discovery error: {e}")
        
        background_tasks.add_task(run_discovery)
        
        return StartDiscoveryResponse(
            target_table_status_id=target_table_status_id,
            tgt_table_physical_name=table["tgt_table_physical_name"],
            status="started",
            message="AI discovery started. Poll /suggestions for results."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Target Tables Router] Error starting discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{target_table_status_id}/discover/sync", response_model=DiscoveryCompleteResponse)
async def start_discovery_sync(
    project_id: int,
    target_table_status_id: int,
    request: StartDiscoveryRequest
):
    """
    Start AI discovery for a target table (synchronous).
    
    Same as /discover but waits for completion.
    Use this for smaller tables or when you need immediate results.
    """
    try:
        # Get the table
        table = await target_table_service.get_target_table_by_id(target_table_status_id)
        if not table:
            raise HTTPException(status_code=404, detail="Target table not found")
        
        # Update started_by
        update_data = TargetTableStatusUpdate(started_by=request.started_by)
        await target_table_service.update_target_table_status(target_table_status_id, update_data)
        
        # Run discovery synchronously
        result = await suggestion_service.generate_suggestions_for_table(
            project_id,
            target_table_status_id,
            table["tgt_table_physical_name"]
        )
        
        # Update project counters
        await project_service.update_project_counters(project_id)
        
        return DiscoveryCompleteResponse(
            target_table_status_id=target_table_status_id,
            suggestions_created=result["suggestions_created"],
            patterns_found=result["patterns_found"],
            no_pattern=result["no_pattern"],
            no_match=result["no_match"],
            pending_review=result["pending_review"],
            status=result["status"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Target Tables Router] Error in sync discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{target_table_status_id}/suggestions", response_model=List[dict])
async def get_table_suggestions(
    project_id: int,
    target_table_status_id: int,
    status: Optional[str] = Query(None, description="Filter by status: PENDING, APPROVED, REJECTED, etc.")
):
    """
    Get all suggestions for a target table.
    
    Returns suggestions ordered by:
    1. Status (PENDING first, then NO_MATCH, NO_PATTERN)
    2. Confidence score (highest first)
    3. Column name
    """
    try:
        suggestions = await suggestion_service.get_suggestions_for_table(
            target_table_status_id,
            status_filter=status
        )
        return suggestions
    except Exception as e:
        print(f"[Target Tables Router] Error getting suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PATTERN LOOKUP
# =============================================================================

@router.get("/{target_table_status_id}/columns/{column_physical_name}/pattern", response_model=dict)
async def get_column_pattern(
    project_id: int,
    target_table_status_id: int,
    column_physical_name: str
):
    """
    Get the approved pattern for a specific target column.
    
    Returns the historical mapping pattern if one exists.
    """
    try:
        # Get the table
        table = await target_table_service.get_target_table_by_id(target_table_status_id)
        if not table:
            raise HTTPException(status_code=404, detail="Target table not found")
        
        pattern = await target_table_service.get_pattern_for_column(
            table["tgt_table_physical_name"],
            column_physical_name
        )
        
        if not pattern:
            return {"pattern": None, "message": "No approved pattern found for this column"}
        
        return {"pattern": pattern}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Target Tables Router] Error getting pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))

