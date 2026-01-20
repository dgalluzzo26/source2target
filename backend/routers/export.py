"""
FastAPI router for export endpoints.

Provides CSV and SQL export functionality for mapped fields.
"""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from typing import Optional, List
from backend.services.export_service import ExportService
from backend.services.project_service import ProjectService
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/api/v4/projects", tags=["Export"])

export_service = ExportService()
project_service = ProjectService()
auth_service = AuthService()


async def get_current_user_email(request: Request) -> str:
    """Extract user email from request headers."""
    return request.headers.get("X-User-Email", "anonymous@example.com")


async def get_current_user_is_admin(request: Request) -> bool:
    """Check if current user is admin."""
    user_email = await get_current_user_email(request)
    try:
        return await auth_service.is_user_admin(user_email)
    except:
        return False


def user_can_access_project(project: dict, user_email: str, is_admin: bool) -> bool:
    """Check if user can access a project."""
    if is_admin:
        return True
    if project.get("created_by") == user_email:
        return True
    team_members = project.get("team_members", "") or ""
    if user_email in [m.strip() for m in team_members.split(",") if m.strip()]:
        return True
    return False


@router.get("/{project_id}/export/tables")
async def get_exportable_tables(
    project_id: int,
    request: Request
):
    """
    Get list of tables with mappings that can be exported.
    
    Returns table names and column counts.
    """
    try:
        # Check access
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        if not user_can_access_project(project, user_email, is_admin):
            raise HTTPException(status_code=403, detail="Access denied")
        
        tables = await export_service.get_mapped_tables(project_id)
        
        return {
            "project_id": project_id,
            "tables": tables
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Export Router] Error getting exportable tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/export/csv", response_class=PlainTextResponse)
async def export_csv(
    project_id: int,
    request: Request,
    table_name: Optional[str] = Query(None, description="Export specific table only")
):
    """
    Export mappings as CSV file.
    
    Args:
        project_id: Project ID
        table_name: Optional table filter
        
    Returns:
        CSV content as plain text
    """
    try:
        # Check access
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        if not user_can_access_project(project, user_email, is_admin):
            raise HTTPException(status_code=403, detail="Access denied")
        
        csv_content = await export_service.export_csv(project_id, table_name)
        
        if not csv_content:
            raise HTTPException(status_code=404, detail="No mappings found to export")
        
        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=mappings_{project_id}{'_' + table_name if table_name else ''}.csv"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Export Router] Error exporting CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/export/sql", response_class=PlainTextResponse)
async def export_sql(
    project_id: int,
    request: Request,
    table_name: str = Query(..., description="Target table physical name"),
    target_catalog: str = Query("${TARGET_CATALOG}", description="Target catalog"),
    target_schema: str = Query("${TARGET_SCHEMA}", description="Target schema")
):
    """
    Export mappings as Databricks SQL INSERT statement.
    
    Generates a single INSERT INTO ... SELECT statement for the target table.
    
    Args:
        project_id: Project ID
        table_name: Target table physical name (required)
        target_catalog: Target catalog placeholder or name
        target_schema: Target schema placeholder or name
        
    Returns:
        SQL content as plain text
    """
    try:
        # Check access
        project = await project_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user_email = await get_current_user_email(request)
        is_admin = await get_current_user_is_admin(request)
        
        if not user_can_access_project(project, user_email, is_admin):
            raise HTTPException(status_code=403, detail="Access denied")
        
        sql_content = await export_service.export_sql(
            project_id, 
            table_name,
            target_catalog,
            target_schema
        )
        
        return PlainTextResponse(
            content=sql_content,
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={table_name}_insert.sql"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Export Router] Error exporting SQL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

