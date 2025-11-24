# Database Column Names - Final Reference

## Complete Table Schemas

### 1. mapped_fields
```sql
CREATE TABLE mapped_fields (
  mapped_field_id BIGINT PRIMARY KEY,          -- ✅ PRIMARY KEY
  semantic_field_id BIGINT NOT NULL,
  tgt_table_name STRING NOT NULL,
  tgt_table_physical_name STRING NOT NULL,
  tgt_column_name STRING NOT NULL,
  tgt_column_physical_name STRING NOT NULL,
  concat_strategy STRING DEFAULT 'NONE',
  concat_separator STRING,
  transformation_expression STRING,
  confidence_score DOUBLE,
  mapping_source STRING DEFAULT 'MANUAL',
  ai_reasoning STRING,
  mapping_status STRING DEFAULT 'ACTIVE',
  mapped_by STRING,
  mapped_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_by STRING,
  updated_ts TIMESTAMP
)
```

### 2. mapping_details
```sql
CREATE TABLE mapping_details (
  mapping_detail_id BIGINT PRIMARY KEY,        -- ✅ PRIMARY KEY
  mapped_field_id BIGINT NOT NULL,             -- ✅ FOREIGN KEY to mapped_fields
  unmapped_field_id BIGINT,
  src_table_name STRING NOT NULL,
  src_column_name STRING NOT NULL,
  src_column_physical_name STRING NOT NULL,
  field_order INT NOT NULL,
  transformations STRING,                      -- ✅ Column name (plural)
  default_value STRING,
  field_confidence_score DOUBLE,
  created_by STRING,
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_by STRING,
  updated_ts TIMESTAMP
)
```

### 3. mapping_joins
```sql
CREATE TABLE mapping_joins (
  mapping_join_id BIGINT PRIMARY KEY,          -- ✅ PRIMARY KEY
  mapped_field_id BIGINT NOT NULL,             -- ✅ FOREIGN KEY to mapped_fields
  left_table_name STRING NOT NULL,
  left_table_physical_name STRING NOT NULL,
  left_join_column STRING NOT NULL,
  right_table_name STRING NOT NULL,
  right_table_physical_name STRING NOT NULL,
  right_join_column STRING NOT NULL,
  join_type STRING DEFAULT 'INNER',
  join_order INT NOT NULL,
  created_by STRING,
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_by STRING,
  updated_ts TIMESTAMP
)
```

---

## All Fixed Queries in _update_mapping_sync()

### ✅ Line 631: UPDATE mapped_fields
```sql
UPDATE {mapped_fields_table}
SET concat_strategy = '...', concat_separator = '...'
WHERE mapped_field_id = {mapping_id}  -- ✅ CORRECT
```

### ✅ Line 643: UPDATE mapping_details
```sql
UPDATE {mapping_details_table}
SET transformations = '{expr_escaped}'  -- ✅ CORRECT (database column)
WHERE mapping_detail_id = {detail_id}  -- ✅ CORRECT (primary key)
  AND mapped_field_id = {mapping_id}   -- ✅ CORRECT (foreign key)
```

### ✅ Line 653: DELETE FROM mapping_joins
```sql
DELETE FROM {mapping_joins_table}
WHERE mapped_field_id = {mapping_id}  -- ✅ CORRECT
```

### ✅ Lines 662-681: INSERT INTO mapping_joins
```sql
INSERT INTO {mapping_joins_table} (
    mapped_field_id,              -- ✅ CORRECT
    left_table_name,              -- ✅ CORRECT
    left_table_physical_name,     -- ✅ CORRECT
    left_join_column,             -- ✅ CORRECT
    right_table_name,             -- ✅ CORRECT
    right_table_physical_name,    -- ✅ CORRECT
    right_join_column,            -- ✅ CORRECT
    join_type,                    -- ✅ CORRECT
    join_order                    -- ✅ CORRECT
) VALUES (...)
```

---

## Column Name Mapping: Code vs Database

| Python Attribute | Database Column | Table | Notes |
|-----------------|-----------------|-------|-------|
| `mapping_id` | `mapped_field_id` | mapped_fields | ⚠️ Inconsistent naming |
| `detail_id` | `mapping_detail_id` | mapping_details | Aliased in SELECT |
| `transformation_expr` | `transformations` | mapping_details | Aliased in SELECT |
| `added_at` | `created_ts` | mapping_details | Aliased in SELECT |
| `mapped_at` | `mapped_ts` | mapped_fields | Aliased in SELECT |

---

## How Aliasing Works

### In SELECT Queries (Line 317):
```sql
SELECT 
  md.mapping_detail_id as detail_id,        -- ✅ Alias for Python
  md.transformations as transformation_expr, -- ✅ Alias for Python
  md.created_ts as added_at                 -- ✅ Alias for Python
FROM mapping_details md
```

### In INSERT/UPDATE/DELETE Queries:
```sql
-- Must use actual database column names
INSERT INTO mapping_details (..., transformations, ...) VALUES (...)
UPDATE mapping_details SET transformations = '...' WHERE mapping_detail_id = ...
DELETE FROM mapping_details WHERE mapping_detail_id = ...
```

---

## Final Status

### All Column Names Fixed ✅

1. ✅ `mapped_field_id` (not `mapping_id`) - Line 631, 643, 653
2. ✅ `mapping_detail_id` (not `detail_id`) - Line 643
3. ✅ `transformations` (not `transformation_expr`) - Line 642
4. ✅ `left_table_name` (not `left_table`) - Line 664
5. ✅ `left_join_column` (not `left_column`) - Line 666
6. ✅ `right_table_name` (not `right_table`) - Line 667
7. ✅ `right_join_column` (not `right_column`) - Line 669

### Verification Commands

```sql
-- Verify mapped_fields structure
DESCRIBE TABLE oztest_dev.source2target.mapped_fields;

-- Verify mapping_details structure
DESCRIBE TABLE oztest_dev.source2target.mapping_details;

-- Verify mapping_joins structure
DESCRIBE TABLE oztest_dev.source2target.mapping_joins;
```

---

**Date:** November 24, 2025  
**Final Fix:** All 7 column name mismatches resolved  
**Status:** ✅ COMPLETE - All database queries now use correct column names

