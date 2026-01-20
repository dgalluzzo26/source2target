# AI Mapping Flow V4 - Target-First with Pattern Reuse

## Overview

The V4 AI mapping flow enables **Target-First** mapping where the AI automatically suggests mappings for entire tables by:

1. **Finding Past Patterns** - Search `mapped_fields` for similar historical mappings
2. **Matching User Sources** - Find user's source fields that match the pattern's semantic roles
3. **Rewriting SQL** - Use LLM to rewrite pattern SQL with user's source tables/columns
4. **Presenting Suggestions** - Store suggestions for user review and approval

## Key Insight

**V3 Problem**: Users had to select source fields one-by-one and search for targets manually.

**V4 Solution**: Work from the target table perspective. Select a target table, and the AI finds the best source fields for ALL columns automatically.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     V4 TARGET-FIRST AI MAPPING FLOW                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ INPUT: User selects target table (e.g., MBR_CNTCT)                          ││
│  │                                                                              ││
│  │ Available: User's source fields in unmapped_fields (with project_id)       ││
│  │ ┌──────────────────────────────────────────────────────────────────────────┐││
│  │ │ my_member_base.MBR_KEY       │ "Member surrogate key"                    │││
│  │ │ my_member_base.ADDR_LINE_1   │ "Primary street address"                  │││
│  │ │ my_member_base.CTY_CODE      │ "County FIPS code"                        │││
│  │ │ my_member_addr.MBR_KEY       │ "Member key reference"                    │││
│  │ │ my_member_addr.STREET_1      │ "Street address line 1"                   │││
│  │ │ my_member_addr.ADDR_TYPE     │ "Address type (R/M)"                      │││
│  │ └──────────────────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                          │                                       │
│                                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ FOR EACH target column in MBR_CNTCT (from semantic_fields):                 ││
│  │   - ADDR_1_TXT (First address line)                                         ││
│  │   - ADDR_2_TXT (Second address line)                                        ││
│  │   - CITY_TXT (City name)                                                    ││
│  │   - MBR_SK (Member surrogate key)                                           ││
│  │   - ... (25 columns total)                                                  ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                          │                                       │
│                                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │                    STEP 1: FIND PAST PATTERN                                ││
│  │                                                                              ││
│  │  Query mapped_fields WHERE:                                                 ││
│  │    - is_approved_pattern = TRUE                                             ││
│  │    - Matches target table/column                                            ││
│  │                                                                              ││
│  │  For: ADDR_1_TXT                                                            ││
│  │  Found Pattern:                                                             ││
│  │  ┌──────────────────────────────────────────────────────────────────────┐  ││
│  │  │ pattern_type: UNION_WITH_JOINS                                       │  ││
│  │  │ source_expression:                                                   │  ││
│  │  │   SELECT DISTINCT INITCAP(b.ADDR_LINE_1) AS ADDR_1_TXT              │  ││
│  │  │   FROM oz_dev.bronze_dmes.t_re_base b                               │  ││
│  │  │   JOIN oz_dev.silver_dmes.mbr_fndtn mf                              │  ││
│  │  │     ON b.SAK_RECIP = mf.SRC_KEY_ID AND mf.CURR_REC_IND='1'          │  ││
│  │  │   LEFT JOIN oz_dev.silver_dmes.cnty_cd c                            │  ││
│  │  │     ON b.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND='1'              │  ││
│  │  │   UNION DISTINCT                                                     │  ││
│  │  │   SELECT DISTINCT INITCAP(a.ADDR_LINE_1) AS ADDR_1_TXT              │  ││
│  │  │   FROM oz_dev.bronze_dmes.t_re_multi_address a ...                  │  ││
│  │  │                                                                      │  ││
│  │  │ join_metadata: { ... structured JSON ... }                          │  ││
│  │  └──────────────────────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                          │                                       │
│                                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │                    STEP 2: MATCH USER'S SOURCE FIELDS                       ││
│  │                                                                              ││
│  │  Use join_metadata to identify required semantic roles:                     ││
│  │  - output_column (required): Address line 1                                 ││
│  │  - join_key_source (required): Member key                                   ││
│  │  - filter_column (optional): Record indicator                               ││
│  │                                                                              ││
│  │  Vector search user's unmapped_fields for matches:                          ││
│  │  ┌────────────────────────────────────────────────────────────────┐        ││
│  │  │ Role            │ Matched Source Field     │ Score │           │        ││
│  │  │ output_column   │ my_member_base.ADDR_LINE_1│ 0.95 │ ✅        │        ││
│  │  │ output_column   │ my_member_addr.STREET_1   │ 0.92 │ ✅ (union)│        ││
│  │  │ join_key_source │ my_member_base.MBR_KEY    │ 0.89 │ ✅        │        ││
│  │  │ join_key_source │ my_member_addr.MBR_KEY    │ 0.87 │ ✅        │        ││
│  │  └────────────────────────────────────────────────────────────────┘        ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                          │                                       │
│                                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │                    STEP 3: LLM REWRITES SQL                                 ││
│  │                                                                              ││
│  │  Prompt to LLM:                                                             ││
│  │  ┌──────────────────────────────────────────────────────────────────────┐  ││
│  │  │ You are rewriting a SQL mapping pattern for a new source system.    │  ││
│  │  │                                                                      │  ││
│  │  │ ORIGINAL PATTERN (from historical mapping):                          │  ││
│  │  │ [pattern SQL]                                                        │  ││
│  │  │                                                                      │  ││
│  │  │ TABLES TO REPLACE (bronze/source tables):                            │  ││
│  │  │ - oz_dev.bronze_dmes.t_re_base → my_member_base                      │  ││
│  │  │ - oz_dev.bronze_dmes.t_re_multi_address → my_member_addr             │  ││
│  │  │                                                                      │  ││
│  │  │ COLUMNS TO REPLACE:                                                  │  ││
│  │  │ - b.ADDR_LINE_1 → b.ADDR_LINE_1 (same name)                          │  ││
│  │  │ - a.ADDR_LINE_1 → a.STREET_1 (different name)                        │  ││
│  │  │ - b.SAK_RECIP → b.MBR_KEY                                            │  ││
│  │  │                                                                      │  ││
│  │  │ KEEP UNCHANGED (silver/lookup tables):                               │  ││
│  │  │ - oz_dev.silver_dmes.mbr_fndtn                                       │  ││
│  │  │ - oz_dev.silver_dmes.cnty_cd                                         │  ││
│  │  │                                                                      │  ││
│  │  │ TRANSFORMATIONS: Keep INITCAP()                                      │  ││
│  │  │                                                                      │  ││
│  │  │ Output the rewritten SQL only.                                       │  ││
│  │  └──────────────────────────────────────────────────────────────────────┘  ││
│  │                                                                              ││
│  │  LLM Output (suggested_sql):                                                ││
│  │  ┌──────────────────────────────────────────────────────────────────────┐  ││
│  │  │ SELECT DISTINCT INITCAP(b.ADDR_LINE_1) AS ADDR_1_TXT                 │  ││
│  │  │ FROM my_member_base b                               ◄── CHANGED      │  ││
│  │  │ JOIN oz_dev.silver_dmes.mbr_fndtn mf                                 │  ││
│  │  │   ON b.MBR_KEY = mf.SRC_KEY_ID AND mf.CURR_REC_IND='1' ◄── CHANGED   │  ││
│  │  │ LEFT JOIN oz_dev.silver_dmes.cnty_cd c                               │  ││
│  │  │   ON b.CTY_CODE = c.CNTY_ID AND c.CURR_REC_IND='1'                   │  ││
│  │  │ UNION DISTINCT                                                       │  ││
│  │  │ SELECT DISTINCT INITCAP(a.STREET_1) AS ADDR_1_TXT   ◄── CHANGED      │  ││
│  │  │ FROM my_member_addr a                               ◄── CHANGED      │  ││
│  │  │ JOIN oz_dev.silver_dmes.mbr_fndtn mf                                 │  ││
│  │  │   ON a.MBR_KEY = mf.SRC_KEY_ID AND mf.CURR_REC_IND='1' ◄── CHANGED   │  ││
│  │  │ ...                                                                  │  ││
│  │  └──────────────────────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                          │                                       │
│                                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │                    STEP 4: STORE SUGGESTION                                 ││
│  │                                                                              ││
│  │  INSERT INTO mapping_suggestions:                                           ││
│  │  ┌──────────────────────────────────────────────────────────────────────┐  ││
│  │  │ suggestion_id: 1                                                     │  ││
│  │  │ project_id: 5                                                        │  ││
│  │  │ target_table_status_id: 42                                           │  ││
│  │  │ tgt_column_name: ADDR_1_TXT                                          │  ││
│  │  │ pattern_type: UNION_WITH_JOINS                                       │  ││
│  │  │ pattern_sql: [original pattern]                                      │  ││
│  │  │ suggested_sql: [rewritten SQL]                                       │  ││
│  │  │ matched_source_fields: [JSON array]                                  │  ││
│  │  │ confidence_score: 0.94                                               │  ││
│  │  │ suggestion_status: PENDING                                           │  ││
│  │  └──────────────────────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                          │                                       │
│                                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │                    STEP 5: USER REVIEW                                      ││
│  │                                                                              ││
│  │  User sees:                                                                 ││
│  │  ┌──────────────────────────────────────────────────────────────────────┐  ││
│  │  │ ✅ ADDR_1_TXT (First address line)               Confidence: 94%    │  ││
│  │  │ Pattern: UNION_WITH_JOINS                                            │  ││
│  │  │ Sources: my_member_base.ADDR_LINE_1, my_member_addr.STREET_1         │  ││
│  │  │                                                                      │  ││
│  │  │ SQL with changes highlighted:                                        │  ││
│  │  │ [... diff view ...]                                                  │  ││
│  │  │                                                                      │  ││
│  │  │ [✓ Approve] [✎ Edit] [✗ Reject] [→ Skip]                            │  ││
│  │  └──────────────────────────────────────────────────────────────────────┘  ││
│  │                                                                              ││
│  │  On Approve:                                                                ││
│  │    → Create mapped_fields row with project_id                               ││
│  │    → Update suggestion_status = 'APPROVED'                                  ││
│  │    → Update source fields mapping_status = 'MAPPED'                         ││
│  │    → Increment table/project counters                                       ││
│  │                                                                              ││
│  │  On Reject:                                                                 ││
│  │    → Record in mapping_feedback for learning                                ││
│  │    → Mark column as needing manual mapping                                  ││
│  │                                                                              ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Structures

### `join_metadata` JSON Schema

The `join_metadata` column in `mapped_fields` stores structured information about complex SQL patterns.

```json
{
  "patternType": "UNION_WITH_JOINS",
  "outputColumn": {
    "alias": "ADDR_1_TXT",
    "transformation": "INITCAP"
  },
  "unionBranches": [
    {
      "branchName": "primary_address",
      "sourceTable": {
        "catalog": "oz_dev",
        "schema": "bronze_dmes",
        "table": "t_re_base",
        "alias": "b",
        "tableType": "bronze"
      },
      "outputColumn": {
        "column": "ADDR_LINE_1",
        "role": "output"
      },
      "joins": [
        {
          "joinType": "INNER",
          "targetTable": {
            "catalog": "oz_dev",
            "schema": "silver_dmes",
            "table": "mbr_fndtn",
            "alias": "mf",
            "tableType": "silver"
          },
          "joinConditions": [
            {
              "sourceColumn": "SAK_RECIP",
              "sourceRole": "join_key_source",
              "targetColumn": "SRC_KEY_ID",
              "targetRole": "join_key_target"
            }
          ],
          "filters": ["mf.CURR_REC_IND = '1'"]
        }
      ]
    },
    {
      "branchName": "alternate_address",
      "sourceTable": {
        "catalog": "oz_dev",
        "schema": "bronze_dmes",
        "table": "t_re_multi_address",
        "alias": "a",
        "tableType": "bronze"
      },
      "subqueryFilter": "trim(CDE_ADDR_USAGE) in ('R','M') and CURR_REC_IND='1'",
      "outputColumn": {
        "column": "ADDR_LINE_1",
        "role": "output"
      },
      "joins": [...]
    }
  ],
  "userColumnsToMap": [
    {
      "role": "output",
      "originalColumn": "ADDR_LINE_1",
      "description": "Address line 1 to be extracted"
    },
    {
      "role": "join_key_source",
      "originalColumn": "SAK_RECIP",
      "description": "Member key for joining to silver"
    }
  ],
  "silverTablesConstant": [
    "oz_dev.silver_dmes.mbr_fndtn",
    "oz_dev.silver_dmes.cnty_cd"
  ]
}
```

### `matched_source_fields` JSON

Stored in `mapping_suggestions` to record which user source fields matched which roles.

```json
[
  {
    "role": "output",
    "originalColumn": "ADDR_LINE_1",
    "matchedTable": "my_member_base",
    "matchedColumn": "ADDR_LINE_1",
    "matchScore": 0.95,
    "matchReason": "Exact semantic match: 'Primary street address'"
  },
  {
    "role": "output",
    "originalColumn": "ADDR_LINE_1",
    "matchedTable": "my_member_addr",
    "matchedColumn": "STREET_1",
    "matchScore": 0.92,
    "matchReason": "Semantic similarity: 'Street address line 1'"
  },
  {
    "role": "join_key_source",
    "originalColumn": "SAK_RECIP",
    "matchedTable": "my_member_base",
    "matchedColumn": "MBR_KEY",
    "matchScore": 0.89,
    "matchReason": "Semantic match: 'Member surrogate key'"
  }
]
```

---

## Confidence Scoring

The overall confidence score combines:

1. **Pattern Confidence** (40%): How well the pattern matches the target column
   - Exact match: 1.0
   - Same table, similar column: 0.8
   - Similar table: 0.6
   - Generic pattern: 0.4

2. **Source Match Confidence** (40%): Average semantic similarity of matched sources
   - Vector search score for each matched field
   - Weighted by role importance

3. **Completeness Confidence** (20%): Are all required roles filled?
   - All roles matched: 1.0
   - Optional roles missing: 0.8
   - Required roles missing: 0.4

```
confidence = (pattern_confidence * 0.4) + 
             (source_match_avg * 0.4) + 
             (completeness * 0.2)
```

---

## Tables Involved

### Source Tables

| Table | Purpose |
|-------|---------|
| `semantic_fields` | Target column definitions (what we're mapping TO) |
| `unmapped_fields` | User's source columns (what we're mapping FROM) |
| `mapped_fields` | Approved patterns (historical + new) |

### Working Tables

| Table | Purpose |
|-------|---------|
| `mapping_projects` | Project tracking and progress |
| `target_table_status` | Per-table mapping progress |
| `mapping_suggestions` | AI suggestions pending review |
| `mapping_feedback` | Rejection learning |

---

## Pattern Recognition

### Pattern Types

| Type | Description | Example |
|------|-------------|---------|
| `DIRECT` | Simple 1:1 mapping | `TRIM(UPPER(col))` |
| `MULTI_FIELD` | Multiple sources concatenated | `first_name || ' ' || last_name` |
| `JOIN` | Single source with JOINs | `SELECT a.col FROM a JOIN b...` |
| `UNION` | Multiple sources combined | `SELECT ... UNION SELECT ...` |
| `UNION_WITH_JOINS` | Complex multi-table | `SELECT ... FROM a JOIN b UNION SELECT ... FROM c JOIN d` |

### Silver vs Bronze Detection

The AI distinguishes between:

**Silver Tables (constant)**: Lookup/reference tables that don't change
- Identified by schema prefix: `silver_*`
- Or explicitly listed in `join_metadata.silverTablesConstant`

**Bronze Tables (replaceable)**: Source data tables
- Identified by schema prefix: `bronze_*`
- Or any table not in silver list

---

## API Endpoints

### Start Discovery
```
POST /api/v4/projects/{id}/target-tables/{table_id}/discover
```

Triggers async AI suggestion generation for all columns in the table.

### Get Suggestions
```
GET /api/v4/projects/{id}/target-tables/{table_id}/suggestions
```

Returns all suggestions for a table with status.

### Approve Suggestion
```
POST /api/v4/suggestions/{suggestion_id}/approve
```

Creates mapped_fields row, updates counters.

### Edit Suggestion
```
POST /api/v4/suggestions/{suggestion_id}/edit
Body: { "edited_sql": "..." }
```

Saves edited SQL, creates mapped_fields row.

### Reject Suggestion
```
POST /api/v4/suggestions/{suggestion_id}/reject
Body: { "reason": "...", "feedback": "..." }
```

Records rejection for learning, marks column as unmatched.

---

## Benefits of V4 Approach

1. **Efficiency**: Map entire tables at once, not field-by-field
2. **Consistency**: Same pattern applied across all columns
3. **Learning**: Rejections improve future suggestions
4. **Visibility**: Clear progress tracking at table and project level
5. **Collaboration**: Multiple users can work on different tables
6. **Auditability**: Full trail of suggestions, edits, approvals

---

## Future Enhancements

1. **Auto-Approval**: Confidence threshold for automatic approval
2. **Batch Patterns**: Generate patterns for similar tables simultaneously
3. **Pattern Suggestions**: AI suggests which historical pattern to use
4. **Conflict Detection**: Identify when same source mapped differently
5. **Impact Analysis**: Show downstream effects of mapping changes

---

**Version**: 4.0 - Target-First Workflow
**Last Updated**: December 2025

