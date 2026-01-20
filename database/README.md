# Smart Mapper V4 - Database Schema

This folder contains the database schema scripts for Smart Mapper V4.

## Schema Files

### 1. `V4_TARGET_FIRST_SCHEMA.sql` (Run First)
Creates all core V4 tables:
- `mapping_projects` - Project tracking and configuration
- `target_table_status` - Progress tracking per target table
- `mapping_suggestions` - AI-generated suggestions before approval
- `semantic_fields` - Target field definitions (from catalog)

**Usage:**
```sql
-- Replace ${CATALOG_SCHEMA} with your catalog.schema
-- e.g., oz_dev.silver_dmes_de
```

### 2. `V4_UNMAPPED_FIELDS_WITH_PROJECT.sql`
Creates/recreates the `unmapped_fields` table with:
- `project_id` column for project association
- `source_semantic_field` format includes PROJECT_ID for vector search

**Usage:**
```sql
-- Run after V4_TARGET_FIRST_SCHEMA.sql
-- Replace ${CATALOG_SCHEMA} with your catalog.schema
```

### 3. `V4_MAPPED_FIELDS_RECREATE.sql`
Adds V4 columns to `mapped_fields` table:
- `project_id` - Links mapping to a project
- `is_approved_pattern` - Whether mapping is approved as AI pattern
- `pattern_approved_by`, `pattern_approved_ts` - Pattern approval tracking
- `team_members` column on projects

**Usage:**
```sql
-- Run after creating mapped_fields table
-- Replace ${CATALOG_SCHEMA} with your catalog.schema
```

## Installation Order

1. Run `V4_TARGET_FIRST_SCHEMA.sql`
2. Run `V4_UNMAPPED_FIELDS_WITH_PROJECT.sql`
3. Run `V4_MAPPED_FIELDS_RECREATE.sql`

## Configuration

Replace `${CATALOG_SCHEMA}` with your Databricks catalog.schema in all files.

Example: `oz_dev.silver_dmes_de`

