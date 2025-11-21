# V2 Database Column Reference

**CRITICAL:** All Pydantic models, services, and API code MUST use these exact column names.

---

## Table 1: semantic_fields
- **Primary Key:** `semantic_field_id` (BIGINT GENERATED ALWAYS AS IDENTITY)
- **Key Columns:**
  - `tgt_table_name` (STRING) - Logical name
  - `tgt_table_physical_name` (STRING) - Physical name
  - `tgt_column_name` (STRING) - Logical name
  - `tgt_column_physical_name` (STRING) - Physical name
  - `semantic_field` (STRING GENERATED) - Computed column
  - `created_ts` (TIMESTAMP) - Creation timestamp
  - `updated_ts` (TIMESTAMP) - Update timestamp

---

## Table 2: unmapped_fields
- **Primary Key:** `unmapped_field_id` (BIGINT GENERATED ALWAYS AS IDENTITY)
- **Key Columns:**
  - `src_table_name` (STRING) - Logical name
  - `src_table_physical_name` (STRING) - Physical name
  - `src_column_name` (STRING) - Logical name
  - `src_column_physical_name` (STRING) - Physical name
  - `src_physical_datatype` (STRING)
  - `src_nullable` (STRING) - 'YES' or 'NO'
  - `src_comments` (STRING)
  - `domain` (STRING)
  - `uploaded_by` (STRING)
  - `uploaded_ts` (TIMESTAMP)
  - `created_ts` (TIMESTAMP)
  - `updated_ts` (TIMESTAMP)

---

## Table 3: mapped_fields
- **Primary Key:** `mapped_field_id` (BIGINT GENERATED ALWAYS AS IDENTITY)
- **Foreign Keys:**
  - `semantic_field_id` → semantic_fields(semantic_field_id)
- **Key Columns:**
  - `tgt_table_name` (STRING) - Denormalized
  - `tgt_table_physical_name` (STRING) - Denormalized
  - `tgt_column_name` (STRING) - Denormalized
  - `tgt_column_physical_name` (STRING) - Denormalized
  - `concat_strategy` (STRING) - 'NONE', 'SPACE', 'COMMA', 'PIPE', 'CONCAT', 'CUSTOM'
  - `concat_separator` (STRING) - ⚠️ NOT custom_concat_value
  - `transformation_expression` (STRING) - ⚠️ NOT final_sql_expression
  - `confidence_score` (DOUBLE) - ⚠️ NOT mapping_confidence_score
  - `mapping_source` (STRING) - 'AI', 'MANUAL', 'BULK_UPLOAD', 'SYSTEM'
  - `ai_reasoning` (STRING)
  - `mapping_status` (STRING) - 'ACTIVE', 'INACTIVE', 'PENDING_REVIEW'
  - `mapped_by` (STRING)
  - `mapped_ts` (TIMESTAMP) - ⚠️ NOT mapped_at
  - `updated_ts` (TIMESTAMP)

---

## Table 4: mapping_details
- **Primary Key:** `mapping_detail_id` (BIGINT GENERATED ALWAYS AS IDENTITY)
- **Foreign Keys:**
  - `mapped_field_id` → mapped_fields(mapped_field_id)
  - `unmapped_field_id` → unmapped_fields(unmapped_field_id)
- **Key Columns:**
  - `src_table_name` (STRING) - Denormalized
  - `src_table_physical_name` (STRING) - Denormalized
  - `src_column_name` (STRING) - Denormalized
  - `src_column_physical_name` (STRING) - Denormalized
  - `field_order` (INT)
  - `transformation_expr` (STRING)
  - `created_ts` (TIMESTAMP) - ⚠️ NOT added_at
  - `updated_ts` (TIMESTAMP)

---

## Table 5: mapping_joins
- **Primary Key:** `mapping_join_id` (BIGINT GENERATED ALWAYS AS IDENTITY)
- **Foreign Keys:**
  - `mapped_field_id` → mapped_fields(mapped_field_id)
- **Key Columns:**
  - `left_table_name` (STRING)
  - `left_table_physical_name` (STRING)
  - `left_join_column` (STRING)
  - `right_table_name` (STRING)
  - `right_table_physical_name` (STRING)
  - `right_join_column` (STRING)
  - `join_type` (STRING) - 'INNER', 'LEFT', 'RIGHT', 'FULL'
  - `join_order` (INT)
  - `created_ts` (TIMESTAMP)
  - `updated_ts` (TIMESTAMP)

---

## Table 6: transformation_library
- **Primary Key:** `transformation_id` (BIGINT GENERATED ALWAYS AS IDENTITY) ⚠️ NOT transform_id
- **Key Columns:**
  - `transformation_name` (STRING)
  - `transformation_code` (STRING)
  - `transformation_expression` (STRING)
  - `transformation_description` (STRING)
  - `category` (STRING)
  - `is_system` (BOOLEAN)
  - `created_ts` (TIMESTAMP)
  - `updated_ts` (TIMESTAMP)

---

## Table 7: mapping_feedback
- **Primary Key:** `feedback_id` (BIGINT GENERATED ALWAYS AS IDENTITY)
- **Foreign Keys:**
  - `mapped_field_id` → mapped_fields(mapped_field_id)
- **Key Columns:**
  - `source_fields_json` (STRING) - JSON array
  - `suggested_tgt_table` (STRING)
  - `suggested_tgt_column` (STRING)
  - `search_score` (DOUBLE)
  - `ai_reasoning` (STRING)
  - `match_quality` (STRING)
  - `rank` (INT)
  - `feedback_action` (STRING) - 'accepted', 'rejected', 'modified'
  - `user_comment` (STRING)
  - `modified_src_table` (STRING)
  - `modified_src_column` (STRING)
  - `modified_transformations` (STRING)
  - `domain` (STRING)
  - `feedback_by` (STRING)
  - `feedback_ts` (TIMESTAMP)

---

## Common Patterns

### Timestamp Columns
- **Creation:** Always `created_ts` (NOT created_at)
- **Update:** Always `updated_ts` (NOT updated_at)
- **Exception:** `mapped_ts` in mapped_fields (NOT mapped_at)
- **Exception:** `uploaded_ts` in unmapped_fields
- **Exception:** `feedback_ts` in mapping_feedback

### ID Columns
- **Pattern:** `{table_name_singular}_id`
- **Examples:**
  - semantic_field_id
  - unmapped_field_id
  - mapped_field_id
  - mapping_detail_id
  - mapping_join_id
  - transformation_id (NOT transform_id)
  - feedback_id

### Logical vs Physical Names
- **Logical:** `{prefix}_table_name`, `{prefix}_column_name`
- **Physical:** `{prefix}_table_physical_name`, `{prefix}_column_physical_name`
- **Prefix:** `tgt_` for target, `src_` for source

---

## Frontend Compatibility

For backward compatibility, services may alias columns in SELECT queries:
```sql
-- Example
SELECT 
  mapped_field_id,          -- Return as-is
  mapped_ts as mapped_at,   -- Alias for frontend
  created_ts as added_at    -- Alias for frontend
```

This allows the frontend to use friendlier names while maintaining database accuracy.

