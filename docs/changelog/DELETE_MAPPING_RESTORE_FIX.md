# Delete Mapping - Restore to Unmapped Fields Fix

**Date:** December 1, 2025  
**Issue:** When users delete a mapped field, the source column(s) were permanently removed without being restored to the unmapped fields table.  
**Impact:** Users lost track of source fields after deleting mappings, requiring re-upload of source columns.

---

## Problem Description

### Original Behavior
When a user deleted a field mapping:
1. ✅ Deleted from `mapping_joins` (join conditions)
2. ✅ Deleted from `mapping_details` (source field details)
3. ✅ Deleted from `mapped_fields` (main mapping record)
4. ❌ **SOURCE FIELDS LOST** - Not restored to `unmapped_fields`

### Expected Behavior
When a user deletes a field mapping:
1. ✅ Delete from `mapping_joins`
2. ✅ Delete from `mapping_details`
3. ✅ Delete from `mapped_fields`
4. ✅ **RESTORE to `unmapped_fields`** - Make source fields available for remapping

---

## Solution

### Implementation
Modified `MappingServiceV2._delete_mapping_sync()` to:

1. **Query source fields before deletion**
   ```sql
   SELECT src_table_name, src_table_physical_name,
          src_column_name, src_column_physical_name
   FROM mapping_details
   WHERE mapped_field_id = {mapping_id}
   ```

2. **Delete mapping records** (existing logic)
   - Delete from mapping_joins
   - Delete from mapping_details
   - Delete from mapped_fields

3. **Restore to unmapped_fields**
   ```sql
   INSERT INTO unmapped_fields (
       src_table_name,
       src_table_physical_name,
       src_column_name,
       src_column_physical_name,
       src_nullable,
       src_physical_datatype,
       src_comments,
       domain,
       uploaded_by
   ) VALUES (...)
   ```

4. **Prevent duplicates**
   - Check if field already exists in `unmapped_fields` before inserting
   - Skip if already present (e.g., field was part of another active mapping)

### Data Completeness
**Note:** Some metadata is marked as 'UNKNOWN' when restored because `mapping_details` doesn't store all original field metadata:

| Field | Restored Value | Source |
|-------|---------------|--------|
| `src_table_name` | ✅ Original | From mapping_details |
| `src_table_physical_name` | ⚠️ Same as logical | Not stored in mapping_details |
| `src_column_name` | ✅ Original | From mapping_details |
| `src_column_physical_name` | ✅ Original | From mapping_details |
| `src_nullable` | ⚠️ 'UNKNOWN' | Not stored in mapping_details |
| `src_physical_datatype` | ⚠️ 'UNKNOWN' | Not stored in mapping_details |
| `src_comments` | ⚠️ 'Restored from deleted mapping' | Not stored in mapping_details |
| `domain` | ⚠️ NULL | Not stored in mapping_details |
| `uploaded_by` | ⚠️ 'system' | Original user not tracked |

**Limitation:** `mapping_details` table does not store `src_table_physical_name`, only the logical `src_table_name`. When restoring, we use the logical name for both fields. This works for most cases but may cause issues if logical and physical table names differ significantly.

**Future Enhancement:** Consider storing `src_table_physical_name` in `mapping_details` schema or using the `unmapped_field_id` FK to query the original unmapped_fields record for complete metadata preservation.

---

## Files Changed

### Backend Service
- **File:** `backend/services/mapping_service_v2.py`
- **Function:** `_delete_mapping_sync()`
- **Changes:**
  - Added step to query source fields before deletion
  - Added step to restore fields to unmapped_fields after deletion
  - Added duplicate checking to prevent re-adding existing fields
  - Updated return message to include restored count

---

## Testing Scenarios

### Test Case 1: Delete Single-Field Mapping
**Setup:**
1. Map source field `src_table.column_a` → target field `tgt_table.field_x`
2. Verify field removed from unmapped_fields

**Action:**
- Delete the mapping via DELETE `/api/v2/mappings/{mapping_id}`

**Expected Result:**
- ✅ Mapping deleted from mapped_fields
- ✅ Source field deleted from mapping_details
- ✅ `src_table.column_a` restored to unmapped_fields
- ✅ Field appears in unmapped fields list for remapping

---

### Test Case 2: Delete Multi-Field Mapping
**Setup:**
1. Map multiple source fields → single target field:
   - `src_table.first_name` + `src_table.last_name` → `tgt_table.full_name`
2. Verify both fields removed from unmapped_fields

**Action:**
- Delete the mapping

**Expected Result:**
- ✅ Both source fields restored to unmapped_fields
- ✅ Both fields available for remapping
- ✅ Message shows: "2 fields restored to unmapped"

---

### Test Case 3: Delete Mapping with Join Conditions
**Setup:**
1. Map fields with join condition:
   - `table1.id` + `table2.name` (joined on table1.id = table2.id) → `target.field`
2. Delete the mapping

**Expected Result:**
- ✅ Join conditions deleted from mapping_joins
- ✅ Both source fields restored to unmapped_fields
- ✅ Both fields available for remapping

---

### Test Case 4: Duplicate Prevention
**Setup:**
1. Map `src_table.column_a` → `tgt_table.field_x`
2. Also map `src_table.column_a` → `tgt_table.field_y` (same source, different target)
3. Delete the first mapping

**Expected Result:**
- ✅ First mapping deleted
- ✅ `src_table.column_a` NOT restored (already in use by second mapping)
- ✅ No duplicate entries in unmapped_fields

---

## User Impact

### Before Fix
❌ **Problem:** User deletes a mapping and loses track of source columns
- Source fields disappear from unmapped list
- User must remember which fields were mapped
- May require re-uploading source metadata

### After Fix
✅ **Solution:** User deletes a mapping and can immediately remap the field
- Source fields automatically return to unmapped list
- No data loss - can remap immediately
- Workflow is more forgiving and intuitive

---

## API Response Changes

### Before
```json
{
  "status": "success",
  "message": "Deleted mapping ID 123 (2 source fields, 1 joins)"
}
```

### After
```json
{
  "status": "success",
  "message": "Deleted mapping ID 123 (2 source fields deleted, 2 restored to unmapped)"
}
```

---

## Related Issues

**Related to:**
- Data consistency in V2 multi-field mapping
- User workflow for mapping iterations
- Unmapped fields management

**See Also:**
- `docs/architecture/V2_MULTI_FIELD_VECTOR_SEARCH.md` - V2 architecture
- `docs/implementation/V2_BACKEND_COMPLETE.md` - V2 backend details
- `database/V2_SCHEMA_DIAGRAM.md` - Database schema

---

## Future Enhancements

1. **Preserve Full Metadata**
   - Store additional metadata in mapping_details during creation
   - Or maintain a reference to original unmapped_field_id
   - Restore complete metadata (nullable, datatype, comments, domain) on delete

2. **Bulk Delete**
   - Support deleting multiple mappings at once
   - Efficiently restore all source fields in a single transaction

3. **Soft Delete**
   - Archive deleted mappings instead of hard delete
   - Allow users to "undo" accidental deletions
   - Maintain mapping history for auditing

4. **User Notification**
   - Show toast notification: "2 fields restored to unmapped"
   - Optionally highlight restored fields in UI

