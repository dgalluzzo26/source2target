"""
Mapping API endpoints.
"""
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
from pydantic import BaseModel
import io
import csv
from backend.models.mapping import MappedField, UnmappedField
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


@router.get("/unmapped-fields", response_model=List[UnmappedField])
async def get_unmapped_fields(request: Request):
    """
    Get all unmapped fields for the current user.
    Returns fields where tgt_column_name IS NULL, filtered by source_owners.
    """
    try:
        print("[Mapping Router] GET /unmapped-fields called")
        
        # Get current user email from request headers
        current_user_email = None
        
        # Try X-Forwarded-Email header (Databricks App)
        forwarded_email = request.headers.get('x-forwarded-email')
        if forwarded_email and '@' in forwarded_email:
            current_user_email = forwarded_email
        
        # Fallback to demo user if no email found
        if not current_user_email:
            current_user_email = "demo.user@gainwell.com"
        
        print(f"[Mapping Router] User email: {current_user_email}")
        
        result = await mapping_service.get_all_unmapped_fields(current_user_email)
        print(f"[Mapping Router] Returning {len(result)} unmapped fields")
        return result
    except Exception as e:
        print(f"[Mapping Router] ERROR fetching unmapped fields: {str(e)}")
        import traceback
        print(f"[Mapping Router] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-template")
async def download_template(request: Request):
    """
    Download a CSV template with headers and one example row.
    This serves as a format guide for users to fill in their mappings.
    """
    try:
        print("[Mapping Router] GET /download-template called")
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header with SOURCE columns only (target columns will be NULL on insert)
        writer.writerow([
            'src_table_name',
            'src_column_name',
            'src_column_physical_name',
            'src_nullable',
            'src_physical_datatype',
            'src_comments'
        ])
        
        # Write one example row
        writer.writerow([
            'patient_demographics',                    # src_table_name
            'patient_id',                              # src_column_name
            'patient_id',                              # src_column_physical_name
            'NO',                                       # src_nullable
            'STRING',                                   # src_physical_datatype
            'Unique identifier for patient records'    # src_comments
        ])
        
        # Create streaming response
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=mapping_template.csv"
            }
        )
    except Exception as e:
        print(f"[Mapping Router] ERROR generating template: {str(e)}")
        import traceback
        print(f"[Mapping Router] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-template")
async def upload_template(request: Request, file: UploadFile = File(...)):
    """
    Upload a CSV template with target mappings filled in.
    Updates the mapping table with the provided target mappings.
    """
    try:
        print("[Mapping Router] POST /upload-template called")
        print(f"[Mapping Router] File: {file.filename}, Content-Type: {file.content_type}")
        
        # Get current user email
        current_user_email = None
        forwarded_email = request.headers.get('x-forwarded-email')
        if forwarded_email and '@' in forwarded_email:
            current_user_email = forwarded_email
        if not current_user_email:
            current_user_email = "demo.user@gainwell.com"
        
        print(f"[Mapping Router] User email: {current_user_email}")
        
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Read and parse CSV
        contents = await file.read()
        decoded = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded))
        
        # Validate required columns (only source columns are required)
        required_columns = {
            'src_table_name', 'src_column_name',
            'src_column_physical_name', 'src_nullable',
            'src_physical_datatype', 'src_comments'
        }
        
        if not required_columns.issubset(set(csv_reader.fieldnames or [])):
            missing = required_columns - set(csv_reader.fieldnames or [])
            raise HTTPException(
                status_code=400,
                detail=f"CSV missing required columns: {', '.join(missing)}"
            )
        
        # Process rows - add all source fields as unmapped (tgt_columns = NULL)
        mappings = []
        for row_num, row in enumerate(csv_reader, start=2):  # start=2 because row 1 is header
            # Skip empty rows
            if not row.get('src_table_name') or not row.get('src_column_name'):
                print(f"[Mapping Router] Skipping row {row_num} - missing source table/column")
                continue
            
            mappings.append({
                'src_table_name': row['src_table_name'],
                'src_column_name': row['src_column_name'],
                'src_column_physical_name': row.get('src_column_physical_name', row['src_column_name']),
                'src_nullable': row.get('src_nullable', 'YES'),
                'src_physical_datatype': row.get('src_physical_datatype', 'STRING'),
                'src_comments': row.get('src_comments', '')
            })
        
        print(f"[Mapping Router] Parsed {len(mappings)} valid mappings from CSV")
        
        if len(mappings) == 0:
            raise HTTPException(
                status_code=400,
                detail="No valid mappings found in CSV. Please fill in target columns."
            )
        
        # Apply mappings via service
        result = await mapping_service.apply_bulk_mappings(current_user_email, mappings)
        
        return {
            "status": "success",
            "message": f"Successfully uploaded {len(mappings)} mappings",
            "mappings_applied": len(mappings),
            "details": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Mapping Router] ERROR uploading template: {str(e)}")
        import traceback
        print(f"[Mapping Router] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/unmap-field")
async def unmap_field(request: Request, src_table_name: str, src_column_name: str):
    """
    Remove mapping for a specific field.
    Sets tgt_columns to NULL for the specified source field.
    """
    try:
        print(f"[Mapping Router] DELETE /unmap-field called for {src_table_name}.{src_column_name}")
        
        # Get current user email
        current_user_email = None
        forwarded_email = request.headers.get('x-forwarded-email')
        if forwarded_email and '@' in forwarded_email:
            current_user_email = forwarded_email
        if not current_user_email:
            current_user_email = "demo.user@gainwell.com"
        
        print(f"[Mapping Router] User email: {current_user_email}")
        
        # Unmap the field
        result = await mapping_service.unmap_field(
            current_user_email,
            src_table_name,
            src_column_name
        )
        
        return result
        
    except Exception as e:
        print(f"[Mapping Router] ERROR unmapping field: {str(e)}")
        import traceback
        print(f"[Mapping Router] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-semantic-table")
async def search_semantic_table(request: Request, search_term: str):
    """
    Search the semantic table by table name, column name, or description.
    Returns up to 50 matching records for manual mapping selection.
    """
    try:
        print(f"[Mapping Router] GET /search-semantic-table called with term: {search_term}")
        
        if not search_term or not search_term.strip():
            raise HTTPException(status_code=400, detail="Search term is required")
        
        # Search semantic table
        results = await mapping_service.search_semantic_table(search_term.strip())
        
        print(f"[Mapping Router] Returning {len(results)} search results")
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Mapping Router] ERROR searching semantic table: {str(e)}")
        import traceback
        print(f"[Mapping Router] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


class SaveManualMappingRequest(BaseModel):
    """Request model for saving a manual mapping."""
    src_table_name: str
    src_column_name: str
    tgt_table_name: str
    tgt_column_name: str
    tgt_table_physical: str
    tgt_column_physical: str


@router.post("/save-manual-mapping")
async def save_manual_mapping(request: Request, body: SaveManualMappingRequest):
    """
    Save a manual mapping selected by the user.
    Updates the mapping table with the target columns.
    """
    try:
        print(f"[Mapping Router] POST /save-manual-mapping called")
        print(f"[Mapping Router] Source: {body.src_table_name}.{body.src_column_name}")
        print(f"[Mapping Router] Target: {body.tgt_table_name}.{body.tgt_column_name}")
        
        # Get current user email
        current_user_email = None
        forwarded_email = request.headers.get('x-forwarded-email')
        if forwarded_email and '@' in forwarded_email:
            current_user_email = forwarded_email
        if not current_user_email:
            current_user_email = "demo.user@gainwell.com"
        
        print(f"[Mapping Router] User email: {current_user_email}")
        
        # Save the mapping
        result = await mapping_service.save_manual_mapping(
            current_user_email,
            body.src_table_name,
            body.src_column_name,
            body.tgt_table_name,
            body.tgt_column_name,
            body.tgt_table_physical,
            body.tgt_column_physical
        )
        
        return result
        
    except Exception as e:
        print(f"[Mapping Router] ERROR saving manual mapping: {str(e)}")
        import traceback
        print(f"[Mapping Router] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

