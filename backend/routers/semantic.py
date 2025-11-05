"""
Semantic table API endpoints.
"""
from fastapi import APIRouter, HTTPException
from typing import List
from backend.models.semantic import SemanticRecord, SemanticRecordCreate, SemanticRecordUpdate
from backend.services.semantic_service import SemanticService


router = APIRouter(prefix="/api/semantic", tags=["semantic"])
semantic_service = SemanticService()


@router.get("/records", response_model=List[SemanticRecord])
async def get_semantic_records():
    """
    Get all semantic table records.
    These represent the target field definitions used for mapping.
    """
    try:
        print("[Semantic Router] GET /records called")
        result = await semantic_service.get_all_records()
        print(f"[Semantic Router] Returning {len(result)} records")
        return result
    except Exception as e:
        print(f"[Semantic Router] ERROR fetching semantic records: {str(e)}")
        import traceback
        print(f"[Semantic Router] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/records", response_model=SemanticRecord)
async def create_semantic_record(record: SemanticRecordCreate):
    """
    Create a new semantic table record.
    The semantic_field will be automatically generated.
    """
    try:
        return await semantic_service.create_record(record)
    except Exception as e:
        print(f"Error creating semantic record: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/records/{record_id}", response_model=SemanticRecord)
async def update_semantic_record(record_id: int, record: SemanticRecordUpdate):
    """
    Update an existing semantic table record.
    The semantic_field will be automatically regenerated.
    """
    try:
        return await semantic_service.update_record(record_id, record)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error updating semantic record: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/records/{record_id}")
async def delete_semantic_record(record_id: int):
    """
    Delete a semantic table record.
    """
    try:
        return await semantic_service.delete_record(record_id)
    except Exception as e:
        print(f"Error deleting semantic record: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

