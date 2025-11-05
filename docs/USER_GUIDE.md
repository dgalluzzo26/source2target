# Source-to-Target Mapping Tool - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Dashboard Overview](#dashboard-overview)
4. [Field Mapping](#field-mapping)
5. [AI-Powered Mapping](#ai-powered-mapping)
6. [Manual Search](#manual-search)
7. [Managing Mappings](#managing-mappings)
8. [Templates](#templates)
9. [FAQ](#faq)

---

## Introduction

The Source-to-Target Mapping Tool helps you map source database fields to target semantic fields using AI-powered suggestions and manual search capabilities. This tool streamlines the data mapping process and ensures consistency across your data integration projects.

### Key Features
- 🤖 **AI-Powered Suggestions**: Get intelligent field mapping recommendations
- 🔍 **Manual Search**: Search and select target fields manually
- 📊 **Real-Time Status**: Monitor system health and configuration
- 📁 **Bulk Operations**: Upload/download field mappings via CSV templates
- 🔒 **User Permissions**: Role-based access control for admins and users

---

## Getting Started

### Accessing the Application
1. Navigate to your Databricks App URL
2. You will be automatically authenticated using your Databricks account
3. Your user type (Admin/User) will be displayed in the header

### User Roles
- **Admin**: Full access to all features including configuration and semantic table management
- **User**: Access to field mapping features only

---

## Dashboard Overview

The main navigation menu provides access to:

### 📊 Introduction
- System status overview
- Quick access to key features
- System health indicators:
  - Database Connection
  - Vector Search Status
  - AI Model Status
  - Configuration Validity

### 🗺️ Field Mapping
Your primary workspace for mapping source fields to target fields.

### ⚙️ Configuration (Admin Only)
- Database settings
- Vector Search configuration
- AI Model configuration
- Admin group settings

### 📋 Semantic Table (Admin Only)
- View and manage semantic field definitions
- Add, edit, and delete semantic records

---

## Field Mapping

The Field Mapping page is divided into three main sections:

### 1. Unmapped Fields
**Purpose**: Shows source fields that haven't been mapped to target fields yet.

**Features**:
- Search/filter unmapped fields
- View field metadata (name, datatype, nullable, comments)
- Select a field to start mapping

**How to Use**:
1. Browse or search for an unmapped field
2. Click on a row to select it
3. The selected field will be highlighted
4. Use AI Suggestions or Manual Search to find a target field

### 2. Mapped Fields
**Purpose**: Shows source fields that have already been mapped.

**Features**:
- View existing mappings
- Search/filter mapped fields
- Delete mappings (unmaps the field)

**How to Delete a Mapping**:
1. Find the mapped field
2. Click the trash icon in the Actions column
3. Confirm the deletion
4. The field will move back to Unmapped Fields

### 3. Selected Field Details
When you select an unmapped field, this section displays:
- Source table and column names
- Physical names
- Data type
- Nullable status
- Comments/description

---

## AI-Powered Mapping

### How AI Suggestions Work
The AI system uses:
1. **Vector Search**: Finds semantically similar target fields
2. **Confidence Scores**: Ranks suggestions by relevance
3. **Context**: Uses field names, descriptions, and data types

### Using AI Suggestions

#### Step 1: Configure AI Settings
- **Number of Vector Results**: How many candidates to retrieve (default: 25)
- **Number of AI Results**: How many suggestions to display (default: 10)
- **User Feedback**: Optional text to guide the AI (e.g., "Focus on patient fields")

#### Step 2: Generate Suggestions
1. Select an unmapped source field
2. Adjust AI settings if needed
3. Click "🤖 Generate AI Mapping Suggestions"
4. Wait for suggestions to load

#### Step 3: Review Suggestions
Each suggestion shows:
- **Rank**: Order by confidence score
- **Target Table**: Logical table name
- **Target Column**: Logical column name
- **Physical Names**: Actual database names
- **Confidence Score**: How confident the AI is (0-1 scale)
- **Reasoning**: Why this mapping was suggested

#### Step 4: Select a Mapping
1. Review the suggestions
2. Click "Select Target" on the best match
3. The mapping is saved automatically
4. The field moves from Unmapped to Mapped

### Tips for Best Results
- ✅ Fill in source field comments/descriptions when possible
- ✅ Use User Feedback to provide context
- ✅ Review confidence scores - higher is better
- ✅ Start with AI suggestions before manual search

---

## Manual Search

### When to Use Manual Search
- When AI suggestions don't provide good matches
- When you know the exact target field you need
- For special cases requiring human judgment

### How to Search

#### Step 1: Select Source Field
1. Choose an unmapped field from the table
2. The field details will appear below

#### Step 2: Enter Search Term
1. Type your search term in the manual search box
2. Search by:
   - Target table name
   - Target column name
   - Field description/comments

#### Step 3: Execute Search
1. Click "🔍 Search Semantic Table"
2. Wait for results (up to 50 matches)
3. Results are sorted by table and column name

#### Step 4: Select Target Field
1. Review the search results table
2. Click "Select Target" on the desired field
3. The mapping is saved automatically
4. Search results are cleared

### Search Tips
- 🔍 Use partial names (e.g., "patient" finds "patient_demographics")
- 🔍 Search by domain terms (e.g., "identifier", "date", "code")
- 🔍 Try different variations if first search yields no results

---

## Managing Mappings

### Viewing Mapped Fields
1. Go to the "Mapped Fields" tab
2. Use the search box to filter mappings
3. View source and target field details

### Deleting a Mapping
1. Locate the mapped field
2. Click the 🗑️ (trash) icon
3. Confirm the deletion in the dialog
4. The field returns to "Unmapped Fields"

### Why Delete a Mapping?
- Incorrect mapping was selected
- Requirements changed
- Need to remap to a different target field

---

## Templates

Templates allow bulk upload of source fields for mapping.

### Downloading a Template

#### Purpose
Get a CSV template with the correct format and an example row.

#### Steps
1. Go to the "Unmapped Fields" section
2. Click "Download Template" button
3. A CSV file will download with:
   - Column headers
   - One example row showing the format

### Uploading a Template

#### Purpose
Add multiple source fields at once for future mapping.

#### Steps
1. Fill in the CSV template with your source fields:
   - `src_table_name`: Source table name
   - `src_column_name`: Source column name
   - `src_column_physical_name`: Physical column name
   - `src_nullable`: "Null" or "Not Null"
   - `src_physical_datatype`: Data type (STRING, INT, etc.)
   - `src_comments`: Field description

2. Click "Upload Template" button
3. Select your filled CSV file
4. Wait for upload to complete
5. Review the results:
   - ✅ Successfully added
   - ⏭️ Skipped (duplicates)
   - ❌ Failed (with error messages)

#### Important Notes
- 📝 Template is for adding **source fields only**
- 📝 Uploaded fields start as **unmapped**
- 📝 You must map them using AI or manual search
- 📝 Duplicates are automatically skipped
- 📝 Only source columns are required

---

## FAQ

### General Questions

**Q: Why can't I see the Configuration page?**  
A: Only users with Admin role can access Configuration and Semantic Table pages. Contact your administrator if you need admin access.

**Q: How do I know if a mapping is good?**  
A: Check the confidence score (higher is better), review the field names and descriptions, and verify the data types match your requirements.

**Q: Can I change a mapping after saving it?**  
A: Yes, delete the existing mapping and create a new one with the correct target field.

### AI Suggestions

**Q: Why am I not getting any AI suggestions?**  
A: Check that:
- Vector Search is available (see system status)
- AI Model is ready (see system status)
- The source field has sufficient metadata (name, comments)

**Q: What's a good confidence score?**  
A: Scores range from 0 to 1:
- 0.8-1.0: Excellent match
- 0.6-0.8: Good match, review carefully
- 0.4-0.6: Possible match, use judgment
- Below 0.4: Consider manual search

**Q: Can I influence the AI suggestions?**  
A: Yes! Use the "User Feedback" field to provide context like "Focus on patient demographics" or "Look for date fields".

### Manual Search

**Q: Why are my search results empty?**  
A: Try:
- Using broader search terms
- Checking spelling
- Searching by field description instead of name
- Verifying the target field exists in the semantic table

**Q: How many results will I see?**  
A: Manual search returns up to 50 matching records.

### Templates

**Q: What happens if I upload duplicate fields?**  
A: Duplicates are automatically skipped. Only new fields are added.

**Q: Can I include target mappings in the upload?**  
A: No, templates are for adding source fields only. Use AI or manual search to map them to targets.

**Q: My upload failed. What should I do?**  
A: Check that:
- File is in CSV format
- All required columns are present
- Field names don't contain special characters
- File size is reasonable (under 10MB)

### Troubleshooting

**Q: The page is loading slowly**  
A: This can happen if:
- The data warehouse is starting up (serverless)
- Large number of records are being loaded
- Network connectivity issues

**Q: I see an error message**  
A: Try:
1. Refresh the page
2. Check the system status on the Introduction page
3. Contact your administrator if the issue persists

**Q: My changes aren't showing**  
A: Click the refresh button or reload the page to fetch the latest data.

---

## Best Practices

### For Efficient Mapping
1. ✅ Start with AI suggestions for most fields
2. ✅ Use manual search for special cases
3. ✅ Review confidence scores before accepting
4. ✅ Add good descriptions to source fields
5. ✅ Work in batches to maintain context

### For Data Quality
1. ✅ Verify data types match
2. ✅ Check nullable constraints
3. ✅ Review physical names for accuracy
4. ✅ Document any special mapping rules

### For Team Collaboration
1. ✅ Use consistent naming conventions
2. ✅ Add clear field descriptions
3. ✅ Review others' mappings periodically
4. ✅ Communicate mapping decisions

---

## Getting Help

If you need assistance:
1. Review this user guide
2. Check the system status on the Introduction page
3. Contact your administrator
4. Reach out to the development team

---

**Version**: 1.0  
**Last Updated**: November 2025

