"""
Transformation library API endpoints.

Provides access to reusable SQL transformation templates.
"""
from fastapi import APIRouter, HTTPException
from typing import List
from backend.models.mapping_v2 import TransformationV2
from backend.services.transformation_service import TransformationService

router = APIRouter(prefix="/api/v2/transformations", tags=["Transformations V2"])

transformation_service = TransformationService()


@router.get("/", response_model=List[TransformationV2])
async def get_all_transformations():
    """
    Get all available transformation templates.
    
    Returns a list of reusable SQL transformations that can be applied to fields.
    Examples: TRIM, UPPER, LOWER, INITCAP, CAST, etc.
    
    Returns:
        List of TransformationV2 models
    
    Raises:
        HTTPException 500: If database query fails
    """
    try:
        transformations = await transformation_service.get_all_transformations()
        print(f"[Transformation API] Retrieved {len(transformations)} transformations")
        return transformations
        
    except Exception as e:
        print(f"[Transformation API] Error fetching transformations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

