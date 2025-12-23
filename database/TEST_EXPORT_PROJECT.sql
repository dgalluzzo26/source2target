-- ============================================================================
-- TEST PROJECT WITH COMPLETED MAPPINGS FOR EXPORT TESTING
-- ============================================================================
-- 
-- This script creates a small test project with completed mappings
-- to test the export functionality.
--
-- Replace ${CATALOG_SCHEMA} with your catalog.schema (e.g., oz_dev.silver_dmes_de)
-- ============================================================================


-- ============================================================================
-- STEP 1: Create Test Project
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.mapping_projects (
  project_name,
  project_description,
  source_system_name,
  target_domains,
  project_status,
  total_target_tables,
  tables_complete,
  total_target_columns,
  columns_mapped,
  created_by,
  created_ts
) VALUES (
  'Export Test Project',
  'Small test project with completed mappings for testing export functionality',
  'TEST_SOURCE',
  'Member',
  'COMPLETE',
  1,
  1,
  5,
  5,
  'test@example.com',
  CURRENT_TIMESTAMP()
);

-- Get the project ID (use this in subsequent queries)
-- You may need to query: SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects;


-- ============================================================================
-- STEP 2: Add Test Source Fields (Unmapped Fields)
-- ============================================================================

-- Note: Replace PROJECT_ID with the actual project_id from step 1

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  project_id,
  src_table_name, src_table_physical_name,
  src_column_name, src_column_physical_name,
  src_physical_datatype, src_nullable, src_comments, domain,
  mapping_status, source_semantic_field
) VALUES
-- Test Person Table
(PROJECT_ID, 'Test Person', 'TEST_PERSON', 'Person ID', 'PERSON_ID', 'BIGINT', 'NO', 'Unique identifier for the person', 'Member', 'MAPPED', 'PROJECT: PROJECT_ID | DESCRIPTION: Unique identifier for the person | TYPE: BIGINT | DOMAIN: Member'),
(PROJECT_ID, 'Test Person', 'TEST_PERSON', 'First Name', 'FIRST_NAME', 'STRING', 'YES', 'First name of the person', 'Member', 'MAPPED', 'PROJECT: PROJECT_ID | DESCRIPTION: First name of the person | TYPE: STRING | DOMAIN: Member'),
(PROJECT_ID, 'Test Person', 'TEST_PERSON', 'Last Name', 'LAST_NAME', 'STRING', 'YES', 'Last name of the person', 'Member', 'MAPPED', 'PROJECT: PROJECT_ID | DESCRIPTION: Last name of the person | TYPE: STRING | DOMAIN: Member'),
(PROJECT_ID, 'Test Person', 'TEST_PERSON', 'Birth Date', 'BIRTH_DT', 'DATE', 'YES', 'Date of birth', 'Member', 'MAPPED', 'PROJECT: PROJECT_ID | DESCRIPTION: Date of birth | TYPE: DATE | DOMAIN: Member'),
(PROJECT_ID, 'Test Person', 'TEST_PERSON', 'SSN', 'SSN_NUM', 'STRING', 'YES', 'Social security number (masked)', 'Member', 'MAPPED', 'PROJECT: PROJECT_ID | DESCRIPTION: Social security number (masked) | TYPE: STRING | DOMAIN: Member');


-- ============================================================================
-- STEP 3: Add Target Table Status
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.target_table_status (
  project_id,
  tgt_table_name, tgt_table_physical_name,
  tgt_table_description,
  mapping_status,
  total_columns,
  columns_mapped,
  columns_with_pattern,
  avg_confidence,
  completed_by, completed_ts
) VALUES (
  PROJECT_ID,
  'Member Foundation', 'MBR_FNDTN',
  'Core member demographic information',
  'COMPLETE',
  5,
  5,
  5,
  0.92,
  'test@example.com', CURRENT_TIMESTAMP()
);


-- ============================================================================
-- STEP 4: Get Semantic Field IDs (run this to find IDs)
-- ============================================================================

-- SELECT semantic_field_id, tgt_table_physical_name, tgt_column_physical_name
-- FROM ${CATALOG_SCHEMA}.semantic_fields
-- WHERE tgt_table_physical_name = 'MBR_FNDTN'
-- LIMIT 10;


-- ============================================================================
-- STEP 5: Add Completed Mappings (mapped_fields)
-- ============================================================================

-- Note: Replace SEMANTIC_FIELD_ID with actual IDs from semantic_fields
-- and PROJECT_ID with the project ID from step 1

-- Example mappings (adjust semantic_field_id values):

-- Mapping 1: Member Key
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id,
  tgt_table_name, tgt_table_physical_name,
  tgt_column_name, tgt_column_physical_name,
  source_expression,
  source_tables, source_tables_physical,
  source_columns, source_columns_physical,
  source_descriptions,
  source_relationship_type,
  confidence_score,
  mapping_source, ai_generated,
  mapping_status,
  mapped_by, mapped_ts,
  project_id,
  is_approved_pattern
) VALUES (
  SEMANTIC_FIELD_ID_1,  -- Replace with actual ID
  'Member Foundation', 'MBR_FNDTN',
  'Member Key', 'MBR_KEY',
  'SELECT p.PERSON_ID AS MBR_KEY FROM TEST_PERSON p',
  'Test Person', 'TEST_PERSON',
  'Person ID', 'PERSON_ID',
  'Unique identifier for the person',
  'SINGLE',
  0.95,
  'AI', true,
  'ACTIVE',
  'test@example.com', CURRENT_TIMESTAMP(),
  PROJECT_ID,
  false
);

-- Mapping 2: First Name
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id,
  tgt_table_name, tgt_table_physical_name,
  tgt_column_name, tgt_column_physical_name,
  source_expression,
  source_tables, source_tables_physical,
  source_columns, source_columns_physical,
  source_descriptions,
  source_relationship_type,
  transformations_applied,
  confidence_score,
  mapping_source, ai_generated,
  mapping_status,
  mapped_by, mapped_ts,
  project_id,
  is_approved_pattern
) VALUES (
  SEMANTIC_FIELD_ID_2,  -- Replace with actual ID
  'Member Foundation', 'MBR_FNDTN',
  'First Name', 'FRST_NM',
  'SELECT INITCAP(TRIM(p.FIRST_NAME)) AS FRST_NM FROM TEST_PERSON p',
  'Test Person', 'TEST_PERSON',
  'First Name', 'FIRST_NAME',
  'First name of the person',
  'SINGLE',
  'INITCAP, TRIM',
  0.92,
  'AI', true,
  'ACTIVE',
  'test@example.com', CURRENT_TIMESTAMP(),
  PROJECT_ID,
  false
);

-- Mapping 3: Last Name
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id,
  tgt_table_name, tgt_table_physical_name,
  tgt_column_name, tgt_column_physical_name,
  source_expression,
  source_tables, source_tables_physical,
  source_columns, source_columns_physical,
  source_descriptions,
  source_relationship_type,
  transformations_applied,
  confidence_score,
  mapping_source, ai_generated,
  mapping_status,
  mapped_by, mapped_ts,
  project_id,
  is_approved_pattern
) VALUES (
  SEMANTIC_FIELD_ID_3,  -- Replace with actual ID
  'Member Foundation', 'MBR_FNDTN',
  'Last Name', 'LAST_NM',
  'SELECT INITCAP(TRIM(p.LAST_NAME)) AS LAST_NM FROM TEST_PERSON p',
  'Test Person', 'TEST_PERSON',
  'Last Name', 'LAST_NAME',
  'Last name of the person',
  'SINGLE',
  'INITCAP, TRIM',
  0.91,
  'AI', true,
  'ACTIVE',
  'test@example.com', CURRENT_TIMESTAMP(),
  PROJECT_ID,
  false
);

-- Mapping 4: Birth Date
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id,
  tgt_table_name, tgt_table_physical_name,
  tgt_column_name, tgt_column_physical_name,
  source_expression,
  source_tables, source_tables_physical,
  source_columns, source_columns_physical,
  source_descriptions,
  source_relationship_type,
  confidence_score,
  mapping_source, ai_generated,
  mapping_status,
  mapped_by, mapped_ts,
  project_id,
  is_approved_pattern
) VALUES (
  SEMANTIC_FIELD_ID_4,  -- Replace with actual ID
  'Member Foundation', 'MBR_FNDTN',
  'Birth Date', 'BRTH_DT',
  'SELECT CAST(p.BIRTH_DT AS DATE) AS BRTH_DT FROM TEST_PERSON p',
  'Test Person', 'TEST_PERSON',
  'Birth Date', 'BIRTH_DT',
  'Date of birth',
  'SINGLE',
  0.94,
  'AI', true,
  'ACTIVE',
  'test@example.com', CURRENT_TIMESTAMP(),
  PROJECT_ID,
  false
);

-- Mapping 5: SSN (masked)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id,
  tgt_table_name, tgt_table_physical_name,
  tgt_column_name, tgt_column_physical_name,
  source_expression,
  source_tables, source_tables_physical,
  source_columns, source_columns_physical,
  source_descriptions,
  source_relationship_type,
  transformations_applied,
  confidence_score,
  mapping_source, ai_generated,
  mapping_status,
  mapped_by, mapped_ts,
  project_id,
  is_approved_pattern
) VALUES (
  SEMANTIC_FIELD_ID_5,  -- Replace with actual ID
  'Member Foundation', 'MBR_FNDTN',
  'SSN', 'SSN_TXT',
  'SELECT CONCAT(''XXX-XX-'', RIGHT(p.SSN_NUM, 4)) AS SSN_TXT FROM TEST_PERSON p',
  'Test Person', 'TEST_PERSON',
  'SSN', 'SSN_NUM',
  'Social security number (masked)',
  'SINGLE',
  'CONCAT, RIGHT',
  0.88,
  'AI', true,
  'ACTIVE',
  'test@example.com', CURRENT_TIMESTAMP(),
  PROJECT_ID,
  false
);


-- ============================================================================
-- STEP 6: Verify the Data
-- ============================================================================

-- Check project:
-- SELECT * FROM ${CATALOG_SCHEMA}.mapping_projects WHERE project_name = 'Export Test Project';

-- Check mappings:
-- SELECT mf.mapped_field_id, mf.tgt_column_physical_name, mf.source_expression, mf.confidence_score
-- FROM ${CATALOG_SCHEMA}.mapped_fields mf
-- WHERE mf.project_id = PROJECT_ID;

-- Now you can test the Export Mappings button on the project detail page!

