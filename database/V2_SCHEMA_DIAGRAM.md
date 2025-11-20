# Source-to-Target Mapping Platform V2 - Schema Diagram

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SEMANTIC_FIELDS                                      │
│  (Target Field Definitions - One record per target field)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  PK  semantic_field_id       BIGINT (auto)                                  │
│      tgt_table               STRING                                          │
│      tgt_column              STRING                                          │
│      tgt_data_type           STRING                                          │
│      tgt_is_nullable         BOOLEAN                                         │
│      tgt_comments            STRING                                          │
│  ✨  domain                  STRING  (NEW: claims, member, provider, etc.)  │
│      semantic_field          STRING (COMPUTED - for vector embedding)        │
│      created_by, created_ts                                                  │
│      updated_by, updated_ts                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1
                                    │
                                    │ many
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MAPPED_FIELDS                                        │
│  (Active Mappings - One record per TARGET field)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  PK  mapped_field_id         BIGINT (auto)                                  │
│  FK  semantic_field_id       BIGINT → semantic_fields                       │
│      tgt_table               STRING (denormalized)                           │
│      tgt_column              STRING (denormalized)                           │
│  ✨  concat_strategy         STRING (NONE, SPACE, COMMA, PIPE, CUSTOM)      │
│  ✨  concat_separator        STRING (custom separator if needed)            │
│  ✨  transformation_expression STRING (full SQL expression)                 │
│      confidence_score        DOUBLE (0.0 - 1.0)                             │
│      mapping_source          STRING (AI, MANUAL, BULK_UPLOAD)               │
│      ai_reasoning            STRING                                          │
│      mapping_status          STRING (ACTIVE, INACTIVE, PENDING_REVIEW)      │
│      mapped_by, mapped_ts                                                    │
│      updated_by, updated_ts                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1
                                    │
                                    │ many
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MAPPING_DETAILS                                      │
│  (Source Fields in Mapping - Multiple per target field)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  PK  mapping_detail_id       BIGINT (auto)                                  │
│  FK  mapped_field_id         BIGINT → mapped_fields                         │
│  FK  unmapped_field_id       BIGINT → unmapped_fields (nullable)            │
│      src_table               STRING (denormalized)                           │
│      src_column              STRING (denormalized)                           │
│  ✨  field_order             INT (1-based ordering for concat)              │
│  ✨  transformations         STRING (comma-separated: TRIM,UPPER,etc.)      │
│  ✨  default_value           STRING (for COALESCE)                          │
│      field_confidence_score  DOUBLE (0.0 - 1.0)                             │
│      created_by, created_ts                                                  │
│      updated_by, updated_ts                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ many
                                    │
                                    │ 1 (nullable)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNMAPPED_FIELDS                                      │
│  (Source Fields Awaiting Mapping)                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  PK  unmapped_field_id       BIGINT (auto)                                  │
│      src_table               STRING                                          │
│      src_column              STRING                                          │
│      src_data_type           STRING                                          │
│      src_is_nullable         BOOLEAN                                         │
│      src_comments            STRING                                          │
│  ✨  domain                  STRING (NEW: claims, member, provider, etc.)   │
│      created_by, created_ts                                                  │
│      updated_by, updated_ts                                                  │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         MAPPING_FEEDBACK                                     │
│  (Audit Trail for AI Suggestions)                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  PK  feedback_id             BIGINT (auto)                                  │
│      suggested_src_table     STRING                                          │
│      suggested_src_column    STRING                                          │
│      suggested_tgt_table     STRING                                          │
│      suggested_tgt_column    STRING                                          │
│      ai_confidence_score     DOUBLE                                          │
│      ai_reasoning            STRING                                          │
│      vector_search_score     DOUBLE                                          │
│      suggestion_rank         INT                                             │
│  ✨  feedback_action         STRING (ACCEPTED, REJECTED, MODIFIED)          │
│  ✨  user_comments           STRING                                          │
│  ✨  modified_src_table      STRING (if MODIFIED)                           │
│  ✨  modified_src_column     STRING (if MODIFIED)                           │
│  ✨  modified_transformations STRING (if MODIFIED)                          │
│  FK  mapped_field_id         BIGINT → mapped_fields (if accepted/modified)  │
│      domain                  STRING                                          │
│      feedback_by, feedback_ts                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ many
                                    │
                                    │ 1 (nullable)
                                    ▼
                         (back to MAPPED_FIELDS)


┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRANSFORMATION_LIBRARY                               │
│  (Reusable Transformation Templates)                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  PK  transformation_id       BIGINT (auto)                                  │
│      transformation_name     STRING (e.g., "Standard Name Format")          │
│      transformation_code     STRING (e.g., "STD_NAME")                      │
│      transformation_expression STRING (e.g., "TRIM(UPPER({field}))")       │
│      transformation_description STRING                                      │
│      category                STRING (TEXT, DATE, NUMERIC, CUSTOM)           │
│      is_system               BOOLEAN (system vs. user-defined)              │
│      created_by, created_ts                                                  │
│      updated_by, updated_ts                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### Flow 1: Creating a Simple 1:1 Mapping (Like V1)

```
User selects:
  Source: T_MEMBER.SSN
  Target: slv_member.ssn_number
  Transformation: TRIM, UNFORMAT_SSN

↓

1. Insert into MAPPED_FIELDS
   - semantic_field_id = (lookup from semantic_fields)
   - tgt_table = 'slv_member'
   - tgt_column = 'ssn_number'
   - concat_strategy = 'NONE'
   - transformation_expression = 'REPLACE(TRIM(T_MEMBER.SSN), "-", "")'
   - mapping_source = 'MANUAL'

↓

2. Insert into MAPPING_DETAILS
   - mapped_field_id = (from step 1)
   - src_table = 'T_MEMBER'
   - src_column = 'SSN'
   - field_order = 1
   - transformations = 'TRIM,UNFORMAT_SSN'

↓

3. Remove from UNMAPPED_FIELDS (optional)
   - DELETE WHERE src_table = 'T_MEMBER' AND src_column = 'SSN'
```

---

### Flow 2: Creating a Multi-Field Mapping (New in V2)

```
User selects:
  Source 1: T_MEMBER.FIRST_NAME (order: 1, transform: TRIM, INITCAP)
  Source 2: T_MEMBER.LAST_NAME  (order: 2, transform: TRIM, INITCAP)
  Target: slv_member.full_name
  Concat: SPACE

↓

1. Insert into MAPPED_FIELDS
   - semantic_field_id = (lookup from semantic_fields)
   - tgt_table = 'slv_member'
   - tgt_column = 'full_name'
   - concat_strategy = 'SPACE'
   - transformation_expression = 'CONCAT(INITCAP(TRIM(T_MEMBER.FIRST_NAME)), " ", ...)'
   - mapping_source = 'MANUAL'

↓

2. Insert into MAPPING_DETAILS (2 records)
   Record 1:
   - mapped_field_id = (from step 1)
   - src_table = 'T_MEMBER'
   - src_column = 'FIRST_NAME'
   - field_order = 1
   - transformations = 'TRIM,INITCAP'

   Record 2:
   - mapped_field_id = (from step 1)
   - src_table = 'T_MEMBER'
   - src_column = 'LAST_NAME'
   - field_order = 2
   - transformations = 'TRIM,INITCAP'

↓

3. Remove from UNMAPPED_FIELDS (2 records)
   - DELETE WHERE src_table = 'T_MEMBER' AND src_column = 'FIRST_NAME'
   - DELETE WHERE src_table = 'T_MEMBER' AND src_column = 'LAST_NAME'
```

---

### Flow 3: AI Suggestion with Feedback

```
1. User requests AI suggestions for T_MEMBER.SSN

↓

2. AI Service:
   - Searches vector index on semantic_fields
   - Calls Foundation Model for reasoning
   - Returns top 5 suggestions with confidence scores

↓

3. User reviews suggestions:
   Suggestion 1: T_MEMBER.SSN → slv_member.ssn_number (95% confidence)
   Suggestion 2: T_MEMBER.SSN → slv_member.tax_id (60% confidence)
   ...

↓

4a. User ACCEPTS Suggestion 1:
    - Insert into MAPPED_FIELDS + MAPPING_DETAILS (as in Flow 1)
    - Insert into MAPPING_FEEDBACK:
      * feedback_action = 'ACCEPTED'
      * mapped_field_id = (from mapping)
      * ai_confidence_score = 0.95
      * ai_reasoning = "Both fields are Social Security identifiers..."

↓

4b. User REJECTS Suggestion 1:
    - Insert into MAPPING_FEEDBACK:
      * feedback_action = 'REJECTED'
      * user_comments = "SSN should map to member_id, not ssn_number"
      * mapped_field_id = NULL

↓

4c. User MODIFIES Suggestion 1:
    - User changes target to slv_member.member_id instead
    - Insert into MAPPED_FIELDS + MAPPING_DETAILS (with modified target)
    - Insert into MAPPING_FEEDBACK:
      * feedback_action = 'MODIFIED'
      * modified_tgt_column = 'member_id'
      * user_comments = "member_id is the correct target, not ssn_number"
      * mapped_field_id = (from mapping)
```

---

## Comparison: V1 vs V2

### V1 Schema (Old)

```
semantic_table (target definitions)
   ↓
combined_fields (source + mapping + target in one table)
   - One record per SOURCE field
   - tgt_table/tgt_column = NULL if unmapped
   - tgt_table/tgt_column = populated if mapped
   - Only supports 1:1 mapping
```

### V2 Schema (New)

```
semantic_fields (target definitions)
   ↓
mapped_fields (one per TARGET)
   ↓
mapping_details (many per TARGET)
   ↓
unmapped_fields (source fields awaiting mapping)

+ mapping_feedback (audit trail)
+ transformation_library (reusable transformations)
```

**Key Improvements**:
- ✅ Supports many-to-one mapping
- ✅ Field ordering for concatenation
- ✅ Per-field transformations
- ✅ Proper normalization (no NULL-heavy combined table)
- ✅ Feedback capture for AI improvement
- ✅ Transformation standardization
- ✅ Domain classification for better AI

---

## Example Queries

### Query 1: Get all mappings for a target field

```sql
SELECT 
  mf.tgt_table,
  mf.tgt_column,
  mf.concat_strategy,
  mf.transformation_expression,
  md.src_table,
  md.src_column,
  md.field_order,
  md.transformations
FROM main.source2target.mapped_fields mf
INNER JOIN main.source2target.mapping_details md
  ON mf.mapped_field_id = md.mapped_field_id
WHERE mf.tgt_table = 'slv_member'
  AND mf.tgt_column = 'full_name'
ORDER BY md.field_order;
```

**Result**:
```
tgt_table    | tgt_column | concat_strategy | src_table | src_column  | field_order | transformations
-------------|------------|-----------------|-----------|-------------|-------------|----------------
slv_member   | full_name  | SPACE           | T_MEMBER  | FIRST_NAME  | 1           | TRIM,INITCAP
slv_member   | full_name  | SPACE           | T_MEMBER  | LAST_NAME   | 2           | TRIM,INITCAP
```

---

### Query 2: Get all unmapped fields in a domain

```sql
SELECT 
  src_table,
  src_column,
  src_data_type,
  src_comments,
  domain
FROM main.source2target.unmapped_fields
WHERE domain = 'member'
ORDER BY src_table, src_column;
```

---

### Query 3: Get feedback statistics

```sql
SELECT 
  feedback_action,
  COUNT(*) AS count,
  AVG(ai_confidence_score) AS avg_confidence,
  AVG(vector_search_score) AS avg_vector_score
FROM main.source2target.mapping_feedback
GROUP BY feedback_action
ORDER BY count DESC;
```

**Result**:
```
feedback_action | count | avg_confidence | avg_vector_score
----------------|-------|----------------|------------------
ACCEPTED        | 150   | 0.87           | 0.032
MODIFIED        | 45    | 0.72           | 0.025
REJECTED        | 30    | 0.55           | 0.018
```

---

### Query 4: Get all transformations by category

```sql
SELECT 
  category,
  transformation_code,
  transformation_name,
  transformation_expression,
  is_system
FROM main.source2target.transformation_library
WHERE category = 'TEXT'
ORDER BY transformation_name;
```

---

### Query 5: Get mappings with low confidence for review

```sql
SELECT 
  mf.tgt_table,
  mf.tgt_column,
  mf.confidence_score,
  mf.mapping_source,
  mf.mapped_ts,
  COUNT(md.mapping_detail_id) AS source_field_count
FROM main.source2target.mapped_fields mf
LEFT JOIN main.source2target.mapping_details md
  ON mf.mapped_field_id = md.mapped_field_id
WHERE mf.confidence_score < 0.7
  AND mf.mapping_status = 'ACTIVE'
GROUP BY 
  mf.mapped_field_id,
  mf.tgt_table,
  mf.tgt_column,
  mf.confidence_score,
  mf.mapping_source,
  mf.mapped_ts
ORDER BY mf.confidence_score ASC;
```

---

## Summary

The V2 schema provides:

1. **Flexibility**: Many-to-one mapping support
2. **Order**: Field ordering for concatenation
3. **Transformation**: Per-field transformation library
4. **Auditability**: Complete feedback trail
5. **Quality**: Confidence scoring at mapping and field level
6. **Domain-Aware**: Better AI recommendations
7. **Normalization**: Clean relational design
8. **Scalability**: Supports complex enterprise mapping scenarios

This architecture enables the "Smart Mapper V2" epic with multi-source, multi-table mapping capabilities!

