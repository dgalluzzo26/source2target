# Mapping Export Feature

## Overview

The mapping export feature allows users to download all their mappings as a CSV file. Each mapping is exported as a **single row** containing all the information needed to generate complete SQL transformation logic.

---

## Features

### ✅ Single Row Per Mapping
Each mapping is exported as one CSV row, making it easy to:
- Generate ETL SQL scripts
- Document mappings for stakeholders
- Import into other tools
- Audit and review mappings

### ✅ Complete Mapping Details
Each row includes:
- Target field information
- All source fields (pipe-separated)
- Field transformations (pipe-separated)
- Concatenation strategy
- Join conditions (pipe-separated)
- Complete SQL transformation expression
- Metadata (who created, when, confidence score)

### ✅ User Filtering
- **Regular users**: Export only their own mappings
- **Admins**: Export all mappings from all users

---

## CSV Structure

### Columns

| Column | Description | Example |
|--------|-------------|---------|
| `mapping_id` | Unique mapping identifier | `123` |
| `target_table` | Target table logical name | `slv_member` |
| `target_table_physical` | Target table physical name | `slv_member` |
| `target_column` | Target column logical name | `full_name` |
| `target_column_physical` | Target column physical name | `full_name` |
| `source_tables` | Pipe-separated source tables | `t_member \| t_member` |
| `source_columns` | Pipe-separated source columns (in order) | `FIRST_NAME \| LAST_NAME` |
| `source_columns_physical` | Pipe-separated physical column names | `first_name \| last_name` |
| `field_order` | Pipe-separated field order numbers | `1 \| 2` |
| `field_transformations` | Pipe-separated transformations | `UPPER(TRIM(first_name)) \| UPPER(TRIM(last_name))` |
| `concat_strategy` | How fields are concatenated | `SPACE` |
| `concat_separator` | Custom separator (if CUSTOM strategy) | ` - ` |
| `transformation_expression` | Complete SQL expression | `CONCAT(UPPER(TRIM(first_name)), ' ', UPPER(TRIM(last_name)))` |
| `join_conditions` | Pipe-separated join conditions | `t_member.member_id INNER JOIN t_address.member_id` |
| `mapped_by` | User who created the mapping | `john.doe@example.com` |
| `mapped_at` | Timestamp when created | `2025-11-24T10:30:00` |
| `confidence_score` | AI confidence score (0.0-1.0) | `0.95` |
| `mapping_source` | How mapping was created | `AI` or `MANUAL` |
| `ai_reasoning` | AI explanation (if applicable) | `High semantic similarity...` |
| `mapping_status` | Status of the mapping | `ACTIVE` |

---

## Usage

### From the Frontend

1. Navigate to **View Mappings** page
2. Click the **"Export Mappings"** button in the toolbar
3. CSV file downloads automatically
4. Filename format: `mappings_export_YYYY-MM-DD.csv`

### From the API

**Endpoint:** `GET /api/v2/mappings/export`

**Authentication:** Required (via Databricks OAuth)

**Response:** CSV file with `Content-Disposition: attachment`

**Example:**
```bash
curl -X GET "https://your-app.databricks.com/api/v2/mappings/export" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output mappings_export.csv
```

---

## Example CSV Output

```csv
mapping_id,target_table,target_table_physical,target_column,target_column_physical,source_tables,source_columns,source_columns_physical,field_order,field_transformations,concat_strategy,concat_separator,transformation_expression,join_conditions,mapped_by,mapped_at,confidence_score,mapping_source,ai_reasoning,mapping_status
1,slv_member,slv_member,full_name,full_name,t_member | t_member,FIRST_NAME | LAST_NAME,first_name | last_name,1 | 2,UPPER(TRIM(first_name)) | UPPER(TRIM(last_name)),SPACE,,CONCAT(UPPER(TRIM(first_name)),' ',UPPER(TRIM(last_name))),,john.doe@example.com,2025-11-24T10:30:00,0.95,AI,High semantic similarity between fields,ACTIVE
2,slv_member,slv_member,mailing_address,mailing_address,t_address | t_address | t_address | t_address,STREET | CITY | STATE | ZIP,street | city | state | zip,1 | 2 | 3 | 4,TRIM(street) | TRIM(city) | TRIM(state) | TRIM(zip),COMMA,,CONCAT(TRIM(street),', ',TRIM(city),', ',TRIM(state),', ',TRIM(zip)),t_member.member_id INNER JOIN t_address.member_id,jane.smith@example.com,2025-11-24T11:00:00,,MANUAL,,ACTIVE
```

---

## Use Cases

### 1. Generate ETL Scripts
Use the exported data to automatically generate SQL transformation scripts:

```python
import pandas as pd

# Read export
df = pd.read_csv('mappings_export.csv')

# Generate SQL for each mapping
for _, row in df.iterrows():
    sql = f"""
    INSERT INTO {row['target_table_physical']} ({row['target_column_physical']})
    SELECT {row['transformation_expression']}
    FROM {row['source_tables'].split(' | ')[0]}
    """
    
    # Add joins if present
    if pd.notna(row['join_conditions']) and row['join_conditions']:
        joins = row['join_conditions'].split(' | ')
        for join in joins:
            sql += f"\n{join}"
    
    print(sql)
```

### 2. Documentation
Share the CSV with stakeholders for:
- Mapping review and approval
- Technical documentation
- Data lineage tracking
- Compliance audits

### 3. Bulk Analysis
Analyze mappings in spreadsheet tools:
- Count mappings by source table
- Identify most common transformations
- Find missing or unmapped fields
- Validate mapping completeness

### 4. Backup and Version Control
- Export mappings regularly for backup
- Track changes over time
- Compare mapping versions
- Restore mappings if needed

---

## Implementation Details

### Backend

**File:** `backend/routers/mapping_v2.py`

**Endpoint:** `@router.get("/export")`

**Key Features:**
- Uses `StreamingResponse` for efficient CSV delivery
- Respects user permissions (filtered exports)
- Includes all mapping relationships (details + joins)
- Generates filename with current date

### Frontend

**File:** `frontend/src/views/MappingsListView.vue`

**Function:** `handleExport()`

**Key Features:**
- Calls export API endpoint
- Downloads file automatically
- Shows toast notifications for progress/success/error
- Generates timestamped filename

---

## CSV Format Details

### Pipe Separator (`|`)
Multiple values within a single field are separated by ` | ` (pipe with spaces):
- Source fields: `FIRST_NAME | LAST_NAME`
- Transformations: `TRIM(a) | UPPER(b)`
- Joins: `table1.col1 JOIN table2.col2 | table2.col3 JOIN table3.col4`

**Why pipe?** 
- Comma is used in SQL and concat strategies
- Pipe is visually distinct
- Easy to split in code: `value.split(' | ')`

### Ordering
All multi-value fields maintain consistent ordering:
- Field 1: `source_tables[0]`, `source_columns[0]`, `field_transformations[0]`
- Field 2: `source_tables[1]`, `source_columns[1]`, `field_transformations[1]`
- etc.

This allows reconstruction of the exact field order for concatenation.

---

## Troubleshooting

### Export Button Not Visible
- Ensure you're on the "View Mappings" page
- Button is in the toolbar next to "Create New Mapping"

### Export Returns Empty File
- Check if you have any mappings created
- Regular users only see their own mappings
- Try logging in as admin to see all mappings

### Download Doesn't Start
- Check browser's download settings
- Allow downloads from the application domain
- Check browser console for errors

### CSV Opens Incorrectly in Excel
- Excel may misinterpret special characters
- Use "Import Data" feature in Excel instead of double-clicking
- Or use Google Sheets, which handles CSV better

---

## Future Enhancements

### Potential Improvements
- [ ] Filter export by date range
- [ ] Filter export by mapping status
- [ ] Export to other formats (JSON, Excel, SQL)
- [ ] Schedule automatic exports
- [ ] Include mapping validation results
- [ ] Add option to include/exclude specific columns

---

## API Response Examples

### Success Response
```
HTTP/1.1 200 OK
Content-Type: text/csv
Content-Disposition: attachment; filename=mappings_export.csv

mapping_id,target_table,target_table_physical...
1,slv_member,slv_member...
2,slv_member,slv_member...
```

### Error Response
```json
{
  "detail": "Error message here"
}
```

---

**Date:** November 24, 2025  
**Feature:** Mapping Export to CSV  
**Status:** ✅ Implemented and deployed

