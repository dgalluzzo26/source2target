# V2 Deployment Checklist

## 🚨 Current Issue: 500 Error on Semantic Fields

The 500 error you're seeing when accessing `/semantic-fields` is because **the V2 database tables haven't been created yet**.

---

## ✅ Step-by-Step Deployment

### 1. Create V2 Database Tables

Open **Databricks SQL Editor** and run these scripts in order:

#### Step 1a: Create Schema (Run First)
```sql
-- Run database/migration_v2_schema.sql
-- This creates 6 new tables:
-- - semantic_fields
-- - unmapped_fields  
-- - mapped_fields
-- - mapping_details
-- - mapping_feedback
-- - transformation_library
```

Copy and paste the **entire contents** of `database/migration_v2_schema.sql` into the SQL Editor and execute.

#### Step 1b: Migrate Data (Run Second)
```sql
-- Run database/migration_v2_data.sql
-- This migrates data from V1 tables to V2 tables
```

Copy and paste the **entire contents** of `database/migration_v2_data.sql` into the SQL Editor and execute.

### 2. Verify Tables Created

Run this query to verify all 6 tables exist:

```sql
SHOW TABLES IN oztest_dev.source2target;
```

You should see:
- ✅ `semantic_fields`
- ✅ `unmapped_fields`
- ✅ `mapped_fields`
- ✅ `mapping_details`
- ✅ `mapping_feedback`
- ✅ `transformation_library`

### 3. Verify Data Migration

Check that data was migrated successfully:

```sql
-- Check semantic fields (target fields)
SELECT COUNT(*) as semantic_fields_count
FROM oztest_dev.source2target.semantic_fields;

-- Check unmapped fields (source fields)
SELECT COUNT(*) as unmapped_fields_count
FROM oztest_dev.source2target.unmapped_fields;

-- Check mapped fields (existing mappings)
SELECT COUNT(*) as mapped_fields_count
FROM oztest_dev.source2target.mapped_fields;
```

### 4. Deploy Latest Code

Pull the latest changes from GitHub:

```bash
git pull origin main
```

Or in Databricks, redeploy the app with the latest code.

### 5. Test the Application

1. **Home Page** - Should load ✅
2. **Create Mappings** (`/unmapped-fields`) - Should show source fields ✅
3. **View Mappings** (`/mappings`) - Should show current mappings ✅
4. **Semantic Fields** (`/semantic-fields`) - Should work now ✅ (Admin only)
5. **Settings** (`/config`) - Should work ✅ (Admin only)

---

## 🔍 Troubleshooting

### Error: "Table does not exist"

**Symptom**: 500 error with message about table not existing

**Solution**: You haven't run the migration scripts yet. Go back to Step 1.

### Error: "Warehouse is STOPPED"

**Symptom**: Connection error about warehouse state

**Solution**: 
1. Go to Databricks SQL Warehouses
2. Find `gia-oztest-dev-data-warehouse`
3. Click "Start"
4. Wait for it to become `RUNNING`
5. Refresh your app

### Error: "Permission denied"

**Symptom**: Can't read/write tables

**Solution**:
1. Make sure your user has permissions on the `oztest_dev` catalog
2. Make sure your user has permissions on the `source2target` schema
3. Contact your Databricks admin if needed

### Semantic Fields View Shows Empty

**Symptom**: View loads but no fields shown

**Solution**: 
1. Check if data migration ran: `SELECT COUNT(*) FROM oztest_dev.source2target.semantic_fields;`
2. If count is 0, re-run `migration_v2_data.sql`
3. If you had data in the old schema, verify the V1 table names in the migration script

---

## 📊 What's New in V2

### For All Users
- **Create Mappings**: Multi-field mapping workflow with AI suggestions
- **View Mappings**: See all existing mappings in one place
- **Field Ordering**: Drag & drop to order fields in multi-field mappings
- **Concatenation**: Choose how to combine fields (space, comma, pipe, custom)
- **Transformations**: Apply TRIM, UPPER, LOWER, etc.

### For Admins
- **Semantic Fields Management**: CRUD operations for target field definitions
- **Vector Search Sync**: Auto-syncs index when fields change
- **Settings**: Configure database, vector search, and AI model

---

## 📁 File Locations

- **Migration Scripts**: `database/migration_v2_schema.sql`, `database/migration_v2_data.sql`
- **Configuration**: `app_config.json`
- **Documentation**: `V2_MIGRATION_GUIDE.md`, `V2_SCHEMA_DIAGRAM.md`

---

## 🆘 Need Help?

If you're still having issues after following these steps:

1. Check the Databricks app logs for detailed error messages
2. Verify your `app_config.json` has the correct table names
3. Ensure warehouse is running and you have permissions
4. Review `V2_MIGRATION_GUIDE.md` for more detailed information

---

## ✅ Success Indicators

You'll know V2 is working correctly when:

- ✅ All views load without 500 errors
- ✅ Semantic Fields view shows target fields (admin only)
- ✅ Unmapped Fields view shows source fields
- ✅ You can drag and reorder fields in the mapping wizard
- ✅ AI suggestions work and show reasoning
- ✅ You can save multi-field mappings

**Current Status**: Need to run migration scripts ⚠️

