"""
Unmapped fields API endpoints for V2 multi-field mapping.

Provides REST API for managing source fields awaiting mapping.
"""
from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional
from backend.models.mapping_v2 import UnmappedFieldV2, UnmappedFieldCreateV2
from backend.services.unmapped_fields_service import UnmappedFieldsService

router = APIRouter(prefix="/api/v2/unmapped-fields", tags=["Unmapped Fields V2"])

unmapped_fields_service = UnmappedFieldsService()


def get_current_user_email(request: Request) -> str:
    """
    Extract current user email from request headers.
    
    In Databricks Apps, the X-Forwarded-Email header contains the authenticated user's email.
    Falls back to demo user for local development.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User email address
    """
    forwarded_email = request.headers.get("X-Forwarded-Email")
    if forwarded_email:
        return forwarded_email
    return "demo.user@gainwell.com"  # Fallback for local dev


@router.get("/", response_model=List[UnmappedFieldV2])
async def get_all_unmapped_fields(
    request: Request,
    limit: Optional[int] = Query(None, description="Limit number of records returned")
):
    """
    Get all unmapped source fields for the current user.
    
    Returns source fields that have not yet been mapped to target fields.
    These are the fields that users will select for mapping in the V2 UI.
    Only returns fields uploaded by the current user.
    
    Args:
        request: FastAPI request (for user email)
        limit: Optional limit on number of records to return
        
    Returns:
        List of unmapped field records for current user
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        current_user_email = get_current_user_email(request)
        print(f"[Unmapped Fields API] Fetching unmapped fields for user: {current_user_email}")
        return await unmapped_fields_service.get_all_unmapped_fields(current_user_email, limit=limit)
    except Exception as e:
        print(f"[Unmapped Fields API] Error fetching unmapped fields: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=UnmappedFieldV2)
async def create_unmapped_field(request: Request, field_data: UnmappedFieldCreateV2):
    """
    Create a new unmapped field record.
    
    Adds a source field to the unmapped_fields table. This is typically
    done during bulk upload of source schema.
    
    Args:
        request: FastAPI request (for user email)
        field_data: Unmapped field data to insert
        
    Returns:
        Newly created unmapped field record
        
    Raises:
        HTTPException: If insert fails
    """
    try:
        current_user_email = get_current_user_email(request)
        print(f"[Unmapped Fields API] Creating unmapped field for user: {current_user_email}")
        
        # Set uploaded_by to current user
        field_data.uploaded_by = current_user_email
        
        return await unmapped_fields_service.create_unmapped_field(field_data)
    except Exception as e:
        print(f"[Unmapped Fields API] Error creating unmapped field: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=dict)
async def bulk_create_unmapped_fields(request: Request, fields: List[UnmappedFieldCreateV2]):
    """
    Bulk create unmapped field records.
    
    Adds multiple source fields to the unmapped_fields table in one operation.
    Used for CSV bulk upload.
    
    Args:
        request: FastAPI request (for user email)
        fields: List of unmapped field data to insert
        
    Returns:
        Dictionary with success_count and error_count
        
    Raises:
        HTTPException: If bulk insert fails
    """
    try:
        current_user_email = get_current_user_email(request)
        print(f"[Unmapped Fields API] Bulk creating {len(fields)} unmapped fields for user: {current_user_email}")
        
        success_count = 0
        error_count = 0
        errors = []
        
        for field_data in fields:
            try:
                # Set uploaded_by to current user
                field_data.uploaded_by = current_user_email
                
                await unmapped_fields_service.create_unmapped_field(field_data)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"{field_data.src_table_name}.{field_data.src_column_name}: {str(e)}")
                print(f"[Unmapped Fields API] Error creating field {field_data.src_table_name}.{field_data.src_column_name}: {str(e)}")
        
        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors if errors else None
        }
    except Exception as e:
        print(f"[Unmapped Fields API] Error in bulk create: {str(e)}")
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


@router.get("/columns-by-table", response_model=dict)
async def get_columns_by_table(request: Request):
    """
    Get all unique columns grouped by table for the current user.
    
    Used for join configuration - returns all available columns for each table
    from unmapped and mapped fields.
    
    Args:
        request: FastAPI request (for user email)
        
    Returns:
        Dictionary mapping table names to lists of column names
        
    Raises:
        HTTPException: If query fails
    """
    try:
        current_user_email = get_current_user_email(request)
        print(f"[Unmapped Fields API] Fetching columns by table for user: {current_user_email}")
        return await unmapped_fields_service.get_columns_by_table(current_user_email)
    except Exception as e:
        print(f"[Unmapped Fields API] Error fetching columns by table: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

