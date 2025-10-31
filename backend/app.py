from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from typing import Optional, Dict, Any
from backend.services.config_service import config_service
from backend.services.system_service import system_service

# Import Databricks SDK for authentication
try:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.core import Config
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    print("Warning: Databricks SDK not available")

app = FastAPI(
    title="Source2Target API",
    description="FastAPI backend for Source2Target Databricks app",
    version="1.0.0"
)

# Configure CORS for Vue frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Databricks
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/api/auth/current-user")
async def get_current_user(request: Request):
    """
    Get current authenticated user from Databricks context.
    Follows the same logic as the Streamlit app's auth.py
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
                return user_info
        
        # Method 3: Check environment variables
        databricks_user = os.environ.get('DATABRICKS_USER')
        if databricks_user and '@' in databricks_user:
            user_info["email"] = databricks_user
            user_info["display_name"] = databricks_user.split('@')[0].replace('.', ' ').title()
            user_info["detection_method"] = "DATABRICKS_USER env"
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
    """Sample data endpoint"""
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
    Get system status with live database check.
    Uses system service for comprehensive health checks.
    """
    return await system_service.get_system_status()

@app.get("/api/config")
async def get_config():
    """
    Get the current application configuration.
    Returns the complete configuration from local file.
    """
    config = config_service.get_config()
    return config.model_dump()

@app.put("/api/config")
async def update_config(config_data: dict):
    """
    Update the application configuration.
    Saves the configuration to local file.
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
            return {
                "status": "error",
                "message": "Failed to save configuration"
            }, 500
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Invalid configuration: {str(e)}"
        }, 400

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



