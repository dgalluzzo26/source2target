"""
FastAPI application entry point for Source-to-Target Mapping Platform.

This is the main FastAPI application that serves both the API backend and the
Vue.js frontend (when built). It provides:
- RESTful API endpoints for mapping, semantic table, and AI suggestions
- Authentication via Databricks workspace context
- System health checks
- Configuration management
- Static file serving for the Vue.js SPA

The application is designed to run as a Databricks App or locally for development.
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from typing import Optional, Dict, Any
from backend.services.config_service import config_service
from backend.services.system_service import system_service
from backend.services.auth_service import auth_service
from backend.routers import semantic, unmapped_fields, feedback
from backend.routers import projects, target_tables, suggestions, export, pattern_import

# Import Databricks SDK for authentication
try:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.core import Config
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    print("Warning: Databricks SDK not available")

app = FastAPI(
    title="Smart Mapper API",
    description="FastAPI backend for Smart Mapper Databricks app (V4 Target-First Workflow)",
    version="4.0.0"
)

# Configure CORS for Vue frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Databricks
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include V4 routers (target-first workflow)
app.include_router(projects.router)
app.include_router(target_tables.router)
app.include_router(suggestions.router)
app.include_router(export.router)
app.include_router(pattern_import.router)

# Include utility routers
app.include_router(unmapped_fields.router)
app.include_router(feedback.router)
app.include_router(semantic.router)

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.
    
    Simple endpoint to verify the API is running and responsive.
    
    Returns:
        dict: Status dictionary with "healthy" status
    """
    return {"status": "healthy"}

@app.get("/api/auth/current-user")
async def get_current_user(request: Request):
    """
    Get current authenticated user from Databricks context.
    
    Attempts to detect the current user through multiple methods:
    1. X-Forwarded-Email header (Databricks App primary method)
    2. Other common Databricks headers (x-databricks-user, etc.)
    3. Environment variables (DATABRICKS_USER)
    4. WorkspaceClient API (current_user.me())
    5. Fallback to demo user for local development
    
    Also checks if the user is a member of the configured admin group.
    Follows the same logic as the original Streamlit app's auth.py.
    
    Args:
        request: FastAPI Request object with headers
        
    Returns:
        dict: User information dictionary containing:
            - email: User email address
            - display_name: User's display name
            - is_admin: Boolean indicating admin status
            - detection_method: Method used to detect the user
    """
    user_info = {
        "email": None,
        "display_name": None,
        "is_admin": False,
        "detection_method": None
    }
    
    try:
        # Method 1: Check Databricks App headers (primary method for service principal apps)
        forwarded_email = request.headers.get('x-forwarded-email')
        if forwarded_email and '@' in forwarded_email:
            user_info["email"] = forwarded_email
            user_info["display_name"] = forwarded_email.split('@')[0].replace('.', ' ').title()
            user_info["detection_method"] = "X-Forwarded-Email header"
            # Check admin status using config list
            user_info["is_admin"] = await auth_service.is_user_admin(forwarded_email)
            return user_info
        
        # Method 2: Check other common headers
        user_headers = [
            'x-databricks-user',
            'x-user-email',
            'x-forwarded-user'
        ]
        for header in user_headers:
            value = request.headers.get(header)
            if value and '@' in value:
                user_info["email"] = value
                user_info["display_name"] = value.split('@')[0].replace('.', ' ').title()
                user_info["detection_method"] = f"{header} header"
                # Check admin status using config list
                user_info["is_admin"] = await auth_service.is_user_admin(value)
                return user_info
        
        # Method 3: Check environment variables
        databricks_user = os.environ.get('DATABRICKS_USER')
        if databricks_user and '@' in databricks_user:
            user_info["email"] = databricks_user
            user_info["display_name"] = databricks_user.split('@')[0].replace('.', ' ').title()
            user_info["detection_method"] = "DATABRICKS_USER env"
            # Check admin status using config list
            user_info["is_admin"] = await auth_service.is_user_admin(databricks_user)
            return user_info
        
        # Method 4: Try Databricks WorkspaceClient (if available)
        if DATABRICKS_AVAILABLE:
            try:
                w = WorkspaceClient()
                current_user = w.current_user.me()
                
                if current_user:
                    # Try to extract email
                    email = None
                    if hasattr(current_user, 'emails') and current_user.emails:
                        for email_obj in current_user.emails:
                            if hasattr(email_obj, 'value') and email_obj.value:
                                if hasattr(email_obj, 'primary') and email_obj.primary:
                                    email = email_obj.value
                                    break
                                elif not email:
                                    email = email_obj.value
                    
                    # Try user_name if no email
                    if not email and hasattr(current_user, 'user_name') and '@' in str(current_user.user_name):
                        email = current_user.user_name
                    
                    if email:
                        user_info["email"] = email
                        user_info["display_name"] = email.split('@')[0].replace('.', ' ').title()
                        user_info["detection_method"] = "WorkspaceClient API"
                        # Check admin status using config list
                        user_info["is_admin"] = await auth_service.is_user_admin(email)
                        return user_info
            except Exception as e:
                print(f"WorkspaceClient error: {str(e)}")
        
        # Method 5: Fallback to demo user for development
        user_info["email"] = "demo.user@gainwell.com"
        user_info["display_name"] = "Demo User"
        user_info["detection_method"] = "fallback (no Databricks context)"
        
    except Exception as e:
        print(f"Error getting current user: {str(e)}")
        user_info["email"] = "demo.user@gainwell.com"
        user_info["display_name"] = "Demo User"
        user_info["detection_method"] = f"error fallback: {str(e)}"
    
    return user_info

@app.get("/api/data")
async def get_data():
    """
    Sample data endpoint (for testing/demo purposes).
    
    Returns sample data to verify API connectivity and JSON serialization.
    
    Returns:
        dict: Dictionary with sample data array
    """
    return {
        "data": [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 200},
            {"id": 3, "name": "Item 3", "value": 300},
        ]
    }

@app.get("/api/system/status")
async def get_system_status():
    """
    Get comprehensive system status with live checks.
    
    Performs health checks on all critical system components:
    - Database warehouse connectivity
    - Vector search endpoint availability
    - AI model endpoint status
    - Configuration validation
    
    Uses system service for comprehensive health checks with proper timeouts.
    
    Returns:
        dict: System status dictionary with component health information
    """
    return await system_service.get_system_status()

@app.get("/api/config")
async def get_config():
    """
    Get the current application configuration.
    
    Returns the complete configuration loaded from the local JSON file,
    including database, vector search, AI model, UI, support, and security settings.
    
    Returns:
        dict: Complete configuration dictionary
    """
    config = config_service.get_config()
    return config.model_dump()

@app.put("/api/config")
async def update_config(config_data: dict):
    """
    Update the application configuration.
    
    Validates the provided configuration data and saves it to the local JSON file.
    The configuration will be available immediately to all services.
    
    Args:
        config_data: Dictionary containing the complete configuration
        
    Returns:
        dict: Result dictionary with status and message
        
    Raises:
        400: If configuration data is invalid
        500: If saving configuration fails
    """
    try:
        from backend.models.config import AppConfig
        config = AppConfig(**config_data)
        success = config_service.save_config(config)
        
        if success:
            return {
                "status": "success",
                "message": "Configuration updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")


@app.get("/api/config/project-types")
async def get_project_types():
    """
    Get the list of available project types.
    
    Returns the configured project types that can be assigned to projects.
    Used for populating dropdowns in the UI.
    
    Returns:
        dict: Dictionary with available_types and default_type
    """
    config = config_service.get_config()
    return {
        "available_types": config.project_types.available_types,
        "default_type": config.project_types.default_type
    }


# ============================================================================
# AI Enhancement Endpoint
# ============================================================================

from pydantic import BaseModel

class EnhanceDescriptionRequest(BaseModel):
    table_name: str
    column_name: str
    current_description: str = ""
    data_type: str = "STRING"

@app.post("/api/v4/ai/enhance-description")
async def enhance_description(request: EnhanceDescriptionRequest):
    """
    Use LLM to generate an enhanced description for a source field.
    
    Given the table name, column name, and current description,
    generates a more detailed and useful description.
    """
    from concurrent.futures import ThreadPoolExecutor
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
    
    try:
        config = config_service.get_config()
        # Use ai_model.foundation_model_endpoint from config
        llm_endpoint = config.ai_model.foundation_model_endpoint
        
        print(f"[AI Enhance] Processing {request.table_name}.{request.column_name} using {llm_endpoint}")
        
        # Build the prompt
        prompt = f"""You are a data documentation expert. Given a database column, generate a clear, concise, and informative description.

TABLE: {request.table_name}
COLUMN: {request.column_name}
DATA TYPE: {request.data_type}
CURRENT DESCRIPTION: {request.current_description or "(none provided)"}

Generate an improved description that:
1. Explains what this column represents in plain English
2. Mentions the data type context (e.g., if it's an ID, date, flag, code, etc.)
3. Notes any common usage patterns if inferable from the name
4. Is concise (1-2 sentences max)
5. If the current description is already good, keep it or slightly enhance it

Return ONLY the enhanced description text, nothing else. No JSON, no explanation, just the description."""

        # Call LLM - matching the pattern from suggestion_service.py
        def call_llm():
            w = WorkspaceClient()
            response = w.serving_endpoints.query(
                name=llm_endpoint,
                messages=[
                    ChatMessage(role=ChatMessageRole.USER, content=prompt)
                ],
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(call_llm)
            enhanced = future.result(timeout=30)
        
        # Clean up the response
        enhanced = enhanced.strip().strip('"').strip("'")
        
        print(f"[AI Enhance] Success: {request.column_name} -> {enhanced[:50]}...")
        
        return {"enhanced_description": enhanced}
        
    except Exception as e:
        print(f"[AI Enhance] Error for {request.table_name}.{request.column_name}: {e}")
        import traceback
        traceback.print_exc()
        # Return original description on error
        return {"enhanced_description": request.current_description or f"Column {request.column_name} from table {request.table_name}"}


class EnhanceDescriptionBatchRequest(BaseModel):
    fields: list  # List of {table_name, column_name, data_type, current_description}

@app.post("/api/v4/ai/enhance-description-batch")
async def enhance_description_batch(request: EnhanceDescriptionBatchRequest):
    """
    Batch endpoint to enhance multiple field descriptions in parallel.
    Much more efficient for large datasets (5K+ fields).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
    
    results = []
    
    try:
        config = config_service.get_config()
        llm_endpoint = config.ai_model.foundation_model_endpoint
        
        print(f"[AI Enhance Batch] Processing {len(request.fields)} fields using {llm_endpoint}")
        
        def enhance_single_field(field_data: dict) -> dict:
            """Process a single field - called in parallel"""
            table_name = field_data.get('table_name', '')
            column_name = field_data.get('column_name', '')
            data_type = field_data.get('data_type', 'STRING')
            current_desc = field_data.get('current_description', '')
            field_id = field_data.get('id')
            
            try:
                prompt = f"""You are a data documentation expert. Given a database column, generate a clear, concise description.

TABLE: {table_name}
COLUMN: {column_name}
DATA TYPE: {data_type}
CURRENT DESCRIPTION: {current_desc or "(none)"}

Generate an improved 1-2 sentence description. Return ONLY the description text."""

                w = WorkspaceClient()
                response = w.serving_endpoints.query(
                    name=llm_endpoint,
                    messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
                    max_tokens=150
                )
                enhanced = response.choices[0].message.content.strip().strip('"').strip("'")
                
                return {
                    "id": field_id,
                    "table_name": table_name,
                    "column_name": column_name,
                    "original_description": current_desc,
                    "enhanced_description": enhanced,
                    "success": True
                }
            except Exception as e:
                print(f"[AI Enhance Batch] Error for {column_name}: {e}")
                return {
                    "id": field_id,
                    "table_name": table_name,
                    "column_name": column_name,
                    "original_description": current_desc,
                    "enhanced_description": current_desc,  # Keep original on error
                    "success": False,
                    "error": str(e)
                }
        
        # Process all fields in parallel with ThreadPoolExecutor
        # Use 20 workers for good parallelism without overwhelming the API
        MAX_WORKERS = 20
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(enhance_single_field, field): field for field in request.fields}
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    field = futures[future]
                    results.append({
                        "id": field.get('id'),
                        "table_name": field.get('table_name', ''),
                        "column_name": field.get('column_name', ''),
                        "original_description": field.get('current_description', ''),
                        "enhanced_description": field.get('current_description', ''),
                        "success": False,
                        "error": str(e)
                    })
        
        success_count = sum(1 for r in results if r.get('success'))
        print(f"[AI Enhance Batch] Complete: {success_count}/{len(results)} successful")
        
        return {"results": results, "total": len(results), "success_count": success_count}
        
    except Exception as e:
        print(f"[AI Enhance Batch] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Mount static files for production (built frontend)
# The dist folder is now at the root level after vite build
static_dir = os.path.join(os.path.dirname(__file__), "..", "dist")
if os.path.exists(static_dir):
    # Mount the entire dist directory as static files
    # This ensures all assets (CSS, JS, fonts, icons, images) are served
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets") if os.path.exists(os.path.join(static_dir, "assets")) else static_dir), name="assets")
    
    # Serve other static files from root (like favicon, etc.)
    @app.get("/favicon.ico")
    async def favicon():
        favicon_path = os.path.join(static_dir, "favicon.ico")
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path)
        return {"error": "Not found"}, 404
    
    # Root route serves index.html
    @app.get("/")
    async def serve_root():
        """Serve the Vue SPA root"""
        return FileResponse(os.path.join(static_dir, "index.html"))
    
    # Catch-all route for Vue Router (SPA) - must be last
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the Vue SPA for all non-API routes"""
        # API routes are handled above, don't serve index.html for them
        if full_path.startswith("api/"):
            return {"error": "Not found"}, 404
        
        # Check if it's a static file in dist root
        file_path = os.path.join(static_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Otherwise serve index.html for client-side routing
        return FileResponse(os.path.join(static_dir, "index.html"))
else:
    @app.get("/")
    async def root():
        """Root endpoint - shown when frontend is not built"""
        return {
            "message": "Welcome to Source2Target API",
            "status": "healthy",
            "version": "1.0.0",
            "note": f"Frontend not built. Looking for dist at: {static_dir}"
        }



