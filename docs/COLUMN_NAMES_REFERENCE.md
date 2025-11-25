# Column Name Reference - Database vs Code

## Summary

The database uses `transformations` (plural) as the column name, but the Python code uses `transformation_expr` as the attribute name. This is handled via SQL aliasing in SELECT queries.

---

## mapping_details Table

### Database Schema (Actual Columns)
```sql
CREATE TABLE mapping_details (
  mapping_detail_id BIGINT PRIMARY KEY,
  mapped_field_id BIGINT NOT NULL,           -- ✅ Foreign key
  src_table_name STRING,
  src_column_name STRING,
  src_column_physical_name STRING,
  field_order INT,
  transformations STRING,                     -- ✅ Database column name (plural)
  default_value STRING,
  field_confidence_score DOUBLE,
  created_by STRING,
  created_ts TIMESTAMP,
  updated_by STRING,
  updated_ts TIMESTAMP
)
```

### Python Model (Pydantic/Code)
```python
class MappingDetailV2(BaseModel):
    detail_id: int
    mapping_id: int                            # ⚠️ Should be mapped_field_id
    src_table_name: str
    src_column_name: str
    src_column_physical_name: str
    field_order: int
    transformation_expr: Optional[str]         # ✅ Code attribute name
    added_at: Optional[datetime]
```

---

## How It Works

### SELECT Queries (Reading Data)
**Line 317 in mapping_service_v2.py:**
```sql
md.transformations as transformation_expr
```
✅ This aliases the database column `transformations` to `transformation_expr` for Python code.

### INSERT Queries (Writing Data)
**Line 175 in mapping_service_v2.py:**
```sql
INSERT INTO mapping_details (..., transformations) VALUES (...)
```
✅ Uses database column name `transformations`.

**Line 182:**
```python
detail.transformation_expr  # Python attribute
```
✅ Reads from Python model's `transformation_expr` attribute and inserts into database's `transformations` column.

### UPDATE Queries (Modifying Data)
**Line 642 in mapping_service_v2.py (JUST FIXED):**
```sql
UPDATE mapping_details
SET transformations = '{expr_escaped}'
WHERE detail_id = {detail_id} AND mapped_field_id = {mapping_id}
```
✅ Now correctly uses database column name `transformations`.

---

## All Fixes Applied

| Line | Query Type | What Was Fixed | Old | New |
|------|------------|----------------|-----|-----|
| 642 | UPDATE | Column name | `transformation_expr` | `transformations` ✅ |
| 631 | UPDATE | WHERE clause | `mapping_id` | `mapped_field_id` ✅ |
| 643 | UPDATE | WHERE clause | `mapping_id` | `mapped_field_id` ✅ |
| 653 | DELETE | WHERE clause | `mapping_id` | `mapped_field_id` ✅ |
| 663-671 | INSERT | Column names | Wrong names | Correct names ✅ |
| 684 | Log | Attribute names | Wrong attrs | Correct attrs ✅ |

---

## Key Takeaways

1. **Database Column**: `transformations` (plural)
2. **Python Attribute**: `transformation_expr` (singular)
3. **SELECT Queries**: Use aliasing: `transformations as transformation_expr`
4. **INSERT/UPDATE Queries**: Use database column name: `transformations`
5. **Python Code**: Use attribute name: `transformation_expr`

---

## Other Table Column Names

### mapped_fields Table
- **Primary Key**: `mapped_field_id` (NOT `mapping_id`)
- Transformation column: `transformation_expression` (full expression)

### mapping_details Table  
- **Primary Key**: `mapping_detail_id` (aliased as `detail_id`)
- **Foreign Key**: `mapped_field_id` (NOT `mapping_id`)
- Transformation column: `transformations` (aliased as `transformation_expr`)

### mapping_joins Table
- **Primary Key**: `mapping_join_id`
- **Foreign Key**: `mapped_field_id` (NOT `mapping_id`)
- Join columns: `left_table_name`, `left_join_column`, etc.

---

## Status

✅ **ALL COLUMN NAMES NOW CORRECT**

The UPDATE query on line 642 now uses the correct database column name `transformations`.

---

**Date:** November 24, 2025  
**Issue:** Column `transformation_expr` could not be resolved  
**Resolution:** Changed UPDATE query to use `transformations` (database column name)

