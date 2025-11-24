"""
Mapping V2 API endpoints for multi-field mapping management.

Provides CRUD operations for creating, reading, and deleting multi-field mappings.
"""
from fastapi import APIRouter, HTTPException, Body, Request
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.models.mapping_v2 import (
    MappedFieldCreateV2,
    MappingDetailCreateV2,
    MappingJoinCreateV2
)
from backend.services.mapping_service_v2 import MappingServiceV2
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/api/v2/mappings", tags=["Mappings V2"])

mapping_service = MappingServiceV2()
auth_service = AuthService()


def get_current_user_email(request: Request) -> str:
    """
    Extract the current user's email from request headers.
    
    In Databricks Apps, the X-Forwarded-Email header contains the authenticated user's email.
    For local development, falls back to "local.user@example.com".
    
    Args:
        request: FastAPI Request object
    
    Returns:
        User's email address
    """
    forwarded_email = request.headers.get("X-Forwarded-Email")
    if forwarded_email:
        return forwarded_email
    
    # Fallback for local development
    return "local.user@example.com"


def is_admin_user(email: str) -> bool:
    """
    Check if the user is an administrator.
    
    Args:
        email: User's email address
    
    Returns:
        True if user is admin, False otherwise
    """
    return auth_service.check_admin_group_membership(email)


class CreateMappingRequest(BaseModel):
    """
    Request body for creating a multi-field mapping.
    
    Attributes:
        mapped_field: Target field information
        mapping_details: List of source fields with ordering and transformations
        mapping_joins: Optional list of join conditions for multi-table mappings
    """
    mapped_field: MappedFieldCreateV2 = Field(
        ...,
        description="Target field information"
    )
    mapping_details: List[MappingDetailCreateV2] = Field(
        ...,
        description="Source fields with ordering (must have at least 1)",
        min_length=1
    )
    mapping_joins: Optional[List[MappingJoinCreateV2]] = Field(
        default=[],
        description="Join conditions for multi-table mappings"
    )


@router.post("/", response_model=Dict[str, Any])
async def create_mapping(request: CreateMappingRequest = Body(...)):
    """
    Create a new multi-field mapping.
    
    **Workflow:**
    1. Creates a mapped_fields record (target field)
    2. Creates mapping_details records (source fields with ordering)
    3. Removes source fields from unmapped_fields table
    4. Returns the new mapping_id
    
    **Example:**
    ```json
    {
      "mapped_field": {
        "tgt_table_name": "slv_member",
        "tgt_table_physical_name": "slv_member",
        "tgt_column_name": "full_name",
        "tgt_column_physical_name": "full_name",
        "concat_strategy": "SPACE",
        "mapped_by": "john.doe@example.com"
      },
      "mapping_details": [
        {
          "mapping_id": 0,  // Will be set by backend
          "src_table_name": "T_MEMBER",
          "src_table_physical_name": "t_member",
          "src_column_name": "FIRST_NAME",
          "src_column_physical_name": "first_name",
          "field_order": 1,
          "transformation_expr": "TRIM(first_name)"
        },
        {
          "mapping_id": 0,
          "src_table_name": "T_MEMBER",
          "src_table_physical_name": "t_member",
          "src_column_name": "LAST_NAME",
          "src_column_physical_name": "last_name",
          "field_order": 2,
          "transformation_expr": "TRIM(last_name)"
        }
      ]
    }
    ```
    
    Args:
        request: CreateMappingRequest with mapped_field and mapping_details
    
    Returns:
        Dictionary with mapping_id and status
    
    Raises:
        HTTPException 400: If validation fails
        HTTPException 500: If database operation fails
    """
    try:
        print(f"[Mapping V2 API] Creating mapping: {request.mapped_field.tgt_column_name}")
        print(f"[Mapping V2 API] Source fields: {len(request.mapping_details)}")
        print(f"[Mapping V2 API] Join conditions: {len(request.mapping_joins or [])}")
        
        result = await mapping_service.create_mapping(
            mapped_field_data=request.mapped_field,
            mapping_details=request.mapping_details,
            mapping_joins=request.mapping_joins or []
        )
        
        print(f"[Mapping V2 API] Mapping created with ID: {result['mapping_id']}")
        
        return result
        
    except ValueError as e:
        print(f"[Mapping V2 API] Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[Mapping V2 API] Error creating mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Dict[str, Any]])
async def get_all_mappings(request: Request):
    """
    Get all multi-field mappings.
    
    Returns mappings with their source fields based on user permissions:
    - **Regular users**: Only see their own mappings (filtered by mapped_by)
    - **Admins**: See all mappings from all users
    
    Each mapping includes:
    - Target field info (from mapped_fields table)
    - List of source fields (from mapping_details table)
    - Ordering and transformations
    
    **Example Response:**
    ```json
    [
      {
        "mapping_id": 1,
        "tgt_table_name": "slv_member",
        "tgt_column_name": "full_name",
        "concat_strategy": "SPACE",
        "transformation_expression": "CONCAT(TRIM(first_name), ' ', TRIM(last_name))",
        "mapped_at": "2025-01-15T10:30:00",
        "mapped_by": "john.doe@example.com",
        "source_fields": [
          {
            "detail_id": 1,
            "src_column_name": "FIRST_NAME",
            "field_order": 1,
            "transformation_expr": "TRIM(first_name)"
          },
          {
            "detail_id": 2,
            "src_column_name": "LAST_NAME",
            "field_order": 2,
            "transformation_expr": "TRIM(last_name)"
          }
        ]
      }
    ]
    ```
    
    Args:
        request: FastAPI Request object (for extracting user email)
    
    Returns:
        List of mapping dictionaries with nested source_fields
    
    Raises:
        HTTPException 500: If database query fails
    """
    try:
        print(f"[Mapping V2 API] GET /api/v2/mappings/ called")
        
        # Get current user
        current_user_email = get_current_user_email(request)
        print(f"[Mapping V2 API] User: {current_user_email}")
        
        # Check admin status
        try:
            is_admin = is_admin_user(current_user_email)
            print(f"[Mapping V2 API] Admin: {is_admin}")
        except Exception as admin_check_error:
            print(f"[Mapping V2 API] Admin check failed: {str(admin_check_error)}")
            # Default to non-admin if check fails
            is_admin = False
        
        # Get mappings with optional user filter
        user_filter = None if is_admin else current_user_email
        print(f"[Mapping V2 API] User filter: {user_filter}")
        
        mappings = await mapping_service.get_all_mappings(user_filter=user_filter)
        
        print(f"[Mapping V2 API] Retrieved {len(mappings)} mappings")
        return mappings
        
    except Exception as e:
        print(f"[Mapping V2 API] Error fetching mappings: {str(e)}")
        print(f"[Mapping V2 API] Error type: {type(e).__name__}")
        import traceback
        print(f"[Mapping V2 API] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateMappingRequest(BaseModel):
    """
    Request body for updating an existing mapping (restricted fields only).
    
    Only allows updating:
    - concat_strategy and concat_separator
    - transformation_expr for existing source fields (by detail_id)
    - join conditions
    
    Cannot change:
    - Target field
    - Source fields list (add/remove)
    - Field order
    
    Attributes:
        concat_strategy: Concatenation strategy (SPACE, COMMA, PIPE, CUSTOM, NONE)
        concat_separator: Custom separator if strategy is CUSTOM
        transformation_updates: Dict mapping detail_id to new transformation_expr
        mapping_joins: Updated list of join conditions
    """
    concat_strategy: Optional[str] = Field(None, description="Concatenation strategy")
    concat_separator: Optional[str] = Field(None, description="Custom separator")
    transformation_updates: Optional[Dict[int, str]] = Field(
        default={},
        description="Map of detail_id to new transformation_expr"
    )
    mapping_joins: Optional[List[MappingJoinCreateV2]] = Field(
        default=None,
        description="Updated join conditions (replaces all existing joins)"
    )


@router.put("/{mapping_id}", response_model=Dict[str, Any])
async def update_mapping(mapping_id: int, request: UpdateMappingRequest = Body(...)):
    """
    Update an existing mapping (restricted fields only).
    
    **Allowed Updates:**
    - Concatenation strategy and separator
    - Transformation expressions for existing source fields
    - Join conditions
    
    **NOT Allowed (requires delete + create new):**
    - Change target field
    - Add/remove source fields
    - Change field order
    
    **Example:**
    ```json
    {
      "concat_strategy": "PIPE",
      "concat_separator": null,
      "transformation_updates": {
        "1": "UPPER(TRIM(first_name))",
        "2": "UPPER(TRIM(last_name))"
      },
      "mapping_joins": [
        {
          "left_table": "t_member",
          "left_column": "member_id",
          "right_table": "t_address",
          "right_column": "member_id",
          "join_type": "LEFT"
        }
      ]
    }
    ```
    
    Args:
        mapping_id: ID of the mapping to update
        request: UpdateMappingRequest with allowed updates
    
    Returns:
        Dictionary with updated mapping info
    
    Raises:
        HTTPException 404: If mapping not found
        HTTPException 400: If validation fails
        HTTPException 500: If database operation fails
    """
    try:
        print(f"[Mapping V2 API] Updating mapping ID: {mapping_id}")
        print(f"[Mapping V2 API] Concat strategy: {request.concat_strategy}")
        print(f"[Mapping V2 API] Transformation updates: {len(request.transformation_updates or {})}")
        print(f"[Mapping V2 API] Join updates: {len(request.mapping_joins or [])}")
        
        result = await mapping_service.update_mapping(
            mapping_id=mapping_id,
            concat_strategy=request.concat_strategy,
            concat_separator=request.concat_separator,
            transformation_updates=request.transformation_updates or {},
            mapping_joins=request.mapping_joins
        )
        
        print(f"[Mapping V2 API] Mapping {mapping_id} updated successfully")
        
        return result
        
    except ValueError as e:
        print(f"[Mapping V2 API] Validation error: {str(e)}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[Mapping V2 API] Error updating mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{mapping_id}")
async def delete_mapping(mapping_id: int):
    """
    Delete a mapping by ID.
    
    Deletes the mapping and all associated source field details and join conditions.
    
    Args:
        mapping_id: ID of the mapping to delete (mapped_field_id)
    
    Returns:
        Success message
    
    Raises:
        HTTPException 404: If mapping not found
        HTTPException 500: If delete operation fails
    """
    try:
        result = await mapping_service.delete_mapping(mapping_id)
        print(f"[Mapping V2 API] Deleted mapping ID: {mapping_id}")
        return result
        
    except Exception as e:
        print(f"[Mapping V2 API] Error deleting mapping: {str(e)}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Mapping ID {mapping_id} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check for Mappings V2 service.
    
    Returns:
        dict: Status and version information
    """
    return {
        "status": "healthy",
        "service": "Mappings V2",
        "features": [
            "Multi-field mapping CRUD",
            "Source field ordering",
            "Per-field transformations",
            "Automatic unmapped cleanup"
        ]
    }

