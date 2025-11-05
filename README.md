# Source-to-Target Mapping Tool

A full-stack AI-powered field mapping application for Databricks. This tool helps data engineers map source database fields to target semantic fields using vector search and AI recommendations.

## 📚 Documentation

Comprehensive documentation is available for different audiences:

- **[User Guide](docs/USER_GUIDE.md)** - For end users mapping fields
  - Getting started with the application
  - Using AI-powered suggestions
  - Manual search and mapping
  - Templates and bulk operations
  - FAQ and troubleshooting

- **[Administrator Guide](docs/ADMIN_GUIDE.md)** - For system administrators
  - User and permission management
  - Configuration setup
  - Semantic table maintenance
  - System monitoring and health checks
  - Security and compliance

- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - For developers and contributors
  - Architecture overview
  - Backend and frontend development
  - API documentation
  - Development workflow
  - Testing and deployment

## 🚀 Quick Start

### Prerequisites
- Databricks workspace with access to:
  - SQL Warehouse (serverless or classic)
  - Vector Search endpoint and index
  - Model Serving endpoint (optional for AI features)
- Python 3.9+
- Node.js 16+

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd source2target
   ```

2. **Install backend dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Configure the application**
   
   Create `app_config.json` in the root directory:
   ```json
   {
     "database": {
       "server_hostname": "your-workspace.cloud.databricks.com",
       "http_path": "/sql/1.0/warehouses/your-warehouse-id",
       "mapping_table": "catalog.schema.mapping_table",
       "semantic_table": "catalog.schema.semantic_table"
     },
     "vector_search": {
       "index_name": "catalog.schema.vector_index",
       "endpoint_name": "your_vector_endpoint"
     },
     "ai_model": {
       "foundation_model_endpoint": "your_model_endpoint",
       "previous_mappings_table_name": "catalog.schema.prev_mappings"
     },
     "admin_group": {
       "group_name": "your_admin_group"
     }
   }
   ```

### Local Development

1. **Start the backend**
   ```bash
   uvicorn backend.app:app --reload --port 8000
   ```

2. **Start the frontend** (in a new terminal)
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Deploy to Databricks

1. **Build the frontend**
   ```bash
   cd frontend
   npm run build
   cd ..
   ```

2. **Deploy using Databricks CLI**
   ```bash
   databricks apps deploy source2target
   ```

3. **Access via Databricks Apps**
   - Navigate to your Databricks workspace
   - Go to Apps section
   - Find and open your deployed app

## 🎯 Key Features

### For Users
- 🤖 **AI-Powered Suggestions**: Get intelligent field mapping recommendations based on semantic similarity
- 🔍 **Manual Search**: Search and select target fields from the semantic table
- 📊 **Real-Time Status**: Monitor system health and configuration
- 📁 **Bulk Operations**: Upload/download field mappings via CSV templates
- ✨ **Confidence Scores**: See how confident the AI is about each suggestion

### For Administrators
- ⚙️ **Configuration Management**: Easy-to-use UI for system configuration
- 📋 **Semantic Table CRUD**: Manage target field definitions
- 👥 **User Management**: Role-based access control (Admin/User)
- 🔒 **Security**: Databricks OAuth authentication, row-level data filtering
- 📈 **System Monitoring**: Health checks for database, vector search, and AI model

### For Developers
- 🏗️ **Modern Architecture**: FastAPI backend + Vue 3 frontend
- 🔄 **Async Operations**: Non-blocking I/O with ThreadPoolExecutor
- 🎨 **Beautiful UI**: PrimeVue components with Gainwell theme
- 📝 **Type Safety**: TypeScript frontend, Pydantic backend
- 🧪 **Testable**: Service layer architecture for easy testing

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (Vue 3 + PrimeVue)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Field       │  │ Configuration│  │   Semantic   │     │
│  │  Mapping     │  │  Management  │  │    Table     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST API
┌─────────────────────────┴───────────────────────────────────┐
│                   Backend (FastAPI + Python)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Mapping    │  │  AI Mapping  │  │   Semantic   │     │
│  │   Service    │  │   Service    │  │   Service    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────┬───────────────────────────────────┘
                          │ Databricks SDK/SQL
┌─────────────────────────┴───────────────────────────────────┐
│                      Databricks Platform                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  SQL Tables  │  │Vector Search │  │ Model Serving│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Technology Stack

### Frontend
- **Vue 3** - Progressive JavaScript framework with Composition API
- **TypeScript** - Type-safe JavaScript
- **Vite** - Lightning-fast build tool
- **PrimeVue** - Rich UI component library
- **Pinia** - Intuitive state management
- **Vue Router** - Client-side routing

### Backend
- **FastAPI** - Modern async Python web framework
- **Databricks SDK** - Workspace and model interactions
- **Databricks SQL Connector** - Database operations
- **Pydantic** - Data validation and settings
- **asyncio** - Async/await support

### Infrastructure
- **Databricks Apps** - Deployment platform
- **Databricks OAuth** - Authentication
- **Unity Catalog** - Data governance
- **Vector Search** - Semantic similarity
- **Model Serving** - AI/LLM endpoints

## 📂 Project Structure

```
source2target/
├── backend/
│   ├── app.py                    # FastAPI application
│   ├── models/                   # Pydantic models
│   ├── routers/                  # API endpoints
│   └── services/                 # Business logic
├── frontend/
│   ├── src/
│   │   ├── assets/               # Styles and images
│   │   ├── components/           # Vue components
│   │   ├── router/               # Route definitions
│   │   ├── services/             # API client
│   │   ├── stores/               # State management
│   │   └── views/                # Page components
│   └── public/                   # Static assets
├── docs/                         # Documentation
│   ├── USER_GUIDE.md
│   ├── ADMIN_GUIDE.md
│   └── DEVELOPER_GUIDE.md
├── dist/                         # Built frontend (generated)
├── app_config.json               # Local configuration
├── app.yaml                      # Databricks app config
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🔑 Key Concepts

### Unmapped Fields
Source database fields that haven't been mapped to target semantic fields yet. Users select these to start the mapping process.

### Mapped Fields
Source fields that have been successfully mapped to target fields. These mappings are stored in the database and can be viewed or deleted.

### Semantic Table
The authoritative list of all possible target fields. Contains logical and physical names, data types, descriptions, and other metadata.

### AI Suggestions
Machine learning-powered recommendations for field mappings based on:
- Vector search similarity scores
- Field names and descriptions
- Data types and constraints
- Historical mapping patterns (future)

### Manual Search
Allows users to search the semantic table by keyword and manually select the appropriate target field when AI suggestions aren't suitable.

### Confidence Score
A measure (0-1) of how confident the AI is about a suggested mapping. Higher scores indicate better semantic similarity.

## 🔒 Security

- **Authentication**: Databricks OAuth (automatic)
- **Authorization**: Role-based access (Admin/User)
- **Data Isolation**: Users see only their own mappings
- **Network**: HTTPS only (enforced by Databricks Apps)
- **Credentials**: No passwords stored, OAuth tokens only

## 🤝 Contributing

We welcome contributions! Please see the [Developer Guide](docs/DEVELOPER_GUIDE.md) for:
- Development setup
- Code standards
- Pull request process
- Testing guidelines

## 📝 License

ISC

## 🆘 Support

- **Users**: See [User Guide](docs/USER_GUIDE.md) FAQ section
- **Admins**: See [Administrator Guide](docs/ADMIN_GUIDE.md) troubleshooting
- **Developers**: See [Developer Guide](docs/DEVELOPER_GUIDE.md) debugging section

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vue 3 Documentation](https://vuejs.org/)
- [Databricks SDK for Python](https://docs.databricks.com/dev-tools/sdk-python.html)
- [Databricks Apps Guide](https://docs.databricks.com/en/dev-tools/databricks-apps/)
- [Vector Search Documentation](https://docs.databricks.com/en/generative-ai/vector-search.html)

---

**Version**: 1.0  
**Last Updated**: November 2025  
**Maintained by**: Gainwell Technologies
