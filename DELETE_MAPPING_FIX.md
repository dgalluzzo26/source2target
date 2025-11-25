# Delete Mapping Fix Summary

## Issue Reported
User reported that deleting a mapping failed with error: "could not find src_table_physical_name"

User correctly identified that delete operations should **only require the primary key (PK)**, not field data like `src_table_physical_name`.

## Root Cause

### Problem 1: Unnecessary Query in Delete Method
The `_delete_mapping_sync` method was querying for source field details before deleting:

```python
# Step 1: Get source fields before deleting
get_details = f"""
SELECT 
    src_table_name,
    src_table_physical_name,  # ← Not needed!
    src_column_name,
    src_column_physical_name
FROM {mapping_details_table}
WHERE mapped_field_id = {mapped_field_id}
"""

cursor.execute(get_details)
source_fields = cursor.fetchall()
```

**Issues:**
- ❌ Fetched `src_table_physical_name` and other fields unnecessarily
- ❌ These fields were only used to count source fields for success message
- ❌ No actual business logic needed this data
- ❌ Added extra database query and potential failure point

### Problem 2: Wrong Column Name in Update Method
The update method was using `transformations` instead of `transformation_expr`:

```python
UPDATE {mapping_details_table}
SET transformations = '{expr_escaped}'  # ← WRONG!
```

**Correct column name:** `transformation_expr` (per V2_COLUMN_REFERENCE.md line 71)

## Fixes Applied

### Fix 1: Simplified Delete Method

**Before:**
```python
# Step 1: Get source fields before deleting
get_details = f"""
SELECT 
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name
FROM {mapping_details_table}
WHERE mapped_field_id = {mapped_field_id}
"""

cursor.execute(get_details)
source_fields = cursor.fetchall()

# Step 2: Delete from mapping_joins
delete_joins = f"DELETE FROM {mapping_joins_table} WHERE mapped_field_id = {mapped_field_id}"
cursor.execute(delete_joins)

# Step 3: Delete from mapping_details
delete_details = f"DELETE FROM {mapping_details_table} WHERE mapped_field_id = {mapped_field_id}"
cursor.execute(delete_details)

# Step 4: Delete from mapped_fields
delete_mapped = f"DELETE FROM {mapped_fields_table} WHERE mapped_field_id = {mapped_field_id}"
cursor.execute(delete_mapped)

return {
    "status": "success",
    "message": f"Deleted mapping ID {mapped_field_id} with {len(source_fields)} source fields"
}
```

**After (Simplified):**
```python
# Step 1: Delete from mapping_joins (if any)
delete_joins = f"DELETE FROM {mapping_joins_table} WHERE mapped_field_id = {mapped_field_id}"
cursor.execute(delete_joins)
joins_deleted = cursor.rowcount

# Step 2: Delete from mapping_details
delete_details = f"DELETE FROM {mapping_details_table} WHERE mapped_field_id = {mapped_field_id}"
cursor.execute(delete_details)
details_deleted = cursor.rowcount

# Step 3: Delete from mapped_fields
delete_mapped = f"DELETE FROM {mapped_fields_table} WHERE mapped_field_id = {mapped_field_id}"
cursor.execute(delete_mapped)
mapped_deleted = cursor.rowcount

if mapped_deleted == 0:
    raise ValueError(f"Mapping ID {mapped_field_id} not found")

return {
    "status": "success",
    "message": f"Deleted mapping ID {mapped_field_id} ({details_deleted} source fields, {joins_deleted} joins)"
}
```

**Benefits:**
- ✅ No unnecessary SELECT query
- ✅ Only uses the PK (mapped_field_id) as it should
- ✅ Uses `cursor.rowcount` to get number of deleted records
- ✅ Validates that mapping exists (mapped_deleted == 0 check)
- ✅ Cleaner, more efficient code
- ✅ Eliminates potential column mismatch errors

### Fix 2: Corrected Column Name in Update Method

**Before:**
```python
UPDATE {mapping_details_table}
SET transformations = '{expr_escaped}'
WHERE mapping_detail_id = {detail_id}
```

**After:**
```python
UPDATE {mapping_details_table}
SET transformation_expr = '{expr_escaped}'
WHERE mapping_detail_id = {detail_id}
```

## Database Schema Reference

Per `V2_COLUMN_REFERENCE.md`:

### mapping_details table columns:
- `mapping_detail_id` (PK)
- `mapped_field_id` (FK)
- `unmapped_field_id` (FK)
- `src_table_name`
- `src_table_physical_name`
- `src_column_name`
- `src_column_physical_name`
- `field_order`
- **`transformation_expr`** ← Correct column name (NOT `transformations`)

## Delete Operation Flow

### Proper Cascade Order:
1. **Delete from `mapping_joins`** (child table with FK to mapped_field_id)
2. **Delete from `mapping_details`** (child table with FK to mapped_field_id)
3. **Delete from `mapped_fields`** (parent table with PK mapped_field_id)

### Why This Order:
- Foreign key constraints require child records be deleted before parent
- `mapping_joins` and `mapping_details` both reference `mapped_fields.mapped_field_id`
- Must delete joins and details first, then the main mapping record

## API Endpoint

**DELETE** `/api/v2/mappings/{mapping_id}`

**Request:**
```
DELETE /api/v2/mappings/123
```

**Required:** Only the `mapping_id` path parameter (which is the `mapped_field_id` PK)

**Response:**
```json
{
  "status": "success",
  "message": "Deleted mapping ID 123 (2 source fields, 0 joins)"
}
```

## Files Modified

1. **`backend/services/mapping_service_v2.py`**
   - Simplified `_delete_mapping_sync` method
   - Removed unnecessary SELECT query
   - Fixed column name from `transformations` to `transformation_expr`
   - Added `cursor.rowcount` to track deleted records
   - Added validation for mapping existence

## Testing

Test the delete functionality:

```bash
# Delete a mapping (only needs mapping_id)
DELETE /api/v2/mappings/123
```

Expected behavior:
- ✅ Deletes mapping using only the PK
- ✅ No error about `src_table_physical_name`
- ✅ Properly cascades to mapping_joins and mapping_details
- ✅ Returns count of deleted source fields and joins
- ✅ Returns 404 if mapping_id doesn't exist

## Benefits of This Fix

1. **Correctness**: Only uses PKs/FKs for deletion (proper database design)
2. **Performance**: One fewer SELECT query
3. **Reliability**: No risk of column mismatch errors
4. **Clarity**: Code clearly shows cascade delete pattern
5. **Validation**: Checks if mapping exists and reports appropriately
6. **Consistency**: Matches standard REST DELETE patterns

## User's Observation

The user's instinct was 100% correct:

> "if we are deleting an existing mapping it should only need the PKs/FKs to delete why is it looking for that field"

**Answer:** It shouldn't have been! The original code had unnecessary logic that queried field data just to count records. This has been removed. Delete operations now correctly use only the primary key as they should.

