# Target Field Descriptions in AI Suggestions

## Summary

The AI Suggestions dialog is **correctly configured** to show target field descriptions, but the `tgt_comments` column in your `semantic_fields` table is likely empty/null.

## ✅ What's Already Working

1. **Backend**: Fetches `tgt_comments` from `semantic_fields` table (line 269 in `ai_mapping_service_v2.py`)
2. **Frontend Interface**: `AISuggestionV2` includes `tgt_comments?: string` 
3. **Frontend Display**: Shows target descriptions in the results table with an info icon

## ❌ The Problem

The `tgt_comments` column in your database is likely NULL or empty, so the conditional `v-if="data.tgt_comments"` hides the description div.

## 🔧 How to Fix

### Step 1: Check Current Status

Run the SQL script I created: `populate_tgt_comments.sql`

The first two queries will show you how many of your semantic fields have comments vs NULL/empty.

### Step 2: Populate Descriptions

**Option A: Via UI (Recommended)**
- Go to "Semantic Management" in the sidebar
- Edit each semantic field
- Fill in the "Comments/Description" field
- Save - this will automatically sync the vector search index

**Option B: Via SQL (Bulk Update)**
Use the UPDATE statements in `populate_tgt_comments.sql` as a template:

```sql
UPDATE oztest_dev.source2target.semantic_fields
SET tgt_comments = 'Unique identifier for the member record',
    updated_ts = CURRENT_TIMESTAMP()
WHERE tgt_table_name = 'T_MEMBER' AND tgt_column_name = 'MEMBER_ID';
```

**Note**: If you update via SQL, you'll need to manually sync the vector search index via the Databricks API, since the automatic sync only happens when editing through the UI.

### Step 3: Verify

After populating descriptions:
1. Refresh your browser
2. Use "Generate AI Suggestions"
3. You should now see the target field description under each suggested target field:

```
T_MEMBER.MEMBER_ID
MEMBER_ID
ℹ️ Unique identifier for the member record
```

## 📋 What Should Be in tgt_comments?

Good descriptions should:
- Explain what the field contains
- Mention any important constraints or formats
- Include business context if relevant

**Examples**:
- ✅ "Unique identifier for the member record"
- ✅ "First name of the member as it appears on official documents"
- ✅ "Date of birth in YYYY-MM-DD format"
- ✅ "Claim amount in USD, excluding tax"
- ❌ "ID" (too vague)
- ❌ "Name" (too vague)

## 🔍 Debugging

If descriptions still don't show after populating:

1. **Check browser console** for JavaScript errors
2. **Check network tab** - look at the response from `/api/v2/ai-mapping/suggestions` and verify `tgt_comments` is included
3. **Clear browser cache** and rebuild frontend
4. **Verify database** - run the check query from `populate_tgt_comments.sql`

## Files Modified for This Feature

- `backend/services/ai_mapping_service_v2.py` - Line 269: Fetches `tgt_comments`
- `frontend/src/stores/aiSuggestionsStoreV2.ts` - Added `tgt_comments?: string` to interface
- `frontend/src/components/AISuggestionsDialog.vue` - Lines 81-84: Displays description with icon

