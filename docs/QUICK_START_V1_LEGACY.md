# Quick Start Guide

## 🚀 Run the Frontend

```bash
cd frontend
npm run dev
```

Visit: `http://localhost:3000`

## 🐍 Run the Backend

```bash
# Install dependencies first (if not done)
pip install -r requirements.txt

# Start the server
cd backend
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Visit API docs: `http://localhost:8000/docs`

## 🎯 Run Both (Using Shell Script)

```bash
./dev.sh
```

This will start both frontend and backend servers automatically.

## 📦 What's Included

### Frontend Features
- ✅ Vue 3 with TypeScript
- ✅ PrimeVue UI components (Button, Card, DataTable, etc.)
- ✅ Vue Router for navigation
- ✅ Pinia for state management
- ✅ API service layer with TypeScript types
- ✅ Proxy configuration for backend API calls
- ✅ Example dashboard with real API integration

### Backend Features
- ✅ FastAPI application
- ✅ CORS middleware configured
- ✅ Health check endpoint
- ✅ Sample data endpoint
- ✅ Auto-generated API documentation

### PrimeVue Components Used
- `Button` - Interactive buttons with icons
- `Card` - Card containers
- `DataTable` - Data grid with sorting
- `Column` - Table columns
- `Message` - Error/info messages
- `ProgressSpinner` - Loading indicator

## 📁 Project Structure

```
source2target/
├── app.yaml              # Databricks configuration
├── package.json          # Root package.json
├── requirements.txt      # Python dependencies
├── dev.sh               # Development startup script
├── README.md            # Full documentation
├── QUICKSTART.md        # This file
├── backend/
│   ├── __init__.py
│   ├── app.py           # FastAPI app
│   └── env.example      # Environment template
└── frontend/
    ├── package.json     # Frontend dependencies
    ├── vite.config.ts   # Vite configuration
    ├── src/
    │   ├── main.ts      # App entry with PrimeVue
    │   ├── App.vue      # Root component
    │   ├── services/
    │   │   └── api.ts   # API service layer
    │   └── views/
    │       └── HomeView.vue  # Dashboard example
    └── ...
```

## 🎨 PrimeVue Theme

The app uses the **Aura** theme preset. You can customize it in `frontend/src/main.ts`:

```typescript
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.dark-mode'
    }
  }
})
```

## 🔧 Common Tasks

### Add a new PrimeVue component

```typescript
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
// Use in your component
```

### Add a new API endpoint

1. Add endpoint in `backend/app.py`:
```python
@app.get("/api/my-endpoint")
async def my_endpoint():
    return {"data": "value"}
```

2. Add service function in `frontend/src/services/api.ts`:
```typescript
export async function getMyData() {
  return apiFetch<MyDataType>('/api/my-endpoint')
}
```

3. Use in Vue component:
```typescript
import { getMyData } from '@/services/api'
const data = await getMyData()
```

## 🌐 Deployment to Databricks

The `app.yaml` file is configured for Databricks deployment:

```yaml
backend:
  command: "cd backend && uvicorn app:app --host 0.0.0.0 --port 8000 --reload"
  
frontend:
  command: "cd frontend && npm run dev -- --host 0.0.0.0 --port 3000"
```

## 📚 Resources

- [Vue 3 Documentation](https://vuejs.org/)
- [PrimeVue Documentation](https://primevue.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vite Documentation](https://vitejs.dev/)

## ❓ Troubleshooting

### Frontend can't connect to backend
- Make sure backend is running on port 8000
- Check the proxy configuration in `vite.config.ts`
- Verify CORS settings in `backend/app.py`

### PrimeVue components not showing
- Check that PrimeVue is properly configured in `main.ts`
- Ensure PrimeIcons CSS is imported
- Verify component imports are correct

### Port already in use
- Change port in `vite.config.ts` (frontend)
- Change port in uvicorn command (backend)

