# Smart Mapper V4 - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Dashboard Overview](#dashboard-overview)
4. [Creating a Project](#creating-a-project)
5. [Uploading Source Fields](#uploading-source-fields)
6. [Initializing Target Tables](#initializing-target-tables)
7. [Starting AI Discovery](#starting-ai-discovery)
8. [Reviewing AI Suggestions](#reviewing-ai-suggestions)
9. [Working with Suggestions](#working-with-suggestions)
10. [Completing a Table](#completing-a-table)
11. [Project Management](#project-management)
12. [Best Practices](#best-practices)
13. [FAQ](#faq)

---

## Introduction

**Smart Mapper V4** uses a **Target-First** workflow for mapping source database fields to target semantic fields. This approach inverts the traditional mapping process for faster, more efficient large-scale migrations.

### What is Target-First Mapping?

| Traditional (Source-First) | Target-First (V4) |
|---------------------------|-------------------|
| 1. Select a source field | 1. Create a project |
| 2. Search for matching target | 2. Upload ALL source fields at once |
| 3. Configure the mapping | 3. Select a target table to map |
| 4. Repeat for each field | 4. AI suggests mappings for ALL columns |
| | 5. Review, approve, or edit each suggestion |
| | 6. Move to next table |

### Why Target-First?

- ✅ **Complete Coverage**: See ALL target columns upfront, nothing missed
- ✅ **AI-Powered**: Suggestions for entire tables, not just one field
- ✅ **Pattern Learning**: AI uses historical mappings to suggest complex SQL
- ✅ **Progress Tracking**: Clear dashboard showing tables complete vs. remaining
- ✅ **Team Collaboration**: Multiple users can work on different tables

### Key Features

- 🎯 **Project-Based Workflow**: Organize mappings by migration project
- 🤖 **Bulk AI Suggestions**: Get suggestions for all columns in a table at once
- 📊 **Real-Time Progress**: Dashboard shows tables mapped, columns complete
- ✏️ **SQL Editor**: Edit AI-suggested SQL before approving
- 🔍 **Pattern Reuse**: Historical mappings inform new suggestions
- 👥 **Team Access**: Share projects with team members

---

## Getting Started

### Accessing the Application

1. Navigate to your Databricks App URL
2. You will be automatically authenticated using your Databricks account
3. Your email is displayed in the header (top-right)

### Navigation

The sidebar has two main sections:

**📊 Mapping Workflow**
```
🏠 Projects           - Main dashboard, all your projects
```

**🔧 Administration** (Admins Only)
```
💾 Semantic Fields    - Manage target field definitions
⚙️ Configuration      - System settings
```

---

## Dashboard Overview

### Projects List

The main page shows all projects you have access to:

- **Your Projects**: Projects you created
- **Shared Projects**: Projects where your email was added as a team member

Each project card shows:
- **Project Name**: Display name
- **Status**: Draft, Active, In Review, Complete
- **Progress Stats**:
  - Tables: `3 / 12 complete`
  - Columns: `45 / 156 mapped`
  - Pending: `23 suggestions to review`

### Project Status Legend

| Status | Icon | Meaning |
|--------|------|---------|
| DRAFT | ⬜ | Project created but not started |
| ACTIVE | 🔄 | Mapping work in progress |
| REVIEW | 📋 | All tables done, final review |
| COMPLETE | ✅ | All mappings finalized |
| ARCHIVED | 📦 | Project archived |

---

## Creating a Project

### Step 1: Click "New Project"

From the Projects dashboard, click the **"+ New Project"** button.

### Step 2: Fill Project Details

**Required:**
- **Project Name**: Descriptive name (e.g., "DMES Member Migration Q1 2025")

**Optional but Recommended:**
- **Description**: Details about the migration project
- **Source System**: Name of the source system (e.g., "DMES", "MMIS")
- **Target Domains**: Filter target tables by domain (e.g., "Member", "Member|Claims")

### Step 3: Add Team Members (Optional)

Enter email addresses of colleagues who should have access to this project:
```
john.smith@gainwell.com
jane.doe@gainwell.com
```

Team members will see this project in their dashboard and can work on tables.

### Step 4: Save

Click **"Create Project"**. You'll be taken to the project detail page.

---

## Uploading Source Fields

### Why Upload All Sources First?

The AI needs to know ALL your available source fields to make good suggestions. It matches target columns to the most semantically similar source columns.

### Step 1: Download the Template

1. On the project detail page, click **"Upload Sources"**
2. Click **"Download Template"** to get the CSV format

### Step 2: Fill the Template

The template has these columns (all required for best AI matching):

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `src_table_name` | ✅ | Logical table name | `T_MEMBER` |
| `src_table_physical_name` | ✅ | Physical table name | `t_member` |
| `src_column_name` | ✅ | Logical column name | `MEMBER_ID` |
| `src_column_physical_name` | ✅ | Physical column name | `member_id` |
| `src_physical_datatype` | ✅ | Data type | `STRING` |
| `src_nullable` | ✅ | Nullable? | `YES` or `NO` |
| `src_comments` | ⚠️ CRITICAL | Description | `Unique member identifier` |
| `domain` | Optional | Category | `member` |

> ⚠️ **Important**: The `src_comments` field is **essential** for AI matching. Without good descriptions, the AI cannot find the best source columns for your target fields.

### Step 3: Upload the CSV

1. Click **"Select CSV File"**
2. Choose your completed template
3. Click **"Upload"**

The system will:
- Validate all required columns are present
- Warn if descriptions are missing
- Show number of fields uploaded and tables found

---

## Initializing Target Tables

### What This Does

Initializing creates a status row for each target table based on your domain filter. This is required before you can start mapping.

### Step 1: Click "Initialize Tables"

On the project detail page, click the **"Initialize Tables"** button.

### Step 2: Review Target Tables

The system will:
1. Query `semantic_fields` for all unique target tables
2. Apply your domain filter (if specified)
3. Create a `target_table_status` row for each table
4. Calculate total columns per table

### Step 3: View Table List

After initialization, you'll see a table like:

| Table | Status | Columns | Progress |
|-------|--------|---------|----------|
| MBR_CNTCT | NOT_STARTED | 25 | 0% |
| MBR_FNDTN | NOT_STARTED | 18 | 0% |
| MBR_ENRL_FNDTN | NOT_STARTED | 32 | 0% |

---

## Starting AI Discovery

### What AI Discovery Does

When you start discovery for a table, the AI:
1. Looks at each target column in that table
2. Searches for past mapping patterns from `mapped_fields`
3. Finds matching source columns from your uploaded fields
4. Uses an LLM to rewrite the SQL with your source columns
5. Creates suggestions with confidence scores

### Step 1: Select a Table

Click on a table row in the target tables list.

### Step 2: Start Discovery

Click **"Start Discovery"** (or the play icon).

The table status changes to **DISCOVERING**.

### Step 3: Wait for Completion

Discovery runs asynchronously. Depending on table size:
- Small tables (10-20 columns): 1-2 minutes
- Medium tables (20-50 columns): 2-5 minutes
- Large tables (50+ columns): 5-10 minutes

You can:
- Watch progress on the page
- Navigate to other tables (discovery continues in background)
- Start discovery on multiple tables simultaneously

### Step 4: Suggestions Ready

When complete, status changes to **SUGGESTIONS_READY**.

Click **"Review Suggestions"** to proceed.

---

## Reviewing AI Suggestions

### Suggestion Panel Layout

Each suggestion shows:

```
┌────────────────────────────────────────────────────────────────┐
│ ✅ ADDR_1_TXT (First address line)              Confidence: 94%│
│ Pattern: UNION_WITH_JOINS                                      │
│ Sources: my_member_base.ADDR_LINE_1, my_member_addr.STREET_1   │
│                                                                │
│ [View SQL ▼]                                                   │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ SELECT DISTINCT                                          │  │
│ │   INITCAP(b.ADDR_LINE_1) AS ADDR_1_TXT    ◄── CHANGED   │  │
│ │ FROM my_member_base b                      ◄── CHANGED   │  │
│ │ JOIN silver.mbr_fndtn mf ON b.MBR_KEY = mf.SRC_KEY_ID   │  │
│ │ LEFT JOIN silver.cnty_cd c ON b.CTY_CODE = c.CNTY_ID    │  │
│ │ WHERE mf.CURR_REC_IND = '1'                              │  │
│ │ UNION DISTINCT                                           │  │
│ │ ...                                                      │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                                │
│ [✓ Approve] [✎ Edit] [✗ Reject] [→ Skip]                      │
└────────────────────────────────────────────────────────────────┘
```

### Understanding Confidence Scores

| Score | Indicator | Meaning |
|-------|-----------|---------|
| 0.85-1.0 | ✅ Green | High confidence - likely correct |
| 0.70-0.84 | ⚠️ Yellow | Medium confidence - review carefully |
| 0.50-0.69 | 🟠 Orange | Low confidence - needs attention |
| 0.0-0.49 | ❌ Red | Very low - consider manual mapping |

### SQL Diff Highlighting

The SQL view highlights changes:
- **Green Background**: Parts replaced with your source tables/columns
- **Unchanged**: Silver tables and static parts remain the same

---

## Working with Suggestions

### Approve

Click **"Approve"** when the suggestion is correct as-is.

What happens:
- Creates a row in `mapped_fields`
- Updates the source fields to `MAPPED` status
- Increments the table's `columns_mapped` counter
- Suggestion status changes to `APPROVED`

### Edit

Click **"Edit"** to modify the SQL before approving.

1. SQL editor opens with the suggested expression
2. Make your changes
3. Click **"Save & Approve"**

Use cases:
- Fix incorrect column references
- Adjust transformations (TRIM, UPPER, etc.)
- Modify filter/WHERE conditions
- Change JOIN types

### Reject

Click **"Reject"** when the suggestion is wrong.

1. A dialog asks for rejection reason
2. Provide feedback (helps improve AI)
3. Click **"Confirm Reject"**

The rejection is recorded in `mapping_feedback` and helps the AI avoid similar mistakes in future.

### Skip

Click **"Skip"** when:
- Column is not needed in this migration
- Will be mapped manually later
- No source data exists for this field

Skipped columns don't count against completion percentage.

### Bulk Actions

Use the header actions for efficiency:

- **Approve All High (≥85%)**: Auto-approve all high-confidence suggestions
- **Expand All**: Show SQL for all suggestions
- **Collapse All**: Hide all SQL details

---

## Completing a Table

### When is a Table Complete?

A table is marked **COMPLETE** when:
- All columns have a final status (approved, rejected, or skipped)
- No columns remain in "pending review" state

### Completion Actions

When you complete the last column:
1. Table status changes to **COMPLETE**
2. Progress bar shows 100%
3. Project counters update automatically
4. A success message appears

### Reopening a Completed Table

If you need to modify a completed table:
1. Navigate to the table
2. Click **"Reopen for Editing"**
3. Status changes back to **IN_PROGRESS**
4. Make your changes
5. Mark complete again

---

## Project Management

### Viewing Project Status

The project detail page shows:

```
┌─────────────────────────────────────────────────────────────┐
│ DMES Member Migration                          Status: ACTIVE│
│                                                              │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│ │    Tables    │  │   Columns    │  │   Pending    │        │
│ │    3 / 12    │  │   45 / 156   │  │     23       │        │
│ │    ████░░░░  │  │   ██░░░░░░   │  │              │        │
│ │     25%      │  │     29%      │  │   Review →   │        │
│ └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### Exporting Mappings

1. Go to project detail page
2. Click **"Export Mappings"**
3. CSV downloads with all approved mappings

Export includes:
- Target table and column
- Complete SQL expression
- Source tables and columns used
- Approval status and timestamp

### Managing Team Members

1. Go to project detail page
2. Click **"Settings"** or the gear icon
3. Add or remove team member emails
4. Save changes

---

## Best Practices

### For Efficient Mapping

1. ✅ **Upload complete source data** with good descriptions
2. ✅ **Start with high-priority tables** (core entities first)
3. ✅ **Use bulk approve** for high-confidence suggestions
4. ✅ **Work table by table** rather than jumping around
5. ✅ **Provide feedback on rejections** to improve AI

### For Quality Mappings

1. ✅ **Review SQL carefully** - especially JOINs and filters
2. ✅ **Check data types match** between source and target
3. ✅ **Verify transformations** are appropriate (TRIM, UPPER, etc.)
4. ✅ **Test with sample data** when possible
5. ✅ **Document edge cases** in user notes

### For Team Collaboration

1. ✅ **Assign table ownership** to avoid conflicts
2. ✅ **Use project notes** to communicate status
3. ✅ **Review each other's mappings** before marking complete
4. ✅ **Keep domain experts involved** for business logic

---

## FAQ

### General Questions

**Q: What's different from the old Source-First workflow?**
A: Target-First inverts the approach. Instead of selecting source fields one-by-one, you work through entire target tables with AI assistance.

**Q: Can multiple people work on the same project?**
A: Yes! Add team members by email. Each person can work on different tables simultaneously.

**Q: How does the AI know what SQL to suggest?**
A: It uses historical mappings (patterns) from past projects. The more mappings completed, the smarter the AI gets.

### Source Fields

**Q: Why do I need to upload all source fields first?**
A: The AI needs to see all available source columns to make good matches. It searches your uploaded fields using semantic similarity.

**Q: What if I forgot a source table?**
A: You can upload additional source fields at any time. Click "Upload Sources" again with the new data.

**Q: My descriptions are in a different column - can I still upload?**
A: Rename the column to `src_comments` in your CSV before uploading.

### AI Suggestions

**Q: Why did AI suggest the wrong source column?**
A: Usually because the source description wasn't clear enough, or there's no historical pattern for that target column.

**Q: Can I improve AI suggestions?**
A: Yes! When you reject a suggestion, provide feedback. When you edit and approve, that becomes a new pattern.

**Q: What if no suggestion appears for a column?**
A: The AI couldn't find a match. You can create a manual mapping or skip the column.

**Q: Why is discovery taking a long time?**
A: Large tables with many columns take longer. The AI is calling the LLM for each column. You can work on other tables while waiting.

### Mappings

**Q: Can I edit an approved mapping?**
A: Yes, go to the completed table and click edit on any mapping.

**Q: What happens when I reject a suggestion?**
A: The rejection is recorded and helps the AI avoid similar mistakes. The column becomes "unmatched" and you can create a manual mapping.

**Q: How do I create a mapping without AI?**
A: Click "Create Manual Mapping" on an unmatched column. Select source fields and write the SQL expression.

### Troubleshooting

**Q: Discovery failed - what happened?**
A: Check the error message. Common causes:
- AI model endpoint is down
- No source fields uploaded
- No historical patterns for this table

**Q: My progress isn't updating**
A: Refresh the page. Counters update in real-time but UI may cache.

**Q: I can't see a project I should have access to**
A: Ask the project owner to add your email to team members.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + K` | Focus search box |
| `Esc` | Close dialogs |
| `Enter` | Submit form (when focused) |

---

## Getting Help

If you need assistance:
1. Review this user guide
2. Check the Quick Start guide
3. Verify system status on Home page
4. Contact your administrator
5. Reach out to the development team

---

**Version**: 4.0 - Target-First Workflow
**Last Updated**: December 2025
**Key Features**: Project-based mapping, Bulk AI suggestions, Progress tracking, Team collaboration
