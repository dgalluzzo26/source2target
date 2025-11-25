# Quick Start Guide

## Welcome to the Source-to-Target Mapping Platform! 🎉

This guide will get you started creating field mappings in just a few minutes using the V2 multi-field mapping system.

---

## Navigation Overview

The application has a clean sidebar navigation with two sections:

### 📊 Mapping Workflow (All Users)
- **Home** - System status and overview
- **Create Mappings** - Map source fields to targets
- **View Mappings** - Review and manage existing mappings

### 🔧 Administration (Admins Only)
- **Semantic Management** - Manage target field definitions
- **Transformation Management** - Transformation library management
- **Settings** - System configuration

---

## The 6-Step Mapping Process

Here's the complete workflow for creating a field mapping:

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Check System Status                                   │
│  ✅ Verify all systems are operational                         │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Navigate to Create Mappings                           │
│  ➕ Open the unmapped fields page                              │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Select Source Field(s)                                │
│  ☑️ Choose 1 or more fields → Click "Map Selected Fields"      │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Choose Target Field                                   │
│  🤖 Use AI Suggestions  OR  🔍 Manual Search                   │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: Configure Mapping                                     │
│  🔧 Set transformations + concatenation + joins                │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6: Save & Verify                                         │
│  💾 Save mapping → View in "View Mappings"                     │
└─────────────────────────────────────────────────────────────────┘
```

**Quick Summary:**
1. **Check** system status → 2. **Navigate** to Create Mappings → 3. **Select** source fields → 4. **Choose** target field → 5. **Configure** transformations → 6. **Save** and verify

---

## Step 1: Check System Status

1. Click **"Home"** in the left sidebar (🏠 icon)
2. Verify all system checks are green:
   - ✅ **Database Connection** - SQL warehouse connectivity
   - ✅ **Vector Search Available** - AI search engine ready
   - ✅ **AI Model Ready** - Suggestion engine operational
   - ✅ **Configuration Valid** - System settings correct

If any checks fail, contact your administrator.

---

## Step 2: Navigate to Create Mappings

1. Click **"Create Mappings"** in the left sidebar (➕ icon)
2. You'll see the **Unmapped Fields** table
3. This shows all source fields waiting to be mapped

---

## Step 3: Select Source Field(s)

### For Single-Field Mapping
1. Click the **checkbox** next to one source field
2. Review the field details (table, column, datatype)

### For Multi-Field Mapping
1. Click **checkboxes** next to multiple related fields
   - Example: FIRST_NAME and LAST_NAME → full_name
   - Example: STREET, CITY, STATE, ZIP → full_address
2. Fields will be combined in the order selected

### Then Click "Map Selected Fields"
3. Click the **"Map Selected Fields"** button
4. The mapping wizard opens

---

## Step 4: Choose Your Target Field

The mapping wizard shows two ways to find your target field:

### Option A: Get AI Suggestions (Recommended) 🤖

1. **Configure AI Settings** (optional):
   - **Vector Results**: 25 (default is fine)
   - **AI Results**: 10 (default is fine)
   - **User Feedback**: Add context like "patient demographics" or "address fields"

2. **Click "🤖 Get AI Suggestions"**
   - Wait 15-25 seconds for processing
   - AI analyzes field names, descriptions, and semantics

3. **Review Suggestions Table**:
   - **Rank**: Ordered by confidence score
   - **Target Table & Column**: Destination field name
   - **Confidence Score**: Higher is better
     - 0.8-1.0 = Excellent match (green)
     - 0.6-0.8 = Good match (blue)
     - 0.4-0.6 = Possible match (yellow)
   - **Reasoning**: Why AI suggested this match

4. **Select Best Match**:
   - Click **"Select"** button on the best suggestion
   - Target field populates in the wizard

### Option B: Manual Search 🔍

1. **Enter Search Term** in the search box
   - Try table names: "member", "claim", "provider"
   - Try column names: "name", "date", "address"
   - Try descriptions: "patient identifier", "service date"

2. **Click "🔍 Search"**
   - Results appear (up to 50 matches)
   - Sorted by table and column name

3. **Select Target Field**:
   - Click **"Select"** button on desired field
   - Target field populates in the wizard

---

## Step 5: Configure Your Mapping

Once you've selected a target, configure how source fields map to it:

### Read-Only Target Information
- **Target Table**: Shows the selected target table
- **Target Column**: Shows the selected target column
- These are **locked** - to change, restart the wizard

### Configure Source Fields

For each selected source field, you can:

#### 1. Apply Transformations
Click the transformation dropdown for each field:

**Pre-built Transformations:**
- **TRIM** - Remove whitespace
- **UPPER** - Convert to uppercase
- **LOWER** - Convert to lowercase
- **TRIM_UPPER** - Trim and uppercase
- **CAST_STRING** - Convert to string
- **CAST_INT** - Convert to integer
- **COALESCE** - Replace NULL with empty string

**Custom Transformations:**
- Select "Custom" from dropdown
- Enter your own SQL expression
- Example: `REGEXP_REPLACE(field, '[^0-9]', '')`

#### 2. Set Concatenation Strategy (Multi-Field Only)

If you selected **multiple source fields**, choose how to combine them:

- **SPACE** - Join with space
  - Example: "John" + "Doe" = `"John Doe"`
  
- **COMMA** - Join with comma and space
  - Example: "John" + "Doe" = `"John, Doe"`
  
- **PIPE** - Join with pipe delimiter
  - Example: "John" + "Doe" = `"John|Doe"`
  
- **CUSTOM** - Use your own separator
  - Enter separator: `" - "`, `"_"`, `" / "`, etc.
  - Example: "John" + "Doe" = `"John - Doe"`
  
- **NONE** - No concatenation (uses last field)
  - Example: "John" + "Doe" = `"Doe"`

#### 3. Add Join Conditions (If Needed)

If your source fields come from different tables:

1. **Click "+ Add Join"** button
2. **Fill Join Details**:
   - **Left Table**: First table name
   - **Left Column**: Join column from first table
   - **Join Type**: INNER, LEFT, RIGHT, or FULL
   - **Right Table**: Second table name
   - **Right Column**: Join column from second table

3. **Example Join**:
   ```
   t_member.member_id LEFT JOIN t_address.member_id
   ```

4. **Multiple Joins**: Click "+ Add Join" again to add more

---

## Step 6: Save Your Mapping

1. **Review Everything**:
   - Source fields and order (shown as badges: 1️⃣, 2️⃣, 3️⃣)
   - Transformations applied to each field
   - Concatenation strategy (if multiple fields)
   - Join conditions (if applicable)

2. **View SQL Expression Preview** (if shown):
   - Complete SQL transformation expression
   - Verify it looks correct

3. **Click "Save Mapping"**:
   - Mapping is created immediately
   - Success message appears
   - Wizard closes automatically

4. **Result**:
   - Source fields removed from unmapped list
   - New mapping appears in "View Mappings"

---

## Step 7: View and Manage Your Mappings

### View All Mappings

1. Click **"View Mappings"** in the left sidebar (📋 icon)
2. See your completed mappings in a data table

### Understanding the Mappings Table

**Each row shows:**
- **Target Field**: Destination table.column
- **Source Field(s)**: Origin fields with count badge
- **Concatenation**: Strategy used (if multiple fields)
- **Transformations**: Indicator if transformations applied
- **Status**: ACTIVE or INACTIVE
- **Created**: Timestamp
- **Actions**: View, Edit, Delete buttons

### View Mapping Details

1. **Click the eye icon** (👁️) to see complete details:
   - All source fields in order
   - Individual field transformations
   - Concatenation details
   - Join conditions
   - Complete SQL expression
   - Metadata (who created, when)

### Edit a Mapping ✏️

**What You CAN Edit:**
- ✅ Transformation expressions on existing fields
- ✅ Concatenation strategy and separator
- ✅ Join conditions (add, modify, remove)

**What You CANNOT Edit** (requires delete + recreate):
- ❌ Target field
- ❌ Add or remove source fields
- ❌ Change field order

**To Edit:**
1. Click the **pencil icon** (✏️) on the mapping
2. Modify transformations, concatenation, or joins in the dialog
3. Click **"Save Changes"**
4. Updates apply immediately

### Delete a Mapping 🗑️

1. Click the **trash icon** (🗑️) on the mapping
2. Confirm the deletion
3. Source fields return to unmapped list
4. Mapping is permanently removed

### Export Mappings 📥

1. Click **"Export Mappings"** button in the toolbar
2. CSV file downloads automatically
3. File includes complete SQL transformation logic
4. Filename: `mappings_export_YYYY-MM-DD.csv`

---

## Complete Example: Mapping Full Name

Let's walk through the complete **6-step process** with a real example:

### Scenario
Map `FIRST_NAME` and `LAST_NAME` from the source system to a `full_name` target field.

### Step-by-Step Walkthrough

#### STEP 1: Check System Status ✅
1. Click **"Home"** in the left sidebar
2. Verify all indicators are green:
   - ✅ Database Connection: Connected
   - ✅ Vector Search: Available
   - ✅ AI Model: Ready
   - ✅ Configuration: Valid
3. All systems operational - ready to proceed!

#### STEP 2: Navigate to Create Mappings ➕
1. Click **"Create Mappings"** in the left sidebar
2. Unmapped Fields table loads
3. See list of available source fields

#### STEP 3: Select Source Field(s) ☑️
1. Find and select fields:
   - ☑️ FIRST_NAME (from t_member table)
   - ☑️ LAST_NAME (from t_member table)
2. Click **"Map Selected Fields"** button
3. Mapping wizard opens

#### STEP 4: Choose Target Field 🎯
**Using AI Suggestions:**
1. Click **"🤖 Get AI Suggestions"**
2. Wait 15-20 seconds for AI processing
3. Review suggestions:
   - **Rank #1**: `slv_member.full_name` (confidence: 0.92) ⭐
   - **Rank #2**: `slv_demographics.member_name` (confidence: 0.78)
   - **Rank #3**: `slv_person.full_legal_name` (confidence: 0.65)
4. Click **"Select"** on Rank #1 (best match)
5. Target field populated: `slv_member.full_name`

#### STEP 5: Configure Mapping 🔧
**Configure Source Fields:**
1. **FIRST_NAME** (Field 1️⃣):
   - Transformation dropdown: Select "Trim and Upper"
   - Expression: `UPPER(TRIM(first_name))`

2. **LAST_NAME** (Field 2️⃣):
   - Transformation dropdown: Select "Trim and Upper"
   - Expression: `UPPER(TRIM(last_name))`

**Set Concatenation:**
3. Concatenation Strategy: **SPACE**
4. Preview: `CONCAT(UPPER(TRIM(first_name)), ' ', UPPER(TRIM(last_name)))`

**Review:**
- Source: FIRST_NAME + LAST_NAME
- Target: slv_member.full_name
- Result: "JOHN DOE" (uppercase, trimmed, space-separated)

#### STEP 6: Save & Verify 💾
1. Click **"Save Mapping"**
2. Success message: "Mapping created successfully!"
3. Wizard closes
4. **Verify:**
   - Click **"View Mappings"** in sidebar
   - Find row: `slv_member.full_name`
   - Source shows: `FIRST_NAME | LAST_NAME` with badge "2 fields"
   - Status: ACTIVE ✅
   - Created: Just now

**🎉 Mapping Complete!** The full_name field will now be populated by combining FIRST_NAME and LAST_NAME with the transformations applied.

---

## Tips for Success

### 🎯 Getting Better AI Suggestions
- ✅ Select logically related fields together
- ✅ Add descriptions to source fields when possible
- ✅ Use the "User Feedback" field for context
- ✅ Review top 3-5 suggestions, not just #1
- ✅ Look for confidence scores above 0.7

### ⚡ Efficient Workflow
- ✅ Start with AI suggestions for most mappings
- ✅ Use manual search for specific/known targets
- ✅ Work on related fields in batches (e.g., all address fields)
- ✅ Apply consistent transformations (e.g., TRIM all text fields)
- ✅ Use edit feature instead of delete+recreate when possible

### 🔧 Using Transformations
- ✅ **TRIM** for all text fields to remove whitespace
- ✅ **UPPER** or **LOWER** for standardization
- ✅ **CAST** when datatypes don't match
- ✅ **COALESCE** to handle NULL values
- ✅ Custom expressions for complex logic

### 🔗 Multi-Field Mapping Best Practices
- ✅ Select fields in logical order (First Name → Last Name, not reversed)
- ✅ Choose appropriate concatenation strategy for your use case
- ✅ Test final expression with sample data
- ✅ Document complex mappings in your notes
- ✅ Use NONE strategy only when you want just the last field

### 📋 Managing Your Mappings
- ✅ Export regularly for backup
- ✅ Review mappings periodically for accuracy
- ✅ Use consistent naming in transformations
- ✅ Set mappings to INACTIVE instead of deleting (if supported)
- ✅ Document business rules in descriptions

---

## Common Questions

**Q: How many source fields can I map to one target?**  
A: As many as needed! Common patterns use 2-4 fields, but you can map more.

**Q: Can I change the order of source fields after saving?**  
A: No, field order cannot be changed. You must delete and recreate the mapping.

**Q: What if I selected the wrong target field?**  
A: Delete the mapping and create a new one. You cannot change the target field.

**Q: Can I use the same source field in multiple mappings?**  
A: Yes! One source field can map to multiple different target fields.

**Q: How long does AI take?**  
A: Usually 15-25 seconds. If it takes longer, check system status.

**Q: What's a good confidence score?**  
A: 0.8-1.0 is excellent, 0.6-0.8 is good, below 0.6 review carefully.

**Q: Can I edit transformations after saving?**  
A: Yes! Click the edit icon (✏️) on the mapping and change transformations.

**Q: What happens if I delete a mapping?**  
A: Source fields return to the unmapped list and can be remapped.

---

## Need More Help?

📖 **Full User Guide**: [USER_GUIDE.md](USER_GUIDE.md) - Detailed feature documentation  
⚙️ **Admin Guide**: [ADMIN_GUIDE.md](ADMIN_GUIDE.md) - For administrators  
💻 **Developer Guide**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Technical reference

---

## Your First Mapping Checklist

- [ ] Check system status (Home page - all green ✅)
- [ ] Go to Create Mappings page
- [ ] Select one or more unmapped fields
- [ ] Get AI suggestions OR manual search
- [ ] Select target field
- [ ] Configure transformations (optional)
- [ ] Set concatenation strategy (if multiple fields)
- [ ] Add joins (if needed)
- [ ] Save mapping
- [ ] Verify in View Mappings page

**Congratulations! You've completed your first mapping!** 🎊

Continue creating more mappings using the same process. The more you use the platform, the faster and more efficient you'll become!

---

**Version**: 2.0  
**Last Updated**: November 2025  
**Platform**: Source-to-Target Mapping (Multi-Field V2)
