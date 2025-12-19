# Quick Start Guide - Smart Mapper V4

## Welcome to Smart Mapper! 🎉

Get started with the **Target-First** workflow in just a few minutes. This guide walks you through creating your first mapping project.

---

## The V4 Target-First Workflow

Smart Mapper V4 uses a **project-based, target-first** approach:

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Create a Project                                       │
│  📁 Give your mapping project a name                            │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Upload Source Fields                                   │
│  📤 Upload CSV with ALL your source columns                     │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Initialize Target Tables                               │
│  🎯 System creates list of target tables to map                 │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Start AI Discovery                                     │
│  🤖 AI suggests mappings for ALL columns in a table             │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: Review & Approve Suggestions                           │
│  ✅ Approve, ✏️ Edit, or ❌ Reject each suggestion               │
└─────────────────────────────────────────────────────────────────┘
                            ⬇️
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6: Complete & Export                                      │
│  📊 Track progress, mark tables complete, export results        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Create a Project

1. Click **"+ New Project"** on the Projects dashboard
2. Enter project details:
   - **Name**: e.g., "DMES Member Migration Q1 2025"
   - **Description**: Optional but helpful
   - **Target Domains**: Filter (e.g., "Member" or "Member|Claims")
3. Click **"Create"**

You'll be taken to your new project's detail page.

---

## Step 2: Upload Source Fields

### Download the Template

1. Click **"Upload Sources"** button
2. Click **"Download Template"**
3. Open the CSV template

### Fill the Template

The template requires these columns:

| Column | Required | Example |
|--------|----------|---------|
| `src_table_name` | ✅ | `T_MEMBER` |
| `src_table_physical_name` | ✅ | `t_member` |
| `src_column_name` | ✅ | `MEMBER_ID` |
| `src_column_physical_name` | ✅ | `member_id` |
| `src_physical_datatype` | ✅ | `STRING` |
| `src_nullable` | ✅ | `YES` or `NO` |
| `src_comments` | ⚠️ **Critical!** | `Unique member identifier` |
| `domain` | Optional | `member` |

> ⚠️ **Important**: The `src_comments` field is **essential** for AI matching. Without descriptions, the AI cannot find good matches!

### Upload

1. Click **"Select CSV File"**
2. Choose your completed CSV
3. Click **"Upload"**
4. Verify: "Uploaded X fields from Y tables"

---

## Step 3: Initialize Target Tables

1. On your project page, click **"Initialize Tables"**
2. System queries target definitions from `semantic_fields`
3. Creates a status row for each target table
4. You'll see a list like:

| Table | Status | Columns | Progress |
|-------|--------|---------|----------|
| MBR_CNTCT | NOT_STARTED | 25 | 0% |
| MBR_FNDTN | NOT_STARTED | 18 | 0% |

---

## Step 4: Start AI Discovery

1. Click on a target table (e.g., `MBR_CNTCT`)
2. Click **"Start Discovery"** (▶️ play icon)
3. Status changes to **DISCOVERING**
4. Wait 1-5 minutes (depending on table size)
5. When done, status changes to **SUGGESTIONS_READY**

**While waiting, you can:**
- Start discovery on other tables
- View project statistics
- Work on already-ready tables

---

## Step 5: Review Suggestions

### Open Review Panel

1. Click **"Review Suggestions"** on a table with status SUGGESTIONS_READY
2. You'll see a list of all columns with their AI suggestions

### Each Suggestion Shows:

```
┌────────────────────────────────────────────────────────────────┐
│ ✅ ADDR_1_TXT (First address line)              Confidence: 94%│
│ Pattern: UNION_WITH_JOINS                                      │
│ Sources: my_member_base.ADDR_LINE_1, my_member_addr.STREET_1   │
│                                                                │
│ [View SQL ▼] - Click to see the complete SQL                  │
│                                                                │
│ [✓ Approve] [✎ Edit] [✗ Reject] [→ Skip]                      │
└────────────────────────────────────────────────────────────────┘
```

### Actions

| Action | When to Use | What Happens |
|--------|-------------|--------------|
| **Approve** ✓ | Suggestion is correct | Creates final mapping |
| **Edit** ✏️ | SQL needs small changes | Opens SQL editor, then creates mapping |
| **Reject** ✗ | Suggestion is wrong | Records feedback, column unmatched |
| **Skip** → | Not needed now | Column skipped, doesn't block completion |

### Bulk Actions

- **Approve All High (≥85%)**: Auto-approve high-confidence suggestions
- **Expand All**: Show SQL for all suggestions

---

## Step 6: Complete & Track Progress

### Table Progress

As you approve suggestions:
- Progress bar fills up
- Counter shows: `15 / 25 columns mapped`
- When all columns have a status → table marked **COMPLETE**

### Project Dashboard

Your project page shows overall progress:

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    Tables    │  │   Columns    │  │   Pending    │
│    3 / 12    │  │   45 / 156   │  │     23       │
│     25%      │  │     29%      │  │   Review →   │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Export Results

1. Click **"Export Mappings"**
2. CSV downloads with:
   - Target table and column
   - Complete SQL expression
   - Source tables and columns used

---

## Complete Example: Mapping MBR_CNTCT

### Setup (Steps 1-3)

1. **Create Project**: "ACME State Migration"
2. **Upload Sources**: 500 source fields from 12 tables
3. **Initialize Tables**: 8 target tables appear

### Map a Table (Steps 4-5)

1. Click on `MBR_CNTCT` (25 columns)
2. Click **"Start Discovery"**
3. Wait 3 minutes...
4. Status: **SUGGESTIONS_READY**
5. Click **"Review Suggestions"**

### Review Suggestions

**High Confidence (approve directly):**
- ✅ `MBR_SK` - 96% confidence - Approve
- ✅ `ADDR_1_TXT` - 94% confidence - Approve
- ✅ `CITY_TXT` - 91% confidence - Approve

**Medium Confidence (review carefully):**
- ⚠️ `CNTCT_TYP_CD` - 72% confidence - Check SQL, then Approve

**Low Confidence (manual work):**
- ❓ `CNTRY_CD` - 45% confidence - Edit SQL or Reject

**No Match Found:**
- ❌ `CUSTOM_FIELD_1` - No pattern - Skip (not in target spec)

### Complete Table

After reviewing all 25 columns:
- 22 approved
- 2 edited and approved
- 1 skipped
- Status: **COMPLETE** ✅

---

## Tips for Success

### 📝 Source Field Descriptions Matter!

**Bad:**
```
src_column_name: ADDR_L1
src_comments: 
```

**Good:**
```
src_column_name: ADDR_L1
src_comments: First line of member mailing address including street number
```

### ⚡ Work Efficiently

- ✅ Start multiple table discoveries at once
- ✅ Use **"Approve All High"** for tables with good patterns
- ✅ Focus manual review on low-confidence suggestions
- ✅ Skip columns that aren't needed rather than spending time on them

### 🤖 Understanding AI Confidence

| Score | Action |
|-------|--------|
| 85%+ | Usually safe to approve directly |
| 70-84% | Review the SQL before approving |
| 50-69% | Check carefully, may need editing |
| <50% | Consider manual mapping |

### 👥 Team Collaboration

- Add team members by email when creating the project
- Different people can work on different tables
- Everyone sees the same progress dashboard

---

## What If...

**Q: AI discovery is taking too long?**
- Large tables (50+ columns) take 5-10 minutes
- You can work on other tables while waiting
- Check if AI model endpoint is healthy

**Q: No suggestions for some columns?**
- No historical pattern exists
- Create a manual mapping
- Your mapping becomes a pattern for future projects!

**Q: Suggestion SQL looks wrong?**
- Click **Edit** and fix it
- Your edits create better patterns

**Q: Made a mistake on an approval?**
- Go to the approved mappings
- Delete and redo, or edit if possible

---

## Confidence Score Legend

| Indicator | Score | Meaning |
|-----------|-------|---------|
| ✅ Green | 85-100% | High confidence - likely correct |
| ⚠️ Yellow | 70-84% | Medium - review before approving |
| 🟠 Orange | 50-69% | Low - needs attention |
| ❌ Red | <50% | Very low - consider manual |

---

## Navigation Reference

### Mapping Workflow
- **Projects** 📁 - Your mapping projects dashboard

### Administration (Admins Only)
- **Semantic Fields** 💾 - Manage target definitions
- **Configuration** ⚙️ - System settings

---

## Your First Project Checklist

- [ ] Create a new project
- [ ] Download the source fields template
- [ ] Fill template with source columns and **descriptions**
- [ ] Upload source fields CSV
- [ ] Click "Initialize Tables"
- [ ] Select a target table
- [ ] Start AI Discovery
- [ ] Wait for suggestions
- [ ] Review and approve/edit suggestions
- [ ] Mark table complete
- [ ] Repeat for remaining tables
- [ ] Export final mappings

**Congratulations! You've completed your first V4 mapping project!** 🎊

---

## Need More Help?

📖 **Full User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
⚙️ **Admin Guide**: [ADMIN_GUIDE.md](ADMIN_GUIDE.md)
🏗️ **Architecture**: [architecture/TARGET_FIRST_WORKFLOW.md](architecture/TARGET_FIRST_WORKFLOW.md)

---

**Version**: 4.0 - Target-First Workflow
**Last Updated**: December 2025
