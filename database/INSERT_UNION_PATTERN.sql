-- ============================================================================
-- INSERT UNION PATTERN: Medicare Part A/B/D → MEMBER FOUNDATION.SRC_KEY_ID
-- ============================================================================
-- This creates a historical mapping pattern that demonstrates UNION of 3 sources
-- When a user selects any Medicare Part A/B/D field, the AI should suggest this pattern
-- ============================================================================

-- NOTE: Replace ${CATALOG_SCHEMA} with your actual catalog.schema (e.g., oz_dev.silver_dmes_de)

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, 
  source_tables, source_tables_physical, 
  source_columns, source_columns_physical, 
  source_descriptions, source_datatypes, source_domain,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  111,  -- semantic_field_id for MEMBER FOUNDATION.SRC_KEY_ID
  'MEMBER FOUNDATION', 'MBR_FNDTN',
  'Source Key Id', 'SRC_KEY_ID', 
  'SRC_KEY_ID is a field that represents the recipient identifier or key within a state assistance or Medicaid program.',
  
  -- FULL UNION SQL EXPRESSION
  'SELECT TRIM(parta_recip_id) AS SRC_KEY_ID FROM mc_part_a
UNION ALL
SELECT TRIM(partb_bene_id) AS SRC_KEY_ID FROM mc_part_b
UNION ALL
SELECT TRIM(partd_mbr_id) AS SRC_KEY_ID FROM mc_part_d',
  
  -- Source tables (pipe-separated)
  'Medicare Part A | Medicare Part B | Medicare Part D', 
  'mc_part_a | mc_part_b | mc_part_d',
  
  -- Source columns (pipe-separated)
  'Part A Recipient ID | Part B Beneficiary ID | Part D Member ID',
  'parta_recip_id | partb_bene_id | partd_mbr_id',
  
  -- Source descriptions (pipe-separated)
  'Member identifier from Medicare Part A eligibility records | Member identifier from Medicare Part B eligibility file | Member identifier from Medicare Part D pharmacy benefits',
  
  -- Source datatypes
  'VARCHAR(50) | VARCHAR(50) | VARCHAR(50)',
  
  -- Domain
  'Member',
  
  -- Relationship type - THIS IS THE KEY: UNION
  'UNION',
  
  -- Transformations
  'TRIM, UNION',
  
  -- Confidence and metadata
  0.95, 
  'MANUAL', 
  'UNION pattern combining Medicare Part A, B, and D member identifiers into a single SRC_KEY_ID. TRIM applied to standardize values.', 
  false, 
  'ACTIVE',
  'test_mapper@gainwell.com', 
  CURRENT_TIMESTAMP()
);

-- ============================================================================
-- VERIFY THE INSERT
-- ============================================================================
-- After running the insert, verify it was added:
-- SELECT * FROM ${CATALOG_SCHEMA}.mapped_fields 
-- WHERE source_relationship_type = 'UNION' 
-- ORDER BY mapped_ts DESC LIMIT 5;

-- ============================================================================
-- SYNC VECTOR SEARCH INDEX (Required for AI to find this pattern)
-- ============================================================================
-- After inserting, sync the vector search index:
-- ALTER INDEX ${CATALOG_SCHEMA}.mapped_fields_source_idx SYNC;

