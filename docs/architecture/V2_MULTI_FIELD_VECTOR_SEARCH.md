# V2 Multi-Field Vector Search & AI Suggestions

## Overview

The V2 AI mapping service supports **multiple source fields → single target field** suggestions using an intelligent combination strategy.

---

## How It Works

### Problem
When a user selects multiple source fields (e.g., `FIRST_NAME`, `LAST_NAME`, `MIDDLE_NAME`), how do we find the best target field (`full_name`)?

### Solution
**Combine multiple fields into a single semantic query** that vector search can understand.

---

## Technical Implementation

### 1. Build Combined Query (`_build_multi_field_query`)

**Single Field:**
```
"Table: T_MEMBER, Column: FIRST_NAME, Type: STRING, Comment: First name"
```

**Multiple Fields:**
```
"Combination of: FIRST_NAME (First name) + LAST_NAME (Last name) + MIDDLE_NAME (Middle initial) from T_MEMBER"
```

This query text captures:
- All source field names
- Their descriptions/comments
- The relationship (they are being combined)
- The source table

### 2. Vector Search with Combined Query

```sql
SELECT 
    tgt_table_name,
    tgt_column_name,
    search_score
FROM vector_search(
    index => 'semantic_fields_vs',
    query => 'Combination of: FIRST_NAME + LAST_NAME from T_MEMBER',
    num_results => 20
)
ORDER BY search_score DESC
```

**Why this works:**
- Vector embeddings understand semantic meaning
- "FIRST_NAME + LAST_NAME" is semantically similar to "full_name"
- The embedding model was trained on patterns like this
- Returns fields like: `full_name`, `member_name`, `complete_name`, etc.

### 3. User Feedback Learning (Parallel) ⭐ NEW

While vector search runs, query `mapping_feedback` for previous user feedback:

```sql
-- Get ACCEPTED feedback (positive examples)
SELECT 
    suggested_src_column,
    suggested_tgt_table,
    suggested_tgt_column,
    ai_confidence_score,
    user_comments
FROM mapping_feedback
WHERE feedback_action = 'ACCEPTED'
AND suggested_src_column IN ('first_name', 'last_name')
ORDER BY feedback_ts DESC
LIMIT 10

-- Get REJECTED feedback (negative examples)  
SELECT 
    suggested_src_column,
    suggested_tgt_table,
    suggested_tgt_column,
    user_comments  -- WHY it was rejected
FROM mapping_feedback
WHERE feedback_action = 'REJECTED'
AND suggested_src_column IN ('first_name', 'last_name')
ORDER BY feedback_ts DESC
LIMIT 10
```

This provides:
- **Accepted mappings**: Confirmed good matches to boost
- **Rejected mappings**: Bad matches to avoid/deprioritize
- **User reasoning**: WHY users accepted or rejected suggestions

### 4. Historical Pattern Matching (Parallel, Deduplicated)

Also query `mapped_fields` + `mapping_details` for manual mappings:

```sql
-- Find previous mappings with same source field combination
SELECT 
    mf.tgt_table_name,
    mf.tgt_column_name,
    mf.concat_strategy,
    COUNT(DISTINCT md.detail_id) as source_field_count
FROM mapped_fields mf
JOIN mapping_details md ON mf.mapping_id = md.mapping_id
WHERE (md.src_column_physical_name = 'first_name')
   OR (md.src_column_physical_name = 'last_name')
GROUP BY ...
HAVING COUNT(DISTINCT md.detail_id) >= 2  -- Must have all source fields
```

**Important**: Historical patterns are **deduplicated** - any patterns already in accepted feedback are removed to avoid sending duplicate info to the LLM.

This finds (only for manual mappings without feedback):
- **Exact matches**: Has this exact combination been mapped before?
- **Pattern learning**: Common patterns like name fields → full_name
- **Concat strategy**: How were they concatenated (SPACE, COMMA, etc.)

### 5. LLM Reasoning (Foundation Model)

Pass to Databricks Foundation Model:
- **Source fields**: List of fields being combined
- **User feedback**: Accepted + rejected mappings with user reasoning ⭐ NEW
- **Historical patterns**: Manual mappings without feedback (deduplicated)
- **Vector results**: Top 5 candidates with scores

**LLM Prompt:**
```
You are a data mapping expert. Analyze these source fields and suggest the best target field mapping.

Source Fields (3):
- FIRST_NAME: First name (STRING)
- LAST_NAME: Last name (STRING)
- MIDDLE_NAME: Middle initial (STRING)

Task: These source fields will be combined to map to a single target field.

User Feedback History (IMPORTANT - learn from this):

PREVIOUSLY ACCEPTED mappings (these are GOOD matches):
  ✓ FIRST_NAME → TGT_MEMBER.full_name - User reason: Perfect match for name concatenation

PREVIOUSLY REJECTED mappings (AVOID these - users said they are wrong):
  ✗ FIRST_NAME → TGT_MEMBER.member_id - User reason: IDs should not contain names

Other Historical Mappings (manual mappings without explicit feedback):
- Previously mapped to: TGT_MEMBER.member_name (Concat: SPACE)

Vector Search Results:
1. TGT_MEMBER.full_name (Score: 0.0452)
2. TGT_MEMBER.member_name (Score: 0.0321)
3. TGT_PERSON.complete_name (Score: 0.0287)

IMPORTANT: 
- If a mapping was PREVIOUSLY ACCEPTED, this is strong evidence it's a good match
- If a mapping was PREVIOUSLY REJECTED, avoid recommending it
- User feedback should heavily influence your reasoning

For each, provide:
1. Match Quality: "Excellent", "Strong", "Good", or "Weak"
2. Reasoning: Why this is a good or poor match. Reference user feedback if applicable.
```

**LLM Response:**
```json
{
  "suggestions": [
    {
      "tgt_table_name": "TGT_MEMBER",
      "tgt_column_name": "full_name",
      "match_quality": "Excellent",
      "reasoning": "Combining first, last, and middle name logically maps to full_name field. User feedback confirms this is the preferred mapping for name fields."
    },
    {
      "tgt_table_name": "TGT_MEMBER",
      "tgt_column_name": "member_name",
      "match_quality": "Strong",
      "reasoning": "Good alternative to full_name. Historical patterns show this has been used successfully for similar combinations."
    }
  ]
}
```

### 6. Merge and Return

Combine:
- Vector scores (numerical similarity)
- LLM reasoning (semantic understanding)
- User feedback (quality signal - accepted/rejected)
- Historical patterns (organizational knowledge for manual mappings)

Return ranked list with all context.

---

## Example Use Cases

### Case 1: Name Fields
**Input:**
- `FIRST_NAME`
- `LAST_NAME`

**Combined Query:**
```
"Combination of: FIRST_NAME (First name) + LAST_NAME (Last name) from T_MEMBER"
```

**Vector Search Finds:**
- `full_name` (0.048)
- `member_name` (0.035)
- `name` (0.029)

**LLM Adds:**
- Excellent match for `full_name`
- Reasoning: "Standard pattern for combining name components"

---

### Case 2: Address Fields
**Input:**
- `ADDRESS_LINE1`
- `CITY`
- `STATE`
- `ZIP_CODE`

**Combined Query:**
```
"Combination of: ADDRESS_LINE1 (Street address) + CITY (City name) + STATE (State code) + ZIP_CODE (Postal code) from T_ADDRESS"
```

**Vector Search Finds:**
- `full_address` (0.052)
- `mailing_address` (0.041)
- `address_text` (0.033)

**LLM Adds:**
- Excellent match for `full_address`
- Reasoning: "Standard address components map to full_address field for complete mailing addresses"

---

### Case 3: Date/Time Fields
**Input:**
- `EVENT_DATE`
- `EVENT_TIME`

**Combined Query:**
```
"Combination of: EVENT_DATE (Date of event) + EVENT_TIME (Time of event) from T_EVENTS"
```

**Vector Search Finds:**
- `event_timestamp` (0.046)
- `event_datetime` (0.044)
- `occurrence_ts` (0.028)

**LLM Adds:**
- Excellent match for `event_timestamp` or `event_datetime`
- Reasoning: "Combining separate date and time fields logically maps to timestamp field"

---

## Advantages of This Approach

### ✅ Single Query
- Only ONE vector search call (not N calls for N fields)
- Faster performance
- Lower cost

### ✅ Semantic Understanding
- Vector embeddings "understand" field combinations
- Trained on millions of examples
- Recognizes patterns like:
  - first_name + last_name → full_name
  - street + city + state → full_address
  - date + time → timestamp

### ✅ User Feedback Learning ⭐ NEW
- Learns from ACCEPTED suggestions (positive examples)
- Avoids REJECTED suggestions (negative examples)
- Uses user comments to understand WHY matches are good/bad
- Creates a feedback loop for continuous improvement

### ✅ Historical Learning
- Learns from organization's previous mappings
- Recognizes company-specific patterns
- Captures manual mappings (without feedback)
- Deduplicated to avoid overlap with feedback

### ✅ Intelligent Reasoning
- LLM provides human-readable explanations
- References user feedback in reasoning
- Helps users understand WHY a match is suggested
- Can identify potential issues

### ✅ Confidence Scoring
- Combines multiple signals:
  - Vector similarity score
  - User feedback (accepted/rejected)
  - Historical pattern matches
  - LLM assessment
- More accurate than vector alone

---

## API Endpoints

### Generate Multi-Field Suggestions

**Endpoint:** `POST /api/v2/ai-mapping/multi-field-suggestions`

**Request:**
```json
{
  "source_fields": [
    {
      "src_table_name": "T_MEMBER",
      "src_table_physical_name": "t_member",
      "src_column_name": "FIRST_NAME",
      "src_column_physical_name": "first_name",
      "src_physical_datatype": "STRING",
      "src_comments": "Member first name"
    },
    {
      "src_table_name": "T_MEMBER",
      "src_table_physical_name": "t_member",
      "src_column_name": "LAST_NAME",
      "src_column_physical_name": "last_name",
      "src_physical_datatype": "STRING",
      "src_comments": "Member last name"
    }
  ],
  "num_results": 10
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "tgt_table_name": "TGT_MEMBER",
      "tgt_column_name": "full_name",
      "tgt_table_physical_name": "tgt_member",
      "tgt_column_physical_name": "full_name",
      "search_score": 0.0452,
      "match_quality": "Excellent",
      "ai_reasoning": "Combining first and last name components logically maps to full_name field...",
      "rank": 1
    },
    ...
  ]
}
```

---

## Frontend Integration

### Store (aiSuggestionsStoreV2.ts)

```typescript
async function generateSuggestions(sourceFields: UnmappedField[]) {
  loading.value = true
  
  const response = await fetch('/api/v2/ai-mapping/multi-field-suggestions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_fields: sourceFields,
      num_results: 25
    })
  })
  
  const data = await response.json()
  suggestions.value = data.suggestions
}
```

### UI Flow

1. User selects 2+ source fields in `UnmappedFieldsView`
2. Clicks "Get AI Suggestions"
3. `AISuggestionsDialog` shows:
   - Source fields summary (e.g., "3 Fields Combined")
   - Loading spinner with "Analyzing fields..."
   - Results table with:
     - Rank
     - Target field
     - Match Quality badge
     - Vector score bar
     - AI Reasoning
     - Accept/Reject buttons

---

## Performance Considerations

### Query Time
- **Vector Search**: ~100-500ms (single query, regardless of field count)
- **Historical Patterns**: ~50-200ms (parallel with vector search)
- **LLM Reasoning**: ~1-3 seconds (Databricks Foundation Model)
- **Total**: ~2-4 seconds for complete results

### Scalability
- ✅ Scales to any number of source fields (1-10+)
- ✅ Single vector search query (no N+1 problem)
- ✅ Parallel execution (historical + vector search)
- ✅ Cached vector index (fast lookups)

---

## Configuration

### Required Settings (app_config.json)

```json
{
  "vector_search": {
    "index_name": "oztest_dev.source2target.semantic_fields_vs",
    "endpoint_name": "s2t_vsendpoint"
  },
  "ai_model": {
    "foundation_model_endpoint": "databricks-meta-llama-3-3-70b-instruct",
    "previous_mappings_table_name": "oztest_dev.source2target.mapped_fields"
  },
  "database": {
    "semantic_fields_table": "oztest_dev.source2target.semantic_fields",
    "mapped_fields_table": "oztest_dev.source2target.mapped_fields",
    "mapping_details_table": "oztest_dev.source2target.mapping_details",
    "mapping_feedback_table": "oztest_dev.source2target.mapping_feedback"
  }
}
```

### Feedback Table (mapping_feedback)

The feedback table stores user responses to AI suggestions:

| Column | Description |
|--------|-------------|
| `feedback_action` | ACCEPTED, REJECTED, or MODIFIED |
| `suggested_src_table` | Source table in suggestion |
| `suggested_src_column` | Source column in suggestion |
| `suggested_tgt_table` | Target table in suggestion |
| `suggested_tgt_column` | Target column in suggestion |
| `user_comments` | Why user accepted/rejected |
| `ai_confidence_score` | Original AI confidence |
| `feedback_by` | User who provided feedback |
| `feedback_ts` | Timestamp |

---

## Testing

### Test Multi-Field Suggestions

```python
# Example: Test name fields
source_fields = [
    {
        "src_table_name": "T_MEMBER",
        "src_table_physical_name": "t_member",
        "src_column_name": "FIRST_NAME",
        "src_column_physical_name": "first_name",
        "src_physical_datatype": "STRING",
        "src_comments": "Member first name"
    },
    {
        "src_table_name": "T_MEMBER",
        "src_table_physical_name": "t_member",
        "src_column_name": "LAST_NAME",
        "src_column_physical_name": "last_name",
        "src_physical_datatype": "STRING",
        "src_comments": "Member last name"
    }
]

service = AIMappingServiceV2()
results = await service.generate_multi_field_suggestions(source_fields, num_results=10)

# Should return suggestions like:
# [
#   {"tgt_column_name": "full_name", "match_quality": "Excellent", ...},
#   {"tgt_column_name": "member_name", "match_quality": "Strong", ...},
#   ...
# ]
```

---

## Summary

The V2 multi-field vector search is fully implemented with feedback learning! Key points:

1. **Single Query**: Combines all source fields into one semantic query
2. **Feedback Learning**: Uses accepted/rejected suggestions to improve over time
3. **Intelligent**: Uses vector search + feedback + historical patterns + LLM reasoning
4. **Fast**: Parallel execution, ~2-4 seconds total
5. **Scalable**: Works for 1-10+ fields without performance degradation
6. **Smart**: Creates a feedback loop - more usage = better suggestions

### Feedback Loop

```
User selects fields → AI suggests → User accepts/rejects → Feedback saved
                                           ↓
Next search ← AI learns from feedback ← Feedback queried
```

The system gets smarter with every user interaction!

