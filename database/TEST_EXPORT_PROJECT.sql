-- ============================================================================
-- TEST PROJECT WITH COMPLETED MAPPINGS FOR EXPORT TESTING
-- ============================================================================
-- 
-- This script creates a small test project with completed mappings
-- to test the export functionality.
--
-- Based on actual MBR_FNDTN semantic fields from MEMBERFOUND.csv
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
-- SELECT MAX(project_id) as new_project_id FROM ${CATALOG_SCHEMA}.mapping_projects;


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
-- Test Recipient Table - maps to MBR_FNDTN columns
(PROJECT_ID, 'Recipient Base', 'T_RE_BASE', 'SAK Recip', 'SAK_RECIP', 'VARCHAR(32)', 'NO', 'Unique identifier for the recipient - maps to member key', 'Member', 'MAPPED', 'PROJECT: PROJECT_ID | DESCRIPTION: Unique identifier for the recipient - maps to member key | TYPE: VARCHAR(32) | DOMAIN: Member'),
(PROJECT_ID, 'Recipient Base', 'T_RE_BASE', 'Source System', 'SRC_SYS', 'VARCHAR(20)', 'NO', 'Code identifying the source system', 'Member', 'MAPPED', 'PROJECT: PROJECT_ID | DESCRIPTION: Code identifying the source system | TYPE: VARCHAR(20) | DOMAIN: Member'),
(PROJECT_ID, 'Recipient Base', 'T_RE_BASE', 'Current Record', 'CURR_REC', 'CHAR(1)', 'NO', 'Y/N indicator for current active record', 'Member', 'MAPPED', 'PROJECT: PROJECT_ID | DESCRIPTION: Y/N indicator for current active record | TYPE: CHAR(1) | DOMAIN: Member'),
(PROJECT_ID, 'Recipient Base', 'T_RE_BASE', 'Created By', 'CREATED_BY', 'VARCHAR(10)', 'NO', 'User ID who created the record', 'Member', 'MAPPED', 'PROJECT: PROJECT_ID | DESCRIPTION: User ID who created the record | TYPE: VARCHAR(10) | DOMAIN: Member'),
(PROJECT_ID, 'Recipient Base', 'T_RE_BASE', 'Created Date', 'CREATED_DT', 'TIMESTAMP', 'NO', 'Date and time when record was created', 'Member', 'MAPPED', 'PROJECT: PROJECT_ID | DESCRIPTION: Date and time when record was created | TYPE: TIMESTAMP | DOMAIN: Member');


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
  'MEMBER FOUNDATION', 'MBR_FNDTN',
  'Core member foundation table with demographic and tracking information',
  'COMPLETE',
  5,
  5,
  5,
  0.93,
  'test@example.com', CURRENT_TIMESTAMP()
);


-- ============================================================================
-- STEP 4: Add Completed Mappings (mapped_fields)
-- ============================================================================
-- Uses actual semantic_field_ids from MEMBERFOUND.csv

-- Mapping 1: SRC_KEY_ID (Source Key Id) - semantic_field_id: 56
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
  56,
  'MEMBER FOUNDATION', 'MBR_FNDTN',
  'Source Key Id', 'SRC_KEY_ID',
  'SELECT CAST(r.SAK_RECIP AS VARCHAR(32)) AS SRC_KEY_ID FROM T_RE_BASE r WHERE r.CURR_REC = ''Y''',
  'Recipient Base', 'T_RE_BASE',
  'SAK Recip', 'SAK_RECIP',
  'Unique identifier for the recipient - maps to member key',
  'SINGLE',
  0.95,
  'AI', true,
  'ACTIVE',
  'test@example.com', CURRENT_TIMESTAMP(),
  PROJECT_ID,
  false
);

-- Mapping 2: SRC_SYS_CD (Source System Code) - semantic_field_id: 58
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
  58,
  'MEMBER FOUNDATION', 'MBR_FNDTN',
  'Src_Sys_Cd', 'SRC_SYS_CD',
  'SELECT UPPER(TRIM(r.SRC_SYS)) AS SRC_SYS_CD FROM T_RE_BASE r',
  'Recipient Base', 'T_RE_BASE',
  'Source System', 'SRC_SYS',
  'Code identifying the source system',
  'SINGLE',
  0.94,
  'AI', true,
  'ACTIVE',
  'test@example.com', CURRENT_TIMESTAMP(),
  PROJECT_ID,
  false
);

-- Mapping 3: CURR_REC_IND (Current Record Indicator) - semantic_field_id: 60
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
  60,
  'MEMBER FOUNDATION', 'MBR_FNDTN',
  'Curr_Rec_Ind', 'CURR_REC_IND',
  'SELECT CASE WHEN r.CURR_REC = ''Y'' THEN ''Y'' ELSE ''N'' END AS CURR_REC_IND FROM T_RE_BASE r',
  'Recipient Base', 'T_RE_BASE',
  'Current Record', 'CURR_REC',
  'Y/N indicator for current active record',
  'SINGLE',
  0.96,
  'AI', true,
  'ACTIVE',
  'test@example.com', CURRENT_TIMESTAMP(),
  PROJECT_ID,
  false
);

-- Mapping 4: CRT_BY_USER_ID (Created By User) - semantic_field_id: 59
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
  59,
  'MEMBER FOUNDATION', 'MBR_FNDTN',
  'Crt_By_User_Id', 'CRT_BY_USER_ID',
  'SELECT UPPER(TRIM(r.CREATED_BY)) AS CRT_BY_USER_ID FROM T_RE_BASE r',
  'Recipient Base', 'T_RE_BASE',
  'Created By', 'CREATED_BY',
  'User ID who created the record',
  'SINGLE',
  0.92,
  'AI', true,
  'ACTIVE',
  'test@example.com', CURRENT_TIMESTAMP(),
  PROJECT_ID,
  false
);

-- Mapping 5: CRT_DTTM (Created Datetime) - semantic_field_id: 61
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
  61,
  'MEMBER FOUNDATION', 'MBR_FNDTN',
  'Crt_Dt', 'CRT_DTTM',
  'SELECT CAST(r.CREATED_DT AS TIMESTAMP) AS CRT_DTTM FROM T_RE_BASE r',
  'Recipient Base', 'T_RE_BASE',
  'Created Date', 'CREATED_DT',
  'Date and time when record was created',
  'SINGLE',
  0.91,
  'AI', true,
  'ACTIVE',
  'test@example.com', CURRENT_TIMESTAMP(),
  PROJECT_ID,
  false
);


-- ============================================================================
-- STEP 5: Verify the Data
-- ============================================================================

-- Check project:
-- SELECT * FROM ${CATALOG_SCHEMA}.mapping_projects WHERE project_name = 'Export Test Project';

-- Check target table status:
-- SELECT * FROM ${CATALOG_SCHEMA}.target_table_status WHERE project_id = PROJECT_ID;

-- Check mappings:
-- SELECT 
--   mf.mapped_field_id, 
--   mf.tgt_column_physical_name, 
--   mf.source_expression, 
--   mf.confidence_score,
--   mf.mapping_status
-- FROM ${CATALOG_SCHEMA}.mapped_fields mf
-- WHERE mf.project_id = PROJECT_ID
-- ORDER BY mf.tgt_column_physical_name;

-- ============================================================================
-- EXPECTED EXPORT OUTPUT
-- ============================================================================
-- When you export this project, you should see 5 mappings:
--
-- | Target Column    | Source Column | SQL Expression                                      |
-- |------------------|---------------|-----------------------------------------------------|
-- | SRC_KEY_ID       | SAK_RECIP     | SELECT CAST(r.SAK_RECIP...) AS SRC_KEY_ID           |
-- | SRC_SYS_CD       | SRC_SYS       | SELECT UPPER(TRIM(r.SRC_SYS)) AS SRC_SYS_CD         |
-- | CURR_REC_IND     | CURR_REC      | SELECT CASE WHEN r.CURR_REC... AS CURR_REC_IND      |
-- | CRT_BY_USER_ID   | CREATED_BY    | SELECT UPPER(TRIM(r.CREATED_BY)) AS CRT_BY_USER_ID  |
-- | CRT_DTTM         | CREATED_DT    | SELECT CAST(r.CREATED_DT AS TIMESTAMP) AS CRT_DTTM  |
-- ============================================================================
