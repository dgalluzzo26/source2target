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

Let's walk through a complete example:

### Scenario
Map `FIRST_NAME` and `LAST_NAME` to `full_name` target field.

### Step-by-Step

1. **Navigate**: Click "Create Mappings"

2. **Select Source Fields**:
   - ☑️ FIRST_NAME (from t_member table)
   - ☑️ LAST_NAME (from t_member table)
   - Click "Map Selected Fields"

3. **Get AI Suggestions**:
   - Click "🤖 Get AI Suggestions"
   - Wait for results
   - AI suggests: `slv_member.full_name` (confidence: 0.92)
   - Click "Select" on that suggestion

4. **Configure Mapping**:
   - **Source Field 1** (FIRST_NAME):
     - Transformation: `TRIM_UPPER` → `UPPER(TRIM(first_name))`
   - **Source Field 2** (LAST_NAME):
     - Transformation: `TRIM_UPPER` → `UPPER(TRIM(last_name))`
   - **Concatenation**: `SPACE`
   - **Result Preview**: `CONCAT(UPPER(TRIM(first_name)), ' ', UPPER(TRIM(last_name)))`

5. **Save Mapping**:
   - Click "Save Mapping"
   - Success! ✅

6. **Verify**:
   - Go to "View Mappings"
   - See: `slv_member.full_name` ← `FIRST_NAME | LAST_NAME`
   - Status: ACTIVE

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
