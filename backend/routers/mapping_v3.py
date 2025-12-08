"""
FastAPI router for V3 mapping endpoints.

V3 KEY CHANGES:
- Simplified CRUD for single-table mappings
- Source expression instead of separate details/joins
- Feedback endpoint for rejections
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from backend.services.mapping_service_v3 import MappingServiceV3
from backend.models.mapping_v3 import (
    MappedFieldV3,
    MappedFieldCreateV3,
    MappedFieldUpdateV3,
    MappingFeedbackCreateV3
)

router = APIRouter(prefix="/api/v3/mappings", tags=["V3 Mappings"])

# Service instance
mapping_service = MappingServiceV3()


# Request/Response models
class CreateMappingRequest(BaseModel):
    """Request body for creating a V3 mapping."""
    mapping: MappedFieldCreateV3
    unmapped_field_ids: Optional[List[int]] = None


class CreateMappingResponse(BaseModel):
    """Response for create mapping."""
    mapping_id: int
    message: str


class UpdateMappingResponse(BaseModel):
    """Response for update mapping."""
    mapping_id: int
    message: str


class DeleteMappingResponse(BaseModel):
    """Response for delete mapping."""
    mapping_id: int
    message: str


# =========================================================================
# CRUD ENDPOINTS
# =========================================================================

@router.get("/", response_model=List[dict])
async def get_all_mappings(
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, INACTIVE, PENDING_REVIEW")
):
    """
    Get all V3 mappings.
    
    Returns list of mappings with source_expression and metadata.
    Optionally filter by mapping_status.
    """
    try:
        mappings = await mapping_service.get_mappings(status_filter=status)
        return mappings
    except Exception as e:
        print(f"[V3 Mappings Router] Error getting mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{mapping_id}", response_model=dict)
async def get_mapping(mapping_id: int):
    """
    Get a single V3 mapping by ID.
    """
    try:
        mapping = await mapping_service.get_mapping(mapping_id)
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")
        return mapping
    except HTTPException:
        raise
    except Exception as e:
        print(f"[V3 Mappings Router] Error getting mapping {mapping_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=CreateMappingResponse)
async def create_mapping(request: CreateMappingRequest):
    """
    Create a new V3 mapping.
    
    - mapping: The mapping data including source_expression
    - unmapped_field_ids: Optional list of unmapped field IDs to remove
    """
    try:
        result = await mapping_service.create_mapping(
            data=request.mapping,
            unmapped_field_ids=request.unmapped_field_ids
        )
        return CreateMappingResponse(
            mapping_id=result["mapping_id"],
            message=result["message"]
        )
    except Exception as e:
        print(f"[V3 Mappings Router] Error creating mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{mapping_id}", response_model=UpdateMappingResponse)
async def update_mapping(mapping_id: int, data: MappedFieldUpdateV3):
    """
    Update a V3 mapping.
    
    Can update:
    - source_expression
    - source_tables, source_columns, etc.
    - transformations_applied
    - mapping_status
    - ai_reasoning, ai_generated
    """
    try:
        # Check if mapping exists
        existing = await mapping_service.get_mapping(mapping_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        result = await mapping_service.update_mapping(mapping_id, data)
        return UpdateMappingResponse(
            mapping_id=result["mapping_id"],
            message=result["message"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[V3 Mappings Router] Error updating mapping {mapping_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{mapping_id}", response_model=DeleteMappingResponse)
async def delete_mapping(
    mapping_id: int,
    restore: bool = Query(False, description="Whether to restore source fields to unmapped_fields")
):
    """
    Delete a V3 mapping.
    
    - restore: If true, attempts to restore source fields to unmapped_fields table
    """
    try:
        # Check if mapping exists
        existing = await mapping_service.get_mapping(mapping_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        result = await mapping_service.delete_mapping(mapping_id, restore_to_unmapped=restore)
        return DeleteMappingResponse(
            mapping_id=result["mapping_id"],
            message=result["message"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[V3 Mappings Router] Error deleting mapping {mapping_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# FEEDBACK ENDPOINT
# =========================================================================

@router.post("/feedback")
async def record_feedback(data: MappingFeedbackCreateV3):
    """
    Record feedback for a rejected AI suggestion.
    
    This helps AI learn to avoid similar bad suggestions in the future.
    The feedback is stored with source_semantic_field for vector search.
    """
    try:
        result = await mapping_service.record_feedback(data)
        return result
    except Exception as e:
        print(f"[V3 Mappings Router] Error recording feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# TRANSFORMATIONS ENDPOINT
# =========================================================================

@router.get("/transformations/library")
async def get_transformations():
    """
    Get the transformation library.
    
    Returns list of reusable transformation templates for the UI.
    """
    try:
        transformations = await mapping_service.get_transformations()
        return transformations
    except Exception as e:
        print(f"[V3 Mappings Router] Error getting transformations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

