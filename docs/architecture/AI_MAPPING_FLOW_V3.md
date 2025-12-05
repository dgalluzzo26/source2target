# AI Mapping Flow V3 - Complete Patterns + Rejection Learning

## Overview

The V3 AI mapping flow uses:
1. **Vector Search on Semantic Fields** - Find matching target fields
2. **Vector Search on Mapping Patterns** - Find similar past mappings (complete context)
3. **Vector Search on Rejections** - Find past rejections to avoid
4. **LLM Reasoning** - Combine all inputs to generate intelligent suggestions

## Key Insight

**Previous Issue:** `mapping_feedback` only captured individual column pairs, missing:
- Multi-field mappings (first_name + last_name → full_name)
- Transformations applied (TRIM, UPPER)
- Join conditions for multi-table mappings

**Solution:** New `mapping_patterns` table captures complete mappings as single rows, like the export output.

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI MAPPING SUGGESTION FLOW V3                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User Selects Source Fields                                                 │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │ • first_name (STRING) - "Member's first name"            │              │
│  │ • last_name (STRING) - "Member's last name"              │              │
│  └──────────────────────────────────────────────────────────┘              │
│                          │                                                  │
│                          ▼                                                  │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │            BUILD SEMANTIC QUERY                          │              │
│  │  "SOURCE TABLES: member | SOURCE COLUMNS: first_name,    │              │
│  │   last_name | DESCRIPTIONS: Member's first name,         │              │
│  │   Member's last name | TYPES: STRING, STRING"            │              │
│  └──────────────────────────────────────────────────────────┘              │
│                          │                                                  │
│         ┌────────────────┼────────────────┐                                │
│         │                │                │                                │
│         ▼                ▼                ▼                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                        │
│  │   VECTOR    │  │   VECTOR    │  │   VECTOR    │                        │
│  │   SEARCH    │  │   SEARCH    │  │   SEARCH    │                        │
│  │  ─────────  │  │  ─────────  │  │  ─────────  │                        │
│  │  semantic   │  │  mapping    │  │  mapping    │                        │
│  │  _fields    │  │  _patterns  │  │  _feedback  │                        │
│  │  (targets)  │  │  (history)  │  │  (rejects)  │                        │
│  └─────────────┘  └─────────────┘  └─────────────┘                        │
│         │                │                │                                │
│         │                │                │                                │
│         ▼                ▼                ▼                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                        │
│  │ Top Target  │  │ Similar     │  │ Past        │                        │
│  │ Matches     │  │ Patterns    │  │ Rejections  │                        │
│  │             │  │             │  │             │                        │
│  │ • full_name │  │ • 2 fields  │  │ • Avoid     │                        │
│  │ • member_id │  │   → name    │  │   these     │                        │
│  │ • ssn       │  │ • TRIM+     │  │   combos    │                        │
│  │             │  │   UPPER     │  │             │                        │
│  └─────────────┘  └─────────────┘  └─────────────┘                        │
│         │                │                │                                │
│         └────────────────┼────────────────┘                                │
│                          │                                                  │
│                          ▼                                                  │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │                    LLM REASONING                         │              │
│  │                                                          │              │
│  │  Input:                                                  │              │
│  │  • Source fields with descriptions                       │              │
│  │  • Target field candidates from semantic search          │              │
│  │  • Similar past mappings (complete patterns)             │              │
│  │  • Past rejections to avoid                              │              │
│  │                                                          │              │
│  │  Output:                                                 │              │
│  │  • Ranked suggestions with reasoning                     │              │
│  │  • Recommended transformations                           │              │
│  │  • Multi-field combination suggestions                   │              │
│  │  • Confidence scores                                     │              │
│  └──────────────────────────────────────────────────────────┘              │
│                          │                                                  │
│                          ▼                                                  │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │               AI SUGGESTIONS TO USER                     │              │
│  │                                                          │              │
│  │  1. full_name (95%) - "Combine first + last with SPACE,  │              │
│  │     apply TRIM+UPPER based on similar past mapping"      │              │
│  │                                                          │              │
│  │  2. member_name (72%) - "Alternative target..."          │              │
│  └──────────────────────────────────────────────────────────┘              │
│                          │                                                  │
│              ┌───────────┴───────────┐                                     │
│              ▼                       ▼                                     │
│       ┌─────────────┐         ┌─────────────┐                             │
│       │   ACCEPT    │         │   REJECT    │                             │
│       │             │         │             │                             │
│       │  → Create   │         │  → Record   │                             │
│       │    mapping  │         │    in       │                             │
│       │  → Record   │         │    feedback │                             │
│       │    pattern  │         │    (vector  │                             │
│       │    (auto)   │         │    indexed) │                             │
│       └─────────────┘         └─────────────┘                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tables Involved

### 1. `semantic_fields` (Existing)
Target field definitions with vector-searchable semantic field.
```
semantic_field = "TABLE: Member | COLUMN: Full Name | TYPE: STRING | DESCRIPTION: Complete member name"
```

### 2. `mapping_patterns` (NEW)
Complete mapping history as single rows.
```
source_semantic_field = "SOURCE TABLES: member | SOURCE COLUMNS: first_name, last_name | 
                         DESCRIPTIONS: Member first name, Member last name | 
                         TRANSFORMATIONS: TRIM, UPPER | MULTI-FIELD: true"
```

Key fields:
- `source_fields_json` - Complete source field details as JSON array
- `source_descriptions` - Combined descriptions for vector search
- `transformation_expression` - Full SQL expression
- `source_field_count` - For multi-field detection
- `has_joins` / `joins_json` - Join details

### 3. `mapping_feedback` (Simplified - Rejections Only)
Now primarily for rejections (acceptances automatically go to mapping_patterns).
```
source_semantic_field = "TABLE: claims | COLUMN: member_ssn | DESCRIPTION: Social security number"
```

---

## When Mappings Are Created

```python
# After user accepts a mapping:
1. Insert into mapped_fields (target side)
2. Insert into mapping_details (source fields)
3. Insert into mapping_joins (if multi-table)
4. AUTO-INSERT into mapping_patterns (for future AI learning)
```

The `mapping_patterns` record captures the COMPLETE picture in a single row.

---

## Code Changes Required

### Backend Changes

1. **New Service: `mapping_patterns_service.py`**
   - Create pattern from completed mapping
   - Vector search on patterns

2. **Update: `ai_mapping_service_v2.py`**
   - Add `_vector_search_patterns_sync()` method
   - Add `_vector_search_rejections_sync()` method  
   - Update `generate_multi_field_suggestions()` to use all 3 vector searches
   - Update LLM prompt to include pattern history

3. **Update: `mapping_service_v2.py`**
   - After creating mapping, auto-insert into `mapping_patterns`

4. **Update: `feedback_service.py`**
   - Add `source_semantic_field` to rejections for vector search

### Config Changes

Add to `app_config.json`:
```json
{
  "database": {
    "mapping_patterns_table": "mapping_patterns"
  },
  "vector_search": {
    "patterns_index_name": "oztest_dev.source2target.mapping_patterns_semantic_idx",
    "feedback_index_name": "oztest_dev.source2target.feedback_rejection_idx"
  }
}
```

---

## Benefits of This Approach

1. **Complete Context**: AI sees full mappings, not just column pairs
2. **Learn Transformations**: AI can suggest TRIM, UPPER, etc. based on history
3. **Multi-Field Detection**: AI knows when to suggest combining fields
4. **Avoid Past Mistakes**: Vector search on rejections prevents repeating bad suggestions
5. **Semantic Matching**: Works across different source systems with different naming conventions

