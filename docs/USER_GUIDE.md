# Source-to-Target Mapping Platform - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Dashboard Overview](#dashboard-overview)
4. [Creating Mappings](#creating-mappings)
5. [Multi-Field Mappings](#multi-field-mappings)
6. [Using Transformations](#using-transformations)
7. [AI-Powered Suggestions](#ai-powered-suggestions)
8. [Manual Search](#manual-search)
9. [Managing Mappings](#managing-mappings)
10. [Editing Mappings](#editing-mappings)
11. [Best Practices](#best-practices)
12. [FAQ](#faq)

---

## Introduction

The Source-to-Target Mapping Platform helps you map source database fields to target semantic fields using AI-powered suggestions and manual search capabilities. **Version 2.0** introduces multi-field mapping, transformation library, and mapping editing capabilities.

### Key Features
- 🤖 **AI-Powered Suggestions**: Get intelligent field mapping recommendations
- 🔄 **Multi-Field Mapping**: Map multiple source fields to one target field
- 🔧 **Transformation Library**: Apply pre-built or custom SQL transformations
- ✏️ **Mapping Editor**: Edit transformations and join conditions without recreating
- 🔗 **Join Support**: Define joins across multiple source tables
- 🔍 **Manual Search**: Search and select target fields manually
- 📊 **Real-Time Status**: Monitor system health and configuration

---

## Getting Started

### Accessing the Application
1. Navigate to your Databricks App URL
2. You will be automatically authenticated using your Databricks account
3. Your user type (Admin/User) will be displayed in the header

### User Roles
- **Admin**: Full access including transformation library management
- **User**: Access to all mapping features

### Navigation Menu
- **Home**: System status and quick links
- **Create Mappings**: Main workspace for creating new mappings
- **View Mappings**: Browse and manage existing mappings
- **Semantic Management** (Admin): Manage target field definitions
- **Transformation Management** (Admin): Transformation library management
- **Settings** (Admin): System configuration

---

## Dashboard Overview

### Home Page
The home page shows system status indicators:

- **Database Connection**: SQL warehouse connectivity
- **Vector Search Status**: AI search engine availability
- **AI Model Status**: Suggestion engine readiness
- **Configuration Validity**: System settings verification

All should show green ✅ for optimal performance. Contact your administrator if any checks fail.

---

## Creating Mappings

### Workflow Overview
1. Select source field(s) from unmapped fields
2. Choose target field (AI suggestions or manual search)
3. Configure transformations and concatenation
4. Define join conditions (if needed)
5. Save mapping

### Step-by-Step Process

#### 1. Access Create Mappings Page
- Click **"Create Mappings"** in the sidebar
- View your unmapped source fields table
- Use search to filter specific fields

#### 2. Select Source Fields
**Single Field:**
- Click checkbox next to one field
- Click **"Map Selected Fields"** button

**Multiple Fields:**
- Click checkboxes next to related fields (e.g., FIRST_NAME, LAST_NAME)
- Click **"Map Selected Fields"** button
- These will be combined into one target field

#### 3. Choose Target Field

**Option A: AI Suggestions**
1. Review AI configuration settings
2. Click **"🤖 Get AI Suggestions"**
3. Wait 15-25 seconds
4. Review suggestions with confidence scores
5. Click **"Select"** on best match

**Option B: Manual Search**
1. Enter search term in search box
2. Click **"🔍 Search"**
3. Browse results
4. Click **"Select"** on desired field

#### 4. Configure Mapping
The mapping configuration wizard opens with selected fields.

---

## Multi-Field Mappings

### What is Multi-Field Mapping?
Combine multiple source fields into a single target field with customizable concatenation and transformations.

### Use Cases
- **Full Name**: FIRST_NAME + LAST_NAME → full_name
- **Address**: STREET + CITY + STATE + ZIP → full_address
- **Date-Time**: DATE + TIME → datetime_stamp
- **Identifiers**: PREFIX + ID + SUFFIX → complete_id

### Concatenation Strategies

#### SPACE
Joins fields with a single space.
```
John + Doe = "John Doe"
```

#### COMMA
Joins fields with comma and space.
```
John + Doe = "John, Doe"
```

#### PIPE
Joins fields with pipe delimiter.
```
John + Doe = "John|Doe"
```

#### CUSTOM
Use your own separator.
```
Separator: " - "
John + Doe = "John - Doe"
```

#### NONE
No concatenation (useful for overwrite scenarios).
```
John + Doe = "Doe" (uses last field)
```

### Field Order
Fields are concatenated in the order you selected them. Order is preserved and displayed as badges (1️⃣, 2️⃣, 3️⃣, etc.).

---

## Using Transformations

### What are Transformations?
SQL expressions applied to source fields before mapping. Transform data to match target requirements.

### Transformation Library
Pre-built transformations managed by administrators:

#### String Transformations
- **TRIM**: Remove leading/trailing whitespace
- **UPPER**: Convert to uppercase
- **LOWER**: Convert to lowercase
- **INITCAP**: Capitalize first letter of each word
- **TRIM_UPPER**: Trim and convert to uppercase
- **TRIM_LOWER**: Trim and convert to lowercase

#### Data Type Conversions
- **CAST_STRING**: Convert to string
- **CAST_INT**: Convert to integer
- **CAST_DATE**: Convert to date
- **CAST_TIMESTAMP**: Convert to timestamp

#### Null Handling
- **COALESCE**: Replace NULL with empty string
- **COALESCE_ZERO**: Replace NULL with zero

#### Custom Transformations
Enter any valid SQL expression using `{field}` as placeholder.

### Applying Transformations

#### In Mapping Wizard
1. For each source field, find the transformation dropdown
2. Select from library or choose custom
3. Enter custom SQL if needed
4. Preview shows the expression

#### Example: Clean and Uppercase Name
```
Source: first_name
Transformation: TRIM_UPPER
Result: UPPER(TRIM(first_name))
```

#### Example: Custom Phone Format
```
Source: phone_number
Transformation: Custom
Expression: REGEXP_REPLACE({field}, '[^0-9]', '')
Result: REGEXP_REPLACE(phone_number, '[^0-9]', '')
```

### Transformation Expression Preview
The final SQL expression is shown in the mapping wizard, combining:
- Individual field transformations
- Concatenation strategy
- Join conditions (if applicable)

---

## AI-Powered Suggestions

### How AI Works
1. **Vector Search**: Finds semantically similar target fields
2. **Confidence Scoring**: Ranks matches by relevance
3. **Context Analysis**: Uses field names, descriptions, and data types

### Using AI Suggestions

#### Configuration Options
- **Number of Vector Results**: Candidates to retrieve (default: 25)
- **Number of AI Results**: Suggestions to display (default: 10)
- **User Feedback**: Optional context (e.g., "Focus on patient fields", "Date fields only")

#### Generating Suggestions
1. Select source field(s)
2. Click "Map Selected Fields"
3. Click **"🤖 Get AI Suggestions"**
4. Wait for processing (15-25 seconds)

#### Reviewing Suggestions
Each suggestion displays:
- **Rank**: Order by confidence
- **Target Table & Column**: Destination field
- **Physical Names**: Actual database names
- **Confidence Score**: 0.0 to 1.0 scale
  - 0.8-1.0: Excellent match
  - 0.6-0.8: Good match
  - 0.4-0.6: Possible match
  - <0.4: Consider manual search
- **Reasoning**: Why this match was suggested

#### Selecting a Suggestion
1. Review top 3-5 suggestions
2. Check confidence scores
3. Read reasoning
4. Click **"Select"** on best match
5. Proceed to mapping configuration

### Tips for Better Suggestions
- ✅ Select related fields together for multi-field suggestions
- ✅ Provide clear, descriptive source field names
- ✅ Use the User Feedback field for context
- ✅ Ensure source fields have good descriptions/comments

---

## Manual Search

### When to Use Manual Search
- AI suggestions have low confidence
- You know the exact target field needed
- Special business rules apply
- Need to explore available target fields

### Searching

#### Step 1: Enter Search Term
Type in the search box. Search covers:
- Target table names
- Target column names
- Field descriptions/comments

#### Step 2: Execute Search
1. Click **"🔍 Search"**
2. Results load (up to 50 matches)
3. Results sorted by table and column name

#### Step 3: Review Results
Browse the results table showing:
- Target table and column names
- Physical names
- Data types
- Descriptions

#### Step 4: Select Target
1. Find the desired field
2. Click **"Select"** button
3. Proceed to mapping configuration

### Search Tips
- Try partial names: "patient" finds "patient_demographics"
- Use domain terms: "identifier", "date", "code"
- Search descriptions if field names don't match
- Try variations if first search yields no results

---

## Managing Mappings

### Viewing Mappings

#### Access View Mappings Page
- Click **"View Mappings"** in sidebar
- See all your completed mappings
- Mappings display as expandable rows

#### Understanding the Mappings List
Each mapping shows:
- **Target Field**: Destination table.column
- **Source Fields**: Origin fields (badges show count)
- **Concatenation**: Strategy used
- **Transformations**: Indicator if transformations applied
- **Status**: Active/Inactive
- **Created**: Date and time
- **Actions**: View, Edit, Delete buttons

#### View Mapping Details
Click the **eye icon** (👁️) to see:
- Complete source field list with order
- All transformations
- Concatenation details
- Join conditions
- SQL expression
- Metadata (created by, date)

### Search and Filter
Use the search box to filter by:
- Target table or column name
- Source table or column name
- Any visible field content

---

## Editing Mappings

### What Can Be Edited
✅ **Allowed:**
- Transformation expressions for existing source fields
- Concatenation strategy and separator
- Join conditions (add, modify, remove)

❌ **Not Allowed** (requires delete + recreate):
- Target field
- Add or remove source fields
- Change field order

### Edit Process

#### Step 1: Open Editor
1. Go to **View Mappings** page
2. Find the mapping to edit
3. Click the **pencil icon** (✏️)
4. Edit dialog opens

#### Step 2: Review Current Settings
The dialog shows:
- **Target Field** (read-only, grayed out)
- **Source Fields** with current transformations
- **Concatenation** strategy
- **Join Conditions** (if any)

#### Step 3: Make Changes

**Edit Transformations:**
- For each source field, use the dropdown
- Select from transformation library
- Or enter custom SQL expression
- Expression updates immediately

**Change Concatenation:**
- Select new strategy from dropdown
- If CUSTOM, enter separator
- Preview updates automatically

**Manage Joins:**
- Click **"+ Add Join"** to create new
- Edit existing join fields inline
- Click trash icon to remove join
- Support for LEFT, RIGHT, INNER, FULL joins

#### Step 4: Save Changes
1. Review all modifications
2. Click **"Save Changes"**
3. Mapping updates immediately
4. List refreshes automatically

### Edit Examples

#### Example 1: Change Transformation
**Before:** `TRIM(first_name)`
**Edit:** Change dropdown to "Trim and Upper"
**After:** `UPPER(TRIM(first_name))`

#### Example 2: Add Join Condition
**Before:** No joins
**Edit:** Add LEFT JOIN t_address ON t_member.member_id = t_address.member_id
**After:** Multi-table mapping with join

#### Example 3: Change Concatenation
**Before:** SPACE strategy
**Edit:** Change to PIPE strategy
**After:** Fields joined with | instead of space

---

## Best Practices

### For Efficient Mapping
1. ✅ Start with AI suggestions for most fields
2. ✅ Use manual search for special cases
3. ✅ Group related fields for multi-field mappings
4. ✅ Apply transformations from the library
5. ✅ Edit existing mappings instead of recreating

### For Data Quality
1. ✅ Verify data types match target requirements
2. ✅ Test transformations with sample data
3. ✅ Use appropriate concatenation strategies
4. ✅ Document custom transformations
5. ✅ Review AI confidence scores carefully

### For Multi-Field Mappings
1. ✅ Select fields in logical order
2. ✅ Choose appropriate concatenation strategy
3. ✅ Apply consistent transformations (e.g., TRIM all)
4. ✅ Test final expression with sample data
5. ✅ Use NONE strategy only when appropriate

### For Transformations
1. ✅ Start with library transformations
2. ✅ Test custom SQL expressions before applying
3. ✅ Keep expressions simple and readable
4. ✅ Document complex custom transformations
5. ✅ Reuse common patterns via transformation library

### For Join Conditions
1. ✅ Define all necessary joins upfront
2. ✅ Use appropriate join types (LEFT, INNER, etc.)
3. ✅ Verify join columns match data types
4. ✅ Document join logic for future reference
5. ✅ Test multi-table mappings carefully

---

## FAQ

### General Questions

**Q: What's new in Version 2.0?**  
A: Multi-field mapping, transformation library, mapping editor, and join support.

**Q: Can I map multiple source fields to one target?**  
A: Yes! Select multiple fields before creating the mapping.

**Q: What's the difference between V1 and V2 mappings?**  
A: V2 supports multiple source fields per target, transformations, and joins. V1 was 1-to-1 only.

**Q: Why can't I access Transformation Management?**  
A: Only users with Admin role can access transformation library management.

### Creating Mappings

**Q: How many source fields can I select?**  
A: You can select as many as needed. Common patterns are 2-4 fields.

**Q: What if my fields are in different tables?**  
A: Use join conditions to define relationships between tables.

**Q: Can I map one field without transformations?**  
A: Yes, just don't select any transformation (leave dropdown empty).

**Q: What happens if I select fields in wrong order?**  
A: Delete the mapping and recreate with correct order. Field order cannot be edited.

### Transformations

**Q: Where do transformations come from?**  
A: System transformations are pre-loaded. Admins can add custom ones to the library.

**Q: Can I write my own transformation?**  
A: Yes, select "Custom" and enter any valid SQL expression.

**Q: What is the {field} placeholder?**  
A: It's replaced with the actual field name at runtime. Use it in custom transformations.

**Q: Can I chain multiple transformations?**  
A: Yes, in custom expressions. Example: `UPPER(TRIM(COALESCE(field, '')))`

### AI Suggestions

**Q: Why no AI suggestions?**  
A: Check system status - Vector Search and AI Model must be ready.

**Q: Can I improve AI suggestions?**  
A: Yes, use User Feedback field and ensure source fields have good descriptions.

**Q: What if AI suggests wrong field?**  
A: Use manual search or try different source field selections.

**Q: How long should AI take?**  
A: Typically 15-25 seconds. Longer times may indicate system issues.

### Editing Mappings

**Q: Can I add another source field after saving?**  
A: No, you must delete and recreate the mapping with all desired fields.

**Q: Can I change the target field?**  
A: No, you must delete and recreate the mapping with the new target.

**Q: Why can't I change field order?**  
A: Order affects concatenation result. Changing it would alter the mapping's meaning.

**Q: What happens if I edit a transformation?**  
A: The SQL expression updates immediately. Source data isn't affected until ETL runs.

### Troubleshooting

**Q: Page is loading slowly**  
A: SQL warehouse may be starting up (serverless). Wait and retry.

**Q: Changes aren't showing**  
A: Refresh the page or check if there was an error during save.

**Q: I see duplicate mappings**  
A: Each mapping is unique by target field. Check if mapping was created multiple times.

**Q: Error when saving mapping**  
A: Check for:
- Required fields filled
- Valid SQL expressions
- Join columns exist
- Network connectivity

---

## Keyboard Shortcuts

- **Ctrl/Cmd + K**: Focus search box
- **Esc**: Close dialogs
- **Enter**: Submit search/form (when focused)

---

## Getting Help

If you need assistance:
1. Review this user guide
2. Check the Quick Start guide
3. Verify system status on Home page
4. Contact your administrator
5. Check with the development team

---

**Version**: 2.0  
**Last Updated**: November 2025  
**New Features**: Multi-field mapping, Transformation library, Mapping editor, Join support
