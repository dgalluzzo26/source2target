"""
Mapping API endpoints.
"""
from fastapi import APIRouter, HTTPException, Request
from typing import List
from backend.models.mapping import MappedField
from backend.services.mapping_service import MappingService


router = APIRouter(prefix="/api/mapping", tags=["mapping"])
mapping_service = MappingService()


@router.get("/mapped-fields", response_model=List[MappedField])
async def get_mapped_fields(request: Request):
    """
    Get all mapped fields for the current user.
    Filtered by source_owners to show only user's mappings.
    """
    try:
        print("[Mapping Router] GET /mapped-fields called")
        
        # Get current user email from request headers (same as auth endpoint)
        current_user_email = None
        
        # Try X-Forwarded-Email header (Databricks App)
        forwarded_email = request.headers.get('x-forwarded-email')
        if forwarded_email and '@' in forwarded_email:
            current_user_email = forwarded_email
        
        # Fallback to demo user if no email found
        if not current_user_email:
            current_user_email = "demo.user@gainwell.com"
        
        print(f"[Mapping Router] User email: {current_user_email}")
        
        result = await mapping_service.get_all_mapped_fields(current_user_email)
        print(f"[Mapping Router] Returning {len(result)} mapped fields")
        return result
    except Exception as e:
        print(f"[Mapping Router] ERROR fetching mapped fields: {str(e)}")
        import traceback
        print(f"[Mapping Router] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

