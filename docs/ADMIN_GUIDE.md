# Source-to-Target Mapping Platform - Administrator Guide

## Table of Contents
1. [Administrator Overview](#administrator-overview)
2. [Navigation Structure](#navigation-structure)
3. [User Management](#user-management)
4. [Settings Configuration](#settings-configuration)
5. [Semantic Management](#semantic-management)
6. [Transformation Management](#transformation-management)
7. [Vector Search Sync](#vector-search-sync)
8. [Mapping Management](#mapping-management)
9. [System Monitoring](#system-monitoring)
10. [Database Schema V2](#database-schema-v2)
11. [Troubleshooting](#troubleshooting)
12. [Maintenance](#maintenance)
13. [Security](#security)

---

## Administrator Overview

As an administrator, you have full access to all features and are responsible for:
- Managing user access and permissions
- Configuring system settings (database, AI, vector search)
- Maintaining semantic field definitions
- Managing the transformation library
- Monitoring system health and vector search sync
- Supporting users and troubleshooting issues

### Admin Identification
Admins are identified by:
- Green **"Admin"** badge in the header (top-right)
- Access to **Administration** section in sidebar
- Membership in the configured admin group

### Version 2.0 Features
- **Multi-Field Mapping**: Map multiple source fields to one target
- **Transformation Library**: Reusable SQL transformation templates
- **Mapping Editor**: Edit transformations and joins without recreating
- **Vector Search Auto-Sync**: Automatic index updates
- **Export Mappings**: Download complete mapping details as CSV

---

## Navigation Structure

The application uses a left sidebar with two main sections:

### 📊 Mapping Workflow (All Users)
```
🏠 Home                - System status dashboard
➕ Create Mappings     - Map source fields to targets
📋 View Mappings       - Review and manage mappings
```

### 🔧 Administration (Admins Only)
```
💾 Semantic Management       - Manage target field definitions
🛡️  Transformation Management - Transformation library management
⚙️  Settings                 - System configuration
```

---

## User Management

### Admin Group Configuration

#### Setting Up Admin Access

1. **Navigate to Settings**:
   - Click **"Settings"** (⚙️ icon) in the sidebar
   - Go to **"Security"** or **"Admin Group"** section

2. **Configure Admin Group**:
   - **Admin Group Name**: Enter your Databricks workspace group name
     - Example: `source2target_admins`
     - Example: `data_platform_admins`
   - Click **"Save Configuration"**

3. **Verify Admin Access**:
   - Users in this group will see "Admin" badge
   - They'll have access to Administration section
   - Group membership checked via Databricks Workspace API

#### Best Practices
- ✅ Use a dedicated admin group (e.g., "source2target_admins")
- ✅ Limit admin access to 3-5 trusted users
- ✅ Review group membership monthly in Databricks
- ✅ Document who has admin access in your runbook
- ✅ Use consistent naming conventions for admin groups

### User Permissions Matrix

| Permission | Admin | Regular User |
|------------|-------|--------------|
| View Home Page | ✅ | ✅ |
| Create Mappings | ✅ | ✅ |
| View Own Mappings | ✅ | ✅ |
| Edit Mappings | ✅ | ✅ |
| Delete Mappings | ✅ | ✅ |
| Export Mappings | ✅ | ✅ |
| AI Suggestions | ✅ | ✅ |
| Manual Search | ✅ | ✅ |
| **View All Mappings** | ✅ | ❌ |
| **Semantic Management** | ✅ | ❌ |
| **Transformation Management** | ✅ | ❌ |
| **Settings** | ✅ | ❌ |

### Data Visibility
- **Regular Users**: See only mappings they created (filtered by `mapped_by` email)
- **Admins**: See all mappings from all users (no filter)
- **Audit Trail**: All actions tracked in database with user email and timestamp

---

## Settings Configuration

Access Settings by clicking **"Settings"** (⚙️) in the sidebar.

### Database Configuration

#### Required Settings

**1. Warehouse Name**
- **Label**: SQL Warehouse or Cluster name
- **Example**: `my-sql-warehouse`
- **Purpose**: Compute resource for queries

**2. Server Hostname**
- **Label**: Databricks workspace hostname
- **Format**: `your-workspace.cloud.databricks.com`
- **Example**: `adb-1234567890123456.7.azuredatabricks.net`
- **Where to Find**: Databricks workspace URL (without https://)

**3. HTTP Path** (Optional)
- **Label**: SQL Warehouse or Cluster HTTP path
- **Format**: `/sql/1.0/warehouses/abc123def456`
- **Example**: `/sql/1.0/warehouses/a1b2c3d4e5f67890`
- **Where to Find**: 
  - SQL Warehouse → Connection Details → HTTP Path
  - If left empty, auto-detected from warehouse name

**4. Catalog Name**
- **Label**: Unity Catalog name
- **Example**: `prod_db` or `main`
- **Purpose**: Top-level namespace

**5. Schema Name**
- **Label**: Database schema name
- **Example**: `source2target`
- **Purpose**: Contains all platform tables

**6. Table Names**
Enter table names **without** catalog.schema prefix:
- **Semantic Management Table**: `semantic_fields`
- **Unmapped Fields Table**: `unmapped_fields`
- **Mapped Fields Table**: `mapped_fields`
- **Mapping Details Table**: `mapping_details`
- **Mapping Joins Table**: `mapping_joins`
- **Transformation Library Table**: `transformation_library`

⚠️ **Important**: Enter table names only (e.g., `semantic_fields`), NOT fully qualified names (e.g., `catalog.schema.semantic_fields`)

#### Setup Steps
1. Navigate to **Settings** → **Database**
2. Fill in all required fields
3. Click **"Save Configuration"**
4. Go to **Home** page to verify connection
5. Check for green ✅ "Database Connection" status

#### Validation
The system automatically checks:
- ✅ Server hostname format
- ✅ HTTP path format (if provided)
- ✅ Table names don't contain catalog/schema prefixes
- ✅ Connection to SQL warehouse
- ✅ Access to specified tables

### Vector Search Configuration

#### Required Settings

**1. Index Name**
- **Label**: Vector search index full name
- **Format**: `catalog.schema.index_name`
- **Example**: `prod_db.source2target.semantic_fields_vs`
- **Purpose**: AI semantic search on target fields

**2. Endpoint Name**
- **Label**: Vector search endpoint name
- **Example**: `s2t_vsendpoint`
- **Purpose**: Compute endpoint for vector search

#### Prerequisites
Before configuring vector search:

1. **Create Vector Search Endpoint** in Databricks:
   - Navigate to: Compute → Vector Search
   - Click "Create Endpoint"
   - Name: `s2t_vsendpoint` (or your chosen name)
   - Wait for endpoint to be "Ready"

2. **Create Vector Search Index**:
   ```sql
   CREATE VECTOR SEARCH INDEX catalog.schema.semantic_fields_vs
   ON TABLE catalog.schema.semantic_fields (semantic_field)
   COMPUTE ENDPOINT s2t_vsendpoint
   ```
   - Index the `semantic_field` column
   - Wait for initial sync to complete

#### Setup Steps
1. Navigate to **Settings** → **Vector Search**
2. Enter **Index Name** (fully qualified)
3. Enter **Endpoint Name**
4. Click **"Save Configuration"**
5. Go to **Home** to verify: "Vector Search Available" ✅

#### Testing
- Check "Vector Search Available" on Home page
- Should show "✓ Available" if configured correctly
- Try AI suggestions in Create Mappings to verify

### AI Model Configuration

#### Required Settings

**1. Foundation Model Endpoint**
- **Label**: Databricks Model Serving endpoint name
- **Example**: `databricks-meta-llama-3-3-70b-instruct`
- **Example**: `databricks-dbrx-instruct`
- **Purpose**: AI model for generating mapping suggestions

**2. Previous Mappings Table** (Optional)
- **Label**: Historical mappings table for learning
- **Format**: `catalog.schema.table_name`
- **Example**: `prod_db.source2target.mapping_history`
- **Purpose**: Improve AI suggestions based on past mappings

#### Prerequisites

1. **Deploy AI Model** in Databricks Model Serving:
   - Navigate to: Machine Learning → Serving
   - Click "Create Serving Endpoint"
   - Select foundation model (e.g., Llama 3.3 70B)
   - Name: `databricks-meta-llama-3-3-70b-instruct`
   - Wait for endpoint to be "Ready"

#### Setup Steps
1. Navigate to **Settings** → **AI/ML Models**
2. Enter **Foundation Model Endpoint** name
3. (Optional) Enter **Previous Mappings Table**
4. Click **"Save Configuration"**
5. Go to **Home** to verify: "AI Model Ready" ✅

#### Testing
- Check "AI Model Ready" on Home page
- Status should show "Ready" for full functionality
- Test in Create Mappings → Get AI Suggestions

### Configuration File

All settings are stored in `app_config.json` at the app root:

```json
{
  "database": {
    "warehouse_name": "my-sql-warehouse",
    "server_hostname": "workspace.cloud.databricks.com",
    "http_path": "/sql/1.0/warehouses/...",
    "catalog_name": "prod_db",
    "schema_name": "source2target",
    "semantic_fields_table": "semantic_fields",
    "unmapped_fields_table": "unmapped_fields",
    "mapped_fields_table": "mapped_fields",
    "mapping_details_table": "mapping_details",
    "mapping_joins_table": "mapping_joins",
    "transformation_library_table": "transformation_library"
  },
  "vector_search": {
    "index_name": "prod_db.source2target.semantic_fields_vs",
    "endpoint_name": "s2t_vsendpoint"
  },
  "ai_model": {
    "foundation_model_endpoint": "databricks-meta-llama-3-3-70b-instruct",
    "previous_mappings_table_name": "prod_db.source2target.mapping_history"
  },
  "admin_group": {
    "group_name": "source2target_admins"
  }
}
```

#### Backup and Restore
1. **Backup**: Copy `app_config.json` to safe location before changes
2. **Restore**: Replace `app_config.json` and restart app
3. **Version Control**: Store in git (without sensitive data)

---

## Semantic Management

Access by clicking **"Semantic Management"** (💾) in the sidebar.

### Overview
Semantic fields define all possible **target fields** that source fields can be mapped to. Each record represents one target column with semantic metadata for AI matching.

### Viewing Semantic Fields

**The Table Shows:**
- **Table Name**: Logical target table name
- **Column Name**: Logical target column name
- **Physical Names**: Actual database table.column
- **Data Type**: STRING, INT, DATE, etc.
- **Nullable**: YES or NO
- **Description**: Semantic description (critical for AI!)
- **Domain**: Category (e.g., member, claims, provider)

**Features:**
- Search/filter by any field
- Sort by any column
- Pagination (10, 25, 50, 100 rows)

### Adding Semantic Fields

Currently done via direct database insert:

```sql
INSERT INTO catalog.schema.semantic_fields (
  tgt_table_name,
  tgt_table_physical_name,
  tgt_column_name,
  tgt_column_physical_name,
  tgt_nullable,
  tgt_physical_datatype,
  tgt_comments,
  domain
) VALUES (
  'Member Demographics',              -- Logical table name
  'slv_member_demographics',          -- Physical table name
  'Full Name',                        -- Logical column name
  'full_name',                        -- Physical column name
  'NO',                               -- Nullable
  'STRING',                           -- Data type
  'Member full name combining first and last names',  -- Description
  'member'                            -- Domain
);
```

**Note**: The `semantic_field` column is auto-generated via computed column.

#### Best Practices for Semantic Fields
- ✅ **Detailed Descriptions**: Write clear, comprehensive descriptions
  - Bad: "Name"
  - Good: "Member full legal name as appears on insurance card"
- ✅ **Consistent Naming**: Use standard naming conventions
- ✅ **Include All Targets**: Add every possible target field
- ✅ **Use Domains**: Categorize by business domain
- ✅ **Update Regularly**: Keep descriptions current as requirements change

### Editing Semantic Fields

1. Find the record in the table
2. Click the **✏️ edit icon**
3. Modify fields in the dialog:
   - Table/column names (logical and physical)
   - Data type
   - Nullable flag
   - Description
   - Domain
4. Click **"Save"**
5. **Vector search index auto-syncs** immediately

### Deleting Semantic Fields

1. Find the record in the table
2. Click the **🗑️ delete icon**
3. Confirm deletion
4. ⚠️ **Warning**: Cannot be undone!
5. **Check for existing mappings first** - deleting a target that has mappings will break those mappings
6. **Vector search index auto-syncs** immediately

### Vector Search Integration

After any semantic field changes (create, update, delete):
1. System **automatically triggers** vector search index sync
2. Success message appears in backend logs
3. Sync typically takes 30-60 seconds to propagate
4. AI suggestions reflect changes after sync completes
5. If auto-sync fails, index will sync automatically within 5-10 minutes

---

## Transformation Management

Access by clicking **"Transformation Management"** (🛡️) in the sidebar.

### Overview
The transformation library provides **reusable SQL transformation templates** that users can apply to source fields during mapping. This ensures consistency and reduces errors.

### Viewing Transformations

**The Transformation Library Table Shows:**
- **Name**: Display name (e.g., "Trim Whitespace")
- **Code**: Unique identifier (e.g., "TRIM")
- **Expression**: SQL template with `{field}` placeholder
- **Category**: Grouping (STRING, DATE, NUMERIC, etc.)
- **Description**: What the transformation does
- **System Badge**: Blue badge for protected system transformations

**Features:**
- Search across all fields
- Filter by category
- Sort by any column
- Pagination (10, 25, 50 rows per page)

### Creating Transformations

#### Step 1: Click "Add Transformation"
Opens the creation dialog.

#### Step 2: Fill Required Fields

**Name** (required):
- **Label**: User-friendly name shown in dropdowns
- **Example**: "Remove Special Characters"
- **Example**: "Format Phone Number"

**Code** (required):
- **Label**: Unique identifier for the transformation
- **Format**: UPPERCASE_WITH_UNDERSCORES
- **Example**: `REMOVE_SPECIAL`
- **Example**: `FORMAT_PHONE`
- ⚠️ Must be unique across all transformations

**SQL Expression** (required):
- **Label**: SQL template using `{field}` as placeholder
- **Example**: `REGEXP_REPLACE({field}, '[^A-Za-z0-9 ]', '')`
- **Example**: `TRIM(UPPER({field}))`
- ⚠️ Must include `{field}` or validation fails
- The `{field}` placeholder is replaced with actual field name at runtime

**Description** (optional):
- **Label**: Explanation of what the transformation does
- **Example**: "Removes all non-alphanumeric characters from the field"
- **Tip**: Include examples or use cases

**Category** (optional):
- **Label**: Group similar transformations
- **Options**: STRING, DATE, NUMERIC, CONVERSION, NULL_HANDLING, CUSTOM
- **Default**: CUSTOM
- **Purpose**: Organize transformations in the library

**Mark as System** (checkbox):
- **Label**: System-protected transformation
- **Default**: Unchecked (custom transformation)
- **If Checked**: Transformation cannot be edited or deleted
- **Use Case**: Core transformations you never want changed

#### Step 3: Save
1. Click **"Create"** button
2. Validation runs:
   - Checks `{field}` placeholder exists
   - Checks code is unique
3. Success message appears
4. Transformation immediately available to users

#### Examples

**Example 1: Phone Number Formatting**
```
Name: Format Phone Number
Code: FORMAT_PHONE
Expression: REGEXP_REPLACE({field}, '[^0-9]', '')
Description: Removes all non-numeric characters from phone numbers (keeps only 0-9)
Category: STRING
System: No
```

**Example 2: Date to ISO Format**
```
Name: ISO Date Format
Code: ISO_DATE
Expression: TO_DATE({field}, 'yyyy-MM-dd')
Description: Converts date field to ISO 8601 format (YYYY-MM-DD)
Category: DATE
System: No
```

**Example 3: Clean Currency**
```
Name: Clean Currency Value
Code: CLEAN_CURRENCY
Expression: CAST(REGEXP_REPLACE({field}, '[^0-9.]', '') AS DECIMAL(10,2))
Description: Removes currency symbols and converts to decimal (e.g., "$1,234.56" → 1234.56)
Category: NUMERIC
System: No
```

### Editing Transformations

#### Restrictions
- ✅ **Custom transformations** can be edited
- ❌ **System transformations** cannot be edited (button disabled, grayed out)

#### Edit Process
1. Find the transformation in the table
2. Click the **✏️ pencil icon** (disabled if system transformation)
3. Edit dialog opens with current values
4. Modify any field **except** system flag
5. Click **"Update"**
6. Changes apply immediately
7. All existing mappings using this transformation **keep their current expression** (not updated)

**Note**: Editing a transformation affects new mappings only. Existing mappings store the actual SQL expression, not a reference.

### Deleting Transformations

#### Restrictions
- ✅ **Custom transformations** can be deleted
- ❌ **System transformations** cannot be deleted (button disabled, grayed out)

#### Delete Process
1. Find the transformation in the table
2. Click the **🗑️ trash icon** (disabled if system transformation)
3. Confirmation dialog shows:
   - Transformation name and code
   - Warning that action cannot be undone
4. Click **"Delete"** to confirm
5. Transformation removed from library
6. **Important**: Does NOT break existing mappings (they store the expression)

#### Safety Warning
- Deleting a transformation **does not break existing mappings**
- Existing mappings store the actual SQL expression
- Users can still see the expression in existing mappings
- Future mappings won't have this transformation in dropdown

### System Transformations

#### Pre-Loaded Transformations

**STRING Category:**
- **Trim Whitespace** (TRIM): `TRIM({field})`
- **Upper Case** (UPPER): `UPPER({field})`
- **Lower Case** (LOWER): `LOWER({field})`
- **Initial Caps** (INITCAP): `INITCAP({field})`
- **Trim and Upper** (TRIM_UPPER): `UPPER(TRIM({field}))`
- **Trim and Lower** (TRIM_LOWER): `LOWER(TRIM({field}))`

**CONVERSION Category:**
- **Cast to String** (CAST_STRING): `CAST({field} AS STRING)`
- **Cast to Integer** (CAST_INT): `CAST({field} AS INT)`

**DATE Category:**
- **Cast to Date** (CAST_DATE): `CAST({field} AS DATE)`
- **Cast to Timestamp** (CAST_TIMESTAMP): `CAST({field} AS TIMESTAMP)`

**NULL_HANDLING Category:**
- **Replace Nulls** (COALESCE): `COALESCE({field}, '')`
- **Replace Nulls with Zero** (COALESCE_ZERO): `COALESCE({field}, 0)`

#### Protection
System transformations are protected:
- Cannot be edited (button disabled)
- Cannot be deleted (button disabled)
- Show blue "SYSTEM" badge
- Protected at API level (403 error if attempted)
- Ensure core transformations always available

### Best Practices

#### For Transformation Design
1. ✅ Keep expressions simple and readable
2. ✅ Use descriptive names (not just "Transform 1")
3. ✅ Provide clear descriptions with examples
4. ✅ Test expressions with sample data before adding
5. ✅ Use appropriate categories for organization
6. ✅ Follow SQL best practices

#### For Code Naming
1. ✅ Use UPPER_CASE_WITH_UNDERSCORES
2. ✅ Keep codes short but descriptive (max 20 chars)
3. ✅ Prefix related transformations (e.g., CAST_*, TRIM_*)
4. ✅ Avoid special characters except underscore
5. ✅ Make codes memorable and intuitive

#### For Expression Templates
1. ✅ Always include {field} placeholder
2. ✅ Use valid Databricks SQL syntax
3. ✅ Escape single quotes properly in expressions
4. ✅ Test with various data types
5. ✅ Document complex logic in description

#### For Library Management
1. ✅ Mark core/standard transformations as system
2. ✅ Review and clean unused custom transformations monthly
3. ✅ Keep categories organized (5-10 transformations per category max)
4. ✅ Document transformation usage patterns
5. ✅ Train users on new transformations when added

---

## Vector Search Sync

### Overview
When semantic field records are created, updated, or deleted, the vector search index must be synchronized to reflect changes for AI suggestions.

### Automatic Sync Triggers
The system **automatically triggers** vector search sync after:
1. Creating a new semantic field
2. Updating an existing semantic field  
3. Deleting a semantic field

No manual intervention required!

### Sync Process

**Step 1: Database Change**
Admin creates/updates/deletes semantic field via UI or SQL.

**Step 2: Trigger Sync**
Immediately after commit, backend calls:
```python
workspace_client.vector_search_indexes.sync_index(index_name)
```

**Step 3: Monitor Result**

**Success (Backend Logs):**
```
================================================================================
[Vector Search Sync] Triggering sync for index: prod_db.source2target.semantic_fields_vs
================================================================================
[Vector Search Sync] ✅ Sync triggered successfully
[Vector Search Sync] Note: Full sync may take a few moments to complete
================================================================================
```

**Failure (Backend Logs):**
```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
[Vector Search Sync] ⚠️ Warning: Could not sync vector search index
[Vector Search Sync] Error type: HTTPError
[Vector Search Sync] Error message: Endpoint not responding
[Vector Search Sync] The index will auto-sync eventually (may take 5-10 minutes)
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

**Step 4: Propagation**
- Sync trigger is immediate
- Full propagation takes 30-60 seconds
- AI suggestions reflect changes after propagation
- Users may see slight delay in new fields appearing

### Monitoring Sync

#### Check Backend Logs
1. Go to Databricks workspace
2. Navigate to **Apps** → Your App
3. Click **"Logs"** tab
4. Filter for "Vector Search Sync"
5. Look for success (✅) or warning (⚠️) messages

#### Success Indicators
- ✅ "Sync triggered successfully" in logs
- ✅ No error messages
- ✅ AI suggestions include new/updated fields within 1-2 minutes
- ✅ Deleted fields disappear from suggestions

#### Failure Indicators
- ⚠️ Warning messages in logs
- ⚠️ Error type and detailed message shown
- ⚠️ AI suggestions don't reflect changes immediately
- ⚠️ May need to wait for auto-sync (5-10 minutes)

### Manual Sync Fallback

If automatic sync fails repeatedly:

**Option 1: Via Databricks UI**
1. Go to **Compute** → **Vector Search**
2. Find your index
3. Click **"Sync Now"** button
4. Wait for completion (usually 1-2 minutes)

**Option 2: Via Databricks SQL**
```sql
-- Force refresh of vector search index
REFRESH VECTOR SEARCH INDEX catalog.schema.semantic_fields_vs;
```

**Option 3: Via Python API**
```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
w.vector_search_indexes.sync_index("catalog.schema.semantic_fields_vs")
```

### Troubleshooting Sync

#### Common Issues

**1. Vector Search Endpoint Stopped**
- **Symptom**: Sync fails with "endpoint not available"
- **Solution**: Start the vector search endpoint in Databricks

**2. Index Not Found**
- **Symptom**: Sync fails with "index does not exist"
- **Solution**: Verify index name in Settings matches actual index

**3. Permissions Issues**
- **Symptom**: Sync fails with "access denied"
- **Solution**: Check service principal has sync permissions on index

**4. Network Issues**
- **Symptom**: Sync fails with timeout
- **Solution**: Check Databricks workspace connectivity

**5. Service Disruption**
- **Symptom**: All syncs failing
- **Solution**: Check Databricks status page for outages

---

## Mapping Management

### Viewing All Mappings (Admin)

Admins see **all mappings** from all users in View Mappings:
- No user filter applied
- Can see `mapped_by` column showing who created each mapping
- Can export all mappings

Regular users only see their own mappings.

### Export All Mappings

1. Navigate to **View Mappings**
2. Click **"Export Mappings"** button
3. CSV downloads with complete mapping details:
   - Single row per mapping
   - All source fields (pipe-separated)
   - Complete SQL transformation expressions
   - Join conditions
   - User metadata

**Admin Export** includes all users' mappings.  
**User Export** includes only their own mappings.

### Bulk Operations

Currently not implemented via UI, but can be done via SQL:

**Bulk Delete Mappings:**
```sql
-- Delete all INACTIVE mappings
DELETE FROM catalog.schema.mapped_fields WHERE mapping_status = 'INACTIVE';
DELETE FROM catalog.schema.mapping_details WHERE mapped_field_id NOT IN (SELECT mapped_field_id FROM catalog.schema.mapped_fields);
DELETE FROM catalog.schema.mapping_joins WHERE mapped_field_id NOT IN (SELECT mapped_field_id FROM catalog.schema.mapped_fields);
```

**Bulk Update Status:**
```sql
-- Set all user's mappings to INACTIVE
UPDATE catalog.schema.mapped_fields 
SET mapping_status = 'INACTIVE', updated_ts = CURRENT_TIMESTAMP()
WHERE mapped_by = 'user@example.com';
```

---

## System Monitoring

### System Status Dashboard (Home Page)

**Database Connection**
- **Status**: Connected / Failed
- **Checks**: Warehouse accessibility, table access, authentication
- **Troubleshooting**: 
  - Verify warehouse is running
  - Check OAuth/service principal permissions
  - Validate HTTP path in Settings

**Vector Search**
- **Status**: Available / Unavailable / Not Configured
- **Checks**: Endpoint running, index accessible, sync capability
- **Troubleshooting**:
  - Verify endpoint is running
  - Check index exists and name is correct
  - Validate endpoint name in Settings

**AI Model**
- **Status**: Ready / Not Ready / Not Configured
- **Checks**: Model endpoint status, inference capability
- **Troubleshooting**:
  - Verify endpoint is deployed and running
  - Check endpoint name matches Settings
  - Review Model Serving logs in Databricks

**Configuration**
- **Status**: Valid / Invalid
- **Checks**: All required fields present, format validation
- **Troubleshooting**:
  - Review Settings page for missing fields
  - Validate field formats
  - Check console for error messages

### Performance Metrics

**Typical Query Times:**
- Home page load: 2-5 seconds
- Unmapped fields: 5-10 seconds
- Mapped fields: 5-10 seconds
- Semantic fields: 10-15 seconds
- Vector search: 15-25 seconds
- AI suggestions: 20-30 seconds total

**If Queries Are Slow:**
1. Check warehouse state (serverless may need warmup)
2. Review data volume (large tables = slower)
3. Monitor warehouse utilization
4. Check network latency
5. Consider warehouse scaling (larger size)

### Database Warehouse Recommendations

**Serverless (Recommended for Cost):**
- ✅ Starts on-demand
- ✅ Scales automatically
- ⚠️ Initial queries slow (cold start)
- ✅ Cost-effective for intermittent use

**Classic (Recommended for Performance):**
- ✅ Always running (if configured)
- ✅ Consistent fast performance
- ⚠️ Higher cost
- ✅ Best for heavy usage

### Accessing Logs

**Backend Application Logs:**
1. Go to Databricks workspace
2. Navigate to **Apps**
3. Select your app
4. Click **"Logs"** tab
5. Filter by:
   - Time period
   - Log level (ERROR, INFO, DEBUG)
   - Service name (e.g., "Mapping Service V2", "Vector Search Sync")

**Log Format:**
```
[Service Name] Message type: Details
```

**Examples:**
```
[Semantic Service] Successfully updated record ID: 42
[Vector Search Sync] ✅ Sync triggered successfully
[Mapping Service V2] Creating mapping: slv_member.full_name
[Transformation Service] Created transformation: FORMAT_PHONE
```

---

## Database Schema V2

### Schema Overview

Version 2.0 uses normalized tables for multi-field mapping:

```
semantic_fields (target field definitions)
       ↓ (semantic_field_id FK)
mapped_fields (target fields with mappings)
       ↓ (mapped_field_id FK)
       ├─ mapping_details (source fields: order, transformations)
       └─ mapping_joins (join conditions for multi-table)

unmapped_fields (source fields awaiting mapping)

transformation_library (reusable transformation templates)

mapping_feedback (AI suggestion feedback)
```

### Key Tables

**semantic_fields**
- Primary Key: `semantic_field_id`
- Vector Search Column: `semantic_field` (auto-generated)
- Purpose: Define all possible target fields

**unmapped_fields**
- Primary Key: `unmapped_field_id`
- Filtered By: `uploaded_by`
- Purpose: Source fields to be mapped

**mapped_fields**
- Primary Key: `mapped_field_id`
- Foreign Key: `semantic_field_id` → semantic_fields
- Filtered By: `mapped_by` (users see only their own)
- Purpose: One row per target field with mapping

**mapping_details**
- Primary Key: `mapping_detail_id`
- Foreign Key: `mapped_field_id` → mapped_fields
- Ordered By: `field_order`
- Contains: `transformations` (SQL expression)
- Purpose: Individual source fields in each mapping

**mapping_joins**
- Primary Key: `mapping_join_id`
- Foreign Key: `mapped_field_id` → mapped_fields
- Ordered By: `join_order`
- Purpose: Join conditions for multi-table mappings

**transformation_library**
- Primary Key: `transformation_id`
- Unique: `transformation_code`
- Protected: `is_system` (boolean)
- Purpose: Reusable SQL transformation templates

### Column Name Reference

⚠️ **Important Column Names** (commonly confused):

| Table | Primary Key | Foreign Key | Notes |
|-------|-------------|-------------|-------|
| mapped_fields | `mapped_field_id` | - | NOT `mapping_id` |
| mapping_details | `mapping_detail_id` | `mapped_field_id` | NOT `detail_id`, NOT `mapping_id` |
| mapping_joins | `mapping_join_id` | `mapped_field_id` | NOT `mapping_id` |
| - | - | - | - |
| mapping_details | - | - | Column: `transformations` (NOT `transformation_expr`) |

---

## Troubleshooting

### Transformation Library Issues

**Cannot Edit/Delete System Transformation**
- **Symptom**: Edit/delete buttons grayed out
- **Cause**: Transformation marked as system
- **Solution**: This is by design to protect core transformations

**Duplicate Code Error**
- **Symptom**: "Transformation with code 'XXX' already exists"
- **Cause**: Code must be unique
- **Solution**: Choose different code or edit existing transformation

**Expression Validation Error**
- **Symptom**: "Expression must include {field} placeholder"
- **Cause**: SQL expression missing required {field}
- **Solution**: Add {field} where field name should appear

### Vector Search Sync Issues

**Sync Always Fails**
- **Symptom**: ⚠️ warning in logs, changes not in AI suggestions
- **Cause**: Vector search endpoint or permissions issue
- **Solution**:
  1. Check endpoint is running in Databricks
  2. Verify index exists
  3. Check service principal permissions
  4. Try manual sync

**Sync Succeeds But Changes Not Visible**
- **Symptom**: ✅ success but AI doesn't show new fields
- **Cause**: Sync propagation delay
- **Solution**: Wait 1-2 minutes, then test again

### Mapping Issues

**Mapping Update Fails**
- **Symptom**: Error when editing transformation
- **Cause**: Backend column name mismatch (all fixed in v2)
- **Solution**: Should work now; check logs if still failing

**Transformation Expression Not Updating**
- **Symptom**: Changed transformation but expression not updated
- **Cause**: Was a bug, now fixed (Step 4 in update process)
- **Solution**: Update again; should rebuild expression

### Settings Issues

**Database Connection Failed**
- **Symptom**: "Database Connection Failed" on Home
- **Solution**:
  1. Verify SQL warehouse is running
  2. Check HTTP path is correct
  3. Test OAuth token generation
  4. Review backend logs
  5. Increase timeout if serverless

**Vector Search Unavailable**
- **Symptom**: "Vector Search Unavailable" on Home
- **Solution**:
  1. Verify endpoint is running
  2. Check index name matches Settings
  3. Ensure index is synced
  4. Test endpoint accessibility

**AI Model Not Ready**
- **Symptom**: "AI Model Not Ready" on Home
- **Solution**:
  1. Check model endpoint is deployed
  2. Verify endpoint is in "Ready" state
  3. Confirm endpoint name in Settings
  4. Test endpoint with sample query

---

## Maintenance

### Daily Tasks
- ✅ Monitor system status dashboard (all green ✅)
- ✅ Review backend logs for errors
- ✅ Check user-reported issues
- ✅ Verify vector search sync working

### Weekly Tasks
- ✅ Review semantic fields for accuracy
- ✅ Check transformation library usage
- ✅ Monitor mapping activity trends
- ✅ Clean unused custom transformations
- ✅ Export mappings for backup

### Monthly Tasks
- ✅ Audit admin group membership
- ✅ Review Settings for updates needed
- ✅ Analyze mapping patterns and quality
- ✅ Update documentation as needed
- ✅ Test disaster recovery procedures
- ✅ Review and optimize database indexes

### Backup Strategy

**Configuration:**
- Backup `app_config.json` before changes
- Store in version control
- Document configuration changes

**Database Tables:**
- Use Databricks table snapshots (Delta Lake)
- Export critical tables weekly
- Test restore procedures monthly
- Document backup schedule

**Transformation Library:**
- Export transformations to SQL script
- Version control custom transformations
- Document transformation business logic

---

## Security

### Authentication
- Users authenticated via **Databricks OAuth**
- Email captured from `X-Forwarded-Email` header
- No separate login required
- Session managed by Databricks

### Authorization
- Admin access via **Databricks group membership**
- Regular users limited to own mappings
- Row-level filtering by `mapped_by` email field
- Transformation library changes admin-only

### Data Access
- Users see only their own mappings (by `mapped_by`)
- Admins can view all data via UI and direct database access
- Service principal has full read/write to tables
- Audit trail tracks all user actions

### Best Practices
1. ✅ Use service principal for app deployment
2. ✅ Limit admin group to 3-5 trusted users
3. ✅ Enable audit logging in Databricks
4. ✅ Review access logs weekly
5. ✅ Use HTTPS only (enforced by Databricks Apps)
6. ✅ Keep dependencies updated
7. ✅ Monitor for suspicious activity
8. ✅ Document security procedures
9. ✅ Regular security reviews

### Compliance
- User actions tracked via `mapped_by` and timestamps
- Audit trail in all database tables
- Access logs in Databricks
- GDPR: User data filterable/deletable by email

---

## Support Resources

### Documentation
- **Quick Start**: [QUICK_START.md](QUICK_START.md)
- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Developer Guide**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Database Schema**: [database/V2_SCHEMA_DIAGRAM.md](../database/V2_SCHEMA_DIAGRAM.md)
- **Feature Docs**: Check `/` root for `*_FEATURE.md` and `*_FIX.md` files

### Getting Help
1. Review this admin guide
2. Check system logs
3. Review Databricks documentation
4. Contact development team
5. Check GitHub issues (if applicable)

---

**Version**: 2.0  
**Last Updated**: November 2025  
**Platform**: Source-to-Target Mapping (Multi-Field V2)  
**New Features**: Transformation library, Mapping editor, Export, Vector auto-sync
