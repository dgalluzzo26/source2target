# Delete Unmapped Field - Column Name Fix

**Date:** December 1, 2025  
**Issue:** Delete unmapped field operation fails with column not found error  
**Root Cause:** DELETE query used wrong column name (`id` instead of `unmapped_field_id`)

---

## Problem Description

### Error
When users tried to delete an unmapped field via the UI or API:
```
Error: Column 'id' not found in table unmapped_fields
```

### Root Cause
The DELETE query in `unmapped_fields_service.py` used:
```sql
DELETE FROM unmapped_fields WHERE id = {field_id}
```

But the actual database column name is `unmapped_field_id`, not `id`.

### Why the Confusion?
The SELECT query aliased the column for convenience:
```sql
SELECT unmapped_field_id as id, ...
FROM unmapped_fields
```

This alias works for reading data (and populating the Pydantic model), but DELETE operations must use the **actual column name** from the database schema.

---

## Solution

### Fixed DELETE Query
Changed from:
```sql
DELETE FROM unmapped_fields WHERE id = {field_id}
```

To:
```sql
DELETE FROM unmapped_fields WHERE unmapped_field_id = {field_id}
```

### Additional Improvements
1. **Row count validation** - Check if any rows were deleted
2. **Better error handling** - Raise ValueError if field not found
3. **Consistent logging** - Confirm successful deletion

---

## Database Schema Reference

### Unmapped Fields Table
From `database/V2_COLUMN_REFERENCE.md`:

```
Table: unmapped_fields
- Primary Key: unmapped_field_id (BIGINT GENERATED ALWAYS AS IDENTITY)
- Columns:
  - unmapped_field_id (PK)
  - src_table_name
  - src_table_physical_name
  - src_column_name
  - src_column_physical_name
  - src_physical_datatype
  - src_nullable
  - src_comments
  - domain
  - uploaded_by
  - uploaded_ts
  - created_ts
  - updated_ts
```

### Pydantic Model Mapping
The `UnmappedFieldV2` Pydantic model uses `id` as the field name:

```python
class UnmappedFieldV2(BaseModel):
    id: Optional[int]  # Maps to unmapped_field_id in database
    src_table_name: str
    # ... other fields
```

This is populated via the SQL alias:
```sql
SELECT unmapped_field_id as id, ...
```

---

## Files Changed

### Backend Service
- **File:** `backend/services/unmapped_fields_service.py`
- **Function:** `_delete_unmapped_field_sync()`
- **Line:** 275

**Before:**
```python
query = f"DELETE FROM {unmapped_fields_table} WHERE id = {field_id}"
cursor.execute(query)
connection.commit()

print(f"[Unmapped Fields Service] Unmapped field deleted successfully")
return {"status": "success", "message": f"Deleted unmapped field ID {field_id}"}
```

**After:**
```python
query = f"DELETE FROM {unmapped_fields_table} WHERE unmapped_field_id = {field_id}"
cursor.execute(query)
rows_deleted = cursor.rowcount
connection.commit()

if rows_deleted == 0:
    raise ValueError(f"Unmapped field ID {field_id} not found")

print(f"[Unmapped Fields Service] Unmapped field deleted successfully")
return {"status": "success", "message": f"Deleted unmapped field ID {field_id}"}
```

---

## Testing Scenarios

### Test Case 1: Delete Existing Unmapped Field
**Setup:**
1. Upload source fields to create unmapped records
2. Verify fields appear in unmapped fields list

**Action:**
- Click delete button on an unmapped field in the UI
- Or call DELETE `/api/v2/unmapped-fields/{field_id}`

**Expected Result:**
- ✅ Field deleted successfully
- ✅ Field removed from unmapped fields list
- ✅ API returns: `{"status": "success", "message": "Deleted unmapped field ID {id}"}`

---

### Test Case 2: Delete Non-Existent Field
**Action:**
- Call DELETE `/api/v2/unmapped-fields/99999` (non-existent ID)

**Expected Result:**
- ❌ Error raised: `ValueError: Unmapped field ID 99999 not found`
- ❌ HTTP 500 error response
- ❌ No database changes

---

### Test Case 3: Delete After Bulk Upload
**Setup:**
1. Bulk upload source fields via CSV
2. Verify all fields appear in unmapped list

**Action:**
- Delete one or more unmapped fields

**Expected Result:**
- ✅ Selected fields deleted
- ✅ Remaining fields still visible
- ✅ Total count decreases appropriately

---

## Related Issues

**Related Column Name Consistency:**
- All V2 tables use `{table_name}_id` pattern for primary keys:
  - `unmapped_fields` → `unmapped_field_id`
  - `mapped_fields` → `mapped_field_id`
  - `mapping_details` → `mapping_detail_id`
  - `mapping_joins` → `mapping_join_id`
  - `semantic_fields` → `semantic_field_id`
  - `mapping_feedback` → `feedback_id`

**Pydantic Model Aliasing:**
- Models use shorter `id` field name for convenience
- SQL queries must use actual database column names
- SELECT can alias: `SELECT unmapped_field_id as id`
- DELETE/UPDATE/INSERT must use actual names

---

## Developer Notes

### Best Practice: Always Use Actual Column Names
When writing DML statements (DELETE, UPDATE, INSERT), always use the actual database column names, not aliases.

❌ **Wrong:**
```sql
DELETE FROM unmapped_fields WHERE id = ?
```

✅ **Correct:**
```sql
DELETE FROM unmapped_fields WHERE unmapped_field_id = ?
```

### When Aliases Are OK
Aliases are fine for SELECT queries and Pydantic mapping:

```sql
SELECT unmapped_field_id as id,  -- OK for reading
       src_table_name,
       src_column_name
FROM unmapped_fields
```

---

## Impact

### Before Fix
❌ **User Experience:**
- Delete button in UI throws error
- Error message: "Column 'id' not found"
- No way to remove unwanted unmapped fields
- Confusing error for users

### After Fix
✅ **User Experience:**
- Delete button works correctly
- Fields removed from list immediately
- Clear success message
- Better error handling for invalid IDs

---

## See Also

- `database/V2_COLUMN_REFERENCE.md` - Complete column reference
- `database/V2_SCHEMA_DIAGRAM.md` - Database schema diagram
- `backend/models/mapping_v2.py` - Pydantic models
- `docs/changelog/DELETE_MAPPING_RESTORE_FIX.md` - Related delete mapping fix

