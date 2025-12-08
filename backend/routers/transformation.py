"""
Transformation library API endpoints.

Provides access to reusable SQL transformation templates.
"""
from fastapi import APIRouter, HTTPException
from typing import List
from backend.models.shared import TransformationV2, TransformationCreateV2
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


@router.get("/{transformation_id}", response_model=TransformationV2)
async def get_transformation(transformation_id: int):
    """
    Get a specific transformation by ID.
    
    Args:
        transformation_id: The unique identifier of the transformation
    
    Returns:
        TransformationV2 model
    
    Raises:
        HTTPException 404: If transformation not found
        HTTPException 500: If database query fails
    """
    try:
        transformation = await transformation_service.get_transformation_by_id(transformation_id)
        if not transformation:
            raise HTTPException(status_code=404, detail=f"Transformation {transformation_id} not found")
        return transformation
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Transformation API] Error fetching transformation {transformation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=TransformationV2)
async def create_transformation(transformation: TransformationCreateV2):
    """
    Create a new transformation template.
    
    Args:
        transformation: TransformationCreateV2 model with new transformation details
    
    Returns:
        Created TransformationV2 model with generated ID
    
    Raises:
        HTTPException 400: If transformation code already exists
        HTTPException 500: If database operation fails
    """
    try:
        # Check if transformation code already exists
        existing = await transformation_service.get_transformation_by_code(transformation.transformation_code)
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Transformation with code '{transformation.transformation_code}' already exists"
            )
        
        created = await transformation_service.create_transformation(transformation)
        print(f"[Transformation API] Created transformation: {created.transformation_name}")
        return created
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Transformation API] Error creating transformation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{transformation_id}", response_model=TransformationV2)
async def update_transformation(transformation_id: int, transformation: TransformationCreateV2):
    """
    Update an existing transformation template.
    
    Args:
        transformation_id: The unique identifier of the transformation to update
        transformation: TransformationCreateV2 model with updated details
    
    Returns:
        Updated TransformationV2 model
    
    Raises:
        HTTPException 403: If trying to update a system transformation
        HTTPException 404: If transformation not found
        HTTPException 500: If database operation fails
    """
    try:
        # Check if transformation exists and is not a system transformation
        existing = await transformation_service.get_transformation_by_id(transformation_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Transformation {transformation_id} not found")
        
        if existing.is_system:
            raise HTTPException(
                status_code=403,
                detail="System transformations cannot be modified"
            )
        
        updated = await transformation_service.update_transformation(transformation_id, transformation)
        print(f"[Transformation API] Updated transformation: {updated.transformation_name}")
        return updated
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Transformation API] Error updating transformation {transformation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{transformation_id}")
async def delete_transformation(transformation_id: int):
    """
    Delete a transformation template.
    
    Args:
        transformation_id: The unique identifier of the transformation to delete
    
    Returns:
        Success message
    
    Raises:
        HTTPException 403: If trying to delete a system transformation
        HTTPException 404: If transformation not found
        HTTPException 500: If database operation fails
    """
    try:
        # Check if transformation exists and is not a system transformation
        existing = await transformation_service.get_transformation_by_id(transformation_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Transformation {transformation_id} not found")
        
        if existing.is_system:
            raise HTTPException(
                status_code=403,
                detail="System transformations cannot be deleted"
            )
        
        await transformation_service.delete_transformation(transformation_id)
        print(f"[Transformation API] Deleted transformation: {existing.transformation_name}")
        return {"message": f"Transformation {transformation_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Transformation API] Error deleting transformation {transformation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

