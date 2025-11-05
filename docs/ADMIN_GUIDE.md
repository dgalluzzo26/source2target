# Source-to-Target Mapping Tool - Administrator Guide

## Table of Contents
1. [Administrator Overview](#administrator-overview)
2. [User Management](#user-management)
3. [Configuration Management](#configuration-management)
4. [Semantic Table Management](#semantic-table-management)
5. [System Monitoring](#system-monitoring)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)
8. [Security](#security)

---

## Administrator Overview

As an administrator, you have full access to all features and are responsible for:
- Managing user access and permissions
- Configuring system settings
- Maintaining the semantic table
- Monitoring system health
- Troubleshooting issues

### Admin Identification
Admins are identified by:
- Green "Admin" badge in the header
- Access to Configuration and Semantic Table pages
- Membership in the configured admin group

---

## User Management

### Admin Group Configuration

#### Setting Up Admin Access
1. Go to **Configuration** → **Admin Group**
2. Enter the Databricks workspace group name
3. Click **Save**
4. Members of this group will have admin access

#### Group Membership
- Users are automatically identified by their Databricks email
- Admin status is checked via Databricks Workspace API
- Group membership is cached during the session

#### Best Practices
- ✅ Use a dedicated admin group (e.g., "source2target_admins")
- ✅ Limit admin access to trusted users
- ✅ Review group membership regularly
- ✅ Document who has admin access

### User Permissions

| Permission | Admin | User |
|------------|-------|------|
| View Introduction | ✅ | ✅ |
| Field Mapping | ✅ | ✅ |
| AI Suggestions | ✅ | ✅ |
| Manual Search | ✅ | ✅ |
| Upload/Download Templates | ✅ | ✅ |
| Configuration | ✅ | ❌ |
| Semantic Table | ✅ | ❌ |

### Monitoring User Activity
- User email is captured in `source_owners` field
- Each user only sees their own mappings
- Audit trail via database queries

---

## Configuration Management

### Database Configuration

#### Settings
1. **Server Hostname**: Databricks workspace hostname
   - Format: `your-workspace.cloud.databricks.com`
   - Get from Databricks workspace URL

2. **HTTP Path**: SQL Warehouse or Cluster HTTP path
   - Format: `/sql/1.0/warehouses/abc123def456`
   - Get from SQL Warehouse → Connection Details

3. **Mapping Table**: Full table name for mappings
   - Format: `catalog.schema.table_name`
   - Example: `prod_db.mapping.source_to_target`

4. **Semantic Table**: Full table name for semantic definitions
   - Format: `catalog.schema.table_name`
   - Example: `prod_db.semantic.target_fields`

#### Setup Steps
1. Navigate to **Configuration** → **Database**
2. Fill in all required fields
3. Click **Save Configuration**
4. Verify connection on Introduction page

#### Validation
The system checks:
- ✅ Server hostname format
- ✅ HTTP path format
- ✅ Table names contain catalog and schema
- ⚠️ Connection test is performed on system startup

### Vector Search Configuration

#### Settings
1. **Index Name**: Vector search index name
   - Format: `catalog.schema.index_name`
   - Example: `prod_db.semantic.vector_search_idx`
   - Must be created separately in Databricks

2. **Endpoint Name**: Vector search endpoint
   - Example: `s2t_vsendpoint`
   - Must be running and accessible

#### Setup Steps
1. Create vector search endpoint in Databricks first
2. Create vector search index on semantic table
3. Enter names in Configuration → Vector Search
4. Save configuration

#### Testing
- Check "Vector Search Available" on Introduction page
- Should show "✓ Available" if configured correctly

### AI Model Configuration

#### Settings
1. **Foundation Model Endpoint**: Databricks Model Serving endpoint
   - Example: `databricks-meta-llama-3-1-70b-instruct`
   - Must be a deployed and running endpoint

2. **Previous Mappings Table**: Optional table for historical mappings
   - Format: `catalog.schema.table_name`
   - Used for learning from past mappings

#### Setup Steps
1. Deploy AI model in Databricks Model Serving
2. Get endpoint name
3. Enter in Configuration → AI Model
4. Save configuration

#### Testing
- Check "AI Model Ready" on Introduction page
- Status should be "Ready" for full functionality

### Configuration File

#### Local Storage
Configuration is stored in `app_config.json` at the app root:
```json
{
  "database": {
    "server_hostname": "workspace.cloud.databricks.com",
    "http_path": "/sql/1.0/warehouses/...",
    "mapping_table": "catalog.schema.mapping",
    "semantic_table": "catalog.schema.semantic"
  },
  "vector_search": {
    "index_name": "catalog.schema.vs_index",
    "endpoint_name": "endpoint_name"
  },
  "ai_model": {
    "foundation_model_endpoint": "model_endpoint",
    "previous_mappings_table_name": "catalog.schema.prev_mappings"
  },
  "admin_group": {
    "group_name": "admin_group_name"
  }
}
```

#### Backup and Restore
1. **Backup**: Copy `app_config.json` to safe location
2. **Restore**: Replace `app_config.json` and restart app
3. **Version Control**: Consider storing in git (without sensitive data)

---

## Semantic Table Management

### Overview
The semantic table defines all possible target fields that source fields can be mapped to.

### Viewing Semantic Records
1. Go to **Semantic Table** page
2. Browse all target field definitions
3. Use search to filter records
4. View: table names, columns, data types, descriptions

### Adding Records

#### Manual Addition
1. Click **"Bulk Add from CSV"** button (currently disabled)
2. Alternatively, use database tools to insert records

#### Required Fields
- `tgt_table_name`: Logical target table name
- `tgt_column_name`: Logical target column name
- `tgt_table_physical_name`: Physical database table
- `tgt_column_physical_name`: Physical database column
- `tgt_physical_datatype`: Data type
- `tgt_nullable`: "Null" or "Not Null"
- `tgt_comments`: Description (important for AI matching!)

#### Best Practices
- ✅ Provide detailed, accurate descriptions
- ✅ Use consistent naming conventions
- ✅ Include all possible target fields
- ✅ Update descriptions as requirements change

### Editing Records
1. Click the ✏️ edit icon on any record
2. Modify fields in the dialog
3. Click **Save** to commit changes
4. Changes take effect immediately

### Deleting Records
1. Click the 🗑️ delete icon on any record
2. Confirm deletion
3. ⚠️ **Warning**: This cannot be undone
4. Check for existing mappings first

### Vector Search Index
After modifying semantic records:
1. Vector search index should auto-update
2. If not, manually trigger index refresh in Databricks
3. Test AI suggestions to verify

---

## System Monitoring

### System Status Dashboard

#### Database Connection
- **Status**: Connected / Failed
- **Checks**: SQL warehouse accessibility, authentication
- **Troubleshooting**: 
  - Verify warehouse is running
  - Check OAuth permissions
  - Validate HTTP path

#### Vector Search
- **Status**: Available / Unavailable
- **Checks**: Endpoint running, index accessible
- **Troubleshooting**:
  - Verify endpoint is running in Databricks
  - Check index exists and is synced
  - Validate endpoint name in config

#### AI Model
- **Status**: Ready / Not Ready / Not Configured
- **Checks**: Model endpoint status
- **Troubleshooting**:
  - Verify endpoint is deployed and running
  - Check model endpoint name in config
  - Review Databricks Model Serving logs

#### Configuration
- **Status**: Valid / Invalid
- **Checks**: All required fields present
- **Troubleshooting**:
  - Review Configuration page for missing fields
  - Validate field formats
  - Check for error messages

### Performance Monitoring

#### Query Performance
- Typical query times:
  - Unmapped fields: 5-10 seconds
  - Mapped fields: 5-10 seconds
  - Semantic table: 10-15 seconds
  - Vector search: 15-25 seconds

#### Slow Queries
If queries are slow:
1. Check warehouse state (serverless may need warmup)
2. Review data volume (large tables take longer)
3. Monitor warehouse utilization
4. Consider scaling up warehouse

#### Database Warehouse
- **Serverless**: Starts on-demand, fast once running
- **Classic**: Should be kept running for best performance
- **Recommendation**: Use serverless for cost, classic for speed

### Logging

#### Backend Logs
Located in Databricks app logs:
- Service initialization
- Database connections
- Query execution
- Error messages
- User actions

#### Log Levels
- `[Service Name]` prefix on all messages
- `ERROR` for failures
- `INFO` for successful operations
- `DEBUG` for detailed troubleshooting

#### Accessing Logs
1. Go to Databricks workspace
2. Navigate to Apps
3. Select your app
4. Click "Logs" tab
5. Filter by time period

---

## Troubleshooting

### Common Issues

#### Users Can't Access Configuration
**Symptoms**: Non-admin users see Configuration link  
**Solution**: 
1. Verify admin group name in Configuration
2. Check user is in correct group
3. Test group membership API call
4. Review backend logs for 403 errors

#### Database Connection Failed
**Symptoms**: "Database connection failed" on dashboard  
**Solution**:
1. Verify SQL warehouse is running
2. Check HTTP path is correct
3. Test OAuth token generation
4. Review backend logs for connection errors
5. Increase timeout if serverless

#### Vector Search Not Available
**Symptoms**: "Vector Search Unavailable" on dashboard  
**Solution**:
1. Verify endpoint is running in Databricks
2. Check index name matches configuration
3. Ensure index is synced
4. Test endpoint accessibility
5. Review endpoint logs

#### AI Model Not Ready
**Symptoms**: "AI Model not ready" or no suggestions  
**Solution**:
1. Check model endpoint is deployed
2. Verify endpoint is in "Ready" state
3. Confirm endpoint name in configuration
4. Test endpoint with sample query
5. Review model serving logs

#### Mappings Not Saving
**Symptoms**: User reports mapping saved but doesn't appear  
**Solution**:
1. Check database write permissions
2. Verify source_owners filtering
3. Review backend logs for errors
4. Test database UPDATE query manually
5. Confirm user email is captured correctly

#### Slow Performance
**Symptoms**: Queries timeout or take very long  
**Solution**:
1. Check warehouse state and size
2. Review data volume in tables
3. Increase query timeouts in code
4. Consider warehouse scaling
5. Optimize table indexes

### Error Messages

#### "Database query timed out after 30 seconds"
- **Cause**: Warehouse is cold-starting or query is complex
- **Fix**: Wait and retry, or increase timeout in code

#### "Vector search timed out"
- **Cause**: Endpoint not responding or index is large
- **Fix**: Check endpoint health, increase timeout

#### "Cannot verify user permissions"
- **Cause**: Unable to get user email from headers
- **Fix**: Check Databricks app authentication setup

#### "No matching fields found"
- **Cause**: Search term doesn't match any records
- **Fix**: User should try different search terms

---

## Maintenance

### Regular Tasks

#### Daily
- Monitor system status dashboard
- Review error logs for issues
- Check user-reported problems

#### Weekly
- Review semantic table for accuracy
- Check for duplicate or incorrect records
- Monitor mapping activity and trends

#### Monthly
- Audit admin group membership
- Review configuration for updates needed
- Clean up old or incorrect mappings
- Update documentation as needed

### Database Maintenance

#### Mapping Table
- Contains source-to-target mappings
- Filtered by `source_owners` per user
- Cleanup: Remove mappings for decommissioned sources

#### Semantic Table
- Contains all target field definitions
- Should be kept up-to-date with data model
- Cleanup: Remove obsolete target fields

#### Backup Strategy
1. Use Databricks table snapshots
2. Export critical tables to backup location
3. Test restore procedures
4. Document backup schedule

### Updates and Upgrades

#### Application Updates
1. Review release notes
2. Test in non-production environment
3. Backup current configuration
4. Deploy new version
5. Verify system status
6. Monitor for issues

#### Configuration Changes
1. Backup `app_config.json`
2. Make changes via UI
3. Test each component
4. Verify system status
5. Document changes

---

## Security

### Authentication
- Users authenticated via Databricks OAuth
- Email captured from `X-Forwarded-Email` header
- No separate login required

### Authorization
- Admin access via Databricks group membership
- Regular users limited to mapping features
- Row-level filtering by `source_owners`

### Data Access
- Users see only their own mappings
- Admins can view all data via direct database access
- Service principal has read/write to all tables

### Best Practices
1. ✅ Use service principal for app deployment
2. ✅ Limit admin group membership
3. ✅ Enable audit logging in Databricks
4. ✅ Review access logs regularly
5. ✅ Use HTTPS only (enforced by Databricks Apps)
6. ✅ Keep dependencies updated
7. ✅ Monitor for suspicious activity

### Compliance
- User actions tracked via `source_owners`
- Audit trail in database tables
- Access logs in Databricks
- GDPR: User data can be filtered/deleted by email

---

## Advanced Topics

### Custom SQL Queries

#### View All Mappings
```sql
SELECT 
  src_table_name,
  src_column_name,
  tgt_columns.tgt_table_name,
  tgt_columns.tgt_column_name,
  source_owners
FROM catalog.schema.mapping_table
WHERE tgt_columns IS NOT NULL
ORDER BY src_table_name, src_column_name
```

#### Find Unmapped Fields
```sql
SELECT 
  src_table_name,
  src_column_name,
  src_columns.src_comments
FROM catalog.schema.mapping_table
WHERE tgt_columns IS NULL 
   OR tgt_columns.tgt_column_name IS NULL
ORDER BY src_table_name, src_column_name
```

#### User Activity Report
```sql
SELECT 
  source_owners,
  COUNT(*) as total_mappings,
  COUNT(DISTINCT src_table_name) as tables_mapped
FROM catalog.schema.mapping_table
WHERE tgt_columns IS NOT NULL
GROUP BY source_owners
ORDER BY total_mappings DESC
```

### Extending the Application

#### Adding New Features
1. Review developer guide for architecture
2. Follow existing patterns for consistency
3. Test thoroughly in non-production
4. Update documentation
5. Train users on new features

#### Custom Integrations
- REST API endpoints available
- Can integrate with external tools
- Consider authentication requirements
- Document integration points

---

## Support and Resources

### Getting Help
1. Review this admin guide
2. Check developer documentation
3. Review Databricks documentation
4. Contact development team

### Useful Links
- Databricks SQL Warehouses
- Databricks Vector Search
- Databricks Model Serving
- Databricks Apps Documentation

### Contact Information
- **Development Team**: [Insert contact info]
- **Databricks Support**: [Insert support channel]
- **Emergency Contact**: [Insert emergency contact]

---

## Appendix

### Configuration Schema
See `backend/models/config.py` for complete configuration model.

### Database Schema
See `backend/models/` for table structures:
- `mapping.py`: MappedField, UnmappedField
- `semantic.py`: SemanticRecord

### API Endpoints
See `backend/routers/` for all available endpoints:
- `/api/auth/*`: Authentication
- `/api/system/*`: System status
- `/api/config/*`: Configuration
- `/api/semantic/*`: Semantic table
- `/api/mapping/*`: Field mapping
- `/api/ai-mapping/*`: AI suggestions

---

**Version**: 1.0  
**Last Updated**: November 2025

