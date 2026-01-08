-- ============================================================================
-- Smart Mapper V4 - Add Vector Search Candidates & LLM Debug Info
-- ============================================================================
-- 
-- PURPOSE: Store vector search alternatives and LLM debug info for transparency
-- 
-- NEW COLUMNS on mapping_suggestions:
-- 1. vector_search_candidates - All VS results per pattern column (before LLM chose)
-- 2. llm_debug_info - Full prompt/response for debugging
--
-- This enables:
-- - Users can see alternative matches the LLM didn't choose
-- - Admins can debug LLM decisions
-- - Better transparency into AI mapping process
--
-- ============================================================================
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema
-- ============================================================================


-- ============================================================================
-- ADD COLUMNS to mapping_suggestions
-- ============================================================================

-- Vector search candidates: All VS results per pattern column BEFORE LLM made its choice
-- Format: {
--   "SAK_RECIP": [
--     {"unmapped_field_id": 123, "src_column_physical_name": "MEMBER_ID", "src_table_physical_name": "t_member", 
--      "src_comments": "Member identifier", "score": 0.92},
--     {"unmapped_field_id": 456, "src_column_physical_name": "RECIP_KEY", "src_table_physical_name": "t_recipient",
--      "src_comments": "Recipient key", "score": 0.87}
--   ],
--   "CDE_COUNTY": [...]
-- }
ALTER TABLE ${CATALOG_SCHEMA}.mapping_suggestions
ADD COLUMN vector_search_candidates STRING COMMENT 'JSON object: VS results per pattern column before LLM selection. Keys are pattern column names, values are arrays of candidates with scores.';


-- LLM debug info: Full prompt and response for troubleshooting
-- Format: {
--   "prompt_sent": "...",
--   "raw_response": "...", 
--   "model_endpoint": "databricks-meta-llama-3-3-70b-instruct",
--   "latency_ms": 2340,
--   "timestamp": "2025-01-08T12:34:56Z"
-- }
ALTER TABLE ${CATALOG_SCHEMA}.mapping_suggestions
ADD COLUMN llm_debug_info STRING COMMENT 'JSON object: LLM prompt sent, raw response, timing for debugging';


-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================
-- Run this after the ALTER statements to verify columns were added:
--
-- DESCRIBE ${CATALOG_SCHEMA}.mapping_suggestions;
--
-- Expected to see:
-- vector_search_candidates  STRING  JSON object: VS results per pattern column...
-- llm_debug_info            STRING  JSON object: LLM prompt sent, raw response...
-- ============================================================================

