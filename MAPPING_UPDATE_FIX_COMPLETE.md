# Mapping Update Fix - Complete Resolution

## Problem

When attempting to update an existing mapping through the edit dialog, the API returned a **422 Unprocessable Entity** error, followed by database errors even after fixing the frontend.

---

## Root Causes

### Issue #1: Frontend Field Name Mismatch
**Location:** `frontend/src/views/MappingsListView.vue`

The frontend was sending join condition data with field names that didn't match the backend API's expected format.

**Frontend was sending:**
```javascript
{
  left_table: "...",
  left_column: "...",
  right_table: "...",
  right_column: "...",
  join_type: "..."
}
```

**Backend expected (MappingJoinCreateV2):**
```python
{
  left_table_name: str
  left_table_physical_name: str
  left_join_column: str
  right_table_name: str
  right_table_physical_name: str
  right_join_column: str
  join_type: str
  join_order: int
}
```

### Issue #2: Backend Database Column Name Mismatch
**Location:** `backend/services/mapping_service_v2.py`

The backend service's `_update_mapping_sync` method was using incorrect column names when working with the `mapping_joins` table.

**Wrong code in DELETE:**
```python
DELETE FROM {mapping_joins_table}
WHERE mapping_id = {mapping_id}  # ❌ WRONG - column doesn't exist
```

**Wrong code in INSERT:**
```python
INSERT INTO {mapping_joins_table} (
    mapping_id,        # ❌ WRONG
    left_table,        # ❌ WRONG
    left_column,       # ❌ WRONG
    right_table,       # ❌ WRONG
    right_column,      # ❌ WRONG
    join_type
)
```

**Actual database schema:**
```sql
CREATE TABLE mapping_joins (
  mapping_join_id BIGINT PRIMARY KEY,
  mapped_field_id BIGINT NOT NULL,      -- ✓ Correct FK name
  left_table_name STRING NOT NULL,       -- ✓ Correct column name
  left_table_physical_name STRING NOT NULL,
  left_join_column STRING NOT NULL,      -- ✓ Correct column name
  right_table_name STRING NOT NULL,      -- ✓ Correct column name
  right_table_physical_name STRING NOT NULL,
  right_join_column STRING NOT NULL,     -- ✓ Correct column name
  join_type STRING DEFAULT 'INNER',
  join_order INT NOT NULL
)
```

---

## Solutions Applied

### Fix #1: Frontend Data Mapping

**File:** `frontend/src/views/MappingsListView.vue`  
**Function:** `saveEditedMapping()`

**Before:**
```javascript
const updateRequest = {
  concat_strategy: editFormData.value.concat_strategy,
  concat_separator: editFormData.value.concat_strategy === 'CUSTOM' 
    ? editFormData.value.concat_separator : null,
  transformation_updates,
  mapping_joins: editFormData.value.joins.length > 0 
    ? editFormData.value.joins : []
}
```

**After:**
```javascript
// Map frontend join format to backend format
const mapping_joins = editFormData.value.joins.length > 0
  ? editFormData.value.joins.map((join: any, index: number) => ({
      left_table_name: join.left_table,
      left_table_physical_name: join.left_table,
      left_join_column: join.left_column,
      right_table_name: join.right_table,
      right_table_physical_name: join.right_table,
      right_join_column: join.right_column,
      join_type: join.join_type,
      join_order: index + 1
    }))
  : []

const updateRequest = {
  concat_strategy: editFormData.value.concat_strategy,
  concat_separator: editFormData.value.concat_strategy === 'CUSTOM' 
    ? editFormData.value.concat_separator : null,
  transformation_updates,
  mapping_joins
}
```

### Fix #2: Backend Database Queries

**File:** `backend/services/mapping_service_v2.py`  
**Function:** `_update_mapping_sync()`

**Before (DELETE):**
```python
DELETE FROM {mapping_joins_table}
WHERE mapping_id = {mapping_id}  # ❌ WRONG COLUMN NAME
```

**After (DELETE):**
```python
DELETE FROM {mapping_joins_table}
WHERE mapped_field_id = {mapping_id}  # ✅ CORRECT COLUMN NAME
```

**Before (INSERT):**
```python
INSERT INTO {mapping_joins_table} (
    mapping_id,
    left_table,
    left_column,
    right_table,
    right_column,
    join_type
) VALUES (
    {mapping_id},
    '{join.left_table.replace("'", "''")}',
    '{join.left_column.replace("'", "''")}',
    '{join.right_table.replace("'", "''")}',
    '{join.right_column.replace("'", "''")}',
    '{join.join_type}'
)
```

**After (INSERT):**
```python
INSERT INTO {mapping_joins_table} (
    mapped_field_id,
    left_table_name,
    left_table_physical_name,
    left_join_column,
    right_table_name,
    right_table_physical_name,
    right_join_column,
    join_type,
    join_order
) VALUES (
    {mapping_id},
    '{join.left_table_name.replace("'", "''")}',
    '{join.left_table_physical_name.replace("'", "''")}',
    '{join.left_join_column.replace("'", "''")}',
    '{join.right_table_name.replace("'", "''")}',
    '{join.right_table_physical_name.replace("'", "''")}',
    '{join.right_join_column.replace("'", "''")}',
    '{join.join_type}',
    {join.join_order}
)
```

---

## Key Changes Summary

### Frontend Changes
1. ✅ **Field Name Mapping**: Translate UI field names to API field names
2. ✅ **Added Physical Names**: Include physical table names (using logical for simplicity)
3. ✅ **Added Join Order**: Assign order based on array index (1-based)

### Backend Changes
1. ✅ **Fixed DELETE Query**: Use `mapped_field_id` instead of `mapping_id`
2. ✅ **Fixed INSERT Columns**: Use correct column names matching database schema
3. ✅ **Added Missing Columns**: Include `join_order` and physical table names

---

## Testing Checklist

After applying both fixes:

- [x] Edit an existing mapping
- [x] Modify transformations on source fields
- [x] Change concatenation strategy
- [x] Add join conditions
- [x] Edit existing join conditions
- [x] Delete join conditions
- [x] Save changes
- [x] Verify API call succeeds (200 OK instead of 422 or 500)
- [x] Confirm mapping updates persist in database
- [x] Verify joins are correctly saved

---

## Files Modified

### Backend
- `backend/services/mapping_service_v2.py` - Fixed database queries in `_update_mapping_sync()`

### Frontend
- `frontend/src/views/MappingsListView.vue` - Fixed join data mapping in `saveEditedMapping()`

### Documentation
- `MAPPING_UPDATE_FIX_COMPLETE.md` - This file (comprehensive fix documentation)

---

## Root Cause Analysis

### Why Did This Happen?

1. **Schema Evolution**: The `_update_mapping_sync` method was likely written before the database schema was finalized, or copied from an older version with different column names.

2. **Inconsistent Usage**: Other methods in the same service (`_create_mapping_sync` on line 194, `_delete_mapping_sync` on line 458) were using the CORRECT column names, but the update method wasn't.

3. **Missing Code Review**: The discrepancy between create/delete (correct) and update (incorrect) wasn't caught during code review.

### Lessons Learned

1. ✅ Always reference the actual database schema when writing SQL queries
2. ✅ Use consistent column names throughout the service
3. ✅ Test all CRUD operations (Create, Read, Update, Delete) thoroughly
4. ✅ Consider using an ORM to avoid SQL string formatting issues
5. ✅ Add integration tests for database operations

---

## Prevention Strategies

### Short-term
- [ ] Add unit tests for `_update_mapping_sync` method
- [ ] Add integration tests that verify actual database operations
- [ ] Document the correct column names in code comments

### Long-term
- [ ] Consider using SQLAlchemy or similar ORM
- [ ] Add database schema validation in CI/CD
- [ ] Create a schema documentation generator
- [ ] Implement automated schema-to-code verification

---

## Status

✅ **FULLY FIXED** - Mapping updates now work correctly with both frontend and backend fixes applied.

---

**Date:** November 24, 2025  
**Issue:** Unprocessable Entity (422) and database column errors on mapping update  
**Resolution:** Fixed frontend field mapping AND backend database queries  
**Impact:** Mapping editor now fully functional

