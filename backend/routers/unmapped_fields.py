"""
Unmapped fields API endpoints for V2 multi-field mapping.

Provides REST API for managing source fields awaiting mapping.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from backend.models.mapping_v2 import UnmappedFieldV2, UnmappedFieldCreateV2
from backend.services.unmapped_fields_service import UnmappedFieldsService

router = APIRouter(prefix="/api/v2/unmapped-fields", tags=["Unmapped Fields V2"])

unmapped_fields_service = UnmappedFieldsService()


@router.get("/", response_model=List[UnmappedFieldV2])
async def get_all_unmapped_fields(
    limit: Optional[int] = Query(None, description="Limit number of records returned")
):
    """
    Get all unmapped source fields.
    
    Returns source fields that have not yet been mapped to target fields.
    These are the fields that users will select for mapping in the V2 UI.
    
    Args:
        limit: Optional limit on number of records to return
        
    Returns:
        List of unmapped field records
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        return await unmapped_fields_service.get_all_unmapped_fields(limit=limit)
    except Exception as e:
        print(f"[Unmapped Fields API] Error fetching unmapped fields: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=UnmappedFieldV2)
async def create_unmapped_field(field_data: UnmappedFieldCreateV2):
    """
    Create a new unmapped field record.
    
    Adds a source field to the unmapped_fields table. This is typically
    done during bulk upload of source schema.
    
    Args:
        field_data: Unmapped field data to insert
        
    Returns:
        Newly created unmapped field record
        
    Raises:
        HTTPException: If insert fails
    """
    try:
        return await unmapped_fields_service.create_unmapped_field(field_data)
    except Exception as e:
        print(f"[Unmapped Fields API] Error creating unmapped field: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{field_id}")
async def delete_unmapped_field(field_id: int):
    """
    Delete an unmapped field by ID.
    
    Removes a field from the unmapped_fields table. This is typically done
    after a field has been successfully mapped.
    
    Args:
        field_id: ID of the field to delete
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If delete fails
    """
    try:
        result = await unmapped_fields_service.delete_unmapped_field(field_id)
        return result
    except Exception as e:
        print(f"[Unmapped Fields API] Error deleting unmapped field: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

