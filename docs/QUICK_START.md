# Quick Start Guide

## Welcome to the Source-to-Target Mapping Platform! 🎉

This guide will get you started mapping fields in just a few minutes. The platform now supports **multi-field mappings** with transformations!

---

## Step 1: Check System Status

1. Click on **"Home"** in the left sidebar
2. Verify all system checks are green:
   - ✅ Database Connection
   - ✅ Vector Search Available
   - ✅ AI Model Ready
   - ✅ Configuration Valid

If any checks fail, contact your administrator.

---

## Step 2: Navigate to Create Mappings

1. Click on **"Create Mappings"** in the left sidebar
2. You'll see your **Unmapped Fields** table
3. Browse available source fields waiting to be mapped

---

## Step 3: Select Source Fields for Mapping

### Single Field Mapping
1. Click the checkbox next to a source field
2. Click **"Map Selected Fields"** button
3. The mapping wizard opens

### Multiple Fields to One Target (Advanced)
1. Select multiple related fields (e.g., FIRST_NAME, LAST_NAME)
2. Click **"Map Selected Fields"**
3. The platform will help you combine them into one target field

---

## Step 4: Choose Your Target Field

### Option A: Get AI Suggestions (Recommended)
1. Review the AI Configuration section
2. Click **"🤖 Get AI Suggestions"**
3. Wait 15-25 seconds for intelligent recommendations
4. Review suggestions with confidence scores
5. Click **"Select"** on the best match

### Option B: Manual Search
1. Type a search term in the search box
2. Click **"🔍 Search"**
3. Browse search results
4. Click **"Select"** on your desired target field

---

## Step 5: Configure Your Mapping

Once you've selected a target field:

### 1. Review Source Fields
- See all selected source fields
- Order is preserved (for multi-field mappings)

### 2. Add Transformations (Optional)
For each source field:
- Click the **transformation dropdown**
- Choose from the library: TRIM, UPPER, LOWER, etc.
- Or enter a custom SQL expression
- Example: `UPPER(TRIM(first_name))`

### 3. Set Concatenation Strategy (Multi-Field Only)
If mapping multiple fields to one target:
- **SPACE**: Join with space (e.g., "John Doe")
- **COMMA**: Join with comma (e.g., "John,Doe")
- **PIPE**: Join with pipe (e.g., "John|Doe")
- **CUSTOM**: Use your own separator
- **NONE**: No concatenation

### 4. Add Join Conditions (Advanced)
If fields come from different tables:
- Click **"+ Add Join"**
- Define LEFT, RIGHT, INNER, or FULL joins
- Specify join columns

---

## Step 6: Save Your Mapping

1. Review all settings
2. Click **"Save Mapping"**
3. Success! The mapping is created
4. Source fields are removed from unmapped list

---

## Step 7: View and Manage Mappings

### View Your Mappings
1. Click **"View Mappings"** in the sidebar
2. See all your completed mappings
3. Use search to filter specific mappings

### Edit a Mapping
You can edit (without recreating):
- ✏️ **Transformations** on existing fields
- 🔗 **Join conditions**
- 📋 **Concatenation strategy**

**Cannot edit** (requires delete + recreate):
- ❌ Target field
- ❌ Add/remove source fields  
- ❌ Field order

**To Edit:**
1. Find your mapping
2. Click the **pencil icon** (✏️)
3. Make changes in the dialog
4. Click **"Save Changes"**

### Delete a Mapping
1. Find the mapping
2. Click the **trash icon** (🗑️)
3. Confirm deletion
4. Fields return to unmapped list

---

## Quick Tips

### 🎯 For Best AI Suggestions
- ✅ Select related fields together
- ✅ Provide context in the feedback field
- ✅ Review confidence scores (0.8+ is excellent)
- ✅ Check multiple suggestions before deciding

### ⚡ For Efficient Mapping
- ✅ Start with AI suggestions
- ✅ Use transformations from the library
- ✅ Work on related fields in batches
- ✅ Edit existing mappings instead of recreating

### 🔧 Using Transformations
- ✅ **TRIM**: Remove whitespace
- ✅ **UPPER/LOWER**: Change case
- ✅ **CAST**: Change data type
- ✅ **COALESCE**: Handle nulls
- ✅ **Custom**: Write your own SQL

### 🔗 Multi-Field Mapping Examples

**Example 1: Full Name**
- Source: FIRST_NAME, LAST_NAME
- Target: full_name
- Concat: SPACE
- Transformations: TRIM on both
- Result: `CONCAT(TRIM(first_name), ' ', TRIM(last_name))`

**Example 2: Address Line**
- Source: STREET, CITY, STATE, ZIP
- Target: full_address
- Concat: COMMA
- Transformations: TRIM on all
- Result: `CONCAT(TRIM(street), ', ', TRIM(city), ', ', TRIM(state), ', ', TRIM(zip))`

---

## Common Questions

**Q: Can I map multiple source fields to one target?**  
A: Yes! Select multiple fields before clicking "Map Selected Fields".

**Q: How do I change a transformation after saving?**  
A: Click the edit icon (✏️) on your mapping, change the transformation, and save.

**Q: What if I need to add another source field to my mapping?**  
A: You must delete the mapping and recreate it with all desired source fields.

**Q: Can I see the final SQL expression?**  
A: Yes! View the mapping details to see the complete transformation expression.

**Q: What's the difference between transformation library and custom?**  
A: Library has pre-built transformations (TRIM, UPPER, etc.). Custom lets you write any SQL expression.

---

## Your First Mapping Checklist

- [ ] Check system status (all green)
- [ ] Go to Create Mappings page
- [ ] Select one or more unmapped fields
- [ ] Get AI suggestions or search manually
- [ ] Select target field
- [ ] Add transformations (optional)
- [ ] Set concatenation if multiple fields
- [ ] Save mapping
- [ ] Verify in View Mappings page

**Congratulations! You've completed your first mapping!** 🎊

---

## Need More Help?

📖 **Full User Guide**: [docs/USER_GUIDE.md](USER_GUIDE.md)  
⚙️ **Admin Guide**: [docs/ADMIN_GUIDE.md](ADMIN_GUIDE.md)  
💻 **Developer Guide**: [docs/DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)

---

**Version**: 2.0  
**Last Updated**: November 2025  
**New Features**: Multi-field mapping, Transformation library, Mapping editor
