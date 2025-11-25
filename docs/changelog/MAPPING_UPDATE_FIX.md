# Mapping Update Fix - Unprocessable Entity Error

## Problem

When attempting to update an existing mapping through the edit dialog, the API returned a **422 Unprocessable Entity** error.

---

## Root Cause

**Field name mismatch** between frontend and backend for join conditions.

### Backend Expected (MappingJoinCreateV2):
```python
class MappingJoinCreateV2(BaseModel):
    left_table_name: str
    left_table_physical_name: str
    left_join_column: str
    right_table_name: str
    right_table_physical_name: str
    right_join_column: str
    join_type: str
    join_order: int
```

### Frontend Was Sending:
```javascript
{
  left_table: "...",
  left_column: "...",
  right_table: "...",
  right_column: "...",
  join_type: "..."
  // Missing: physical names, join_order
}
```

---

## Solution

Updated `frontend/src/views/MappingsListView.vue` in the `saveEditedMapping()` function to properly map the frontend join format to the backend expected format.

### Changes Made

**Before:**
```javascript
const updateRequest = {
  concat_strategy: editFormData.value.concat_strategy,
  concat_separator: editFormData.value.concat_strategy === 'CUSTOM' ? editFormData.value.concat_separator : null,
  transformation_updates,
  mapping_joins: editFormData.value.joins.length > 0 ? editFormData.value.joins : []
}
```

**After:**
```javascript
// Map frontend join format to backend format
const mapping_joins = editFormData.value.joins.length > 0
  ? editFormData.value.joins.map((join: any, index: number) => ({
      left_table_name: join.left_table,
      left_table_physical_name: join.left_table,  // Use logical name as physical
      left_join_column: join.left_column,
      right_table_name: join.right_table,
      right_table_physical_name: join.right_table,  // Use logical name as physical
      right_join_column: join.right_column,
      join_type: join.join_type,
      join_order: index + 1
    }))
  : []

const updateRequest = {
  concat_strategy: editFormData.value.concat_strategy,
  concat_separator: editFormData.value.concat_strategy === 'CUSTOM' ? editFormData.value.concat_separator : null,
  transformation_updates,
  mapping_joins
}
```

---

## Key Fixes

1. ✅ **Field Name Mapping**: 
   - `left_table` → `left_table_name`
   - `left_column` → `left_join_column`
   - `right_table` → `right_table_name`
   - `right_column` → `right_join_column`

2. ✅ **Added Physical Names**: 
   - `left_table_physical_name` (uses logical name for simplicity)
   - `right_table_physical_name` (uses logical name for simplicity)

3. ✅ **Added Join Order**: 
   - `join_order` set based on array index (1-based)

---

## Testing

After applying the fix and rebuilding the frontend:

1. ✅ Edit an existing mapping
2. ✅ Modify join conditions (add, edit, delete)
3. ✅ Save changes
4. ✅ Verify API call succeeds (200 OK instead of 422)
5. ✅ Confirm mapping updates persist

---

## Files Modified

- `frontend/src/views/MappingsListView.vue` - Fixed join data mapping in `saveEditedMapping()`
- `dist/` - Rebuilt frontend bundle

---

## Status

✅ **FIXED** - Mapping updates now work correctly with proper join data format.

---

**Date:** November 24, 2025  
**Issue:** Unprocessable Entity (422) on mapping update  
**Resolution:** Field name mapping in frontend

