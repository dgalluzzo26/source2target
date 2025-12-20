"""
FastAPI router for pattern import endpoints.

Admin-only endpoints for bulk importing historical mapping patterns.

Workflow:
1. POST /upload - Upload CSV file, get parsed data and headers
2. POST /session - Create import session with column mapping
3. POST /session/{id}/process - Process patterns (generate join_metadata)
4. GET /session/{id}/preview - Get processed patterns for review
5. POST /session/{id}/save - Save approved patterns to mapped_fields
6. DELETE /session/{id} - Cancel and delete session
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import uuid
from backend.services.pattern_import_service import PatternImportService
from backend.services.auth_service import AuthService
from backend.services.vector_search_service import VectorSearchService

router = APIRouter(prefix="/api/v4/admin/patterns", tags=["Pattern Import (Admin)"])

pattern_import_service = PatternImportService()
auth_service = AuthService()
vector_search_service = VectorSearchService()


async def get_current_user_email(request: Request) -> str:
    """Extract user email from request headers."""
    return request.headers.get("X-User-Email", "anonymous@example.com")


async def require_admin(request: Request) -> str:
    """Require admin access, return user email."""
    user_email = await get_current_user_email(request)
    try:
        is_admin = await auth_service.is_user_admin(user_email)
        if not is_admin:
            raise HTTPException(
                status_code=403, 
                detail="Admin access required for pattern import"
            )
        return user_email
    except HTTPException:
        raise
    except Exception as e:
        # In development, allow access
        print(f"[Pattern Import] Admin check failed: {e}, allowing in dev mode")
        return user_email


# =============================================================================
# REQUEST MODELS
# =============================================================================

class ColumnMappingRequest(BaseModel):
    """Request to create an import session with column mapping."""
    column_mapping: Dict[str, str]  # mapped_fields column -> CSV column


class SavePatternsRequest(BaseModel):
    """Request to save patterns."""
    pattern_indices: Optional[List[int]] = None  # Specific patterns to save, or all if None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/upload")
async def upload_csv(
    request: Request,
    file: UploadFile = File(..., description="CSV file with historical mappings")
):
    """
    Upload and parse a CSV file with historical mapping patterns.
    
    Returns parsed headers and preview data for column mapping.
    
    Admin only.
    """
    await require_admin(request)
    
    try:
        # Read file content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Parse CSV
        result = pattern_import_service.parse_csv(csv_content)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Pattern Import] Error uploading CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session")
async def create_session(
    request: Request,
    file: UploadFile = File(..., description="CSV file"),
    column_mapping: str = Body(..., description="JSON string of column mapping")
):
    """
    Create an import session with column mapping.
    
    Args:
        file: CSV file
        column_mapping: JSON string mapping mapped_fields columns to CSV columns
        
    Returns:
        Session ID and info
        
    Admin only.
    """
    user_email = await require_admin(request)
    
    try:
        import json
        
        # Parse column mapping
        mapping = json.loads(column_mapping)
        
        # Read and parse CSV
        content = await file.read()
        csv_content = content.decode('utf-8')
        csv_data = pattern_import_service.parse_csv(csv_content)
        
        if csv_data.get("status") == "error":
            raise HTTPException(status_code=400, detail=csv_data.get("error"))
        
        # Create session
        session_id = str(uuid.uuid4())
        result = pattern_import_service.create_session(
            session_id,
            csv_data,
            mapping,
            user_email
        )
        
        return result
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid column mapping JSON: {e}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Pattern Import] Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/process")
async def process_patterns(
    session_id: str,
    request: Request
):
    """
    Process patterns in a session - generate join_metadata via LLM.
    
    This can take time for large files as it calls LLM for each pattern.
    
    Admin only.
    """
    await require_admin(request)
    
    try:
        result = await pattern_import_service.process_patterns(session_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Pattern Import] Error processing patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/preview")
async def get_preview(
    session_id: str,
    request: Request
):
    """
    Get preview of processed patterns for review.
    
    Returns all patterns with generated join_metadata for approval.
    
    Admin only.
    """
    await require_admin(request)
    
    try:
        result = pattern_import_service.get_preview(session_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result.get("error"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Pattern Import] Error getting preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/progress")
async def get_progress(
    session_id: str,
    request: Request
):
    """
    Get processing progress for a session.
    
    Admin only.
    """
    await require_admin(request)
    
    try:
        session = pattern_import_service.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "status": session.get("status"),
            "progress": session.get("processing_progress", 0),
            "total_rows": session.get("total_rows", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Pattern Import] Error getting progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/save")
async def save_patterns(
    session_id: str,
    request: Request,
    body: SavePatternsRequest = Body(default=SavePatternsRequest())
):
    """
    Save approved patterns to mapped_fields.
    
    Optionally specify pattern_indices to save specific patterns,
    or save all if not specified.
    
    Triggers vector search index sync after save.
    
    Admin only.
    """
    await require_admin(request)
    
    try:
        result = await pattern_import_service.save_patterns(
            session_id,
            body.pattern_indices
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Pattern Import] Error saving patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    request: Request
):
    """
    Delete/cancel an import session.
    
    Admin only.
    """
    await require_admin(request)
    
    try:
        deleted = pattern_import_service.delete_session(session_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"status": "success", "message": "Session deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Pattern Import] Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mappable-columns")
async def get_mappable_columns(request: Request):
    """
    Get list of mapped_fields columns that can be mapped from CSV.
    
    Admin only.
    """
    await require_admin(request)
    
    return {
        "columns": pattern_import_service.MAPPABLE_COLUMNS,
        "required": [
            "tgt_table_physical_name",
            "tgt_column_physical_name",
            "source_expression"
        ]
    }


@router.post("/sync-vector-index")
async def sync_vector_index(request: Request):
    """
    Manually trigger vector search index sync.
    
    Admin only.
    """
    await require_admin(request)
    
    try:
        result = await vector_search_service.sync_mapped_fields_index()
        return result
    except Exception as e:
        print(f"[Pattern Import] Error syncing index: {e}")
        raise HTTPException(status_code=500, detail=str(e))

