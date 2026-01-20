# Smart Mapper V4 Documentation

This directory contains all project documentation for the **Target-First** mapping workflow.

## What's New in V4

V4 introduces a **Target-First** approach to field mapping:

| Aspect | V3 (Source-First) | V4 (Target-First) |
|--------|-------------------|-------------------|
| Workflow | Select source → find target | Select target table → AI maps all |
| Organization | Per-user mappings | Project-based with teams |
| AI Scope | One field at a time | Entire table at once |
| Progress | Individual field tracking | Table and project dashboards |

---

## Directory Structure

### `/docs/` (root) - User-Facing Guides

| File | Description |
|------|-------------|
| **USER_GUIDE.md** | Complete user guide for V4 target-first workflow |
| **ADMIN_GUIDE.md** | Administrator guide: schema, procedures, patterns |
| **QUICK_START.md** | Quick start for new users |
| **DEVELOPER_GUIDE.md** | Developer setup and contribution guide |
| **V4_MIGRATION_PLAN.md** | Migration plan from V3 to V4 |

### `/docs/architecture/` - System Architecture

| File | Description |
|------|-------------|
| **TARGET_FIRST_WORKFLOW.md** | V4 workflow diagrams and ERD |
| **AI_MAPPING_FLOW_V4.md** | AI suggestion generation flow |
| **AI_MAPPING_FLOW_V3.md** | (Legacy) V3 AI flow for reference |
| **MAPPING_APPROACH_COMPARISON.md** | Comparison of mapping approaches |

### `/docs/deployment/` - Deployment & Operations

| File | Description |
|------|-------------|
| **DATABRICKS_DEPLOY.md** | Databricks-specific deployment guide |

### `/docs/presentations/` - Presentations

| File | Description |
|------|-------------|
| **AI_MAPPING_ARCHITECTURE_V3.md** | Architecture presentation |

---

## Database Files

V4 database files are in `/database/`:

| File | Description |
|------|-------------|
| **V4_TARGET_FIRST_SCHEMA.sql** | V4 table definitions (projects, status, suggestions) |
| **V4_STORED_PROCEDURES.sql** | Databricks SQL stored procedures |
| **V4_TEST_DATA.sql** | Test data for development |
| **V4_LOAD_HISTORICAL_MAPPINGS.sql** | Load historical patterns |
| **V4_MAPPED_FIELDS_RECREATE.sql** | Updated mapped_fields schema |
| **V3_SCHEMA_CREATE.sql** | Base schema (semantic_fields, etc.) |

---

## Quick Links

### Getting Started
1. [Quick Start Guide](QUICK_START.md) - Get mapping in 10 minutes
2. [User Guide](USER_GUIDE.md) - Complete feature documentation
3. [Admin Guide](ADMIN_GUIDE.md) - System configuration

### For Developers
1. [Developer Guide](DEVELOPER_GUIDE.md) - Setup and development
2. [Target-First Workflow](architecture/TARGET_FIRST_WORKFLOW.md) - Architecture
3. [AI Mapping Flow](architecture/AI_MAPPING_FLOW_V4.md) - How AI works

### For Administrators
1. [Admin Guide](ADMIN_GUIDE.md) - Full admin documentation
2. [Stored Procedures](../database/V4_STORED_PROCEDURES.sql) - SQL procedures
3. [Loading Patterns](../database/V4_LOAD_HISTORICAL_MAPPINGS.sql) - Import patterns

---

## V4 Key Concepts

### Projects
Mappings are organized into **projects**. Each project:
- Has a name and description
- Contains uploaded source fields
- Tracks progress across target tables
- Can be shared with team members

### Target Tables
Within a project, you map **target tables** one at a time:
- Initialize from semantic_fields
- Start AI discovery for all columns
- Review and approve suggestions
- Mark complete when done

### Suggestions
AI generates **suggestions** for each column:
- Based on historical patterns
- Matched to your source fields
- Include confidence scores
- Must be approved/rejected by users

### Patterns
Approved mappings become **patterns** for future AI:
- Historical mappings loaded as patterns
- New approved mappings can be promoted
- Patterns include complete SQL with JOINs

---

## API Version

V4 APIs use the `/api/v4/` prefix:

```
GET    /api/v4/projects                         List projects
POST   /api/v4/projects                         Create project
GET    /api/v4/projects/{id}                    Get project details
POST   /api/v4/projects/{id}/source-fields      Upload source fields
POST   /api/v4/projects/{id}/initialize-tables  Initialize target tables
GET    /api/v4/projects/{id}/target-tables      Get target table status
POST   /api/v4/target-tables/{id}/discover      Start AI discovery
GET    /api/v4/target-tables/{id}/suggestions   Get suggestions
POST   /api/v4/suggestions/{id}/approve         Approve suggestion
POST   /api/v4/suggestions/{id}/edit            Edit and approve
POST   /api/v4/suggestions/{id}/reject          Reject suggestion
```

---

**Version**: 4.0 - Target-First Workflow
**Last Updated**: December 2025
