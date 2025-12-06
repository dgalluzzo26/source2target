-- ============================================================================
-- LLM Prompt Testing for Smart Mapper AI Suggestions
-- ============================================================================
-- 
-- 4 Test Scenarios:
-- 1. Single mapping - semantic search only (no history)
-- 2. Single mapping - semantic search + historical patterns
-- 3. Multi-field mapping - semantic search + historical patterns
-- 4. Multi-field mapping - semantic search + patterns + rejections
--
-- Run these in Databricks to test LLM responses with different models
-- ============================================================================


-- ============================================================================
-- SCENARIO 1: Single Source Field - Semantic Search Only (No History)
-- ============================================================================
-- Use case: First time mapping a field, no prior patterns exist
-- Source: member_ssn from source table
-- Expected: AI suggests SSN-related target fields
-- ============================================================================

SELECT ai_query(
  'databricks-meta-llama-3-3-70b-instruct',
  CONCAT(
    'You are an expert data mapping assistant. Your task is to recommend the best target field mapping for the given source field(s).\n\n',
    
    '## SOURCE FIELDS TO MAP\n',
    'The user wants to map the following source field(s) to a target field:\n\n',
    '| # | Table | Column | Data Type | Description |\n',
    '|---|-------|--------|-----------|-------------|\n',
    '| 1 | member_info | member_ssn | STRING | Social security number of the member |\n\n',
    
    '## VECTOR SEARCH RESULTS (Target Field Candidates)\n',
    'Based on semantic similarity, these target fields are potential matches:\n\n',
    '| Rank | Target Table | Target Column | Data Type | Description | Similarity Score |\n',
    '|------|--------------|---------------|-----------|-------------|------------------|\n',
    '| 1 | Member | SSN | STRING | Member social security number | 0.92 |\n',
    '| 2 | Member | Tax_ID | STRING | Tax identification number | 0.78 |\n',
    '| 3 | Member | Member_ID | STRING | Unique member identifier | 0.65 |\n',
    '| 4 | Provider | Provider_SSN | STRING | Provider social security number | 0.61 |\n\n',
    
    '## HISTORICAL MAPPING PATTERNS\n',
    'No similar mappings found in history.\n\n',
    
    '## REJECTION HISTORY\n',
    'No relevant rejections found.\n\n',
    
    '## YOUR TASK\n',
    'Based on the above information, recommend the best target field mapping.\n\n',
    
    'Provide your response in this exact JSON format:\n',
    '```json\n',
    '{\n',
    '  "recommended_target": {\n',
    '    "table": "target table name",\n',
    '    "column": "target column name",\n',
    '    "confidence": 0.0 to 1.0\n',
    '  },\n',
    '  "transformations": ["list of recommended transformations like TRIM, UPPER, etc."],\n',
    '  "reasoning": "Brief explanation of why this mapping is recommended",\n',
    '  "alternative_targets": [\n',
    '    {"table": "...", "column": "...", "confidence": 0.0, "reason": "..."}\n',
    '  ]\n',
    '}\n',
    '```'
  )
) AS scenario_1_response;


-- ============================================================================
-- SCENARIO 2: Single Source Field - Semantic Search + Historical Patterns
-- ============================================================================
-- Use case: Mapping a field where similar mappings exist in history
-- Source: first_name from patient table
-- Expected: AI uses historical patterns to suggest TRIM+UPPER transformations
-- ============================================================================

SELECT ai_query(
  'databricks-meta-llama-3-3-70b-instruct',
  CONCAT(
    'You are an expert data mapping assistant. Your task is to recommend the best target field mapping for the given source field(s).\n\n',
    
    '## SOURCE FIELDS TO MAP\n',
    'The user wants to map the following source field(s) to a target field:\n\n',
    '| # | Table | Column | Data Type | Description |\n',
    '|---|-------|--------|-----------|-------------|\n',
    '| 1 | patient_data | first_name | VARCHAR(50) | Patient first name |\n\n',
    
    '## VECTOR SEARCH RESULTS (Target Field Candidates)\n',
    'Based on semantic similarity, these target fields are potential matches:\n\n',
    '| Rank | Target Table | Target Column | Data Type | Description | Similarity Score |\n',
    '|------|--------------|---------------|-----------|-------------|------------------|\n',
    '| 1 | Member | First_Name | STRING | Member legal first name | 0.94 |\n',
    '| 2 | Member | Full_Name | STRING | Complete member name | 0.72 |\n',
    '| 3 | Member | Display_Name | STRING | Name for display purposes | 0.68 |\n',
    '| 4 | Provider | First_Name | STRING | Provider first name | 0.65 |\n\n',
    
    '## HISTORICAL MAPPING PATTERNS\n',
    'Similar mappings that were successful in the past:\n\n',
    '| Source Table | Source Column | Target Column | Transformations | Times Used |\n',
    '|--------------|---------------|---------------|-----------------|------------|\n',
    '| member_info | fname | First_Name | TRIM, UPPER | 12 |\n',
    '| enrollment | first_nm | First_Name | TRIM, UPPER | 8 |\n',
    '| subscriber | subscriber_first | First_Name | TRIM, INITCAP | 5 |\n\n',
    
    '## REJECTION HISTORY\n',
    'No relevant rejections found.\n\n',
    
    '## YOUR TASK\n',
    'Based on the above information, recommend the best target field mapping.\n',
    'Pay special attention to the historical patterns - they show what transformations worked well.\n\n',
    
    'Provide your response in this exact JSON format:\n',
    '```json\n',
    '{\n',
    '  "recommended_target": {\n',
    '    "table": "target table name",\n',
    '    "column": "target column name",\n',
    '    "confidence": 0.0 to 1.0\n',
    '  },\n',
    '  "transformations": ["list of recommended transformations like TRIM, UPPER, etc."],\n',
    '  "reasoning": "Brief explanation of why this mapping is recommended",\n',
    '  "historical_influence": "How historical patterns influenced this recommendation",\n',
    '  "alternative_targets": [\n',
    '    {"table": "...", "column": "...", "confidence": 0.0, "reason": "..."}\n',
    '  ]\n',
    '}\n',
    '```'
  )
) AS scenario_2_response;


-- ============================================================================
-- SCENARIO 3: Multi-Field Mapping - Semantic Search + Historical Patterns
-- ============================================================================
-- Use case: User selected 2 source fields that should combine into one target
-- Source: first_name + last_name from member table
-- Expected: AI suggests combining into Full_Name with SPACE concatenation
-- ============================================================================

SELECT ai_query(
  'databricks-meta-llama-3-3-70b-instruct',
  CONCAT(
    'You are an expert data mapping assistant. Your task is to recommend the best target field mapping for the given source field(s).\n\n',
    
    '## SOURCE FIELDS TO MAP\n',
    'The user wants to map the following source field(s) to a target field:\n',
    '**Note: Multiple source fields may need to be COMBINED into a single target field.**\n\n',
    '| # | Table | Column | Data Type | Description |\n',
    '|---|-------|--------|-----------|-------------|\n',
    '| 1 | member_info | first_name | VARCHAR(50) | Member legal first name |\n',
    '| 2 | member_info | last_name | VARCHAR(50) | Member legal last name |\n\n',
    
    '## VECTOR SEARCH RESULTS (Target Field Candidates)\n',
    'Based on semantic similarity, these target fields are potential matches:\n\n',
    '| Rank | Target Table | Target Column | Data Type | Description | Similarity Score |\n',
    '|------|--------------|---------------|-----------|-------------|------------------|\n',
    '| 1 | Member | Full_Name | STRING | Complete member name (first + last) | 0.89 |\n',
    '| 2 | Member | Display_Name | STRING | Name for display purposes | 0.82 |\n',
    '| 3 | Member | First_Name | STRING | Member legal first name | 0.76 |\n',
    '| 4 | Member | Last_Name | STRING | Member legal last name | 0.75 |\n',
    '| 5 | Member | Member_Name | STRING | Member name field | 0.71 |\n\n',
    
    '## HISTORICAL MAPPING PATTERNS\n',
    'Similar multi-field mappings that were successful in the past:\n\n',
    '| Source Fields | Target Column | Concat Strategy | Transformations | Expression | Times Used |\n',
    '|---------------|---------------|-----------------|-----------------|------------|------------|\n',
    '| fname, lname | Full_Name | SPACE | TRIM, UPPER | CONCAT(TRIM(UPPER(fname)), '' '', TRIM(UPPER(lname))) | 15 |\n',
    '| first_nm, last_nm | Full_Name | SPACE | TRIM, INITCAP | CONCAT(TRIM(INITCAP(first_nm)), '' '', TRIM(INITCAP(last_nm))) | 9 |\n',
    '| given_name, surname | Display_Name | COMMA | TRIM | CONCAT(TRIM(surname), '', '', TRIM(given_name)) | 4 |\n\n',
    
    '## REJECTION HISTORY\n',
    'No relevant rejections found.\n\n',
    
    '## YOUR TASK\n',
    'Based on the above information, recommend the best target field mapping.\n',
    'Since multiple source fields are provided, determine if they should be:\n',
    '- Combined into a single target field (specify concatenation strategy)\n',
    '- Mapped to separate target fields\n\n',
    
    'Provide your response in this exact JSON format:\n',
    '```json\n',
    '{\n',
    '  "recommended_target": {\n',
    '    "table": "target table name",\n',
    '    "column": "target column name",\n',
    '    "confidence": 0.0 to 1.0\n',
    '  },\n',
    '  "is_multi_field_combination": true/false,\n',
    '  "concatenation_strategy": "SPACE/COMMA/PIPE/CUSTOM/NONE",\n',
    '  "custom_separator": "only if CUSTOM strategy",\n',
    '  "field_order": ["first field", "second field"],\n',
    '  "transformations_per_field": {\n',
    '    "first_name": ["TRIM", "UPPER"],\n',
    '    "last_name": ["TRIM", "UPPER"]\n',
    '  },\n',
    '  "final_expression": "SQL expression showing the full transformation",\n',
    '  "reasoning": "Brief explanation of why this mapping and combination is recommended",\n',
    '  "historical_influence": "How historical patterns influenced this recommendation",\n',
    '  "alternative_approaches": [\n',
    '    {"approach": "description", "pros": "...", "cons": "..."}\n',
    '  ]\n',
    '}\n',
    '```'
  )
) AS scenario_3_response;


-- ============================================================================
-- SCENARIO 4: Multi-Field Mapping - Semantic + Patterns + REJECTIONS
-- ============================================================================
-- Use case: User selected fields, but some combinations were rejected before
-- Source: street_addr + city + state from address table
-- Expected: AI avoids the rejected Full_Address combination, suggests separately
-- ============================================================================

SELECT ai_query(
  'databricks-meta-llama-3-3-70b-instruct',
  CONCAT(
    'You are an expert data mapping assistant. Your task is to recommend the best target field mapping for the given source field(s).\n\n',
    
    '## SOURCE FIELDS TO MAP\n',
    'The user wants to map the following source field(s) to a target field:\n',
    '**Note: Multiple source fields may need to be COMBINED into a single target field.**\n\n',
    '| # | Table | Column | Data Type | Description |\n',
    '|---|-------|--------|-----------|-------------|\n',
    '| 1 | address_info | street_addr | VARCHAR(100) | Street address line 1 |\n',
    '| 2 | address_info | city | VARCHAR(50) | City name |\n',
    '| 3 | address_info | state_code | VARCHAR(2) | Two-letter state code |\n\n',
    
    '## VECTOR SEARCH RESULTS (Target Field Candidates)\n',
    'Based on semantic similarity, these target fields are potential matches:\n\n',
    '| Rank | Target Table | Target Column | Data Type | Description | Similarity Score |\n',
    '|------|--------------|---------------|-----------|-------------|------------------|\n',
    '| 1 | Member_Address | Full_Address | STRING | Complete formatted address | 0.88 |\n',
    '| 2 | Member_Address | Street_Line_1 | STRING | Primary street address | 0.85 |\n',
    '| 3 | Member_Address | City | STRING | City name | 0.84 |\n',
    '| 4 | Member_Address | State | STRING | State code | 0.83 |\n',
    '| 5 | Member_Address | Address_Text | STRING | Concatenated address for display | 0.79 |\n\n',
    
    '## HISTORICAL MAPPING PATTERNS\n',
    'Similar mappings that were successful in the past:\n\n',
    '| Source Fields | Target Column | Concat Strategy | Transformations | Expression | Times Used |\n',
    '|---------------|---------------|-----------------|-----------------|------------|------------|\n',
    '| addr1 | Street_Line_1 | NONE | TRIM, UPPER | TRIM(UPPER(addr1)) | 18 |\n',
    '| city_name | City | NONE | TRIM, INITCAP | TRIM(INITCAP(city_name)) | 15 |\n',
    '| st_cd | State | NONE | TRIM, UPPER | TRIM(UPPER(st_cd)) | 15 |\n',
    '| addr1, city, state | Full_Address | COMMA_SPACE | TRIM | CONCAT(TRIM(addr1), '', '', TRIM(city), '', '', TRIM(state)) | 3 |\n\n',
    
    '## REJECTION HISTORY\n',
    '**IMPORTANT: These mappings were REJECTED by users. AVOID suggesting similar combinations.**\n\n',
    '| Source Fields | Suggested Target | Rejection Reason | Rejected By | Date |\n',
    '|---------------|------------------|------------------|-------------|------|\n',
    '| street, city, state | Full_Address | "Full_Address field has specific formatting requirements that don''t match our source format. Map to individual fields instead." | john.smith@company.com | 2024-01-15 |\n',
    '| address_line, city_nm, st | Full_Address | "We need separate fields for reporting, not combined address" | mary.jones@company.com | 2024-02-20 |\n',
    '| addr_1, addr_city, addr_st | Address_Text | "Address_Text is auto-generated, should not be directly mapped" | admin@company.com | 2024-03-10 |\n\n',
    
    '## YOUR TASK\n',
    'Based on the above information, recommend the best target field mapping.\n\n',
    '**CRITICAL: Pay close attention to the REJECTION HISTORY.**\n',
    'Users have explicitly rejected certain mapping approaches. Learn from their feedback:\n',
    '- Avoid combinations that were rejected\n',
    '- Consider the rejection reasons when making recommendations\n',
    '- If a similar approach was rejected, suggest an alternative\n\n',
    
    'Provide your response in this exact JSON format:\n',
    '```json\n',
    '{\n',
    '  "recommended_approach": "COMBINE_TO_SINGLE / MAP_SEPARATELY",\n',
    '  "mappings": [\n',
    '    {\n',
    '      "source_fields": ["field1", "field2"],\n',
    '      "target_table": "...",\n',
    '      "target_column": "...",\n',
    '      "transformations": ["TRIM", "UPPER"],\n',
    '      "expression": "SQL expression",\n',
    '      "confidence": 0.0 to 1.0\n',
    '    }\n',
    '  ],\n',
    '  "reasoning": "Brief explanation of why this mapping approach is recommended",\n',
    '  "rejection_considerations": "How rejection history influenced this recommendation",\n',
    '  "why_not_combined": "If not combining, explain why based on rejections",\n',
    '  "warnings": ["Any warnings about potential issues"]\n',
    '}\n',
    '```'
  )
) AS scenario_4_response;


-- ============================================================================
-- RUN ALL SCENARIOS AT ONCE (Combined View)
-- ============================================================================

SELECT 
  'Scenario 1: Single field, semantic only' AS scenario,
  ai_query(
    'databricks-meta-llama-3-3-70b-instruct',
    'You are a data mapping assistant. Map source field: member_info.member_ssn (STRING, "Social security number") to best target from: [Member.SSN (0.92), Member.Tax_ID (0.78), Member.Member_ID (0.65)]. No historical patterns. Respond with JSON: {"target": "table.column", "confidence": 0.0-1.0, "transformations": [], "reasoning": "..."}'
  ) AS response

UNION ALL

SELECT 
  'Scenario 2: Single field, semantic + history' AS scenario,
  ai_query(
    'databricks-meta-llama-3-3-70b-instruct',
    'You are a data mapping assistant. Map source field: patient_data.first_name (VARCHAR, "Patient first name") to best target from: [Member.First_Name (0.94), Member.Full_Name (0.72)]. Historical patterns show fname→First_Name used TRIM,UPPER 12 times. Respond with JSON: {"target": "table.column", "confidence": 0.0-1.0, "transformations": [], "reasoning": "..."}'
  ) AS response

UNION ALL

SELECT 
  'Scenario 3: Multi-field combination' AS scenario,
  ai_query(
    'databricks-meta-llama-3-3-70b-instruct',
    'You are a data mapping assistant. Map 2 source fields: member_info.first_name + member_info.last_name to best target from: [Member.Full_Name (0.89), Member.First_Name (0.76), Member.Last_Name (0.75)]. History shows fname+lname→Full_Name with SPACE concat and TRIM,UPPER used 15 times. Respond with JSON: {"target": "table.column", "combine": true, "concat_strategy": "SPACE", "transformations": {"first_name": [], "last_name": []}, "expression": "SQL", "reasoning": "..."}'
  ) AS response

UNION ALL

SELECT 
  'Scenario 4: Multi-field with rejections' AS scenario,
  ai_query(
    'databricks-meta-llama-3-3-70b-instruct',
    'You are a data mapping assistant. Map 3 source fields: address_info.street_addr + city + state_code. Targets: [Full_Address (0.88), Street_Line_1 (0.85), City (0.84), State (0.83)]. CRITICAL - REJECTED mappings to avoid: street+city+state→Full_Address was rejected ("Need separate fields for reporting"). Recommend approach avoiding rejected patterns. Respond with JSON: {"approach": "COMBINE/SEPARATE", "mappings": [{"source": [], "target": "...", "transforms": []}], "rejection_influence": "..."}'
  ) AS response;


-- ============================================================================
-- BONUS: Test with Different Models
-- ============================================================================
-- Uncomment and modify the model name to test with different LLMs

/*
-- Test with Claude
SELECT ai_query(
  'databricks-claude-3-5-sonnet',
  '... your prompt here ...'
) AS claude_response;

-- Test with GPT-4
SELECT ai_query(
  'databricks-gpt-4o',
  '... your prompt here ...'
) AS gpt4_response;

-- Test with Mixtral
SELECT ai_query(
  'databricks-mixtral-8x7b-instruct',
  '... your prompt here ...'
) AS mixtral_response;
*/


