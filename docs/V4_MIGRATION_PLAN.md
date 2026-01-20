# V4 Migration Plan: Target-First Workflow

## Overview

This document outlines the plan to migrate from V3 (source-first) to V4 (target-first) workflow while cleaning up the codebase to only contain V4 code.

## Branch: `v4-target-first`

---

## Current State Analysis

### Backend Files

| File | Action | Reason |
|------|--------|--------|
| **Routers** | | |
| `ai_mapping.py` | 🗑️ DELETE | V2, replaced by V4 |
| `ai_mapping_v3.py` | 🔄 RENAME → `ai_suggestions.py` | Keep logic, rename for V4 |
| `mapping.py` | 🗑️ DELETE | V2, replaced by V4 |
| `mapping_v3.py` | 🔄 RENAME → `mappings.py` | Keep logic, update for V4 |
| `feedback.py` | ✅ KEEP | Still needed |
| `semantic.py` | ✅ KEEP | Still needed |
| `unmapped_fields.py` | ✅ KEEP | Still needed (source fields) |
| ➕ `projects.py` | ✨ NEW | Project management endpoints |
| ➕ `target_tables.py` | ✨ NEW | Target table status endpoints |
| ➕ `suggestions.py` | ✨ NEW | Suggestion review endpoints |
| **Services** | | |
| `ai_mapping_service.py` | 🗑️ DELETE | V2, replaced by V4 |
| `ai_mapping_service_v3.py` | 🔄 RENAME → `ai_suggestion_service.py` | Update for target-first |
| `mapping_service.py` | 🗑️ DELETE | V2, replaced by V4 |
| `mapping_service_v3.py` | 🔄 RENAME → `mapping_service.py` | Update for V4 |
| `auth_service.py` | ✅ KEEP | Still needed |
| `config_service.py` | ✅ KEEP | Still needed |
| `feedback_service.py` | ✅ KEEP | Still needed |
| `semantic_service.py` | ✅ KEEP | Still needed |
| `system_service.py` | ✅ KEEP | Still needed |
| `unmapped_fields_service.py` | ✅ KEEP | Still needed |
| ➕ `project_service.py` | ✨ NEW | Project CRUD |
| ➕ `target_table_service.py` | ✨ NEW | Target table management |
| ➕ `suggestion_service.py` | ✨ NEW | Suggestion generation & review |
| **Models** | | |
| `mapping.py` | 🗑️ DELETE | V2, replaced by V4 |
| `mapping_v3.py` | 🔄 RENAME → `mapping.py` | Update for V4 |
| `config.py` | ✅ KEEP | Still needed |
| `semantic.py` | ✅ KEEP | Still needed |
| `shared.py` | ✅ KEEP | Still needed |
| ➕ `project.py` | ✨ NEW | Project models |
| ➕ `suggestion.py` | ✨ NEW | Suggestion models |

### Frontend Files

| File | Action | Reason |
|------|--------|--------|
| **Views** | | |
| `MappingView.vue` | 🗑️ DELETE | V2, old source-first flow |
| `MappingConfigViewV3.vue` | 🔄 UPDATE → `SuggestionReviewView.vue` | Adapt for suggestion review |
| `MappingsListViewV3.vue` | 🔄 UPDATE → `MappingsListView.vue` | Simplify name |
| `HomeView.vue` | 🔄 UPDATE | Make project dashboard |
| `UnmappedFieldsView.vue` | ✅ KEEP | Source fields upload |
| `SemanticFieldsView.vue` | ✅ KEEP | Target field management |
| `ConfigView.vue` | ✅ KEEP | Configuration |
| `IntroductionView.vue` | 🔄 UPDATE | Update for V4 workflow |
| `AboutView.vue` | ✅ KEEP | About page |
| ➕ `ProjectDashboardView.vue` | ✨ NEW | Main project dashboard |
| ➕ `TargetTableListView.vue` | ✨ NEW | Target tables for a project |
| ➕ `SuggestionReviewView.vue` | ✨ NEW | Review suggestions for a table |
| **Components** | | |
| `PatternTemplateCard.vue` | 🔄 UPDATE | Adapt for suggestion display |
| `AISuggestionsDialog.vue` | 🗑️ DELETE | V3, replaced by new flow |
| `FeedbackDialog.vue` | ✅ KEEP | Still needed for rejections |
| `AppLayout.vue` | ✅ KEEP | Layout component |
| `AppSidebar.vue` | 🔄 UPDATE | Update navigation for V4 |
| `AppToolbar.vue` | ✅ KEEP | Toolbar component |
| `HelpButton.vue` | ✅ KEEP | Help component |
| ➕ `ProjectCard.vue` | ✨ NEW | Project summary card |
| ➕ `TargetTableCard.vue` | ✨ NEW | Table progress card |
| ➕ `SuggestionCard.vue` | ✨ NEW | Individual suggestion card |
| ➕ `SQLDiffViewer.vue` | ✨ NEW | Show SQL changes |
| ➕ `ProgressStats.vue` | ✨ NEW | Progress counters component |
| **Stores** | | |
| `aiSuggestionsStore.ts` | 🗑️ DELETE | V3, replaced by V4 |
| `mappingsStoreV3.ts` | 🔄 RENAME → `mappingsStore.ts` | Update for V4 |
| `unmappedFieldsStore.ts` | ✅ KEEP | Source fields |
| `user.ts` | ✅ KEEP | User state |
| `counter.ts` | 🗑️ DELETE | Example file, not used |
| ➕ `projectStore.ts` | ✨ NEW | Project state |
| ➕ `suggestionsStore.ts` | ✨ NEW | Suggestions state |
| **Services** | | |
| `api.ts` | 🔄 UPDATE | Add new V4 endpoints |

### Database Files

| File | Action | Reason |
|------|--------|--------|
| `V3_SCHEMA_CREATE.sql` | ✅ KEEP | Base schema reference |
| `V3_ADD_JOIN_METADATA.sql` | ✅ KEEP | Join metadata addition |
| `V4_TARGET_FIRST_SCHEMA.sql` | ✨ NEW | V4 schema additions |
| Other V3 migration files | ✅ KEEP | Historical reference |
| `BR Scenario -Table 1.csv` | ✅ KEEP | Historical mapping data |

---

## Migration Approach

### Phase 1: Schema & Data (You do this in Databricks)
1. Run `V4_TARGET_FIRST_SCHEMA.sql` to create new tables
2. Load historical mappings with `join_metadata` (mark `is_approved_pattern = true`)
3. Verify data integrity

### Phase 2: Backend Cleanup & New Code
1. Delete V2 files (ai_mapping.py, mapping.py, ai_mapping_service.py, mapping_service.py)
2. Rename V3 files (remove _v3 suffix)
3. Create new V4 files (projects, target_tables, suggestions)
4. Update app.py to register new routers

### Phase 3: Frontend Cleanup & New Code
1. Delete unused files (MappingView.vue, counter.ts, aiSuggestionsStore.ts)
2. Rename V3 files (remove V3 suffix)
3. Create new V4 views and components
4. Update router and navigation

### Phase 4: Integration & Testing
1. Connect new frontend to new backend
2. Test complete workflow
3. Update documentation

---

## New V4 Navigation Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Smart Mapper V4                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  📊 Dashboard          ← ProjectDashboardView (main page)                   │
│     └── All projects with stats                                             │
│                                                                              │
│  📁 Projects                                                                 │
│     ├── Project 1                                                           │
│     │   ├── 📤 Source Fields    ← UnmappedFieldsView (filtered by project) │
│     │   ├── 🎯 Target Tables    ← TargetTableListView                       │
│     │   │   ├── MBR_CNTCT       ← SuggestionReviewView                     │
│     │   │   ├── MBR_FNDTN       ← SuggestionReviewView                     │
│     │   │   └── ...                                                         │
│     │   └── ✅ Completed        ← MappingsListView (approved mappings)      │
│     └── Project 2                                                           │
│         └── ...                                                              │
│                                                                              │
│  ⚙️ Admin                                                                    │
│     ├── Semantic Fields    ← SemanticFieldsView (target definitions)        │
│     ├── Pattern Library    ← Historical approved patterns                   │
│     └── Configuration      ← ConfigView                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints (V4)

### Projects
```
GET    /api/v4/projects                         List all projects
POST   /api/v4/projects                         Create new project
GET    /api/v4/projects/{id}                    Get project details
PUT    /api/v4/projects/{id}                    Update project
DELETE /api/v4/projects/{id}                    Delete project
```

### Source Fields (per project)
```
GET    /api/v4/projects/{id}/source-fields      Get source fields
POST   /api/v4/projects/{id}/source-fields      Upload source fields (CSV)
DELETE /api/v4/projects/{id}/source-fields/{fid} Remove source field
```

### Target Tables (per project)
```
GET    /api/v4/projects/{id}/target-tables      Get all target tables with status
GET    /api/v4/projects/{id}/target-tables/{tid} Get single table details
POST   /api/v4/projects/{id}/target-tables/{tid}/discover  Start AI discovery
GET    /api/v4/projects/{id}/target-tables/{tid}/suggestions  Get suggestions
```

### Suggestions
```
GET    /api/v4/suggestions/{sid}                Get suggestion details
POST   /api/v4/suggestions/{sid}/approve        Approve suggestion as-is
POST   /api/v4/suggestions/{sid}/edit           Edit and approve
POST   /api/v4/suggestions/{sid}/reject         Reject with feedback
POST   /api/v4/suggestions/{sid}/skip           Skip column
```

### Mappings (approved)
```
GET    /api/v4/projects/{id}/mappings           Get approved mappings
GET    /api/v4/mappings/{mid}                   Get mapping details
PUT    /api/v4/mappings/{mid}                   Update mapping
DELETE /api/v4/mappings/{mid}                   Delete mapping
POST   /api/v4/mappings/{mid}/approve-as-pattern  Mark as approved pattern
```

### Patterns (for AI)
```
GET    /api/v4/patterns                         Get approved patterns
GET    /api/v4/patterns/{target_table}/{target_column}  Get pattern for column
```

---

## File Creation Order

### Backend (create in this order)
1. `backend/models/project.py` - Project and TargetTableStatus models
2. `backend/models/suggestion.py` - Suggestion models
3. `backend/services/project_service.py` - Project CRUD
4. `backend/services/target_table_service.py` - Target table management
5. `backend/services/suggestion_service.py` - AI suggestion generation
6. `backend/routers/projects.py` - Project endpoints
7. `backend/routers/target_tables.py` - Target table endpoints
8. `backend/routers/suggestions.py` - Suggestion endpoints
9. Update `backend/app.py` - Register new routers

### Frontend (create in this order)
1. `frontend/src/stores/projectStore.ts` - Project state
2. `frontend/src/stores/suggestionsStore.ts` - Suggestions state
3. `frontend/src/services/api.ts` - Add new endpoints
4. `frontend/src/components/ProgressStats.vue` - Reusable stats
5. `frontend/src/components/ProjectCard.vue` - Project summary
6. `frontend/src/components/TargetTableCard.vue` - Table progress
7. `frontend/src/components/SuggestionCard.vue` - Suggestion display
8. `frontend/src/components/SQLDiffViewer.vue` - SQL diff view
9. `frontend/src/views/ProjectDashboardView.vue` - Main dashboard
10. `frontend/src/views/TargetTableListView.vue` - Tables list
11. `frontend/src/views/SuggestionReviewView.vue` - Review suggestions
12. Update `frontend/src/router/index.ts` - New routes
13. Update `frontend/src/components/AppSidebar.vue` - New navigation

---

## Styling Reference

Keep existing Gainwell theme from:
- `frontend/src/assets/gainwell-theme.css`
- `frontend/src/assets/main.css`
- `frontend/src/assets/base.css`

Component styling patterns from:
- `MappingConfigViewV3.vue` - Card layouts, form styling
- `UnmappedFieldsView.vue` - Table styling, upload UI
- `PatternTemplateCard.vue` - Suggestion card styling

---

## Cleanup Commands (after V4 is complete)

```bash
# Backend cleanup
rm backend/routers/ai_mapping.py
rm backend/routers/mapping.py
rm backend/services/ai_mapping_service.py
rm backend/services/mapping_service.py
rm backend/models/mapping.py

# Rename V3 files
mv backend/routers/ai_mapping_v3.py backend/routers/ai_suggestions.py
mv backend/routers/mapping_v3.py backend/routers/mappings.py
mv backend/services/ai_mapping_service_v3.py backend/services/ai_suggestion_service.py
mv backend/services/mapping_service_v3.py backend/services/mapping_service.py
mv backend/models/mapping_v3.py backend/models/mapping.py

# Frontend cleanup
rm frontend/src/views/MappingView.vue
rm frontend/src/stores/counter.ts
rm frontend/src/components/AISuggestionsDialog.vue

# Rename V3 files
mv frontend/src/views/MappingConfigViewV3.vue frontend/src/views/MappingConfigView.vue
mv frontend/src/views/MappingsListViewV3.vue frontend/src/views/MappingsListView.vue
mv frontend/src/stores/mappingsStoreV3.ts frontend/src/stores/mappingsStore.ts
```

---

## Ready to Start?

Once you've run the V4 schema in Databricks, we can start creating the new files in this order:
1. Backend models
2. Backend services  
3. Backend routers
4. Frontend stores
5. Frontend components
6. Frontend views
7. Update routing
8. Final cleanup

