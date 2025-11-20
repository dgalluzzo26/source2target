# Source-to-Target Mapping Platform V2 - Migration Guide

## Overview

This guide documents the migration from V1 to V2 schema, which introduces support for **multi-column, multi-table mapping** to a single target field with **field ordering**, **concatenation strategies**, and **per-field transformations**.

---

## 🎯 Major Changes in V2

### 1. **Multi-Source Mapping Support**
- **V1**: One source field → One target field (1:1)
- **V2**: Multiple source fields → One target field (many:1)
- **Example**: `first_name` + `last_name` → `full_name`

### 2. **Field Ordering**
- Source fields can be ordered for concatenation
- UI will allow drag-and-drop reordering

### 3. **Concatenation Strategies**
- **NONE**: Single field mapping (like V1)
- **SPACE**: Concatenate with space delimiter
- **COMMA**: Concatenate with comma delimiter
- **PIPE**: Concatenate with pipe delimiter
- **CONCAT**: Direct concatenation (no separator)
- **CUSTOM**: User-defined separator

### 4. **Per-Field Transformations**
- Apply transformations to individual fields before concatenation
- **TEXT**: TRIM, UPPER, LOWER, INITCAP, etc.
- **DATE**: Format conversions, extraction (YEAR, MONTH)
- **NUMERIC**: ROUND, CAST, COALESCE
- **CUSTOM**: User-defined SQL expressions

### 5. **Feedback & Audit Trail**
- Capture user feedback on AI suggestions (ACCEPTED/REJECTED/MODIFIED)
- Track user comments for model improvement
- Enable analytics on mapping quality

### 6. **Domain Classification**
- Group fields by domain (claims, member, provider, finance, pharmacy)
- Enable domain-aware AI suggestions
- Support domain-specific vector search indexes

---

## 📊 New Schema Architecture

### **Table Relationships**

```
semantic_fields (Target Definitions)
       ↓ (1:many)
mapped_fields (One per target field)
       ↓ (1:many)
mapping_details (Source fields in mapping)
       ↓ (many:1)
unmapped_fields (Source fields awaiting mapping)

mapping_feedback (Audit trail)
       ↓ (many:1)
mapped_fields
```

---

## 📋 Table Descriptions

### 1. **semantic_fields** (Enhanced Target Field Definitions)

**Purpose**: Define all target fields available for mapping

**Key Columns**:
- `semantic_field_id`: Primary key (auto-generated)
- `tgt_table`, `tgt_column`: Target field identifier
- `tgt_data_type`, `tgt_is_nullable`: Metadata
- `tgt_comments`: Description for AI/vector search
- `domain`: Domain classification (NEW in V2)
- `semantic_field`: Computed field for vector embedding

**Changes from V1**:
- Added `domain` column for domain-aware recommendations
- Added `semantic_field_id` as primary key (was composite in V1)

---

### 2. **unmapped_fields** (Source Fields Awaiting Mapping)

**Purpose**: Store source fields that need to be mapped

**Key Columns**:
- `unmapped_field_id`: Primary key (auto-generated)
- `src_table`, `src_column`: Source field identifier
- `src_data_type`, `src_is_nullable`: Metadata
- `src_comments`: Description
- `domain`: Domain classification (NEW in V2)

**Changes from V1**:
- Extracted from V1's `combined_fields` table
- Removed mapping-related columns (moved to `mapped_fields`)

---

### 3. **mapped_fields** (Target Fields with Mappings)

**Purpose**: One record per TARGET field, supporting multiple source fields

**Key Columns**:
- `mapped_field_id`: Primary key (auto-generated)
- `semantic_field_id`: Foreign key to `semantic_fields`
- `tgt_table`, `tgt_column`: Denormalized target field
- `concat_strategy`: How to combine multiple sources (NEW)
- `concat_separator`: Custom separator if needed (NEW)
- `transformation_expression`: Full SQL expression (NEW)
- `confidence_score`: Overall mapping confidence
- `mapping_source`: AI, MANUAL, BULK_UPLOAD, SYSTEM
- `ai_reasoning`: AI explanation
- `mapping_status`: ACTIVE, INACTIVE, PENDING_REVIEW

**Changes from V1**:
- One record per TARGET (was one per SOURCE in V1)
- Added concatenation strategy and transformation expression
- Added status field for workflow management

---

### 4. **mapping_details** (Source Fields in Each Mapping)

**Purpose**: Store individual source fields that contribute to a target mapping

**Key Columns**:
- `mapping_detail_id`: Primary key (auto-generated)
- `mapped_field_id`: Foreign key to `mapped_fields`
- `unmapped_field_id`: Foreign key to `unmapped_fields` (nullable)
- `src_table`, `src_column`: Denormalized source field
- `field_order`: Order in concatenation (1-based) (NEW)
- `transformations`: Comma-separated transformation codes (NEW)
- `default_value`: For COALESCE (NEW)
- `field_confidence_score`: Per-field confidence

**New Table in V2**: Enables many-to-one mapping with ordering

---

### 5. **mapping_feedback** (Audit Trail for AI Suggestions)

**Purpose**: Capture user feedback on AI suggestions

**Key Columns**:
- `feedback_id`: Primary key (auto-generated)
- `suggested_src_table`, `suggested_src_column`: AI suggestion
- `suggested_tgt_table`, `suggested_tgt_column`: AI suggestion
- `ai_confidence_score`: AI confidence
- `ai_reasoning`: AI explanation
- `vector_search_score`: Raw similarity score
- `suggestion_rank`: Rank of suggestion (1 = top)
- `feedback_action`: ACCEPTED, REJECTED, MODIFIED (NEW)
- `user_comments`: User explanation (NEW)
- `modified_*`: If user modified the suggestion (NEW)
- `mapped_field_id`: Link to final mapping

**New Table in V2**: Enables model improvement and analytics

---

### 6. **transformation_library** (Reusable Transformation Templates)

**Purpose**: Store common transformation patterns

**Key Columns**:
- `transformation_id`: Primary key (auto-generated)
- `transformation_name`: Friendly name (e.g., "Standard Name Format")
- `transformation_code`: Short code (e.g., "STD_NAME")
- `transformation_expression`: SQL template (e.g., "TRIM(UPPER({field}))")
- `category`: TEXT, DATE, NUMERIC, CUSTOM
- `is_system`: System-provided or user-defined

**New Table in V2**: Standardizes transformations across mappings

**Pre-Seeded Transformations**:
- TRIM, UPPER, LOWER, INITCAP
- TRIM_UPPER, TRIM_LOWER
- COALESCE_EMPTY, COALESCE_ZERO
- FORMAT_SSN, FORMAT_PHONE
- DATE_TO_STR, STR_TO_DATE
- ROUND_2, TO_STRING, TO_INT, TO_DECIMAL
- And more...

---

## 🚀 Migration Process

### Prerequisites

1. **Backup your current database** ✅ (Already done with tar.gz)
2. **Ensure Databricks workspace access**
3. **Have admin permissions on catalog/schema**

### Step 1: Create V2 Schema

```sql
-- Run this script in Databricks SQL Editor or notebook
%run /path/to/migration_v2_schema.sql
```

This will:
- Create 6 new tables with proper constraints and indexes
- Pre-seed `transformation_library` with 20+ common transformations
- Enable Change Data Feed and auto-optimize

### Step 2: Migrate V1 Data to V2

```sql
-- Run this script in Databricks SQL Editor or notebook
%run /path/to/migration_v2_data.sql
```

This will:
1. **Backup V1 tables** (`semantic_table_v1_backup`, `combined_fields_v1_backup`)
2. **Migrate semantic_table → semantic_fields**
   - Preserve all fields and audit data
   - Initialize `domain` as NULL (populate later)
3. **Migrate unmapped fields → unmapped_fields**
   - Extract records where `tgt_table IS NULL` from `combined_fields`
4. **Migrate mapped fields → mapped_fields + mapping_details**
   - Create one `mapped_fields` record per unique target
   - Create one `mapping_details` record per source field
   - Set `concat_strategy = 'NONE'` (single field like V1)
   - Set `field_order = 1` (only one field)
5. **Run data quality checks**
   - Verify record counts match
   - Check referential integrity
6. **Generate summary report**

### Step 3: Post-Migration Tasks

#### A. Populate Domain Classification

Option 1: **Manual Review**
```sql
-- Review tables and assign domains manually
UPDATE main.source2target.semantic_fields
SET domain = 'member', updated_by = 'admin', updated_ts = CURRENT_TIMESTAMP()
WHERE tgt_table IN ('slv_member', 'slv_eligibility');
```

Option 2: **Automated by Naming Convention**
```sql
-- Uncomment the domain classification query in migration_v2_data.sql
-- Customize patterns based on your naming conventions
```

#### B. Update Vector Search Index

```sql
-- Sync vector search index with new semantic_fields table
-- This requires Databricks Vector Search endpoint
-- Update your vector search configuration to point to:
--   - Source: main.source2target.semantic_fields
--   - Embedding column: semantic_field
```

#### C. Update Application Configuration

Update `backend/config/default_config.json`:
```json
{
  "database": {
    "catalog": "main",
    "schema": "source2target",
    "semantic_table": "semantic_fields",       // Changed
    "combined_fields_table": "unmapped_fields", // Changed
    "mapped_fields_table": "mapped_fields"      // New
  }
}
```

#### D. Test Migration

1. **Verify record counts**:
   ```sql
   SELECT COUNT(*) FROM main.source2target.semantic_fields;
   SELECT COUNT(*) FROM main.source2target.unmapped_fields;
   SELECT COUNT(*) FROM main.source2target.mapped_fields;
   SELECT COUNT(*) FROM main.source2target.mapping_details;
   ```

2. **Test AI suggestions** in the UI
3. **Test manual mapping** with single field
4. **Test feedback capture** (once UI is updated)

#### E. Drop V1 Tables (Optional)

⚠️ **Only after thorough validation!**

```sql
-- Drop V1 tables (backups remain)
DROP TABLE main.source2target.combined_fields;
DROP TABLE main.source2target.semantic_table;
```

---

## 🔧 Example Use Cases

### Use Case 1: Simple 1:1 Mapping (Like V1)

**Scenario**: Map `T_MEMBER.SSN` → `slv_member.ssn_number`

**V2 Data**:

```sql
-- mapped_fields
INSERT INTO mapped_fields (semantic_field_id, tgt_table, tgt_column, concat_strategy, ...)
VALUES (123, 'slv_member', 'ssn_number', 'NONE', ...);

-- mapping_details
INSERT INTO mapping_details (mapped_field_id, src_table, src_column, field_order, transformations, ...)
VALUES (456, 'T_MEMBER', 'SSN', 1, 'TRIM,UNFORMAT_SSN', ...);
```

**Transformation Expression**:
```sql
REPLACE(TRIM(T_MEMBER.SSN), "-", "")
```

---

### Use Case 2: Concatenate Two Fields with Space

**Scenario**: Map `T_MEMBER.FIRST_NAME` + `T_MEMBER.LAST_NAME` → `slv_member.full_name`

**V2 Data**:

```sql
-- mapped_fields
INSERT INTO mapped_fields (semantic_field_id, tgt_table, tgt_column, concat_strategy, ...)
VALUES (789, 'slv_member', 'full_name', 'SPACE', ...);

-- mapping_details
INSERT INTO mapping_details (mapped_field_id, src_table, src_column, field_order, transformations, ...)
VALUES 
  (999, 'T_MEMBER', 'FIRST_NAME', 1, 'TRIM,INITCAP', ...),
  (999, 'T_MEMBER', 'LAST_NAME', 2, 'TRIM,INITCAP', ...);
```

**Transformation Expression**:
```sql
CONCAT(INITCAP(TRIM(T_MEMBER.FIRST_NAME)), ' ', INITCAP(TRIM(T_MEMBER.LAST_NAME)))
```

---

### Use Case 3: Multi-Table Join with Custom Concat

**Scenario**: Map `T_ADDRESS.STREET` + `T_ADDRESS.CITY` + `T_STATE.STATE_NAME` → `slv_member.full_address`

**V2 Data**:

```sql
-- mapped_fields
INSERT INTO mapped_fields (semantic_field_id, tgt_table, tgt_column, concat_strategy, concat_separator, ...)
VALUES (111, 'slv_member', 'full_address', 'CUSTOM', ', ', ...);

-- mapping_details
INSERT INTO mapping_details (mapped_field_id, src_table, src_column, field_order, transformations, ...)
VALUES 
  (222, 'T_ADDRESS', 'STREET', 1, 'TRIM,INITCAP', ...),
  (222, 'T_ADDRESS', 'CITY', 2, 'TRIM,UPPER', ...),
  (222, 'T_STATE', 'STATE_NAME', 3, 'UPPER', ...);
```

**Transformation Expression**:
```sql
CONCAT_WS(', ',
  INITCAP(TRIM(T_ADDRESS.STREET)),
  UPPER(TRIM(T_ADDRESS.CITY)),
  UPPER(T_STATE.STATE_NAME)
)
```

**Note**: Multi-table mapping requires join metadata (to be designed in UI)

---

## 📝 Data Quality Checks

Run these queries after migration to verify data integrity:

```sql
-- Check 1: All V1 semantic fields migrated
SELECT 
  COUNT(*) AS v1_count FROM main.source2target.semantic_table_v1_backup;
SELECT 
  COUNT(*) AS v2_count FROM main.source2target.semantic_fields;

-- Check 2: All V1 unmapped fields migrated
SELECT 
  COUNT(*) AS v1_unmapped FROM main.source2target.combined_fields_v1_backup WHERE tgt_table IS NULL;
SELECT 
  COUNT(*) AS v2_unmapped FROM main.source2target.unmapped_fields;

-- Check 3: All V1 mapped fields migrated
SELECT 
  COUNT(*) AS v1_mapped FROM main.source2target.combined_fields_v1_backup WHERE tgt_table IS NOT NULL;
SELECT 
  COUNT(*) AS v2_mapped FROM main.source2target.mapped_fields;
SELECT 
  COUNT(*) AS v2_details FROM main.source2target.mapping_details;

-- Check 4: No orphaned mapping_details
SELECT COUNT(*) AS orphan_count
FROM main.source2target.mapping_details md
LEFT JOIN main.source2target.mapped_fields mf ON md.mapped_field_id = mf.mapped_field_id
WHERE mf.mapped_field_id IS NULL;
-- Expected: 0

-- Check 5: All mapped_fields have at least one detail
SELECT COUNT(*) AS missing_details
FROM main.source2target.mapped_fields mf
LEFT JOIN main.source2target.mapping_details md ON mf.mapped_field_id = md.mapped_field_id
WHERE md.mapping_detail_id IS NULL;
-- Expected: 0
```

---

## 🎨 UI Changes Required

To support V2 schema, the frontend will need these enhancements:

### 1. **Multi-Field Selection**
- Allow selecting multiple source fields for a single target
- Show selected fields in a list with drag-and-drop reordering

### 2. **Concatenation Strategy Selector**
- Dropdown: NONE, SPACE, COMMA, PIPE, CONCAT, CUSTOM
- If CUSTOM: Show text input for separator

### 3. **Per-Field Transformation Picker**
- For each source field, show transformation dropdown
- Populate from `transformation_library` table
- Categories: TEXT, DATE, NUMERIC, CUSTOM
- Show preview of transformation expression

### 4. **Live Transformation Preview**
- As user selects fields/transformations, show:
  - Final transformation expression
  - Sample output (if data available)

### 5. **Feedback Capture Dialog**
- When accepting/rejecting AI suggestion:
  - Radio buttons: ACCEPTED, REJECTED, MODIFIED
  - Comments text area (required for REJECTED)
  - If MODIFIED: Show what changed

### 6. **Enhanced AI Suggestions Table**
- Add "Multi-Source" indicator if suggestion involves multiple fields
- Add "Transformation" column showing applied transformations
- Add feedback buttons: ✓ Accept | ✗ Reject | ✏️ Modify

### 7. **Mapping Details View**
- Expand mapped field row to show all source fields
- Show field order, transformations, confidence per field
- Allow editing order and transformations

---

## 🔄 Rollback Plan

If migration fails or V2 is not working as expected:

### Step 1: Restore V1 Tables

```sql
-- Drop V2 tables
DROP TABLE IF EXISTS main.source2target.semantic_fields;
DROP TABLE IF EXISTS main.source2target.unmapped_fields;
DROP TABLE IF EXISTS main.source2target.mapped_fields;
DROP TABLE IF EXISTS main.source2target.mapping_details;
DROP TABLE IF EXISTS main.source2target.mapping_feedback;
DROP TABLE IF EXISTS main.source2target.transformation_library;

-- Restore from backups
CREATE TABLE main.source2target.semantic_table AS 
SELECT * FROM main.source2target.semantic_table_v1_backup;

CREATE TABLE main.source2target.combined_fields AS 
SELECT * FROM main.source2target.combined_fields_v1_backup;
```

### Step 2: Restore Application Config

Revert `backend/config/default_config.json` to V1 table names.

### Step 3: Restore Code

```bash
cd /Users/david.galluzzo/source2target
tar -xzf ../source2target_backup_20251120_083849.tar.gz
```

---

## 📞 Support & Questions

If you encounter issues during migration:

1. **Check migration logs** in Databricks SQL history
2. **Run data quality checks** (see section above)
3. **Review V1 backup tables** to verify data wasn't lost
4. **Test with small dataset first** before full migration

---

## 📅 Migration Checklist

- [ ] Create full project backup (tar.gz) ✅
- [ ] Review V2 schema SQL (`migration_v2_schema.sql`)
- [ ] Run V2 schema creation in Databricks
- [ ] Verify all 6 tables created successfully
- [ ] Review data migration SQL (`migration_v2_data.sql`)
- [ ] Run data migration in Databricks
- [ ] Run all data quality checks (5 checks)
- [ ] Populate domain classification (manual or automated)
- [ ] Update vector search index configuration
- [ ] Update application config (`default_config.json`)
- [ ] Test AI suggestions with V2 schema
- [ ] Test manual mapping with single field
- [ ] Update frontend for multi-field support (separate epic)
- [ ] Test multi-field mapping in UI
- [ ] Test feedback capture in UI
- [ ] Document any custom transformations added
- [ ] Train users on new features
- [ ] Drop V1 tables (after validation period)
- [ ] Remove V1 backup tables (after 30-90 days)

---

## 🎉 Benefits of V2

1. **Flexibility**: Support complex mapping scenarios (many:1)
2. **Standardization**: Reusable transformation library
3. **Transparency**: Full transformation expressions visible
4. **Quality**: Confidence scoring and feedback for continuous improvement
5. **Domain-Aware**: Better AI recommendations based on domain context
6. **Auditability**: Complete trail of user decisions on AI suggestions
7. **Scalability**: Proper normalization for large-scale mappings
8. **Maintainability**: Clear separation of concerns across tables

---

*Migration Guide Version: 2.0*  
*Last Updated: November 20, 2024*  
*Author: AI Assistant (Claude)*

