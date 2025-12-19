"""
FastAPI router for V4 project endpoints.

V4 Target-First Workflow:
- Create and manage mapping projects
- Upload source fields to a project
- Initialize target tables from semantic_fields
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Request
from typing import List, Optional
from pydantic import BaseModel
import csv
import io
from backend.services.project_service import ProjectService
from backend.services.unmapped_fields_service import UnmappedFieldsService
from backend.models.project import (
    MappingProject,
    MappingProjectCreate,
    MappingProjectUpdate,
    ProjectDashboard,
    ProjectStatus
)

router = APIRouter(prefix="/api/v4/projects", tags=["V4 Projects"])

# Service instances
project_service = ProjectService()
unmapped_fields_service = UnmappedFieldsService()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreateProjectResponse(BaseModel):
    """Response for create project."""
    project_id: int
    project_name: str
    status: str


class UpdateProjectResponse(BaseModel):
    """Response for update project."""
    project_id: int
    status: str


class InitializeTablesResponse(BaseModel):
    """Response for initialize target tables."""
    project_id: int
    tables_initialized: int
    columns_total: int
    status: str


class UploadSourceFieldsResponse(BaseModel):
    """Response for upload source fields."""
    project_id: int
    fields_uploaded: int
    tables_found: List[str]
    status: str


# =============================================================================
# PROJECT CRUD ENDPOINTS
# =============================================================================

@router.get("/", response_model=List[dict])
async def get_projects(
    include_archived: bool = Query(False, description="Include archived projects")
):
    """
    Get all mapping projects.
    
    Returns list of projects with progress stats.
    """
    try:
        projects = await project_service.get_projects(include_archived=include_archived)
        return projects
    except Exception as e:
        print(f"[Projects Router] Error getting projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=CreateProjectResponse)
async def create_project(data: MappingProjectCreate):
    """
    Create a new mapping project.
    
    After creation, you can:
    1. Upload source fields via POST /projects/{id}/source-fields
    2. Initialize target tables via POST /projects/{id}/initialize-tables
    """
    try:
        result = await project_service.create_project(data)
        return CreateProjectResponse(
            project_id=result["project_id"],
            project_name=result["project_name"],
            status=result["status"]
        )
    except Exception as e:
        print(f"[Projects Router] Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}", response_model=dict)
async def get_project(project_id: int):
    """
    Get a single project by ID with full details.
    """
    try:
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Projects Router] Error getting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}", response_model=UpdateProjectResponse)
async def update_project(project_id: int, data: MappingProjectUpdate):
    """
    Update a project's metadata or status.
    """
    try:
        result = await project_service.update_project(project_id, data)
        return UpdateProjectResponse(
            project_id=project_id,
            status=result["status"]
        )
    except Exception as e:
        print(f"[Projects Router] Error updating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: int):
    """
    Delete a project and all related data.
    
    This will delete:
    - Target table status records
    - Mapping suggestions
    
    Source fields will be unlinked (not deleted).
    Approved mappings will remain.
    """
    try:
        result = await project_service.delete_project(project_id)
        return result
    except Exception as e:
        print(f"[Projects Router] Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TARGET TABLE INITIALIZATION
# =============================================================================

@router.post("/{project_id}/initialize-tables", response_model=InitializeTablesResponse)
async def initialize_target_tables(
    project_id: int,
    domain: Optional[str] = Query(None, description="Domain filter (pipe-separated for multiple)")
):
    """
    Initialize target tables for a project from semantic_fields.
    
    Creates target_table_status rows for each unique target table.
    Optionally filter by domain (e.g., "Member" or "Member|Claims").
    
    Call this after uploading source fields.
    """
    try:
        # Verify project exists
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Use project's target_domains if no domain specified
        domain_filter = domain or project.get("target_domains")
        
        result = await project_service.initialize_target_tables(project_id, domain_filter)
        return InitializeTablesResponse(
            project_id=project_id,
            tables_initialized=result["tables_initialized"],
            columns_total=result["columns_total"],
            status=result["status"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Projects Router] Error initializing tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SOURCE FIELD UPLOAD
# =============================================================================

@router.post("/{project_id}/source-fields", response_model=UploadSourceFieldsResponse)
async def upload_source_fields(
    project_id: int,
    file: UploadFile = File(..., description="CSV file with source fields")
):
    """
    Upload source fields for a project from CSV.
    
    Expected CSV columns:
    - src_table_name (required)
    - src_column_name (required)
    - src_table_physical_name (optional, defaults to src_table_name)
    - src_column_physical_name (optional, defaults to src_column_name)
    - src_physical_datatype (optional)
    - src_nullable (optional, default YES)
    - src_comments (optional, but recommended for AI matching)
    - domain (optional)
    """
    try:
        # Verify project exists
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Read CSV
        contents = await file.read()
        decoded = contents.decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        
        fields_to_upload = []
        tables_found = set()
        
        for row in reader:
            # Validate required fields
            if not row.get("src_table_name") or not row.get("src_column_name"):
                continue
            
            field = {
                "src_table_name": row.get("src_table_name", "").strip(),
                "src_column_name": row.get("src_column_name", "").strip(),
                "src_table_physical_name": row.get("src_table_physical_name", row.get("src_table_name", "")).strip(),
                "src_column_physical_name": row.get("src_column_physical_name", row.get("src_column_name", "")).strip(),
                "src_physical_datatype": row.get("src_physical_datatype", "STRING").strip(),
                "src_nullable": row.get("src_nullable", "YES").strip(),
                "src_comments": row.get("src_comments", "").strip(),
                "domain": row.get("domain", "").strip(),
                "project_id": project_id
            }
            
            fields_to_upload.append(field)
            tables_found.add(field["src_table_name"])
        
        if not fields_to_upload:
            raise HTTPException(
                status_code=400, 
                detail="No valid fields found in CSV. Required columns: src_table_name, src_column_name"
            )
        
        # Bulk upload fields
        result = await unmapped_fields_service.bulk_upload_with_project(
            fields_to_upload, 
            project_id
        )
        
        return UploadSourceFieldsResponse(
            project_id=project_id,
            fields_uploaded=result.get("fields_uploaded", len(fields_to_upload)),
            tables_found=list(tables_found),
            status="uploaded"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Projects Router] Error uploading source fields: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/source-fields", response_model=List[dict])
async def get_project_source_fields(
    project_id: int,
    table_filter: Optional[str] = Query(None, description="Filter by table name")
):
    """
    Get source fields for a project.
    
    Optionally filter by source table name.
    """
    try:
        fields = await unmapped_fields_service.get_fields_by_project(
            project_id, 
            table_filter=table_filter
        )
        return fields
    except Exception as e:
        print(f"[Projects Router] Error getting source fields: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PROJECT STATS
# =============================================================================

@router.get("/{project_id}/stats", response_model=dict)
async def get_project_stats(project_id: int):
    """
    Get detailed statistics for a project.
    
    Returns counts for tables, columns, and progress.
    """
    try:
        # Update counters first
        await project_service.update_project_counters(project_id)
        
        # Get fresh project data
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Calculate progress
        total_columns = project.get("total_target_columns", 0)
        columns_mapped = project.get("columns_mapped", 0)
        progress_percent = round(columns_mapped * 100.0 / total_columns, 1) if total_columns > 0 else 0
        
        return {
            "project_id": project_id,
            "project_name": project.get("project_name"),
            "project_status": project.get("project_status"),
            "total_tables": project.get("total_target_tables", 0),
            "tables_complete": project.get("tables_complete", 0),
            "tables_in_progress": project.get("tables_in_progress", 0),
            "total_columns": total_columns,
            "columns_mapped": columns_mapped,
            "columns_pending_review": project.get("columns_pending_review", 0),
            "progress_percent": progress_percent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Projects Router] Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

