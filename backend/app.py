from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

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

# Mount static files for production (built frontend)
# The dist folder is now at the root level after vite build
static_dir = os.path.join(os.path.dirname(__file__), "..", "dist")
if os.path.exists(static_dir):
    # Serve static assets
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # Root route serves index.html
    @app.get("/")
    async def serve_root():
        """Serve the Vue SPA root"""
        return FileResponse(os.path.join(static_dir, "index.html"))
    
    # Catch-all route for Vue Router (SPA)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the Vue SPA for all non-API routes"""
        # API routes are handled above, don't serve index.html for them
        if full_path.startswith("api"):
            return {"error": "Not found"}, 404
        
        # Check if it's a static file
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



