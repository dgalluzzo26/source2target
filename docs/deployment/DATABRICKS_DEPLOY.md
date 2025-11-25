# Databricks App - Build and Deployment Guide

## Exit Status 127 Fix

Exit status 127 means "command not found". This happens when Databricks can't find `npm`.

### Solution Options:

#### Option 1: Pre-build Frontend Locally (Recommended)
Build the frontend before deploying to Databricks:

```bash
cd frontend
npm run build
```

Then commit and push the `frontend/dist` folder. Update `.gitignore` to NOT ignore dist:

```bash
# In .gitignore, comment out or remove:
# dist/
```

#### Option 2: Use Databricks with Node.js
If Databricks workspace has Node.js, create `databricks.yml`:

```yaml
resources:
  apps:
    source2target:
      name: source2target
      source_code_path: .
      
build:
  commands:
    - "cd frontend && npm ci && npm run build"
```

#### Option 3: Backend-Only Mode (Current)
The app now works without a frontend build:
- Backend serves API at `/api/*`
- If `frontend/dist` exists, it serves the built frontend
- If not, it shows API-only mode

## Deployment Steps

### 1. Build Frontend Locally
```bash
./build.sh
```

### 2. Update .gitignore
```bash
# Comment out this line in .gitignore:
# dist/
```

### 3. Commit and Push
```bash
git add frontend/dist
git add .gitignore
git add backend/app.py
git add app.yaml
git add build.sh
git commit -m "Add pre-built frontend for Databricks deployment"
git push
```

### 4. Deploy to Databricks
Your `app.yaml` is now simplified:
```yaml
command: ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
```

## Testing Locally

```bash
# Build frontend
cd frontend && npm run build && cd ..

# Test with backend serving frontend
source venv/bin/activate
uvicorn backend.app:app --reload
```

Visit `http://localhost:8000` - you should see your Vue app!

## Architecture

- **Development**: Frontend dev server (port 3000) + Backend (port 8000)
- **Production**: Single backend serves both API and built frontend
- API endpoints: `/api/*`
- Frontend: `/` and all other routes

## Databricks Port

Note: Changed to port 8080 in `app.yaml` as Databricks typically uses this port.

