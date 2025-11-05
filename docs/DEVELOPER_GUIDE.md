# Source-to-Target Mapping Tool - Developer Guide

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Backend Development](#backend-development)
5. [Frontend Development](#frontend-development)
6. [Database Schema](#database-schema)
7. [API Documentation](#api-documentation)
8. [Development Workflow](#development-workflow)
9. [Testing](#testing)
10. [Deployment](#deployment)
11. [Performance Optimization](#performance-optimization)
12. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │   Views    │  │ Components │  │   Stores   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│         │                │                │                  │
│         └────────────────┴────────────────┘                  │
│                         │                                    │
│                    API Service                               │
└─────────────────────────┼───────────────────────────────────┘
                          │ HTTP/REST
┌─────────────────────────┼───────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Routers   │  │  Services  │  │   Models   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│         │                │                │                  │
│         └────────────────┴────────────────┘                  │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          │ Databricks SDK / SQL Connector
                          │
┌─────────────────────────┼───────────────────────────────────┐
│                    Databricks                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  SQL Tables  │  │Vector Search │  │ Model Serving│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Patterns

#### 1. Service Layer Pattern
- Business logic separated into service classes
- Routers handle HTTP, services handle data operations
- Promotes reusability and testability

#### 2. Repository Pattern
- Services interact with data sources (Databricks)
- Abstract database operations
- Easier to mock for testing

#### 3. Async/Await Pattern
- FastAPI uses async for non-blocking operations
- Blocking operations run in ThreadPoolExecutor
- Improves responsiveness and scalability

#### 4. Component-Based UI
- Vue 3 Composition API
- Reusable PrimeVue components
- Reactive state management with Pinia

---

## Technology Stack

### Frontend
- **Framework**: Vue 3 (Composition API)
- **UI Library**: PrimeVue 3.x
- **State Management**: Pinia
- **Routing**: Vue Router 4
- **Build Tool**: Vite
- **Language**: TypeScript
- **HTTP Client**: Fetch API

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.9+
- **Database**: Databricks SQL Connector
- **SDK**: Databricks SDK for Python
- **Async**: asyncio, ThreadPoolExecutor
- **Validation**: Pydantic
- **CORS**: FastAPI middleware

### Deployment
- **Platform**: Databricks Apps
- **Authentication**: Databricks OAuth
- **Static Files**: Served by FastAPI

---

## Project Structure

```
source2target/
├── backend/
│   ├── app.py                    # Main FastAPI application
│   ├── models/
│   │   ├── config.py             # Configuration models
│   │   ├── mapping.py            # Mapping data models
│   │   └── semantic.py           # Semantic table models
│   ├── routers/
│   │   ├── ai_mapping.py         # AI mapping endpoints
│   │   ├── mapping.py            # Field mapping endpoints
│   │   └── semantic.py           # Semantic table endpoints
│   └── services/
│       ├── ai_mapping_service.py # AI suggestions logic
│       ├── auth_service.py       # Authentication logic
│       ├── config_service.py     # Configuration management
│       ├── mapping_service.py    # Mapping operations
│       ├── semantic_service.py   # Semantic table operations
│       └── system_service.py     # System health checks
├── frontend/
│   ├── src/
│   │   ├── assets/               # CSS, images, fonts
│   │   ├── components/           # Vue components
│   │   │   └── AppLayout.vue     # Main layout
│   │   ├── router/
│   │   │   └── index.ts          # Route definitions
│   │   ├── services/
│   │   │   └── api.ts            # API client
│   │   ├── stores/
│   │   │   └── user.ts           # User state
│   │   ├── views/                # Page components
│   │   │   ├── ConfigurationView.vue
│   │   │   ├── IntroductionView.vue
│   │   │   ├── MappingView.vue
│   │   │   └── SemanticView.vue
│   │   ├── App.vue               # Root component
│   │   └── main.ts               # App entry point
│   ├── public/                   # Static assets
│   ├── index.html                # HTML template
│   ├── vite.config.ts            # Vite configuration
│   └── package.json              # Frontend dependencies
├── dist/                         # Built frontend (generated)
├── docs/                         # Documentation
├── app_config.json               # Local configuration
├── requirements.txt              # Python dependencies
├── app.yaml                      # Databricks app config
└── README.md                     # Project overview
```

---

## Backend Development

### Service Architecture

#### Service Base Pattern
All services follow this pattern:

```python
class ServiceName:
    def __init__(self):
        self.config_service = ConfigService()
        self._workspace_client = None
    
    @property
    def workspace_client(self):
        """Lazy initialization of WorkspaceClient."""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient()
        return self._workspace_client
    
    def _get_sql_connection(self, server_hostname: str, http_path: str):
        """Get SQL connection with OAuth token."""
        # OAuth token handling
        pass
    
    def _sync_operation(self, ...):
        """Synchronous database operation."""
        # Blocking I/O here
        pass
    
    async def async_operation(self, ...):
        """Async wrapper for sync operation."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            functools.partial(self._sync_operation, ...)
        )
```

#### Why This Pattern?
1. **Lazy WorkspaceClient**: Avoid instantiation during import
2. **OAuth Token Handling**: Explicit token passing for serverless warehouses
3. **ThreadPoolExecutor**: Run blocking DB operations without blocking event loop
4. **Timeout Handling**: Use `asyncio.wait_for()` to prevent hangs

### Adding a New Endpoint

#### Step 1: Define Model (if needed)
```python
# backend/models/your_model.py
from pydantic import BaseModel
from typing import Optional

class YourModel(BaseModel):
    """Description of your model."""
    model_config = {"from_attributes": True}
    
    field1: str
    field2: Optional[int] = None
```

#### Step 2: Create Service Method
```python
# backend/services/your_service.py
class YourService:
    def _sync_method(self, ...):
        """Synchronous database operation."""
        connection = self._get_sql_connection(...)
        try:
            with connection.cursor() as cursor:
                query = "SELECT ..."
                cursor.execute(query)
                results = cursor.fetchall_arrow().to_pandas()
                return results.to_dict('records')
        finally:
            connection.close()
    
    async def async_method(self, ...):
        """Public async interface."""
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                functools.partial(self._sync_method, ...)
            ),
            timeout=30.0
        )
```

#### Step 3: Add Router Endpoint
```python
# backend/routers/your_router.py
from fastapi import APIRouter, Request
from backend.services.your_service import YourService

router = APIRouter(prefix="/api/your-feature", tags=["your-feature"])
your_service = YourService()

@router.get("/endpoint")
async def your_endpoint(request: Request):
    """Endpoint description."""
    try:
        # Get user email
        current_user_email = request.headers.get('x-forwarded-email', 'demo.user@gainwell.com')
        
        # Call service
        result = await your_service.async_method(current_user_email)
        
        return result
    except Exception as e:
        print(f"[Your Router] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### Step 4: Register Router
```python
# backend/app.py
from backend.routers import your_router

app.include_router(your_router.router)
```

### Database Best Practices

#### 1. Always Use ThreadPoolExecutor for Blocking I/O
```python
# ❌ BAD - Blocks event loop
async def bad_method(self):
    connection = sql.connect(...)  # Blocking!
    cursor.execute(query)          # Blocking!

# ✅ GOOD - Runs in thread pool
async def good_method(self):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        functools.partial(self._sync_method, ...)
    )
```

#### 2. Always Close Connections
```python
connection = self._get_sql_connection(...)
try:
    # Operations here
    pass
finally:
    connection.close()  # Always close!
```

#### 3. Use Timeouts
```python
result = await asyncio.wait_for(
    operation,
    timeout=30.0  # Prevent infinite hangs
)
```

#### 4. Escape SQL Inputs
```python
# Escape single quotes
escaped = user_input.replace("'", "''")
query = f"SELECT * FROM table WHERE field = '{escaped}'"
```

#### 5. Handle OAuth Tokens for Serverless
```python
def _get_sql_connection(self, server_hostname: str, http_path: str):
    # Try to get OAuth token
    access_token = None
    if self.workspace_client:
        headers = self.workspace_client.config.authenticate()
        if headers and 'Authorization' in headers:
            access_token = headers['Authorization'].replace('Bearer ', '')
    
    if access_token:
        return sql.connect(
            server_hostname=server_hostname,
            http_path=http_path,
            access_token=access_token  # Explicit token
        )
    else:
        return sql.connect(
            server_hostname=server_hostname,
            http_path=http_path,
            auth_type="databricks-oauth"
        )
```

### Error Handling

#### Standard Pattern
```python
try:
    print(f"[Service] Starting operation")
    result = await operation()
    print(f"[Service] Operation successful")
    return result
except asyncio.TimeoutError:
    print("[Service] Operation timed out")
    raise Exception("Operation timed out after 30 seconds")
except Exception as e:
    print(f"[Service] ERROR: {str(e)}")
    import traceback
    print(f"[Service] Traceback: {traceback.format_exc()}")
    raise
```

#### Router Error Handling
```python
@router.get("/endpoint")
async def endpoint(request: Request):
    try:
        # Operation
        pass
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        print(f"[Router] ERROR: {str(e)}")
        import traceback
        print(f"[Router] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Frontend Development

### Component Structure

#### Composition API Pattern
```typescript
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { YourAPI } from '@/services/api'

// Reactive state
const data = ref<YourType[]>([])
const loading = ref(false)
const searchTerm = ref('')

// Computed properties
const filteredData = computed(() => {
  if (!searchTerm.value) return data.value
  return data.value.filter(item => 
    item.name.toLowerCase().includes(searchTerm.value.toLowerCase())
  )
})

// Methods
const loadData = async () => {
  loading.value = true
  try {
    const result = await YourAPI.getData()
    if (result.data) {
      data.value = result.data
    } else if (result.error) {
      console.error('Error:', result.error)
    }
  } catch (error) {
    console.error('Error:', error)
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadData()
})
</script>
```

### Adding a New API Method

#### Step 1: Define TypeScript Interface
```typescript
// frontend/src/services/api.ts
export interface YourType {
  field1: string
  field2: number
  field3?: string  // Optional
}
```

#### Step 2: Create API Class Method
```typescript
export class YourAPI {
  /**
   * Description of what this does
   */
  static async yourMethod(param: string): Promise<ApiResponse<YourType[]>> {
    return apiFetch<YourType[]>(`/api/your-endpoint?param=${encodeURIComponent(param)}`)
  }
  
  /**
   * POST example
   */
  static async yourPostMethod(data: YourType): Promise<ApiResponse<any>> {
    return apiFetch<any>('/api/your-endpoint', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }
}
```

#### Step 3: Use in Component
```typescript
import { YourAPI, type YourType } from '@/services/api'

const yourData = ref<YourType[]>([])

const fetchData = async () => {
  const result = await YourAPI.yourMethod('param-value')
  if (result.data) {
    yourData.value = result.data
  } else if (result.error) {
    console.error('Error:', result.error)
  }
}
```

### State Management with Pinia

#### Creating a Store
```typescript
// frontend/src/stores/yourStore.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useYourStore = defineStore('your-store', () => {
  // State
  const items = ref<YourType[]>([])
  const loading = ref(false)
  
  // Getters
  const itemCount = computed(() => items.value.length)
  
  // Actions
  const fetchItems = async () => {
    loading.value = true
    try {
      const result = await YourAPI.getItems()
      if (result.data) {
        items.value = result.data
      }
    } finally {
      loading.value = false
    }
  }
  
  return {
    // State
    items,
    loading,
    // Getters
    itemCount,
    // Actions
    fetchItems
  }
})
```

#### Using a Store
```typescript
import { useYourStore } from '@/stores/yourStore'

const yourStore = useYourStore()

// Access state
console.log(yourStore.items)
console.log(yourStore.itemCount)

// Call actions
yourStore.fetchItems()
```

### Styling Guidelines

#### Using Theme Variables
```css
/* Use Gainwell theme variables */
.your-component {
  color: var(--gainwell-primary);
  background: var(--gainwell-background);
  border: 1px solid var(--gainwell-border);
}
```

#### PrimeVue Component Customization
```css
/* Override PrimeVue styles */
.p-datatable .p-datatable-thead > tr > th {
  background: var(--gainwell-primary);
  color: white;
}
```

---

## Database Schema

### Mapping Table

```sql
CREATE TABLE catalog.schema.mapping_table (
  src_table_name STRING,
  src_column_name STRING,
  src_columns STRUCT<
    src_table_name: STRING,
    src_column_name: STRING,
    src_column_physical_name: STRING,
    src_nullable: STRING,
    src_physical_datatype: STRING,
    src_comments: STRING
  >,
  tgt_columns STRUCT<
    tgt_table_name: STRING,
    tgt_table_physical_name: STRING,
    tgt_column_name: STRING,
    tgt_column_physical_name: STRING
  >,
  query_text STRING,
  source_owners STRING
)
```

### Semantic Table

```sql
CREATE TABLE catalog.schema.semantic_table (
  tgt_table_name STRING,
  tgt_column_name STRING,
  tgt_table_physical_name STRING,
  tgt_column_physical_name STRING,
  tgt_physical_datatype STRING,
  tgt_nullable STRING,
  tgt_comments STRING,
  tgt_definition STRING,
  tgt_is_pk BOOLEAN,
  tgt_is_fk BOOLEAN,
  semantic_field STRING
)
```

### Key Concepts

#### 1. Struct Fields
- `src_columns` and `tgt_columns` are structs
- Access nested fields: `src_columns.src_column_physical_name`
- NULL struct means no mapping (unmapped field)

#### 2. Source Owners
- Tracks which user created/owns each mapping
- Used for row-level filtering
- Format: email address

#### 3. Query Text
- Pre-formatted text for AI model input
- Generated automatically during insert
- Format: "TABLE NAME: X; COLUMN NAME: Y; ..."

---

## API Documentation

### Authentication
All endpoints use Databricks OAuth:
- User authenticated via Databricks
- Email captured from `X-Forwarded-Email` header
- Fallback to demo user in development

### Response Format

#### Success Response
```json
{
  "data": [...],
  "error": null
}
```

#### Error Response
```json
{
  "detail": "Error message"
}
```

### Endpoint Categories

#### 1. Authentication (`/api/auth/*`)
- `GET /api/auth/current-user`: Get current user info

#### 2. System (`/api/system/*`)
- `GET /api/system/status`: Get system health status

#### 3. Configuration (`/api/config/*`)
- `GET /api/config`: Get current configuration
- `POST /api/config`: Update configuration

#### 4. Semantic (`/api/semantic/*`)
- `GET /api/semantic/records`: Get all semantic records
- `POST /api/semantic/records`: Create semantic record
- `PUT /api/semantic/records/{id}`: Update semantic record
- `DELETE /api/semantic/records/{id}`: Delete semantic record

#### 5. Mapping (`/api/mapping/*`)
- `GET /api/mapping/mapped-fields`: Get mapped fields
- `GET /api/mapping/unmapped-fields`: Get unmapped fields
- `GET /api/mapping/download-template`: Download CSV template
- `POST /api/mapping/upload-template`: Upload CSV template
- `DELETE /api/mapping/unmap-field`: Remove mapping
- `GET /api/mapping/search-semantic-table`: Search semantic table
- `POST /api/mapping/save-manual-mapping`: Save manual mapping

#### 6. AI Mapping (`/api/ai-mapping/*`)
- `POST /api/ai-mapping/generate-suggestions`: Generate AI suggestions

---

## Development Workflow

### Local Development Setup

#### 1. Prerequisites
```bash
# Python 3.9+
python --version

# Node.js 16+
node --version

# Git
git --version
```

#### 2. Clone and Setup
```bash
# Clone repository
git clone <repository-url>
cd source2target

# Backend setup
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install
cd ..
```

#### 3. Configuration
Create `app_config.json`:
```json
{
  "database": {
    "server_hostname": "your-workspace.cloud.databricks.com",
    "http_path": "/sql/1.0/warehouses/...",
    "mapping_table": "catalog.schema.mapping",
    "semantic_table": "catalog.schema.semantic"
  },
  "vector_search": {
    "index_name": "catalog.schema.vs_index",
    "endpoint_name": "endpoint_name"
  },
  "ai_model": {
    "foundation_model_endpoint": "model_endpoint",
    "previous_mappings_table_name": "catalog.schema.prev_mappings"
  },
  "admin_group": {
    "group_name": "admin_group"
  }
}
```

#### 4. Run Development Servers

Backend:
```bash
uvicorn backend.app:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm run dev
```

### Git Workflow

#### Branch Strategy
```
main
  ├── feature/your-feature-name
  ├── bugfix/your-bugfix-name
  └── hotfix/critical-fix
```

#### Commit Messages
```
feat: Add manual search functionality
fix: Correct vector search timeout
docs: Update user guide
refactor: Improve service architecture
test: Add unit tests for mapping service
```

### Code Review Checklist

#### Backend
- [ ] Service methods use ThreadPoolExecutor
- [ ] Connections are properly closed
- [ ] Timeouts are set appropriately
- [ ] SQL inputs are escaped
- [ ] OAuth tokens handled for serverless
- [ ] Error handling is comprehensive
- [ ] Logging is clear and helpful
- [ ] Type hints are used

#### Frontend
- [ ] TypeScript types are defined
- [ ] API errors are handled
- [ ] Loading states are shown
- [ ] Components are responsive
- [ ] Accessibility is considered
- [ ] No console errors
- [ ] Code follows Vue 3 Composition API patterns

---

## Testing

### Backend Unit Tests

#### Example Test Structure
```python
import pytest
from backend.services.your_service import YourService

@pytest.fixture
def service():
    return YourService()

def test_your_method(service):
    result = await service.your_method()
    assert result is not None
    assert len(result) > 0
```

### Frontend Unit Tests

#### Example Test Structure
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import YourComponent from '@/components/YourComponent.vue'

describe('YourComponent', () => {
  it('renders properly', () => {
    const wrapper = mount(YourComponent, {
      props: { title: 'Test' }
    })
    expect(wrapper.text()).toContain('Test')
  })
})
```

### Integration Testing

#### Manual Testing Checklist
- [ ] User authentication works
- [ ] System status displays correctly
- [ ] Configuration saves and loads
- [ ] Semantic table CRUD operations
- [ ] Unmapped fields load
- [ ] Mapped fields load
- [ ] AI suggestions generate
- [ ] Manual search works
- [ ] Mappings save correctly
- [ ] Templates download/upload
- [ ] Error messages display
- [ ] Loading states show

---

## Deployment

### Databricks Apps Deployment

#### 1. Build Frontend
```bash
cd frontend
npm run build
cd ..
```

#### 2. Prepare app.yaml
```yaml
command: ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 3. Deploy via Databricks CLI
```bash
databricks apps deploy source2target
```

#### 4. Verify Deployment
- Check app status in Databricks workspace
- Review logs for startup errors
- Test system status endpoint
- Verify authentication

### Configuration in Production
- Store `app_config.json` securely
- Use environment variables for sensitive data
- Enable logging
- Monitor performance

---

## Performance Optimization

### Backend Optimization

#### 1. Connection Pooling
- Databricks SQL connector handles pooling
- Reuse WorkspaceClient instances

#### 2. Query Optimization
- Add indexes on frequently queried columns
- Use LIMIT clauses for large result sets
- Filter early in WHERE clause

#### 3. Async Operations
- Use ThreadPoolExecutor for blocking I/O
- Set appropriate timeouts
- Avoid blocking the event loop

### Frontend Optimization

#### 1. Lazy Loading
- Load data on-demand
- Paginate large result sets
- Use virtual scrolling for long lists

#### 2. Caching
- Cache API responses when appropriate
- Use computed properties for derived data
- Memoize expensive calculations

#### 3. Bundle Optimization
- Vite handles code splitting
- Use dynamic imports for large components
- Optimize images and assets

---

## Troubleshooting

### Common Development Issues

#### Backend won't start
- Check Python version (3.9+)
- Verify all dependencies installed
- Review `app_config.json` format
- Check port 8000 is available

#### Frontend won't build
- Check Node version (16+)
- Delete `node_modules` and reinstall
- Clear Vite cache
- Check for TypeScript errors

#### Database connection fails locally
- Verify Databricks credentials
- Check VPN/network access
- Test warehouse is running
- Validate HTTP path

#### Authentication not working
- Check Databricks OAuth setup
- Verify `X-Forwarded-Email` header
- Test with demo user fallback

### Debugging Tips

#### Backend Debugging
```python
# Add print statements
print(f"[Debug] Variable: {variable}")

# Use Python debugger
import pdb; pdb.set_trace()

# Check logs in Databricks
```

#### Frontend Debugging
```typescript
// Console logging
console.log('Debug:', data)

// Vue DevTools
// Install browser extension

// Network tab
// Check API calls in browser DevTools
```

---

## Contributing

### Code Standards
- Follow existing patterns
- Write clear comments
- Add type hints (Python) and types (TypeScript)
- Test your changes
- Update documentation

### Pull Request Process
1. Create feature branch
2. Make changes
3. Test thoroughly
4. Update documentation
5. Submit PR with description
6. Address review feedback
7. Merge when approved

---

## Resources

### Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Vue 3 Docs](https://vuejs.org/)
- [PrimeVue Docs](https://primevue.org/)
- [Databricks SDK](https://docs.databricks.com/dev-tools/sdk-python.html)
- [Pydantic Docs](https://docs.pydantic.dev/)

### Tools
- VS Code with Python and Vue extensions
- Databricks CLI
- Postman for API testing
- Vue DevTools browser extension

---

**Version**: 1.0  
**Last Updated**: November 2025

