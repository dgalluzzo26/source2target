# Smart Mapper: AI-Powered Field Mapping Architecture

## Executive Summary

Smart Mapper uses **AI and vector search** to intelligently suggest data field mappings from source systems to target schemas. The system learns from historical patterns and user feedback to continuously improve suggestions.

---

## The Three Pillars of AI Mapping

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                        THREE VECTOR SEARCHES                                │
│                                                                             │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐       │
│  │                   │  │                   │  │                   │       │
│  │   📎 SEMANTIC     │  │   📚 MAPPING      │  │   🚫 REJECTION    │       │
│  │      FIELDS       │  │      PATTERNS     │  │      HISTORY      │       │
│  │                   │  │                   │  │                   │       │
│  │   "What target    │  │   "How did we     │  │   "What should    │       │
│  │    fields match   │  │    map similar    │  │    we avoid       │       │
│  │    these sources?"│  │    fields before?"│  │    suggesting?"   │       │
│  │                   │  │                   │  │                   │       │
│  │   ─────────────   │  │   ─────────────   │  │   ─────────────   │       │
│  │                   │  │                   │  │                   │       │
│  │   • Target field  │  │   • Multi-field   │  │   • Previously    │       │
│  │     candidates    │  │     combinations  │  │     rejected      │       │
│  │   • Data types    │  │   • Transform-    │  │     mappings      │       │
│  │   • Descriptions  │  │     ations used   │  │   • User feedback │       │
│  │                   │  │   • Join patterns │  │     reasoning     │       │
│  │                   │  │                   │  │                   │       │
│  │   PRIMARY         │  │   LEARNING        │  │   AVOIDANCE       │       │
│  │   Always needed   │  │   From history    │  │   From feedback   │       │
│  │                   │  │                   │  │                   │       │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete AI Mapping Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                         AI MAPPING SUGGESTION FLOW                          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   STEP 1: USER SELECTS SOURCE FIELDS                                        │
│   ══════════════════════════════════                                        │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │  ☑ first_name  (STRING)  "Member's legal first name"            │      │
│   │  ☑ last_name   (STRING)  "Member's legal last name"             │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                                    │                                        │
│                                    ▼                                        │
│   STEP 2: BUILD SEMANTIC QUERY                                              │
│   ════════════════════════════                                              │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │  "SOURCE TABLES: member                                         │      │
│   │   SOURCE COLUMNS: first_name, last_name                         │      │
│   │   DESCRIPTIONS: Member's legal first name, Member's legal last  │      │
│   │   TYPES: STRING, STRING"                                        │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                                    │                                        │
│                    ┌───────────────┼───────────────┐                       │
│                    │               │               │                       │
│                    ▼               ▼               ▼                       │
│   STEP 3: PARALLEL VECTOR SEARCHES                                          │
│   ════════════════════════════════                                          │
│                                                                             │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                      │
│   │  SEMANTIC   │   │  MAPPING    │   │  REJECTION  │                      │
│   │  FIELDS     │   │  PATTERNS   │   │  HISTORY    │                      │
│   │             │   │             │   │             │                      │
│   │  Targets:   │   │  History:   │   │  Avoid:     │                      │
│   │  • full_name│   │  • 2 cols   │   │  • ssn →    │                      │
│   │  • member_  │   │    → name   │   │    full_name│                      │
│   │    name     │   │  • TRIM +   │   │    (wrong!) │                      │
│   │  • display_ │   │    UPPER    │   │             │                      │
│   │    name     │   │  • SPACE    │   │             │                      │
│   │             │   │    concat   │   │             │                      │
│   └─────────────┘   └─────────────┘   └─────────────┘                      │
│          │                 │                 │                              │
│          └─────────────────┴─────────────────┘                              │
│                            │                                                │
│                            ▼                                                │
│   STEP 4: LLM REASONING                                                     │
│   ═════════════════════                                                     │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                    🤖 FOUNDATION MODEL                          │      │
│   │                                                                 │      │
│   │   INPUTS:                                                       │      │
│   │   • Source field names, types, descriptions                     │      │
│   │   • Target field candidates from semantic search                │      │
│   │   • Similar historical mapping patterns                         │      │
│   │   • Past rejections to avoid                                    │      │
│   │                                                                 │      │
│   │   REASONING:                                                    │      │
│   │   "Based on the source fields 'first_name' and 'last_name'     │      │
│   │    with descriptions about member names, and historical         │      │
│   │    patterns showing similar fields mapped to 'full_name'        │      │
│   │    using TRIM+UPPER transformations with SPACE concatenation,   │      │
│   │    I recommend..."                                              │      │
│   │                                                                 │      │
│   │   OUTPUTS:                                                      │      │
│   │   • Ranked target suggestions with confidence scores            │      │
│   │   • Recommended transformations                                 │      │
│   │   • Multi-field combination suggestions                         │      │
│   │   • Human-readable reasoning                                    │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                            │                                                │
│                            ▼                                                │
│   STEP 5: PRESENT SUGGESTIONS                                               │
│   ═══════════════════════════                                               │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                                                                 │      │
│   │   🎯 TOP SUGGESTION (95% confidence)                            │      │
│   │   ─────────────────────────────────                             │      │
│   │   Target: full_name                                             │      │
│   │   Transformations: TRIM, UPPER                                  │      │
│   │   Concatenation: SPACE                                          │      │
│   │                                                                 │      │
│   │   "Combine first_name and last_name with space separator.       │      │
│   │    Apply TRIM and UPPER based on 15 similar past mappings."     │      │
│   │                                                                 │      │
│   │   [ ✓ ACCEPT ]                    [ ✗ REJECT ]                  │      │
│   │                                                                 │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                            │                                                │
│              ┌─────────────┴─────────────┐                                 │
│              ▼                           ▼                                 │
│   STEP 6: LEARNING LOOP                                                     │
│   ═════════════════════                                                     │
│                                                                             │
│   ┌─────────────────────┐       ┌─────────────────────┐                    │
│   │      ✓ ACCEPT       │       │      ✗ REJECT       │                    │
│   │                     │       │                     │                    │
│   │  • Create mapping   │       │  • Record rejection │                    │
│   │  • Auto-save to     │       │    with reason      │                    │
│   │    mapping_patterns │       │  • Vector-indexed   │                    │
│   │  • Available for    │       │    for future       │                    │
│   │    future learning  │       │    avoidance        │                    │
│   │                     │       │                     │                    │
│   │    ┌───────────┐    │       │    ┌───────────┐    │                    │
│   │    │  📚 NEW   │    │       │    │  🚫 NEW   │    │                    │
│   │    │  PATTERN  │    │       │    │ REJECTION │    │                    │
│   │    │  LEARNED  │    │       │    │  LEARNED  │    │                    │
│   │    └───────────┘    │       │    └───────────┘    │                    │
│   └─────────────────────┘       └─────────────────────┘                    │
│                                                                             │
│                         ↻ CONTINUOUS IMPROVEMENT                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Structures

### 1. Semantic Fields (Target Definitions)

**Purpose:** Define available target fields for mapping

| Column | Description | Example |
|--------|-------------|---------|
| `semantic_field_id` | Primary key | 42 |
| `tgt_table_name` | Target table logical name | "Member" |
| `tgt_column_name` | Target column logical name | "Full Name" |
| `tgt_physical_datatype` | Data type | "STRING" |
| `tgt_comments` | Description | "Complete member name" |
| `semantic_field` | **Vector-searchable** | "TABLE: Member \| COLUMN: Full Name \| TYPE: STRING \| DESCRIPTION: Complete member name" |

---

### 2. Mapping Patterns (Complete Mapping History) ⭐ NEW

**Purpose:** Store complete mappings as single rows for AI learning

| Column | Description | Example |
|--------|-------------|---------|
| `pattern_id` | Primary key | 1 |
| `source_fields_json` | Complete source details | `[{table:"member", column:"first_name", desc:"...", transform:"TRIM,UPPER", order:1}, {...}]` |
| `source_tables` | Source tables used | "member" |
| `source_columns` | Source columns used | "first_name, last_name" |
| `source_descriptions` | Source descriptions | "Member's first name, Member's last name" |
| `source_field_count` | Number of source fields | 2 |
| `tgt_column_name` | Target column | "Full Name" |
| `concat_strategy` | How fields combined | "SPACE" |
| `transformation_expression` | Full SQL expression | `CONCAT(TRIM(UPPER(first_name)), ' ', TRIM(UPPER(last_name)))` |
| `transformations_applied` | Transformations used | "TRIM, UPPER" |
| `has_joins` | Multi-table mapping? | false |
| `source_semantic_field` | **Vector-searchable** | "SOURCE TABLES: member \| SOURCE COLUMNS: first_name, last_name \| DESCRIPTIONS: ..." |

**Key Insight:** This table captures the COMPLETE context of a mapping, not just column pairs.

---

### 3. Mapping Feedback (Rejection History)

**Purpose:** Track rejected suggestions for avoidance learning

| Column | Description | Example |
|--------|-------------|---------|
| `feedback_id` | Primary key | 101 |
| `suggested_src_table` | Source table suggested | "claims" |
| `suggested_src_column` | Source column suggested | "member_ssn" |
| `suggested_tgt_column` | Target suggested | "full_name" |
| `feedback_action` | User action | "REJECTED" |
| `user_comments` | Why rejected | "SSN is not a name field" |
| `src_comments` | Source description | "Social security number" |
| `source_semantic_field` | **Vector-searchable** | "TABLE: claims \| COLUMN: member_ssn \| DESCRIPTION: Social security number" |

---

## Why This Architecture?

### Previous Limitation

Old approach only captured **column pairs**:
```
first_name → full_name  ❌ Missing context!
```

Missing:
- Multi-field combinations
- Transformations applied
- Join conditions
- The complete "recipe"

### New Approach

New approach captures **complete patterns**:
```json
{
  "sources": ["first_name", "last_name"],
  "target": "full_name",
  "transformations": ["TRIM", "UPPER"],
  "concat": "SPACE",
  "expression": "CONCAT(TRIM(UPPER(first_name)), ' ', TRIM(UPPER(last_name)))"
}
```

This enables AI to suggest:
- ✅ Multi-field mappings
- ✅ Appropriate transformations
- ✅ Join strategies for multi-table sources
- ✅ Avoid past mistakes

---

## Benefits Summary

| Benefit | Description |
|---------|-------------|
| **🎯 Accurate Suggestions** | Vector search finds semantically similar fields, not just name matches |
| **📚 Historical Learning** | AI learns from complete past mappings, not just column pairs |
| **🔄 Multi-Field Support** | Recognizes when fields should be combined |
| **⚡ Transformation Hints** | Suggests TRIM, UPPER, etc. based on history |
| **🚫 Mistake Avoidance** | Won't repeat previously rejected suggestions |
| **🔍 Cross-System Matching** | Works even when source systems have different naming conventions |
| **📈 Continuous Improvement** | Every accept/reject improves future suggestions |

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Vector Search | Databricks Vector Search |
| LLM | Databricks Foundation Model |
| Database | Delta Lake |
| Backend | FastAPI (Python) |
| Frontend | Vue 3 + PrimeVue |

---

*Smart Mapper - Intelligent Data Field Mapping*

