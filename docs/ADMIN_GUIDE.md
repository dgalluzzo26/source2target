# Smart Mapper V4 - Administrator Guide

## Table of Contents
1. [Administrator Overview](#administrator-overview)
2. [System Architecture](#system-architecture)
3. [Database Schema V4](#database-schema-v4)
4. [Stored Procedures](#stored-procedures)
5. [Views](#views)
6. [Configuration](#configuration)
7. [Semantic Field Management](#semantic-field-management)
8. [Pattern Management](#pattern-management)
9. [Loading Historical Mappings](#loading-historical-mappings)
10. [User & Team Management](#user--team-management)
11. [System Monitoring](#system-monitoring)
12. [Troubleshooting](#troubleshooting)
13. [Maintenance](#maintenance)
14. [Security](#security)

---

## Administrator Overview

As a Smart Mapper V4 administrator, you are responsible for:

- **System Configuration**: Database, AI model, and vector search settings
- **Semantic Field Management**: Maintaining target field definitions
- **Pattern Management**: Loading and curating historical mapping patterns
- **User Support**: Helping users with projects and troubleshooting
- **System Monitoring**: Ensuring all components are operational

### Admin Identification

Admins are identified by:
- Green **"Admin"** badge in the header
- Access to **Administration** section in sidebar
- Email listed in the configured admin users list (Settings → Security)

### V4 Key Changes from V3

| Area | V3 (Source-First) | V4 (Target-First) |
|------|-------------------|-------------------|
| Workflow | Select source → find target | Select target table → AI suggests all |
| Organization | Per-user mappings | Project-based with teams |
| AI Scope | One field at a time | Entire table at once |
| Progress | Individual field tracking | Table and project dashboards |
| Storage | mapped_fields only | projects + tables + suggestions |

---

## System Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SMART MAPPER V4 ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐        ┌──────────────────┐        ┌───────────────┐ │
│  │   Frontend       │        │   Backend        │        │  Databricks   │ │
│  │   Vue.js 3       │◄──────►│   FastAPI        │◄──────►│  Unity Catalog│ │
│  │   PrimeVue       │  REST  │   Python 3.11    │  SQL   │  SQL Warehouse│ │
│  │   Pinia          │        │   OAuth          │  OAuth │  Model Serving│ │
│  └──────────────────┘        └──────────────────┘        │  Vector Search│ │
│                                                           └───────────────┘ │
│                                                                              │
│  Tables:                                                                     │
│  ├── mapping_projects        (NEW - project tracking)                       │
│  ├── target_table_status     (NEW - per-table progress)                     │
│  ├── mapping_suggestions     (NEW - AI suggestions before approval)         │
│  ├── semantic_fields         (target definitions - unchanged)               │
│  ├── unmapped_fields         (source fields + project_id)                   │
│  ├── mapped_fields           (approved mappings + project_id, patterns)     │
│  └── mapping_feedback        (rejection learning)                           │
│                                                                              │
│  Stored Procedures:                                                          │
│  ├── sp_initialize_target_tables                                            │
│  ├── sp_recalculate_table_counters                                          │
│  ├── sp_update_project_counters                                             │
│  ├── sp_mark_table_complete                                                 │
│  └── sp_approve_mapping_as_pattern                                          │
│                                                                              │
│  Views:                                                                      │
│  ├── v_project_dashboard                                                     │
│  ├── v_target_table_progress                                                │
│  └── v_suggestion_review                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Project Creation**: User creates project → `mapping_projects` row created
2. **Source Upload**: User uploads CSV → `unmapped_fields` rows with `project_id`
3. **Table Init**: System reads `semantic_fields` → creates `target_table_status` rows
4. **AI Discovery**: For each target column:
   - Search `mapped_fields` for patterns (where `is_approved_pattern = true`)
   - Search `unmapped_fields` for matching sources (vector search)
   - LLM rewrites SQL with user's sources
   - Store in `mapping_suggestions`
5. **Approval**: User approves → creates `mapped_fields` row with `project_id`
6. **Pattern Promotion**: Admin marks mapping as approved pattern → `is_approved_pattern = true`

---

## Database Schema V4

### New Tables

#### `mapping_projects`

Tracks overall mapping projects with progress stats.

```sql
CREATE TABLE mapping_projects (
  project_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  
  -- Identification
  project_name STRING NOT NULL,
  project_description STRING,
  
  -- Source/target context
  source_system_name STRING,
  source_catalogs STRING,      -- Pipe-separated: "bronze_dmes|bronze_mmis"
  source_schemas STRING,
  target_catalogs STRING,
  target_schemas STRING,
  target_domains STRING,       -- Filter: "Member|Claims"
  
  -- Status: NOT_STARTED, ACTIVE, REVIEW, COMPLETE, ARCHIVED
  project_status STRING DEFAULT 'NOT_STARTED',
  
  -- Progress counters (denormalized for dashboard performance)
  total_target_tables INT DEFAULT 0,
  tables_complete INT DEFAULT 0,
  tables_in_progress INT DEFAULT 0,
  total_target_columns INT DEFAULT 0,
  columns_mapped INT DEFAULT 0,
  columns_pending_review INT DEFAULT 0,
  
  -- Team access
  team_members STRING,         -- Pipe-separated emails
  
  -- Audit
  created_by STRING NOT NULL,
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_by STRING,
  updated_ts TIMESTAMP,
  completed_by STRING,
  completed_ts TIMESTAMP
);
```

#### `target_table_status`

Tracks mapping progress for each target table within a project.

```sql
CREATE TABLE target_table_status (
  target_table_status_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  
  -- Links
  project_id BIGINT NOT NULL,  -- FK to mapping_projects
  
  -- Target table identification
  tgt_table_name STRING NOT NULL,
  tgt_table_physical_name STRING NOT NULL,
  tgt_table_description STRING,
  
  -- Status: NOT_STARTED, DISCOVERING, SUGGESTIONS_READY, 
  --         IN_PROGRESS, COMPLETE, SKIPPED
  mapping_status STRING DEFAULT 'NOT_STARTED',
  
  -- Progress counters
  total_columns INT DEFAULT 0,
  columns_with_pattern INT DEFAULT 0,
  columns_mapped INT DEFAULT 0,
  columns_pending_review INT DEFAULT 0,
  columns_no_match INT DEFAULT 0,
  columns_skipped INT DEFAULT 0,
  
  -- AI processing
  ai_job_id STRING,
  ai_started_ts TIMESTAMP,
  ai_completed_ts TIMESTAMP,
  ai_error_message STRING,
  
  -- Confidence summary
  avg_confidence DOUBLE,
  min_confidence DOUBLE,
  
  -- Ordering
  display_order INT,
  priority STRING DEFAULT 'NORMAL',  -- HIGH, NORMAL, LOW
  
  -- Audit
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  started_by STRING,
  started_ts TIMESTAMP,
  completed_by STRING,
  completed_ts TIMESTAMP
);
```

#### `mapping_suggestions`

Stores AI suggestions before user approval.

```sql
CREATE TABLE mapping_suggestions (
  suggestion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  
  -- Links
  project_id BIGINT NOT NULL,
  target_table_status_id BIGINT NOT NULL,
  semantic_field_id BIGINT,        -- FK to semantic_fields
  
  -- Target identification
  tgt_table_name STRING NOT NULL,
  tgt_table_physical_name STRING NOT NULL,
  tgt_column_name STRING NOT NULL,
  tgt_column_physical_name STRING NOT NULL,
  tgt_column_description STRING,
  
  -- Pattern used (if any)
  pattern_type STRING,              -- DIRECT, UNION, JOIN, UNION_WITH_JOINS
  pattern_mapped_field_id BIGINT,   -- FK to the pattern used
  pattern_sql STRING,               -- Original pattern SQL
  
  -- AI suggestion
  suggested_sql STRING,             -- Rewritten SQL for this project
  matched_source_fields STRING,     -- JSON array of matched sources
  ai_reasoning STRING,              -- LLM explanation
  
  -- Confidence
  confidence_score DOUBLE,
  pattern_confidence DOUBLE,
  source_match_confidence DOUBLE,
  
  -- Warnings
  warnings STRING,                  -- JSON array of warning messages
  
  -- Status: PENDING, APPROVED, EDITED, REJECTED, SKIPPED
  suggestion_status STRING DEFAULT 'PENDING',
  
  -- If approved, link to created mapping
  created_mapped_field_id BIGINT,
  
  -- User actions
  user_edited_sql STRING,
  rejection_reason STRING,
  reviewed_by STRING,
  reviewed_ts TIMESTAMP,
  
  -- Audit
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

### Modified Tables

#### `unmapped_fields` - Added Columns

```sql
-- New column
project_id BIGINT,  -- FK to mapping_projects (NULL for legacy)
```

#### `mapped_fields` - Added Columns

```sql
-- New columns for V4
project_id BIGINT,               -- FK to mapping_projects (NULL = global pattern)
is_approved_pattern BOOLEAN DEFAULT FALSE,
pattern_approved_by STRING,
pattern_approved_ts TIMESTAMP
```

### Key Column Reference

| Table | Primary Key | Important FKs |
|-------|-------------|---------------|
| `mapping_projects` | `project_id` | - |
| `target_table_status` | `target_table_status_id` | `project_id` |
| `mapping_suggestions` | `suggestion_id` | `project_id`, `target_table_status_id`, `semantic_field_id` |
| `unmapped_fields` | `unmapped_field_id` | `project_id` |
| `mapped_fields` | `mapped_field_id` | `project_id`, `semantic_field_id` |

---

## Stored Procedures

V4 uses Databricks SQL stored procedures for complex operations. All procedures accept dynamic catalog and schema parameters.

### `sp_initialize_target_tables`

Populates `target_table_status` from `semantic_fields` when starting a project.

**Parameters:**
- `p_catalog` - Catalog name (e.g., 'oztest_dev')
- `p_schema` - Schema name (e.g., 'smartmapper')
- `p_project_id` - Project ID to initialize
- `p_domain_filter` - Domain filter (NULL for all, or 'Member', 'Member|Claims')

**Example:**
```sql
CALL oztest_dev.smartmapper.sp_initialize_target_tables(
  'oztest_dev', 'smartmapper', 1, 'Member'
);
```

**What it does:**
1. Queries `semantic_fields` for unique target tables (filtered by domain)
2. Inserts rows into `target_table_status` with column counts
3. Updates `mapping_projects` with `total_target_tables` and `total_target_columns`
4. Sets project status to 'ACTIVE'

### `sp_recalculate_table_counters`

Recalculates progress counters for a target table from suggestion data.

**Parameters:**
- `p_catalog` - Catalog name
- `p_schema` - Schema name
- `p_target_table_status_id` - Table status ID to recalculate

**Example:**
```sql
CALL oztest_dev.smartmapper.sp_recalculate_table_counters(
  'oztest_dev', 'smartmapper', 42
);
```

**What it does:**
1. Counts suggestions by status (PENDING, APPROVED, REJECTED, SKIPPED)
2. Updates `target_table_status` with new counters
3. Calculates and updates confidence stats (avg, min)
4. Updates the parent project's counters

### `sp_update_project_counters`

Recalculates project-level progress from all its tables.

**Parameters:**
- `p_catalog` - Catalog name
- `p_schema` - Schema name
- `p_project_id` - Project ID to recalculate

**Example:**
```sql
CALL oztest_dev.smartmapper.sp_update_project_counters(
  'oztest_dev', 'smartmapper', 1
);
```

**What it does:**
1. Aggregates counters from all `target_table_status` rows
2. Updates `mapping_projects` with totals
3. Updates `updated_ts` timestamp

### `sp_mark_table_complete`

Marks a target table as complete and updates all counters.

**Parameters:**
- `p_catalog` - Catalog name
- `p_schema` - Schema name
- `p_target_table_status_id` - Table status ID
- `p_completed_by` - User email

**Example:**
```sql
CALL oztest_dev.smartmapper.sp_mark_table_complete(
  'oztest_dev', 'smartmapper', 42, 'user@example.com'
);
```

### `sp_approve_mapping_as_pattern`

Promotes an approved mapping to be used as a pattern for future AI suggestions.

**Parameters:**
- `p_catalog` - Catalog name
- `p_schema` - Schema name
- `p_mapped_field_id` - Mapped field ID to promote
- `p_approved_by` - Admin user email

**Example:**
```sql
CALL oztest_dev.smartmapper.sp_approve_mapping_as_pattern(
  'oztest_dev', 'smartmapper', 100, 'admin@example.com'
);
```

**What it does:**
1. Sets `is_approved_pattern = TRUE`
2. Records `pattern_approved_by` and `pattern_approved_ts`
3. Pattern becomes available for AI to use in future projects

---

## Views

### `v_project_dashboard`

Aggregated statistics for the main projects dashboard.

```sql
CREATE VIEW v_project_dashboard AS
SELECT 
  p.project_id,
  p.project_name,
  p.project_description,
  p.project_status,
  p.source_system_name,
  p.total_target_tables,
  p.tables_complete,
  p.tables_in_progress,
  p.total_target_columns,
  p.columns_mapped,
  p.columns_pending_review,
  ROUND(p.columns_mapped * 100.0 / NULLIF(p.total_target_columns, 0), 1) AS percent_complete,
  p.created_by,
  p.created_ts,
  p.team_members
FROM mapping_projects p
WHERE p.project_status != 'ARCHIVED';
```

### `v_target_table_progress`

Per-table progress details with status breakdown.

```sql
CREATE VIEW v_target_table_progress AS
SELECT 
  t.target_table_status_id,
  t.project_id,
  p.project_name,
  t.tgt_table_name,
  t.tgt_table_physical_name,
  t.mapping_status,
  t.total_columns,
  t.columns_mapped,
  t.columns_pending_review,
  t.columns_skipped,
  t.columns_no_match,
  ROUND(t.columns_mapped * 100.0 / NULLIF(t.total_columns, 0), 1) AS percent_complete,
  t.avg_confidence,
  t.min_confidence,
  t.display_order,
  t.priority
FROM target_table_status t
JOIN mapping_projects p ON t.project_id = p.project_id;
```

### `v_suggestion_review`

Suggestions pending review with full context.

```sql
CREATE VIEW v_suggestion_review AS
SELECT 
  s.suggestion_id,
  s.project_id,
  s.target_table_status_id,
  t.tgt_table_name,
  s.tgt_column_name,
  s.tgt_column_physical_name,
  s.tgt_column_description,
  s.pattern_type,
  s.suggested_sql,
  s.matched_source_fields,
  s.confidence_score,
  s.warnings,
  s.suggestion_status,
  s.ai_reasoning,
  s.created_ts
FROM mapping_suggestions s
JOIN target_table_status t ON s.target_table_status_id = t.target_table_status_id
WHERE s.suggestion_status = 'PENDING'
ORDER BY s.confidence_score DESC;
```

---

## Configuration

### Database Configuration

Navigate to **Settings** → **Database**.

**Required Settings:**

| Setting | Description | Example |
|---------|-------------|---------|
| Warehouse Name | SQL Warehouse name | `my-sql-warehouse` |
| Server Hostname | Databricks workspace URL | `workspace.cloud.databricks.com` |
| HTTP Path | Warehouse HTTP path | `/sql/1.0/warehouses/abc123` |
| Catalog Name | Unity Catalog name | `oztest_dev` |
| Schema Name | Database schema | `smartmapper` |

**Table Names** (enter without catalog.schema prefix):

| Setting | Default Value |
|---------|---------------|
| Semantic Fields Table | `semantic_fields` |
| Unmapped Fields Table | `unmapped_fields` |
| Mapped Fields Table | `mapped_fields` |
| Mapping Projects Table | `mapping_projects` |
| Target Table Status Table | `target_table_status` |
| Mapping Suggestions Table | `mapping_suggestions` |

### Vector Search Configuration

**Required Settings:**

| Setting | Description | Example |
|---------|-------------|---------|
| Semantic Index | Index for target fields | `oztest_dev.smartmapper.semantic_fields_vs` |
| Patterns Index | Index for mapping patterns | `oztest_dev.smartmapper.mapped_fields_vs` |
| Endpoint Name | Vector search endpoint | `s2t_vsendpoint` |

### AI Model Configuration

**Required Settings:**

| Setting | Description | Example |
|---------|-------------|---------|
| Foundation Model Endpoint | LLM endpoint name | `databricks-meta-llama-3-3-70b-instruct` |

---

## Semantic Field Management

### Overview

Semantic fields define all possible target fields. The V4 workflow depends on complete, well-described semantic fields.

### Viewing Semantic Fields

Navigate to **Administration** → **Semantic Fields**.

The table shows:
- Target table and column names (logical and physical)
- Data type and nullable flag
- Description (critical for AI matching)
- Domain category

### Adding Semantic Fields

**Via UI:**
1. Click **"Add Field"**
2. Fill in all fields
3. Click **"Save"**

**Via SQL:**
```sql
INSERT INTO oztest_dev.smartmapper.semantic_fields (
  tgt_table_name,
  tgt_table_physical_name,
  tgt_column_name,
  tgt_column_physical_name,
  tgt_nullable,
  tgt_physical_datatype,
  tgt_comments,
  domain
) VALUES (
  'Member Contact',
  'MBR_CNTCT',
  'Address Line 1',
  'ADDR_1_TXT',
  'YES',
  'STRING',
  'First line of member address including street number and name',
  'Member'
);
```

### Best Practices for Semantic Fields

1. ✅ **Detailed Descriptions**: Write comprehensive `tgt_comments`
   - Bad: "Address"
   - Good: "First line of member mailing address including street number and name"
   
2. ✅ **Consistent Domains**: Use standard domain names (Member, Claims, Provider)

3. ✅ **Complete Coverage**: Add ALL target columns, even complex ones

4. ✅ **Physical Names Match**: Ensure physical names match actual table/column names

---

## Pattern Management

### What are Patterns?

Patterns are approved mappings that the AI uses to suggest SQL for new projects. They are stored in `mapped_fields` with `is_approved_pattern = TRUE`.

### Pattern Sources

1. **Historical Mappings**: Loaded from past migration projects
2. **Promoted Mappings**: New mappings marked as patterns by admins

### Viewing Patterns

Query the database:
```sql
SELECT 
  mf.mapped_field_id,
  sf.tgt_table_name,
  sf.tgt_column_name,
  mf.source_expression,
  mf.source_tables,
  mf.join_metadata,
  mf.pattern_approved_by,
  mf.pattern_approved_ts
FROM mapped_fields mf
JOIN semantic_fields sf ON mf.semantic_field_id = sf.semantic_field_id
WHERE mf.is_approved_pattern = TRUE
ORDER BY sf.tgt_table_name, sf.tgt_column_name;
```

### Promoting a Mapping to Pattern

**Via Stored Procedure:**
```sql
CALL oztest_dev.smartmapper.sp_approve_mapping_as_pattern(
  'oztest_dev', 'smartmapper', 
  123,  -- mapped_field_id
  'admin@example.com'
);
```

### Pattern Quality Guidelines

1. ✅ **Complete SQL**: Include all JOINs, filters, and transformations
2. ✅ **Documented join_metadata**: Complex patterns should have structured metadata
3. ✅ **Tested**: Verify pattern SQL works with actual data
4. ✅ **Reviewed**: Have another team member review before approving

---

## Loading Historical Mappings (Pattern Import)

### Purpose

Load past migration mappings as patterns for the AI to learn from. The **Pattern Import** feature in the UI provides a guided workflow for this.

### Using Pattern Import (Recommended)

1. Navigate to **Administration** → **Pattern Import**
2. **Step 1 - Upload**: Upload a CSV file with historical mappings
3. **Step 2 - Map Columns**: Map your CSV columns to required fields
4. **Step 3 - Process**: AI analyzes patterns and generates join_metadata
5. **Step 4 - Review**: Review processed patterns before saving
6. **Step 5 - Save**: Save patterns to the mapped_fields table

### CSV Format

Your CSV should include these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `tgt_table_name` | ✅ | Target table name (e.g., "MBR_CNTCT") |
| `tgt_column_name` | ✅ | Target column name (e.g., "ADDR_1_TXT") |
| `source_expression` | ✅ | Complete SQL expression |
| `source_tables` | Optional | Pipe-separated source tables |
| `source_columns` | Optional | Pipe-separated source columns |
| `join_column_descriptions` | Optional | Descriptions for join/filter columns |

### Special Case Handling

The Pattern Import automatically handles special source expressions:

| Source Expression | Pattern Type | Behavior |
|-------------------|--------------|----------|
| `Auto Generated` | AUTO_GENERATED | No SQL generated, marked as auto-mapped |
| `Hard coded as NULL` | HARDCODED | Generates `SELECT NULL AS column` |
| `Hard coded as 'value'` | HARDCODED | Generates `SELECT 'value' AS column` |
| `N/A` | NOT_APPLICABLE | Marked for review, may not need mapping |

### Manual SQL Loading (Alternative)

For bulk loading via SQL:

```sql
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id,
  tgt_table_name, tgt_table_physical_name,
  tgt_column_name, tgt_column_physical_name,
  source_expression,
  source_tables, source_tables_physical,
  source_columns, source_columns_physical,
  join_metadata,
  mapping_status, mapping_source,
  is_approved_pattern, pattern_approved_by, pattern_approved_ts,
  mapped_by, mapped_ts
)
SELECT 
  sf.semantic_field_id,
  sf.tgt_table_name, sf.tgt_table_physical_name,
  sf.tgt_column_name, sf.tgt_column_physical_name,
  h.source_expression,
  h.source_tables, h.source_tables,
  h.source_columns, h.source_columns,
  h.join_metadata,
  'ACTIVE', 'BULK_UPLOAD',
  TRUE, 'admin@example.com', CURRENT_TIMESTAMP(),
  'admin@example.com', CURRENT_TIMESTAMP()
FROM your_staging_table h
JOIN semantic_fields sf 
  ON UPPER(h.tgt_table_name) = UPPER(sf.tgt_table_physical_name) 
  AND UPPER(h.tgt_column_name) = UPPER(sf.tgt_column_physical_name);
```

---

## User & Team Management

### Admin Users Configuration

1. Navigate to **Settings** → **Security**
2. Edit the **Admin Users** list - add email addresses of users who should have admin access
3. Users in this list see "Admin" badge and access Administration menu

**Example admin users:**
```
david.galluzzo@gainwelltechnologies.com
jane.doe@gainwelltechnologies.com
```

> **Note**: The legacy "Admin Group Name" field is still present but admin users list takes precedence.

### Project Team Access

Projects support team-based access:

1. **Creator**: User who creates the project (always has access)
2. **Team Members**: Users added by email to `team_members` column

**Adding Team Members:**
- Via UI: Project Settings → Team Members
- Via SQL:
```sql
UPDATE mapping_projects
SET team_members = 'user1@example.com|user2@example.com'
WHERE project_id = 1;
```

### Permissions Matrix

| Permission | Admin | Project Owner | Team Member |
|------------|-------|---------------|-------------|
| Create projects | ✅ | ✅ | ✅ |
| View own projects | ✅ | ✅ | ✅ |
| View team projects | ✅ | ✅ | ✅ |
| View all projects | ✅ | ❌ | ❌ |
| Edit project settings | ✅ | ✅ | ❌ |
| Add team members | ✅ | ✅ | ❌ |
| Delete project | ✅ | ✅ | ❌ |
| Semantic Management | ✅ | ❌ | ❌ |
| Approve patterns | ✅ | ❌ | ❌ |
| System Configuration | ✅ | ❌ | ❌ |

---

## System Monitoring

### System Status Dashboard

The Home page shows system health:

| Component | Status | What it checks |
|-----------|--------|----------------|
| Database Connection | ✅/❌ | Warehouse accessible, tables exist |
| Vector Search | ✅/❌ | Endpoint running, index accessible |
| AI Model | ✅/❌ | LLM endpoint responding |
| Configuration | ✅/❌ | All required settings present |

### Performance Metrics

**Typical Query Times:**
- Project list: 2-3 seconds
- Target table list: 2-3 seconds
- Suggestions load: 3-5 seconds
- AI discovery (per column): 2-5 seconds

**If Queries Are Slow:**
1. Check warehouse state (serverless may need warmup)
2. Review data volume
3. Monitor warehouse utilization
4. Consider warehouse scaling

### Accessing Logs

**Backend Logs:**
1. Go to Databricks workspace
2. Navigate to **Apps** → Your App
3. Click **"Logs"** tab
4. Filter by service name:
   - `[Projects Router]` - Project API calls
   - `[Target Tables Service]` - Table operations
   - `[Suggestion Service]` - AI suggestion generation
   - `[Vector Search]` - Search operations

---

## Troubleshooting

### Common Issues

**1. Project Not Loading**
- **Symptom**: Spinner indefinitely
- **Cause**: Database connection or warehouse asleep
- **Solution**: Check warehouse status, wait for warmup

**2. Discovery Fails**
- **Symptom**: Table stuck in DISCOVERING
- **Cause**: LLM endpoint down or timeout
- **Solution**: Check AI model endpoint status, retry

**3. No Suggestions Generated**
- **Symptom**: 0 suggestions after discovery
- **Cause**: No patterns found, no source fields match
- **Solution**: Check patterns exist, verify source descriptions

**4. Vector Search Unavailable**
- **Symptom**: AI can't find matches
- **Cause**: Endpoint stopped or index not synced
- **Solution**: Start endpoint, sync index

**5. Team Members Can't See Project**
- **Symptom**: User not seeing shared project
- **Cause**: Email not in team_members
- **Solution**: Add user's exact email to team_members

### Debug Queries

**Check project data:**
```sql
SELECT * FROM mapping_projects WHERE project_id = 1;
```

**Check table status:**
```sql
SELECT * FROM target_table_status WHERE project_id = 1;
```

**Check suggestion counts:**
```sql
SELECT suggestion_status, COUNT(*) 
FROM mapping_suggestions 
WHERE project_id = 1 
GROUP BY suggestion_status;
```

**Check pattern availability:**
```sql
SELECT tgt_table_name, COUNT(*) AS pattern_count
FROM mapped_fields mf
JOIN semantic_fields sf ON mf.semantic_field_id = sf.semantic_field_id
WHERE mf.is_approved_pattern = TRUE
GROUP BY tgt_table_name;
```

---

## Maintenance

### Daily Tasks
- ✅ Monitor system status dashboard
- ✅ Review backend logs for errors
- ✅ Check active project progress

### Weekly Tasks
- ✅ Review pending suggestions older than 7 days
- ✅ Check pattern library coverage
- ✅ Monitor vector search sync status
- ✅ Export project progress reports

### Monthly Tasks
- ✅ Audit admin group membership
- ✅ Review and clean archived projects
- ✅ Analyze AI suggestion accuracy
- ✅ Update documentation as needed
- ✅ Review and promote high-quality mappings to patterns

### Backup Strategy

**Configuration:**
- Backup `app_config.json` before changes
- Store in version control

**Database Tables:**
- Use Delta Lake time travel for recovery
- Export critical tables weekly
- Test restore procedures monthly

---

## Security

### Authentication
- Users authenticated via **Databricks OAuth**
- Email captured from `X-Forwarded-Email` header (or `X-User-Email` from frontend)
- No separate login required

### Authorization
- Admin access via **configured admin users list** (Settings → Security)
- Project access via `created_by` or `team_members`
- Stored procedures use `SQL SECURITY INVOKER`

### Admin Users Configuration

Admin access is controlled by a list of email addresses in `app_config.json`:

```json
{
  "security": {
    "admin_users": [
      "david.galluzzo@gainwelltechnologies.com",
      "jane.doe@company.com"
    ]
  }
}
```

This can also be edited in the UI: **Settings** → **Security** → **Admin Users**

### Data Access
- Users see only projects they own or are team members of
- Admins can view all projects
- Service principal has full read/write to tables

### Best Practices
1. ✅ Use service principal for app deployment
2. ✅ Limit admin group to trusted users
3. ✅ Enable audit logging in Databricks
4. ✅ Review access logs weekly
5. ✅ Use HTTPS only (enforced by Databricks Apps)
6. ✅ Keep dependencies updated

---

## Support Resources

### Documentation
- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Quick Start**: [QUICK_START.md](QUICK_START.md)
- **Developer Guide**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Architecture**: [architecture/TARGET_FIRST_WORKFLOW.md](architecture/TARGET_FIRST_WORKFLOW.md)

### Database Files
- **V4 Schema**: `database/V4_TARGET_FIRST_SCHEMA.sql` - Core schema for projects, tables, suggestions
- **Mapped Fields Updates**: `database/V4_MAPPED_FIELDS_RECREATE.sql` - Pattern approval columns
- **Unmapped Fields**: `database/V4_UNMAPPED_FIELDS_WITH_PROJECT.sql` - Project-aware source fields

---

**Version**: 4.0 - Target-First Workflow
**Last Updated**: December 2025
**Platform**: Smart Mapper (Target-First V4)
**Key Features**: Project management, Stored procedures, Team collaboration, Pattern library
