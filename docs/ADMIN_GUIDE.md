# Source-to-Target Mapping Platform - Administrator Guide

## Table of Contents
1. [Administrator Overview](#administrator-overview)
2. [User Management](#user-management)
3. [Configuration Management](#configuration-management)
4. [Semantic Table Management](#semantic-table-management)
5. [Transformation Library Management](#transformation-library-management)
6. [Vector Search Sync](#vector-search-sync)
7. [System Monitoring](#system-monitoring)
8. [Database Schema V2](#database-schema-v2)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)
11. [Security](#security)

---

## Administrator Overview

As an administrator, you have full access to all features and are responsible for:
- Managing user access and permissions
- Configuring system settings
- Maintaining the semantic table
- Managing the transformation library
- Monitoring system health and vector search sync
- Troubleshooting issues

### Admin Identification
Admins are identified by:
- Green "Admin" badge in the header
- Access to Configuration, Semantic Table, and Admin Tools pages
- Membership in the configured admin group

### New in Version 2.0
- **Transformation Library Management**: Create, edit, delete transformation templates
- **Multi-Field Mapping Support**: Enhanced schema for many-to-one mappings
- **Mapping Editor**: Restricted edit capabilities for existing mappings
- **Vector Search Auto-Sync**: Automatic index synchronization after changes
- **Join Conditions**: Support for multi-table mappings

---

## User Management

### Admin Group Configuration

#### Setting Up Admin Access
1. Go to **Settings** → **Security**
2. Enter the Databricks workspace group name in "Admin Group Name"
3. Click **Save Configuration**
4. Members of this group will have admin access

#### Group Membership
- Users are automatically identified by their Databricks email
- Admin status is checked via Databricks Workspace API
- Group membership is verified per request

#### Best Practices
- ✅ Use a dedicated admin group (e.g., "source2target_admins")
- ✅ Limit admin access to trusted users
- ✅ Review group membership regularly
- ✅ Document who has admin access

### User Permissions

| Permission | Admin | User |
|------------|-------|------|
| View Home | ✅ | ✅ |
| Create Mappings | ✅ | ✅ |
| View Mappings | ✅ | ✅ |
| Edit Mappings | ✅ | ✅ |
| AI Suggestions | ✅ | ✅ |
| Manual Search | ✅ | ✅ |
| Semantic Fields | ✅ | ❌ |
| Admin Tools | ✅ | ❌ |
| Settings | ✅ | ❌ |

### Data Visibility
- **V2 Schema**: Users see only their own mappings (filtered by `mapped_by`)
- **Admins**: Can view all data via direct database access
- **Audit Trail**: All user actions tracked in database

---

## Configuration Management

### Database Configuration

#### V2 Schema Tables
The platform uses multiple tables for V2 multi-field mapping:

1. **Semantic Fields Table** (`semantic_fields`)
   - Target field definitions for AI mapping
   - Enhanced with semantic_field for vector search

2. **Unmapped Fields Table** (`unmapped_fields`)
   - Source fields awaiting mapping

3. **Mapped Fields Table** (`mapped_fields`)
   - Target fields with completed mappings
   - Links to semantic_fields via semantic_field_id

4. **Mapping Details Table** (`mapping_details`)
   - Source field details for each mapping
   - Includes field_order and transformation_expr

5. **Mapping Joins Table** (`mapping_joins`)
   - Join conditions for multi-table mappings

6. **Mapping Feedback Table** (`mapping_feedback`)
   - User feedback on AI suggestions

7. **Transformation Library Table** (`transformation_library`)
   - Reusable SQL transformation templates

#### Configuration Steps
1. Navigate to **Settings** → **Database**
2. Enter warehouse name
3. Server hostname (e.g., `workspace.cloud.databricks.com`)
4. HTTP Path (optional - auto-detected if empty)
5. Catalog and Schema names
6. Table names (without catalog.schema prefix)
7. Click **Save Configuration**
8. Verify connection on Home page

#### Table Name Configuration
**Important**: Enter table names only (not fully qualified):
- ✅ Correct: `semantic_fields`
- ❌ Wrong: `catalog.schema.semantic_fields`

The system automatically prepends catalog and schema.

### Vector Search Configuration

#### Settings
1. **Index Name**: Full name of vector search index
   - Format: `catalog.schema.index_name`
   - Example: `oztest_dev.source2target.semantic_fields_vs`
   
2. **Endpoint Name**: Vector search endpoint
   - Example: `s2t_vsendpoint`
   - Must be running and accessible

#### Setup Steps
1. Create vector search endpoint in Databricks
2. Create vector search index on semantic_fields table
3. Configure index to use `semantic_field` column
4. Enter names in **Settings** → **Vector Search**
5. Save configuration
6. Test on Home page

#### Vector Search Sync
The platform automatically syncs the vector search index after:
- Creating semantic field records
- Updating semantic field records
- Deleting semantic field records

**Sync Process:**
- Triggers immediately after database changes
- Uses Databricks Workspace API
- Shows success/failure in backend logs
- Falls back to auto-sync if manual sync fails (5-10 minutes)

### AI Model Configuration

#### Settings
1. **Foundation Model Endpoint**: Model serving endpoint name
   - Example: `databricks-meta-llama-3-3-70b-instruct`
   - Must be deployed and running

2. **Previous Mappings Table**: Historical mappings for learning
   - Format: `catalog.schema.table_name`
   - Optional but improves suggestions

#### Setup Steps
1. Deploy AI model in Databricks Model Serving
2. Ensure endpoint is in "Ready" state
3. Enter endpoint name in **Settings** → **AI/ML Models**
4. Save configuration
5. Verify on Home page

---

## Semantic Table Management

### Overview
The semantic table defines all possible target fields that source fields can be mapped to. Each record includes a `semantic_field` column used for vector search.

### Viewing Semantic Fields
1. Go to **Semantic Fields** page
2. Browse all target field definitions
3. Use search/filter to find specific fields
4. View metadata: table, column, datatype, description

### Adding Records

#### Via Database Tools
Insert records directly into the semantic_fields table:

```sql
INSERT INTO catalog.schema.semantic_fields (
  tgt_table_name,
  tgt_table_physical_name,
  tgt_column_name,
  tgt_column_physical_name,
  tgt_nullable,
  tgt_physical_datatype,
  tgt_comments
) VALUES (
  'member_demographics',
  'slv_member_demographics',
  'full_name',
  'full_name',
  'NO',
  'STRING',
  'Member full name combining first and last names'
);
```

**Note**: The `semantic_field` column is auto-generated.

#### Required Fields
- `tgt_table_name`: Logical target table name
- `tgt_table_physical_name`: Physical database table
- `tgt_column_name`: Logical target column name
- `tgt_column_physical_name`: Physical database column
- `tgt_physical_datatype`: Data type (STRING, INT, DATE, etc.)
- `tgt_nullable`: YES or NO
- `tgt_comments`: Description (critical for AI matching!)

#### Best Practices
- ✅ Provide detailed, accurate descriptions
- ✅ Use consistent naming conventions
- ✅ Include all possible target fields
- ✅ Update descriptions as requirements change
- ✅ Test AI suggestions after adding fields

### Editing Records
1. Find the record in Semantic Fields page
2. Click the ✏️ edit icon
3. Modify fields in the dialog
4. Click **Save**
5. Vector search index syncs automatically

### Deleting Records
1. Find the record in Semantic Fields page
2. Click the 🗑️ delete icon
3. Confirm deletion
4. ⚠️ **Warning**: This cannot be undone
5. Check for existing mappings first
6. Vector search index syncs automatically

### Vector Search Integration
After any semantic table changes:
1. Platform automatically triggers index sync
2. Success message appears in backend logs
3. If sync fails, index auto-syncs in 5-10 minutes
4. AI suggestions reflect changes immediately after sync

---

## Transformation Library Management

### Overview
The transformation library provides reusable SQL transformation templates that users can apply to source fields during mapping. Admins manage this library through the **Admin Tools** page.

### Accessing Transformation Library
1. Click **Admin Tools** in the sidebar
2. The Transformation Library interface loads
3. View all system and custom transformations

### Viewing Transformations

#### Transformation List
The data table shows:
- **Name**: Display name (e.g., "Trim Whitespace")
- **Code**: Unique identifier (e.g., "TRIM")
- **Expression**: SQL template with {field} placeholder
- **Category**: Grouping (STRING, DATE, NUMERIC, etc.)
- **Description**: Explanation of what it does
- **System Badge**: Indicates system-protected transformations

#### Search and Filter
- Search by name, code, category, or description
- Sort by any column
- Filter by category
- Pagination: 10, 25, or 50 rows per page

### Creating Transformations

#### Step 1: Click "Add Transformation"
The creation dialog opens with a form.

#### Step 2: Fill Required Fields

**Name** (required):
- Display name shown to users
- Example: "Remove Special Characters"

**Code** (required):
- Unique identifier (must be unique across all transformations)
- Use uppercase with underscores
- Example: "REMOVE_SPECIAL"

**SQL Expression** (required):
- Template using `{field}` as placeholder
- Example: `REGEXP_REPLACE({field}, '[^A-Za-z0-9 ]', '')`
- **Must include {field}** or validation fails

**Description** (optional):
- Explain what the transformation does
- Example: "Remove all special characters, keeping only alphanumeric"

**Category** (optional):
- Group similar transformations
- Options: STRING, DATE, NUMERIC, CONVERSION, NULL_HANDLING, CUSTOM
- Example: STRING

**Mark as System** (checkbox):
- System transformations cannot be edited or deleted
- Use for core transformations only
- Default: unchecked (custom transformation)

#### Step 3: Save
1. Click **"Create"** button
2. Validation runs (checks for {field}, unique code)
3. Success message appears
4. Transformation added to library
5. Available immediately for users

#### Example: Creating Phone Format Transformation
```
Name: Format Phone Number
Code: FORMAT_PHONE
Expression: REGEXP_REPLACE({field}, '[^0-9]', '')
Description: Remove all non-numeric characters from phone numbers
Category: STRING
System: No
```

### Editing Transformations

#### Restrictions
- ✅ Custom transformations can be edited
- ❌ System transformations cannot be edited
- System transformations show grayed-out edit button

#### Edit Process
1. Click the ✏️ pencil icon next to a custom transformation
2. Edit dialog opens with current values
3. Modify fields as needed
4. Click **"Update"**
5. Changes apply immediately

**Note**: Cannot change whether a transformation is "system" after creation.

### Deleting Transformations

#### Restrictions
- ✅ Custom transformations can be deleted
- ❌ System transformations cannot be deleted
- System transformations show grayed-out delete button

#### Delete Process
1. Click the 🗑️ trash icon next to a custom transformation
2. Confirmation dialog appears showing:
   - Transformation name
   - Transformation code
   - Warning that action cannot be undone
3. Click **"Delete"** to confirm
4. Transformation removed from library
5. **Note**: Doesn't affect existing mappings using this transformation

#### Safety Warning
Deleting a transformation doesn't break existing mappings because:
- Mappings store the actual SQL expression, not a reference to the transformation
- Users can still see and use the expression in existing mappings
- Future mappings won't have this transformation in the dropdown

### System Transformations

#### Pre-Loaded Transformations
The platform includes these system transformations:

**STRING Category:**
- Trim Whitespace (TRIM)
- Upper Case (UPPER)
- Lower Case (LOWER)
- Initial Caps (INITCAP)
- Trim and Upper (TRIM_UPPER)
- Trim and Lower (TRIM_LOWER)

**CONVERSION Category:**
- Cast to String (CAST_STRING)
- Cast to Integer (CAST_INT)

**DATE Category:**
- Cast to Date (CAST_DATE)
- Cast to Timestamp (CAST_TIMESTAMP)

**NULL_HANDLING Category:**
- Replace Nulls (COALESCE)
- Replace Nulls with Zero (COALESCE_ZERO)

#### Protection
System transformations:
- Cannot be edited (edit button disabled)
- Cannot be deleted (delete button disabled)
- Show blue "SYSTEM" badge in the list
- Protected at backend API level (returns 403 if attempted)

### Categories

#### Standard Categories
- **STRING**: Text manipulation (TRIM, UPPER, LOWER, etc.)
- **DATE**: Date/time operations (CAST_DATE, CAST_TIMESTAMP, etc.)
- **NUMERIC**: Number operations (CAST_INT, ROUND, etc.)
- **CONVERSION**: Type conversions (CAST_STRING, TO_CHAR, etc.)
- **NULL_HANDLING**: NULL value handling (COALESCE, IFNULL, etc.)
- **CUSTOM**: User-defined categories

#### Color Coding
Categories are color-coded in the UI:
- STRING → Green
- DATE → Blue
- NUMERIC → Orange
- CONVERSION → Purple
- NULL_HANDLING → Gray
- CUSTOM → Dark

### Best Practices

#### For Transformation Design
1. ✅ Keep expressions simple and readable
2. ✅ Use descriptive names
3. ✅ Provide clear descriptions
4. ✅ Test expressions before adding
5. ✅ Use appropriate categories
6. ✅ Follow SQL best practices

#### For Code Naming
1. ✅ Use UPPER_CASE_WITH_UNDERSCORES
2. ✅ Keep codes short but descriptive
3. ✅ Prefix related transformations (e.g., CAST_*, TRIM_*)
4. ✅ Avoid special characters
5. ✅ Make codes memorable

#### For Expression Templates
1. ✅ Always include {field} placeholder
2. ✅ Use valid Databricks SQL syntax
3. ✅ Escape single quotes properly
4. ✅ Test with various data types
5. ✅ Document complex logic

#### For Library Management
1. ✅ Mark core transformations as system
2. ✅ Review and clean unused custom transformations
3. ✅ Keep categories organized
4. ✅ Document transformation usage
5. ✅ Train users on new transformations

---

## Vector Search Sync

### Overview
When semantic field records are modified, the vector search index must be synchronized to reflect changes. The platform handles this automatically.

### Automatic Sync Triggers
Vector search index syncs automatically after:
1. Creating a new semantic field
2. Updating an existing semantic field
3. Deleting a semantic field

### Sync Process

#### Step 1: Database Update
Platform modifies the semantic_fields table using standard SQL.

#### Step 2: Trigger Sync
Immediately after commit, platform calls:
```python
workspace_client.vector_search_indexes.sync_index(index_name)
```

#### Step 3: Monitor Result
**Success:**
```
================================================================================
[Vector Search Sync] Triggering sync for index: catalog.schema.index_name
================================================================================
[Vector Search Sync] ✅ Sync triggered successfully
[Vector Search Sync] Note: Full sync may take a few moments to complete
================================================================================
```

**Failure:**
```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
[Vector Search Sync] ⚠️  Warning: Could not sync vector search index
[Vector Search Sync] Error type: <error type>
[Vector Search Sync] Error message: <detailed error>
[Vector Search Sync] The index will auto-sync eventually (may take 5-10 minutes)
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

#### Step 4: Propagation
Even after successful trigger:
- Sync may take 30-60 seconds to complete
- AI suggestions reflect changes after propagation
- Users may see slight delay in new field availability

### Monitoring Sync

#### Backend Logs
Check Databricks app logs for sync messages:
1. Go to Databricks workspace
2. Navigate to Apps → Your App
3. Click "Logs" tab
4. Filter for "Vector Search Sync"

#### Success Indicators
- ✅ "Sync triggered successfully" message
- ✅ No error messages in logs
- ✅ AI suggestions include new/updated fields
- ✅ Deleted fields disappear from suggestions

#### Failure Indicators
- ⚠️ Warning messages in logs
- ⚠️ Error type and message shown
- ⚠️ AI suggestions don't reflect changes immediately
- ⚠️ Must wait for auto-sync (5-10 minutes)

### Manual Sync Fallback

If automatic sync fails, trigger manually:

#### Option 1: Via Databricks UI
1. Go to Vector Search in Databricks workspace
2. Find your index
3. Click "Sync Now" button
4. Wait for completion

#### Option 2: Via Databricks API
```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
w.vector_search_indexes.sync_index("catalog.schema.index_name")
```

### Troubleshooting Sync Issues

#### Common Causes
1. Vector search endpoint is stopped
2. Index doesn't exist
3. Permissions issues
4. Network connectivity problems
5. Databricks service issues

#### Solutions
1. **Endpoint Stopped**: Start the vector search endpoint
2. **Index Not Found**: Verify index name in configuration
3. **Permissions**: Check service principal has sync permissions
4. **Network**: Check Databricks workspace connectivity
5. **Service Issues**: Check Databricks status page

---

## System Monitoring

### System Status Dashboard

#### Access
Home page shows real-time status of all components.

#### Components Monitored

**Database Connection:**
- **Status**: Connected / Failed
- **Checks**: SQL warehouse accessibility, authentication, table access
- **Latency**: Query response time

**Vector Search:**
- **Status**: Available / Unavailable / Not Configured
- **Checks**: Endpoint running, index accessible, sync capability

**AI Model:**
- **Status**: Ready / Not Ready / Not Configured
- **Checks**: Model endpoint status, inference capability

**Configuration:**
- **Status**: Valid / Invalid
- **Checks**: All required fields present, format validation

### Performance Monitoring

#### Typical Query Times
- Unmapped fields: 5-10 seconds
- Mapped fields: 5-10 seconds
- Semantic table: 10-15 seconds
- Vector search: 15-25 seconds
- AI suggestions: 20-30 seconds total

#### Performance Issues
If queries are consistently slow:
1. Check warehouse state (serverless warmup)
2. Review data volume in tables
3. Monitor warehouse utilization
4. Check network latency
5. Consider warehouse scaling

### Logging

#### Backend Logs Location
Databricks app logs contain:
- Service initialization messages
- Database connection logs
- Query execution logs
- Vector search sync logs
- Error messages and stack traces
- User action audit trail

#### Log Format
```
[Service Name] Message type: Details
```

Examples:
```
[Semantic Service] Successfully updated record ID: 42
[Vector Search Sync] ✅ Sync triggered successfully
[Mapping Service V2] Creating mapping: member_demographics.full_name
```

#### Accessing Logs
1. Databricks workspace
2. Apps section
3. Select your app
4. Logs tab
5. Filter by time/service

---

## Database Schema V2

### Schema Overview
Version 2.0 introduces a normalized schema supporting multi-field mappings:

```
semantic_fields (target field definitions)
       ↓ (semantic_field_id)
mapped_fields (target fields with mappings)
       ↓ (mapping_id)
       ├─ mapping_details (source fields with order & transformations)
       └─ mapping_joins (join conditions for multi-table mappings)

unmapped_fields (source fields awaiting mapping)

transformation_library (reusable transformation templates)

mapping_feedback (user feedback on AI suggestions)
```

### Table Details

#### semantic_fields
Defines all possible target fields.
- Primary Key: `semantic_field_id`
- Vector Search: Uses `semantic_field` column
- Auto-syncs to vector search index

#### unmapped_fields
Source fields waiting to be mapped.
- Primary Key: `id`
- Filtered by: `uploaded_by`
- Removed when mapped

#### mapped_fields
Target fields with completed mappings.
- Primary Key: `mapping_id`
- Foreign Key: `semantic_field_id` → semantic_fields
- Filtered by: `mapped_by`

#### mapping_details
Source fields for each mapping.
- Primary Key: `detail_id`
- Foreign Key: `mapping_id` → mapped_fields
- Ordered by: `field_order`
- Contains: `transformation_expr`

#### mapping_joins
Join conditions for multi-table mappings.
- Primary Key: `mapping_join_id`
- Foreign Key: `mapping_id` → mapped_fields
- Ordered by: `join_order`

#### transformation_library
Reusable SQL transformation templates.
- Primary Key: `transformation_id`
- Unique: `transformation_code`
- Protected: `is_system` (boolean)

#### mapping_feedback
User feedback on AI suggestions.
- Primary Key: `feedback_id`
- Links to: source and target fields
- Tracks: accepted/rejected suggestions

### Migration from V1

If upgrading from V1:
1. V1 uses single mapping table with struct columns
2. V2 uses normalized schema with separate tables
3. Migration scripts available in `database/` folder
4. Backup V1 data before migrating
5. Test migration in non-production first

---

## Troubleshooting

### Transformation Library Issues

#### Cannot Edit/Delete Transformation
**Symptoms**: Edit/delete buttons are grayed out
**Cause**: Transformation is marked as system
**Solution**: System transformations are protected by design

#### Duplicate Code Error
**Symptoms**: "Transformation with code 'XXX' already exists"
**Cause**: Code must be unique across all transformations
**Solution**: Choose a different code or edit existing transformation

#### Expression Validation Error
**Symptoms**: "Expression must include {field} placeholder"
**Cause**: SQL expression missing required {field} placeholder
**Solution**: Add {field} to your expression where the field name should appear

### Vector Search Sync Issues

#### Sync Always Fails
**Symptoms**: Warning messages in logs, changes not reflected in AI
**Cause**: Vector search endpoint or permissions issue
**Solution**:
1. Check endpoint is running
2. Verify index exists
3. Check service principal permissions
4. Test sync manually via UI

#### Sync Succeeds But Changes Not Reflected
**Symptoms**: Success message but AI doesn't show new fields
**Cause**: Sync propagation delay
**Solution**: Wait 1-2 minutes for propagation, then test again

### Mapping Editor Issues

#### Cannot Change Target Field
**Symptoms**: Target field is grayed out in edit dialog
**Cause**: By design - target field changes not allowed
**Solution**: Delete mapping and recreate with correct target

#### Cannot Add Source Field
**Symptoms**: No button to add source fields in edit dialog
**Cause**: By design - source field list changes not allowed
**Solution**: Delete mapping and recreate with all desired source fields

### Database Issues

#### Warehouse Connection Timeout
**Symptoms**: "Database query timed out after 30 seconds"
**Cause**: Serverless warehouse cold start or complex query
**Solution**: Wait and retry, or use classic warehouse

#### Table Not Found
**Symptoms**: "Table 'catalog.schema.table_name' not found"
**Cause**: Table doesn't exist or configuration incorrect
**Solution**:
1. Verify table exists in Databricks
2. Check catalog and schema in configuration
3. Verify service principal has access

---

## Maintenance

### Regular Tasks

#### Daily
- ✅ Monitor system status dashboard
- ✅ Review error logs for issues
- ✅ Check user-reported problems
- ✅ Verify vector search sync working

#### Weekly
- ✅ Review semantic table for accuracy
- ✅ Check transformation library usage
- ✅ Monitor mapping activity trends
- ✅ Review and clean unused custom transformations

#### Monthly
- ✅ Audit admin group membership
- ✅ Review configuration for updates needed
- ✅ Clean up old or incorrect mappings
- ✅ Update documentation as needed
- ✅ Test disaster recovery procedures

### Backup Strategy

#### Configuration
- Backup `app_config.json` regularly
- Store in version control
- Document all configuration changes

#### Database Tables
- Use Databricks table snapshots
- Export critical tables periodically
- Test restore procedures
- Document backup schedule

#### Transformation Library
- Export transformations to SQL script
- Version control custom transformations
- Document transformation purposes

### Updates and Upgrades

#### Application Updates
1. Review release notes
2. Test in non-production environment
3. Backup current configuration and data
4. Deploy new version
5. Verify system status
6. Test key workflows
7. Monitor for issues
8. Update documentation

---

## Security

### Authentication
- Users authenticated via Databricks OAuth
- Email captured from request headers
- No separate login required

### Authorization
- Admin access via Databricks group membership
- Row-level filtering by `mapped_by` field
- Transformation library changes admin-only

### Data Access
- Users see only their own mappings
- Admins can view all data via direct database access
- Service principal has full read/write to tables

### Best Practices
1. ✅ Use service principal for app deployment
2. ✅ Limit admin group membership
3. ✅ Enable audit logging in Databricks
4. ✅ Review access logs regularly
5. ✅ Use HTTPS only (enforced by Databricks Apps)
6. ✅ Keep dependencies updated
7. ✅ Monitor for suspicious activity
8. ✅ Document security procedures

---

## Support and Resources

### Documentation
- **Quick Start**: [docs/QUICK_START.md](QUICK_START.md)
- **User Guide**: [docs/USER_GUIDE.md](USER_GUIDE.md)
- **Developer Guide**: [docs/DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Database Schema**: [database/V2_SCHEMA_DIAGRAM.md](../database/V2_SCHEMA_DIAGRAM.md)

### Getting Help
1. Review this admin guide
2. Check system logs
3. Review Databricks documentation
4. Contact development team

---

**Version**: 2.0  
**Last Updated**: November 2025  
**New Features**: Transformation library management, Vector search auto-sync, Multi-field mapping administration, Mapping editor
