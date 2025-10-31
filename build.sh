#!/bin/bash
# Databricks deployment build script

set -e

echo "🏗️  Building Source2Target for Databricks..."

# Check if Node.js is available
if command -v node &> /dev/null; then
    echo "✅ Node.js found: $(node --version)"
    
    # Install frontend dependencies
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm ci --production=false
    
    # Build frontend
    echo "🔨 Building frontend..."
    npm run build
    
    echo "✅ Frontend build complete!"
    cd ..
else
    echo "⚠️  Node.js not found - skipping frontend build"
    echo "    The app will run backend-only mode"
fi

echo "✅ Build complete!"

