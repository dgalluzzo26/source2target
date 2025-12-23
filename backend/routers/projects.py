"""
FastAPI router for V4 project endpoints.

V4 Target-First Workflow:
- Create and manage mapping projects
- Upload source fields to a project
- Initialize target tables from semantic_fields

Access Control:
- Users can only see projects they created OR where they are listed in team_members
- Admins can see all projects
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Request, Depends, Body
from typing import List, Optional
from pydantic import BaseModel
import csv
import io
import os
from backend.services.project_service import ProjectService
from backend.services.unmapped_fields_service import UnmappedFieldsService
from backend.services.auth_service import AuthService
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
auth_service = AuthService()


# =============================================================================
# AUTH HELPER
# =============================================================================

async def get_current_user_email(request: Request) -> Optional[str]:
    """
    Extract current user's email from request headers.
    Returns None if no user detected (allows anonymous access in dev).
    """
    # Try Databricks App headers first
    email = request.headers.get('x-forwarded-email')
    if email and '@' in email:
        return email.lower()
    
    # Try other common headers
    for header in ['x-databricks-user', 'x-user-email', 'x-forwarded-user']:
        value = request.headers.get(header)
        if value and '@' in value:
            return value.lower()
    
    # Environment variable fallback
    databricks_user = os.environ.get('DATABRICKS_USER')
    if databricks_user and '@' in databricks_user:
        return databricks_user.lower()
    
    # Dev mode fallback - allow anonymous access
    return None


async def get_current_user_is_admin(request: Request) -> bool:
    """Check if current user is an admin (uses admin_users list from config)."""
    email = await get_current_user_email(request)
    if not email:
        return False
    return await auth_service.is_user_admin(email)


def user_can_access_project(project: dict, user_email: Optional[str], is_admin: bool) -> bool:
    """
    Check if user has access to a project.
    
    Access granted if:
    - User is admin
    - User created the project
    - User is in team_members list
    - No user detected (dev mode - allows all)
    """
    if is_admin:
        return True
    
    if not user_email:
        # Dev mode - no user detected, allow access
        return True
    
    # Check if creator
    created_by = (project.get("created_by") or "").lower()
    if created_by == user_email:
        return True
    
    # Check team_members (comma or pipe separated)
    team_members = (project.get("team_members") or "").lower()
    if user_email in team_members:
        return True
    
    return False


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
    request: Request,
    include_archived: bool = Query(False, description="Include archived projects")
):
    """
    Get mapping projects the current user has access to.
    
    Users see projects they created OR where they're in team_members.
    Admins see all projects.
    
    Returns list of projects with progress stats.
    """
    try:
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        # Admins see all, regular users get filtered
        filter_email = None if is_admin else user_email
        
        projects = await project_service.get_projects(
            include_archived=include_archived,
            user_email=filter_email
        )
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
async def get_project(project_id: int, request: Request):
    """
    Get a single project by ID with full details.
    
    Access Control: User must be creator, team member, or admin.
    """
    try:
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check access
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        if not user_can_access_project(project, user_email, is_admin):
            raise HTTPException(
                status_code=403, 
                detail="You don't have access to this project. Contact the project owner to be added to team_members."
            )
        
        return project
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Projects Router] Error getting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}", response_model=UpdateProjectResponse)
async def update_project(project_id: int, data: MappingProjectUpdate, request: Request):
    """
    Update a project's metadata or status.
    
    Access Control: User must be creator, team member, or admin.
    """
    try:
        # Check access first
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        if not user_can_access_project(project, user_email, is_admin):
            raise HTTPException(status_code=403, detail="You don't have access to this project")
        
        result = await project_service.update_project(project_id, data)
        return UpdateProjectResponse(
            project_id=project_id,
            status=result["status"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Projects Router] Error updating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: int, request: Request):
    """
    Delete a project and all related data.
    
    This will delete:
    - Target table status records
    - Mapping suggestions
    
    Source fields will be unlinked (not deleted).
    Approved mappings will remain.
    
    Access Control: User must be creator or admin (team members cannot delete).
    """
    try:
        # Check access - only creator or admin can delete
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        # For delete, only creator or admin (not just team member)
        created_by = (project.get("created_by") or "").lower()
        if not is_admin and (not user_email or created_by != user_email):
            raise HTTPException(
                status_code=403, 
                detail="Only the project creator or admin can delete a project"
            )
        
        result = await project_service.delete_project(project_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Projects Router] Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TARGET TABLE INITIALIZATION
# =============================================================================

@router.post("/{project_id}/initialize-tables", response_model=InitializeTablesResponse)
async def initialize_target_tables(
    project_id: int,
    request: Request,
    domain: Optional[str] = Query(None, description="Domain filter (pipe-separated for multiple)")
):
    """
    Initialize target tables for a project from semantic_fields.
    
    Creates target_table_status rows for each unique target table.
    Optionally filter by domain (e.g., "Member" or "Member|Claims").
    
    Call this after uploading source fields.
    
    Access Control: User must be creator, team member, or admin.
    """
    print(f"[Projects Router] >>> initialize_target_tables ENDPOINT CALLED <<<")
    print(f"[Projects Router] project_id={project_id}, domain={domain}")
    try:
        # Verify project exists and check access
        project = await project_service.get_project_by_id(project_id)
        print(f"[Projects Router] Project found: {project.get('project_name') if project else 'None'}")
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        if not user_can_access_project(project, user_email, is_admin):
            raise HTTPException(status_code=403, detail="You don't have access to this project")
        
        # Use domain parameter if provided, otherwise use project's target_domains
        # If neither is set (or empty string), domain_filter will be None (= ALL tables)
        project_domains = project.get("target_domains")
        
        # Treat empty strings as None (= ALL domains)
        if domain is not None and domain.strip():
            domain_filter = domain.strip()
        elif project_domains and project_domains.strip():
            domain_filter = project_domains.strip()
        else:
            domain_filter = None  # This means ALL domains
            
        print(f"[Projects Router] Project target_domains: {project_domains}")
        print(f"[Projects Router] Final domain_filter: {domain_filter} (None = ALL domains)")
        
        result = await project_service.initialize_target_tables(project_id, domain_filter)
        print(f"[Projects Router] Result: {result}")
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
    request: Request,
    file: UploadFile = File(..., description="CSV file with source fields")
):
    """
    Upload source fields for a project from CSV.
    
    This uses the SAME format as the legacy unmapped fields upload.
    
    Expected CSV columns (all required for AI matching):
    - src_table_name: Logical source table name
    - src_table_physical_name: Physical table name in database
    - src_column_name: Logical source column name
    - src_column_physical_name: Physical column name in database
    - src_physical_datatype: Data type (STRING, INT, DATE, etc.)
    - src_nullable: Whether column is nullable (YES/NO)
    - src_comments: Column description (CRITICAL for AI vector search matching)
    - domain: Optional domain category (e.g., member, provider)
    
    Access Control: User must be creator, team member, or admin.
    """
    try:
        # Verify project exists and check access
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        if not user_can_access_project(project, user_email, is_admin):
            raise HTTPException(status_code=403, detail="You don't have access to this project")
        
        # Read CSV
        contents = await file.read()
        decoded = contents.decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        
        # Validate headers
        required_columns = [
            'src_table_name', 
            'src_table_physical_name', 
            'src_column_name', 
            'src_column_physical_name',
            'src_physical_datatype',
            'src_nullable',
            'src_comments'
        ]
        
        headers = reader.fieldnames or []
        missing_columns = [col for col in required_columns if col not in headers]
        
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {', '.join(missing_columns)}. "
                       f"Please download the template to see the correct format."
            )
        
        fields_to_upload = []
        tables_found = set()
        row_number = 1  # Start after header
        warnings = []
        
        for row in reader:
            row_number += 1
            
            # Validate required fields have values
            if not row.get("src_table_name") or not row.get("src_column_name"):
                warnings.append(f"Row {row_number}: Skipped - missing table or column name")
                continue
            
            # Warn if src_comments is empty (affects AI matching quality)
            if not row.get("src_comments", "").strip():
                warnings.append(f"Row {row_number}: {row['src_table_name']}.{row['src_column_name']} - "
                               f"No description provided (may reduce AI matching accuracy)")
            
            field = {
                "src_table_name": row.get("src_table_name", "").strip(),
                "src_table_physical_name": row.get("src_table_physical_name", row.get("src_table_name", "")).strip(),
                "src_column_name": row.get("src_column_name", "").strip(),
                "src_column_physical_name": row.get("src_column_physical_name", row.get("src_column_name", "")).strip(),
                "src_physical_datatype": row.get("src_physical_datatype", "STRING").strip(),
                "src_nullable": row.get("src_nullable", "YES").strip().upper(),
                "src_comments": row.get("src_comments", "").strip(),
                "domain": row.get("domain", "").strip(),
                "project_id": project_id
            }
            
            fields_to_upload.append(field)
            tables_found.add(field["src_table_name"])
        
        if not fields_to_upload:
            raise HTTPException(
                status_code=400, 
                detail="No valid fields found in CSV. Ensure all required columns have values."
            )
        
        # Bulk upload fields
        result = await unmapped_fields_service.bulk_upload_with_project(
            fields_to_upload, 
            project_id
        )
        
        # Log warnings if any
        if warnings:
            print(f"[Projects Router] Upload warnings for project {project_id}:")
            for w in warnings[:10]:  # Log first 10 warnings
                print(f"  - {w}")
            if len(warnings) > 10:
                print(f"  ... and {len(warnings) - 10} more warnings")
        
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
    request: Request,
    table_filter: Optional[str] = Query(None, description="Filter by table name")
):
    """
    Get source fields for a project.
    
    Optionally filter by source table name.
    
    Access Control: User must be creator, team member, or admin.
    """
    try:
        # Check access
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        if not user_can_access_project(project, user_email, is_admin):
            raise HTTPException(status_code=403, detail="You don't have access to this project")
        
        fields = await unmapped_fields_service.get_fields_by_project(
            project_id, 
            table_filter=table_filter
        )
        return fields
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Projects Router] Error getting source fields: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}/source-fields/{field_id}")
async def update_source_field(
    project_id: int,
    field_id: int,
    request: Request,
    updates: dict = Body(...)
):
    """
    Update a source field.
    
    Allows editing source field metadata (name, description, datatype, etc.).
    
    Access Control: User must be creator, team member, or admin.
    """
    try:
        # Get project and check access
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        if not user_can_access_project(project, user_email, is_admin):
            raise HTTPException(status_code=403, detail="You don't have access to this project")
        
        # Update the field
        result = await unmapped_fields_service.update_field(field_id, updates)
        
        return {"status": "success", "field_id": field_id, "updated": result}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Projects Router] Error updating source field: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/source-fields/{field_id}")
async def delete_source_field(
    project_id: int,
    field_id: int,
    request: Request
):
    """
    Delete a source field.
    
    Removes the field from the project's source fields.
    
    Access Control: User must be creator, team member, or admin.
    """
    try:
        # Get project and check access
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        if not user_can_access_project(project, user_email, is_admin):
            raise HTTPException(status_code=403, detail="You don't have access to this project")
        
        # Delete the field
        result = await unmapped_fields_service.delete_unmapped_field(field_id)
        
        return {"status": "success", "field_id": field_id, "message": "Field deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Projects Router] Error deleting source field: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/source-fields")
async def delete_all_source_fields(
    project_id: int,
    request: Request,
    table_name: Optional[str] = Query(None, description="Delete only fields from this table")
):
    """
    Delete all source fields for a project, optionally filtered by table name.
    
    Access Control: User must be creator, team member, or admin.
    """
    try:
        # Get project and check access
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        if not user_can_access_project(project, user_email, is_admin):
            raise HTTPException(status_code=403, detail="You don't have access to this project")
        
        # Delete fields
        result = await unmapped_fields_service.delete_fields_by_project(
            project_id, 
            table_name=table_name
        )
        
        return {
            "status": "success", 
            "project_id": project_id,
            "table_name": table_name,
            "deleted_count": result.get("deleted_count", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Projects Router] Error deleting source fields: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PROJECT STATS
# =============================================================================

@router.get("/{project_id}/stats", response_model=dict)
async def get_project_stats(project_id: int, request: Request):
    """
    Get detailed statistics for a project.
    
    Returns counts for tables, columns, and progress.
    
    Access Control: User must be creator, team member, or admin.
    """
    try:
        # Get project and check access
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        if not user_can_access_project(project, user_email, is_admin):
            raise HTTPException(status_code=403, detail="You don't have access to this project")
        
        # Update counters
        await project_service.update_project_counters(project_id)
        
        # Get fresh project data
        project = await project_service.get_project_by_id(project_id)
        
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

