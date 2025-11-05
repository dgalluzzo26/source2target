# Quick Start Guide

## Welcome to the Source-to-Target Mapping Tool! 🎉

This guide will get you started mapping fields in just a few minutes.

## Step 1: Check System Status

1. Click on **"📊 Introduction"** in the left sidebar
2. Verify all system checks are green:
   - ✅ Database Connection
   - ✅ Vector Search Available
   - ✅ AI Model Ready
   - ✅ Configuration Valid

If any checks fail, contact your administrator.

## Step 2: Navigate to Field Mapping

1. Click on **"🗺️ Field Mapping"** in the left sidebar
2. You'll see three main sections:
   - **Unmapped Fields** - Fields waiting to be mapped
   - **Mapped Fields** - Fields already mapped
   - **Selected Field Details** - Details of your selection

## Step 3: Select a Source Field

1. Browse the **Unmapped Fields** table
2. Use the search box to find specific fields
3. Click on any row to select it
4. The field details will appear below the tables

## Step 4: Get AI Suggestions (Recommended)

1. Review the AI Configuration settings:
   - **Number of Vector Results**: 25 (default is fine)
   - **Number of AI Results**: 10 (default is fine)
   - **User Feedback**: Optional - add context like "focus on patient fields"

2. Click **"🤖 Generate AI Mapping Suggestions"**

3. Wait for the suggestions to load (usually 15-20 seconds)

4. Review the suggestions table:
   - Look at **Confidence Score** - higher is better (0.8+ is excellent)
   - Check **Target Table** and **Target Column** names
   - Read the **Reasoning** for context

5. Click **"Select Target"** on the best match

6. Done! The field is now mapped and moved to the Mapped Fields table.

## Step 5: Try Manual Search (Alternative)

If AI suggestions don't provide a good match:

1. Select an unmapped field (if not already selected)

2. Enter a search term in the **Manual Search** box:
   - Try table names: "patient", "claim", "provider"
   - Try column names: "id", "date", "code"
   - Try descriptions: "identifier", "timestamp"

3. Click **"🔍 Search Semantic Table"**

4. Browse the search results

5. Click **"Select Target"** on the desired field

6. Done! The mapping is saved automatically.

## Step 6: Manage Your Mappings

### View Mapped Fields
- Switch to the **Mapped Fields** tab
- See all your completed mappings
- Use search to find specific mappings

### Delete a Mapping
- Find the mapped field
- Click the 🗑️ (trash) icon
- Confirm the deletion
- The field returns to Unmapped Fields

## Tips for Success

### Getting Better AI Suggestions
✅ Add descriptions to your source fields  
✅ Use the User Feedback field to provide context  
✅ Review multiple suggestions before deciding  
✅ Look for high confidence scores (0.7+)  

### Efficient Workflow
✅ Start with AI suggestions for most fields  
✅ Use manual search for edge cases  
✅ Work in batches of related fields  
✅ Double-check data types match  

### When to Use Manual Search
- AI suggestions have low confidence (<0.6)
- You know exactly which target field you need
- Special business rules apply
- Field has unique characteristics

## Common Questions

**Q: How long does AI take?**  
A: Usually 15-25 seconds for vector search and suggestions.

**Q: Can I change a mapping?**  
A: Yes! Delete the old mapping and create a new one.

**Q: What's a good confidence score?**  
A: 0.8-1.0 is excellent, 0.6-0.8 is good, below 0.6 review carefully.

**Q: Why don't I see suggestions?**  
A: Check system status - Vector Search and AI Model must be ready.

**Q: Can I map multiple fields at once?**  
A: Not currently, but you can use CSV templates to add unmapped fields in bulk.

## Need More Help?

📖 **Full User Guide**: [docs/USER_GUIDE.md](USER_GUIDE.md)  
⚙️ **Admin Guide**: [docs/ADMIN_GUIDE.md](ADMIN_GUIDE.md)  
💻 **Developer Guide**: [docs/DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)

## Your First Mapping Checklist

- [ ] Check system status (all green)
- [ ] Go to Field Mapping page
- [ ] Select an unmapped field
- [ ] Generate AI suggestions
- [ ] Review confidence scores
- [ ] Select a target field
- [ ] Verify mapping appears in Mapped Fields

**Congratulations! You've completed your first mapping!** 🎊

Continue mapping more fields using the same process. The more you use the tool, the faster and more efficient you'll become.

---

**Need help?** Contact your administrator or check the full documentation.

