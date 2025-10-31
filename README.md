# Source2Target - Databricks App

A full-stack application built with Vue 3 + PrimeVue frontend and FastAPI backend, designed to run on Databricks.

## Project Structure

```
source2target/
├── package.json          # Root package.json for workspace scripts
├── requirements.txt      # Python dependencies (FastAPI, Uvicorn)
├── app.yaml             # Databricks app configuration
├── backend/
│   ├── __init__.py
│   └── app.py           # FastAPI application
└── frontend/
    ├── package.json     # Vue project dependencies
    ├── src/
    │   ├── main.ts      # Vue app entry point with PrimeVue setup
    │   ├── App.vue      # Root component
    │   └── ...
    └── ...
```

## Technologies Used

### Frontend
- **Vue 3** - Progressive JavaScript framework
- **Vite** - Next generation frontend tooling
- **TypeScript** - Type safety
- **Vue Router** - Official router for Vue.js
- **Pinia** - State management
- **PrimeVue** - Rich UI component library
- **PrimeIcons** - Icon library

### Backend
- **FastAPI** - Modern, fast Python web framework
- **Uvicorn** - ASGI web server
- **Pydantic** - Data validation

## Getting Started

### Prerequisites
- Node.js 18+ and npm
- Python 3.9+
- pip

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the FastAPI server
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

### Running with Databricks

The `app.yaml` file configures how Databricks starts both frontend and backend processes:

```yaml
backend:
  command: "cd backend && uvicorn app:app --host 0.0.0.0 --port 8000 --reload"
  
frontend:
  command: "cd frontend && npm run dev -- --host 0.0.0.0 --port 3000"
```

## Development

### Frontend Development

The Vue app is configured with:
- Hot Module Replacement (HMR) for instant updates
- TypeScript for type safety
- ESLint for code quality
- Vitest for unit testing
- PrimeVue Aura theme for modern UI

### Backend Development

The FastAPI backend includes:
- CORS middleware configured for Vue frontend
- Automatic API documentation
- Sample endpoints for health checks and data
- Async/await support

## Available Scripts

### Root Level
- `npm run dev` - Start frontend development server
- `npm run build` - Build frontend for production
- `npm run preview` - Preview production build

### Frontend Directory
- `npm run dev` - Start Vite dev server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run test:unit` - Run unit tests
- `npm run lint` - Lint code

## API Endpoints

- `GET /` - Root endpoint with API info
- `GET /api/health` - Health check endpoint
- `GET /api/data` - Sample data endpoint

## Next Steps

1. Customize the Vue frontend in `frontend/src/`
2. Add more API endpoints in `backend/app.py`
3. Configure environment variables
4. Add database connections (if needed)
5. Deploy to Databricks

## License

ISC

