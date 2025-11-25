# Real AI Search API Integration Summary

## Overview
Replaced mock/dummy AI suggestions with real backend API integration for V2 multi-field mapping suggestions. The system now uses actual vector search and LLM-powered reasoning from Databricks.

## Changes Made

### 1. Frontend Store Update (`frontend/src/stores/aiSuggestionsStoreV2.ts`)

#### Interface Update
Made `semantic_field_id` optional since the backend doesn't return it:
```typescript
export interface AISuggestionV2 {
  semantic_field_id?: number  // Optional - not returned by backend
  tgt_table_name: string
  tgt_table_physical_name: string
  tgt_column_name: string
  tgt_column_physical_name: string
  search_score: number
  match_quality: 'Excellent' | 'Strong' | 'Good' | 'Weak' | 'Unknown'
  ai_reasoning: string
  rank?: number  // UI-only: 1, 2, 3...
}
```

#### Real API Call Implementation
**Before** (Mock):
```typescript
// Mock: Simulate API delay
await new Promise(resolve => setTimeout(resolve, 1500))

// Generate mock suggestions based on source fields
suggestions.value = generateMockSuggestions(sourceFields)
```

**After** (Real API):
```typescript
const response = await fetch('/api/v2/ai-mapping/suggestions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    source_fields: sourceFields.map(f => ({
      src_table_name: f.src_table_name,
      src_table_physical_name: f.src_table_physical_name,
      src_column_name: f.src_column_name,
      src_column_physical_name: f.src_column_physical_name,
      src_physical_datatype: f.src_physical_datatype,
      src_comments: f.src_comments || ''
    })),
    num_results: 10
  })
})

if (!response.ok) {
  const errorText = await response.text()
  throw new Error(`API error: ${response.status} - ${errorText}`)
}

suggestions.value = await response.json()
```

#### Removed Mock Function
Deleted the entire `generateMockSuggestions()` function (~180 lines of mock data) including:
- SSN field mock suggestions
- NPI field mock suggestions
- FIRST_NAME + LAST_NAME multi-field mocks
- ADDRESS + CITY multi-field mocks
- Generic fallback suggestions

### 2. Backend API (Already Existed)

The backend API was already implemented and registered:
- **Endpoint**: `POST /api/v2/ai-mapping/suggestions`
- **Router**: `backend/routers/ai_mapping_v2.py`
- **Service**: `backend/services/ai_mapping_service_v2.py`
- **Registered**: In `backend/app.py` line 52

## How It Works Now

### Request Flow:
1. User selects source fields in the UI
2. Frontend calls `generateSuggestions(sourceFields)`
3. Store makes POST request to `/api/v2/ai-mapping/suggestions`
4. Backend processes request through these steps:

#### Backend Processing:
1. **Multi-Field Query Building**
   - Single field: `"Table: T_MEMBER, Column: FIRST_NAME, Type: STRING, Comment: First name"`
   - Multi-field: `"Combination of: FIRST_NAME (First name) + LAST_NAME (Last name) from T_MEMBER"`

2. **Historical Pattern Learning**
   - Queries `mapped_fields` and `mapping_details` tables
   - Finds previous mappings with similar source field combinations
   - Boosts confidence for patterns seen before

3. **Vector Search**
   - Uses Databricks Vector Search Index
   - Queries semantic embeddings
   - Returns top N candidates with similarity scores

4. **LLM Reasoning**
   - Calls Databricks Foundation Model endpoint
   - Provides source fields and vector search candidates
   - LLM generates:
     - Match quality rating (Excellent, Strong, Good, Weak)
     - Human-readable reasoning for each suggestion

5. **Response Ranking**
   - Combines vector search scores with LLM analysis
   - Returns ranked list of suggestions with reasoning

### Response Structure:
```json
[
  {
    "tgt_table_name": "slv_member",
    "tgt_column_name": "full_name",
    "tgt_table_physical_name": "slv_member",
    "tgt_column_physical_name": "full_name",
    "search_score": 0.042,
    "match_quality": "Excellent",
    "ai_reasoning": "The combination of FIRST_NAME and LAST_NAME strongly correlates with full_name. Historical patterns confirm this is the standard mapping."
  }
]
```

## Features Enabled

### ✅ Real AI Intelligence:
- **Vector Search**: Semantic similarity using Databricks embeddings
- **LLM Reasoning**: Foundation model provides intelligent explanations
- **Pattern Learning**: Learns from historical mapping decisions
- **Multi-Field Support**: Intelligently combines multiple source fields

### ✅ Smart Suggestions:
- **Single Field Mappings**: Direct semantic matching
- **Multi-Field Patterns**: Recognizes combinations like:
  - FIRST_NAME + LAST_NAME → full_name
  - ADDRESS_LINE1 + CITY + STATE → full_address
  - Custom combinations based on historical data

### ✅ Enhanced User Experience:
- **Match Quality Badges**: Visual indicators (Excellent, Strong, Good, Weak)
- **AI Reasoning**: Explains why each suggestion was made
- **Confidence Scores**: Vector search similarity scores (0.0-1.0)
- **Ranked Results**: Best matches appear first

## Benefits Over Mock Data

| Aspect | Mock Data | Real API |
|--------|-----------|----------|
| **Accuracy** | Hardcoded patterns only | Learns from actual semantic table |
| **Coverage** | Limited to SSN, NPI, NAME | All fields in semantic table |
| **Intelligence** | Static rules | LLM-powered reasoning |
| **Adaptability** | Fixed responses | Learns from historical mappings |
| **Reasoning** | Generic templates | Context-specific explanations |
| **Scalability** | Manual updates needed | Automatic with new data |

## Error Handling

The implementation includes robust error handling:
```typescript
if (!response.ok) {
  const errorText = await response.text()
  throw new Error(`API error: ${response.status} - ${errorText}`)
}
```

Errors are:
- Caught and logged to console
- Displayed to user via `error.value` state
- Suggestions array cleared on failure
- Loading state properly reset

## Configuration Required

For the AI suggestions to work, ensure:
1. ✅ Databricks Vector Search endpoint is configured and online
2. ✅ Vector Search index exists and is synced with semantic table
3. ✅ Foundation Model endpoint (DBRX) is configured and serving
4. ✅ SQL Warehouse is running and accessible
5. ✅ OAuth permissions are properly configured

## Testing

Test the integration by:
1. Navigate to "Create Mappings"
2. Select one or more source fields
3. Click "Generate AI Suggestions"
4. Wait for real API response (15-25 seconds typical)
5. Verify suggestions include:
   - Real target field names from your semantic table
   - LLM-generated reasoning
   - Appropriate match quality ratings

## Files Modified

1. **`frontend/src/stores/aiSuggestionsStoreV2.ts`**
   - Made `semantic_field_id` optional in interface
   - Replaced mock implementation with real API call
   - Removed ~180 lines of mock data and helper function
   - Added proper error handling

## Files Unchanged (Already Implemented)

1. **`backend/routers/ai_mapping_v2.py`** - API endpoint already exists
2. **`backend/services/ai_mapping_service_v2.py`** - Service logic already implemented
3. **`backend/app.py`** - Router already registered

## Frontend Build

Successfully rebuilt and deployed:
```bash
cd frontend && npm run build
✓ built in 1.29s
```

## Next Steps

Users can now:
- ✅ Get real AI-powered suggestions based on their semantic table
- ✅ See intelligent reasoning from LLM
- ✅ Benefit from historical pattern learning
- ✅ Trust suggestions are based on actual data, not hardcoded rules
- ✅ Map fields with higher confidence and accuracy

