-- ============================================================================
-- V4 Target-First Test Data - MBR_CNTCT Table
-- ============================================================================
-- 
-- This script creates test data for the V4 target-first workflow:
-- 1. Semantic fields (target columns) for MBR_CNTCT table
-- 2. Past mappings (patterns) in mapped_fields with join_metadata
-- 3. A test project
-- 4. Unmapped source fields that should match the patterns
--
-- Run this in Databricks SQL after creating the V4 schema
-- Replace ${CATALOG_SCHEMA} with your catalog.schema (e.g., oztest_dev.smartmapper)
-- ============================================================================

-- ============================================================================
-- STEP 1: Ensure semantic_fields has MBR_CNTCT columns
-- ============================================================================

-- First, delete any existing MBR_CNTCT records to avoid duplicates
DELETE FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE UPPER(tgt_table_physical_name) = 'MBR_CNTCT';

-- Insert MBR_CNTCT target columns
INSERT INTO ${CATALOG_SCHEMA}.semantic_fields (
  domain,
  tgt_table_name,
  tgt_table_physical_name,
  tgt_column_name,
  tgt_column_physical_name,
  tgt_nullable,
  tgt_physical_datatype,
  tgt_comments
) VALUES
  ('Member', 'MEMBER CONTACT', 'MBR_CNTCT', 'Member Sk', 'MBR_SK', 'NO', 'BIGINT', 'Unique identifier for a given member. Auto generated key linking to MBR_FNDTN table.'),
  ('Member', 'MEMBER CONTACT', 'MBR_CNTCT', 'Address 1 Text', 'ADDR_1_TXT', 'YES', 'STRING', 'First address line of mailing address of member or recipient.'),
  ('Member', 'MEMBER CONTACT', 'MBR_CNTCT', 'Address 2 Text', 'ADDR_2_TXT', 'YES', 'STRING', 'Second address line of mailing address of member or recipient.'),
  ('Member', 'MEMBER CONTACT', 'MBR_CNTCT', 'City Name', 'CITY_NM', 'YES', 'STRING', 'City of mailing address of member or recipient.'),
  ('Member', 'MEMBER CONTACT', 'MBR_CNTCT', 'State Code', 'ST_CD', 'YES', 'STRING', 'State of mailing address of member or recipient.'),
  ('Member', 'MEMBER CONTACT', 'MBR_CNTCT', 'Zip Code', 'ZIP_CD', 'YES', 'STRING', 'ZIP code of mailing address of member or recipient.'),
  ('Member', 'MEMBER CONTACT', 'MBR_CNTCT', 'Contact Type Code', 'CNTCT_TYP_CD', 'YES', 'STRING', 'Code indicating the contact type (e.g., M=Mail, R=Residence).'),
  ('Member', 'MEMBER CONTACT', 'MBR_CNTCT', 'Country Code', 'CNTRY_CD', 'YES', 'STRING', 'Country code for the member address.'),
  ('Member', 'MEMBER CONTACT', 'MBR_CNTCT', 'Member Contact SSK', 'MBR_CNTCT_SSK', 'NO', 'STRING', 'System Surrogate Key - unique identifier for this contact record.'),
  ('Member', 'MEMBER CONTACT', 'MBR_CNTCT', 'County Code', 'CNTY_CD', 'YES', 'STRING', 'County code from the county lookup table.');


-- ============================================================================
-- STEP 2: Insert Past Mappings (Patterns) with join_metadata
-- ============================================================================

-- Delete existing patterns for MBR_CNTCT
DELETE FROM ${CATALOG_SCHEMA}.mapped_fields 
WHERE UPPER(tgt_table_physical_name) = 'MBR_CNTCT' 
  AND project_id IS NULL;

-- Pattern 1: MBR_SK (Lookup with UNION)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id,
  project_id,
  tgt_table_name,
  tgt_table_physical_name,
  tgt_column_name,
  tgt_column_physical_name,
  tgt_comments,
  source_expression,
  source_tables,
  source_tables_physical,
  source_columns,
  source_columns_physical,
  source_descriptions,
  source_datatypes,
  source_domain,
  source_relationship_type,
  transformations_applied,
  join_metadata,
  mapping_status,
  confidence_score,
  is_approved_pattern,
  pattern_approved_by,
  pattern_approved_ts,
  mapped_by
) VALUES (
  (SELECT semantic_field_id FROM ${CATALOG_SCHEMA}.semantic_fields WHERE tgt_column_physical_name = 'MBR_SK' AND tgt_table_physical_name = 'MBR_CNTCT' LIMIT 1),
  NULL, -- Global pattern (not project-specific)
  'MEMBER CONTACT',
  'MBR_CNTCT',
  'Member Sk',
  'MBR_SK',
  'Unique identifier for a given member. Auto generated key linking to MBR_FNDTN table.',
  'SELECT DISTINCT mf.MBR_SK FROM oz_dev.bronze_dmes_de.t_re_base b JOIN oz_dev.silver_dmes_de.mbr_fndtn mf ON b.SAK_RECIP = mf.SRC_KEY_ID AND mf.CURR_REC_IND=''1'' LEFT JOIN oz_dev.silver_dmes_de.cnty_cd c ON b.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1'' WHERE mf.CURR_REC_IND=''1'' UNION DISTINCT SELECT DISTINCT mf.MBR_SK FROM (SELECT * FROM oz_dev.bronze_dmes_de.t_re_multi_address WHERE TRIM(CDE_ADDR_USAGE) IN (''R'',''M'') AND CURR_REC_IND=''1'') a JOIN oz_dev.silver_dmes_de.mbr_fndtn mf ON a.SAK_RECIP = mf.SRC_KEY_ID LEFT JOIN oz_dev.silver_dmes_de.cnty_cd c ON a.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1'' WHERE mf.CURR_REC_IND=''1''',
  'T_RE_BASE|T_RE_MULTI_ADDRESS|MBR_FNDTN|CNTY_CD',
  't_re_base|t_re_multi_address|mbr_fndtn|cnty_cd',
  'SAK_RECIP|SAK_RECIP|SRC_KEY_ID|MBR_SK|CDE_COUNTY|CNTY_ID',
  'SAK_RECIP|SAK_RECIP|SRC_KEY_ID|MBR_SK|CDE_COUNTY|CNTY_ID',
  'SAK_RECIP: Recipient identifier to uniquely represent individuals|SRC_KEY_ID: Source key ID in member foundation|MBR_SK: Member surrogate key|CDE_COUNTY: County code for address|CNTY_ID: County identifier in lookup table',
  'BIGINT|BIGINT|BIGINT|BIGINT|STRING|STRING',
  'Member',
  'UNION_JOIN',
  'Lookup',
  '{
    "patternType": "UNION_WITH_JOINS",
    "outputColumn": "MBR_SK",
    "description": "Member SK lookup via recipient ID with UNION from base and multi-address tables",
    "silverTables": [
      {"alias": "mf", "physicalName": "oz_dev.silver_dmes_de.mbr_fndtn", "isConstant": true, "description": "Member Foundation - lookup table"},
      {"alias": "c", "physicalName": "oz_dev.silver_dmes_de.cnty_cd", "isConstant": true, "description": "County Code lookup table"}
    ],
    "unionBranches": [
      {
        "branchId": 1,
        "description": "Primary address from T_RE_BASE",
        "bronzeTable": {"alias": "b", "physicalName": "oz_dev.bronze_dmes_de.t_re_base", "isConstant": false, "description": "Base recipient table"},
        "joins": [
          {"type": "INNER", "toTable": "mf", "onCondition": "b.SAK_RECIP = mf.SRC_KEY_ID AND mf.CURR_REC_IND=''1''"},
          {"type": "LEFT", "toTable": "c", "onCondition": "b.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''"}
        ],
        "whereClause": "mf.CURR_REC_IND=''1''"
      },
      {
        "branchId": 2,
        "description": "Additional addresses from T_RE_MULTI_ADDRESS",
        "bronzeTable": {"alias": "a", "physicalName": "oz_dev.bronze_dmes_de.t_re_multi_address", "isConstant": false, "description": "Multi-address table", "subquery": "SELECT * FROM oz_dev.bronze_dmes_de.t_re_multi_address WHERE TRIM(CDE_ADDR_USAGE) IN (''R'',''M'') AND CURR_REC_IND=''1''"},
        "joins": [
          {"type": "INNER", "toTable": "mf", "onCondition": "a.SAK_RECIP = mf.SRC_KEY_ID"},
          {"type": "LEFT", "toTable": "c", "onCondition": "a.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''"}
        ],
        "whereClause": "mf.CURR_REC_IND=''1''"
      }
    ],
    "userColumnsToMap": [
      {"role": "join_key_source", "originalColumn": "SAK_RECIP", "description": "Recipient ID from bronze table - maps to SRC_KEY_ID in member foundation"},
      {"role": "filter_source", "originalColumn": "CDE_COUNTY", "description": "County code from bronze for county lookup"}
    ],
    "userTablesToMap": [
      {"role": "bronze_primary", "originalTable": "oz_dev.bronze_dmes_de.t_re_base", "description": "Primary bronze table with base recipient data"},
      {"role": "bronze_secondary", "originalTable": "oz_dev.bronze_dmes_de.t_re_multi_address", "description": "Secondary bronze table with multi-address data"}
    ]
  }',
  'ACTIVE',
  0.95,
  TRUE,
  'system',
  CURRENT_TIMESTAMP(),
  'system'
);

-- Pattern 2: ADDR_1_TXT (Address Line 1 with transformation)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id,
  project_id,
  tgt_table_name,
  tgt_table_physical_name,
  tgt_column_name,
  tgt_column_physical_name,
  tgt_comments,
  source_expression,
  source_tables,
  source_tables_physical,
  source_columns,
  source_columns_physical,
  source_descriptions,
  source_datatypes,
  source_domain,
  source_relationship_type,
  transformations_applied,
  join_metadata,
  mapping_status,
  confidence_score,
  is_approved_pattern,
  pattern_approved_by,
  pattern_approved_ts,
  mapped_by
) VALUES (
  (SELECT semantic_field_id FROM ${CATALOG_SCHEMA}.semantic_fields WHERE tgt_column_physical_name = 'ADDR_1_TXT' AND tgt_table_physical_name = 'MBR_CNTCT' LIMIT 1),
  NULL,
  'MEMBER CONTACT',
  'MBR_CNTCT',
  'Address 1 Text',
  'ADDR_1_TXT',
  'First address line of mailing address of member or recipient.',
  'SELECT DISTINCT INITCAP(b.ADR_STREET_1) AS ADDR_1_TXT FROM oz_dev.bronze_dmes_de.t_re_base b JOIN oz_dev.silver_dmes_de.mbr_fndtn mf ON b.SAK_RECIP = mf.SRC_KEY_ID AND mf.CURR_REC_IND=''1'' LEFT JOIN oz_dev.silver_dmes_de.cnty_cd c ON b.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1'' WHERE mf.CURR_REC_IND=''1'' UNION DISTINCT SELECT DISTINCT INITCAP(a.ADR_STREET_1) AS ADDR_1_TXT FROM (SELECT * FROM oz_dev.bronze_dmes_de.t_re_multi_address WHERE TRIM(CDE_ADDR_USAGE) IN (''R'',''M'') AND CURR_REC_IND=''1'') a JOIN oz_dev.silver_dmes_de.mbr_fndtn mf ON a.SAK_RECIP = mf.SRC_KEY_ID LEFT JOIN oz_dev.silver_dmes_de.cnty_cd c ON a.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1'' WHERE mf.CURR_REC_IND=''1''',
  'T_RE_BASE|T_RE_MULTI_ADDRESS',
  't_re_base|t_re_multi_address',
  'ADR_STREET_1|ADR_STREET_1',
  'ADR_STREET_1|ADR_STREET_1',
  'ADR_STREET_1: Primary street address line for recipient',
  'STRING|STRING',
  'Member',
  'UNION_JOIN',
  'INITCAP',
  '{
    "patternType": "UNION_WITH_JOINS",
    "outputColumn": "ADDR_1_TXT",
    "outputTransformation": "INITCAP",
    "description": "Address line 1 with INITCAP transformation from UNION of base and multi-address tables",
    "silverTables": [
      {"alias": "mf", "physicalName": "oz_dev.silver_dmes_de.mbr_fndtn", "isConstant": true},
      {"alias": "c", "physicalName": "oz_dev.silver_dmes_de.cnty_cd", "isConstant": true}
    ],
    "unionBranches": [
      {
        "branchId": 1,
        "bronzeTable": {"alias": "b", "physicalName": "oz_dev.bronze_dmes_de.t_re_base", "isConstant": false},
        "outputExpression": "INITCAP(b.ADR_STREET_1)"
      },
      {
        "branchId": 2,
        "bronzeTable": {"alias": "a", "physicalName": "oz_dev.bronze_dmes_de.t_re_multi_address", "isConstant": false},
        "outputExpression": "INITCAP(a.ADR_STREET_1)"
      }
    ],
    "userColumnsToMap": [
      {"role": "output", "originalColumn": "ADR_STREET_1", "description": "Street address line 1 from bronze table"}
    ]
  }',
  'ACTIVE',
  0.92,
  TRUE,
  'system',
  CURRENT_TIMESTAMP(),
  'system'
);

-- Pattern 3: CITY_NM
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id,
  project_id,
  tgt_table_name,
  tgt_table_physical_name,
  tgt_column_name,
  tgt_column_physical_name,
  tgt_comments,
  source_expression,
  source_tables,
  source_tables_physical,
  source_columns,
  source_columns_physical,
  source_descriptions,
  source_datatypes,
  source_domain,
  source_relationship_type,
  transformations_applied,
  join_metadata,
  mapping_status,
  confidence_score,
  is_approved_pattern,
  pattern_approved_by,
  pattern_approved_ts,
  mapped_by
) VALUES (
  (SELECT semantic_field_id FROM ${CATALOG_SCHEMA}.semantic_fields WHERE tgt_column_physical_name = 'CITY_NM' AND tgt_table_physical_name = 'MBR_CNTCT' LIMIT 1),
  NULL,
  'MEMBER CONTACT',
  'MBR_CNTCT',
  'City Name',
  'CITY_NM',
  'City of mailing address of member or recipient.',
  'SELECT DISTINCT INITCAP(b.ADR_CITY) AS CITY_NM FROM oz_dev.bronze_dmes_de.t_re_base b JOIN oz_dev.silver_dmes_de.mbr_fndtn mf ON b.SAK_RECIP = mf.SRC_KEY_ID AND mf.CURR_REC_IND=''1'' WHERE mf.CURR_REC_IND=''1'' UNION DISTINCT SELECT DISTINCT INITCAP(a.ADR_CITY) AS CITY_NM FROM oz_dev.bronze_dmes_de.t_re_multi_address a JOIN oz_dev.silver_dmes_de.mbr_fndtn mf ON a.SAK_RECIP = mf.SRC_KEY_ID WHERE mf.CURR_REC_IND=''1'' AND TRIM(a.CDE_ADDR_USAGE) IN (''R'',''M'')',
  'T_RE_BASE|T_RE_MULTI_ADDRESS',
  't_re_base|t_re_multi_address',
  'ADR_CITY|ADR_CITY',
  'ADR_CITY|ADR_CITY',
  'ADR_CITY: City name from the address record',
  'STRING|STRING',
  'Member',
  'UNION_JOIN',
  'INITCAP',
  '{
    "patternType": "UNION_WITH_JOINS",
    "outputColumn": "CITY_NM",
    "outputTransformation": "INITCAP",
    "userColumnsToMap": [
      {"role": "output", "originalColumn": "ADR_CITY", "description": "City from address record"}
    ]
  }',
  'ACTIVE',
  0.90,
  TRUE,
  'system',
  CURRENT_TIMESTAMP(),
  'system'
);

-- Pattern 4: ST_CD (State Code - no transformation)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id,
  project_id,
  tgt_table_name,
  tgt_table_physical_name,
  tgt_column_name,
  tgt_column_physical_name,
  tgt_comments,
  source_expression,
  source_tables,
  source_tables_physical,
  source_columns,
  source_columns_physical,
  source_descriptions,
  source_datatypes,
  source_domain,
  source_relationship_type,
  transformations_applied,
  join_metadata,
  mapping_status,
  confidence_score,
  is_approved_pattern,
  pattern_approved_by,
  pattern_approved_ts,
  mapped_by
) VALUES (
  (SELECT semantic_field_id FROM ${CATALOG_SCHEMA}.semantic_fields WHERE tgt_column_physical_name = 'ST_CD' AND tgt_table_physical_name = 'MBR_CNTCT' LIMIT 1),
  NULL,
  'MEMBER CONTACT',
  'MBR_CNTCT',
  'State Code',
  'ST_CD',
  'State of mailing address of member or recipient.',
  'SELECT DISTINCT b.ADR_STATE AS ST_CD FROM oz_dev.bronze_dmes_de.t_re_base b JOIN oz_dev.silver_dmes_de.mbr_fndtn mf ON b.SAK_RECIP = mf.SRC_KEY_ID AND mf.CURR_REC_IND=''1'' WHERE mf.CURR_REC_IND=''1'' UNION DISTINCT SELECT DISTINCT a.ADR_STATE AS ST_CD FROM oz_dev.bronze_dmes_de.t_re_multi_address a JOIN oz_dev.silver_dmes_de.mbr_fndtn mf ON a.SAK_RECIP = mf.SRC_KEY_ID WHERE mf.CURR_REC_IND=''1'' AND TRIM(a.CDE_ADDR_USAGE) IN (''R'',''M'')',
  'T_RE_BASE|T_RE_MULTI_ADDRESS',
  't_re_base|t_re_multi_address',
  'ADR_STATE|ADR_STATE',
  'ADR_STATE|ADR_STATE',
  'ADR_STATE: State code from address record',
  'STRING|STRING',
  'Member',
  'UNION_JOIN',
  NULL,
  '{
    "patternType": "UNION_WITH_JOINS",
    "outputColumn": "ST_CD",
    "userColumnsToMap": [
      {"role": "output", "originalColumn": "ADR_STATE", "description": "State code from address"}
    ]
  }',
  'ACTIVE',
  0.91,
  TRUE,
  'system',
  CURRENT_TIMESTAMP(),
  'system'
);

-- Pattern 5: CNTCT_TYP_CD (Contact Type with hardcode and column)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id,
  project_id,
  tgt_table_name,
  tgt_table_physical_name,
  tgt_column_name,
  tgt_column_physical_name,
  tgt_comments,
  source_expression,
  source_tables,
  source_tables_physical,
  source_columns,
  source_columns_physical,
  source_descriptions,
  source_datatypes,
  source_domain,
  source_relationship_type,
  transformations_applied,
  join_metadata,
  mapping_status,
  confidence_score,
  is_approved_pattern,
  pattern_approved_by,
  pattern_approved_ts,
  mapped_by
) VALUES (
  (SELECT semantic_field_id FROM ${CATALOG_SCHEMA}.semantic_fields WHERE tgt_column_physical_name = 'CNTCT_TYP_CD' AND tgt_table_physical_name = 'MBR_CNTCT' LIMIT 1),
  NULL,
  'MEMBER CONTACT',
  'MBR_CNTCT',
  'Contact Type Code',
  'CNTCT_TYP_CD',
  'Code indicating the contact type (e.g., M=Mail, R=Residence).',
  'SELECT DISTINCT ''BSE'' AS CNTCT_TYP_CD FROM oz_dev.bronze_dmes_de.t_re_base b JOIN oz_dev.silver_dmes_de.mbr_fndtn mf ON b.SAK_RECIP = mf.SRC_KEY_ID WHERE mf.CURR_REC_IND=''1'' UNION DISTINCT SELECT DISTINCT TRIM(a.CDE_ADDR_USAGE) AS CNTCT_TYP_CD FROM oz_dev.bronze_dmes_de.t_re_multi_address a JOIN oz_dev.silver_dmes_de.mbr_fndtn mf ON a.SAK_RECIP = mf.SRC_KEY_ID WHERE mf.CURR_REC_IND=''1'' AND TRIM(a.CDE_ADDR_USAGE) IN (''R'',''M'')',
  'T_RE_BASE|T_RE_MULTI_ADDRESS',
  't_re_base|t_re_multi_address',
  'HARDCODE_BSE|CDE_ADDR_USAGE',
  'HARDCODE_BSE|CDE_ADDR_USAGE',
  'CDE_ADDR_USAGE: Address usage type code (R=Residence, M=Mail)',
  'STRING|STRING',
  'Member',
  'UNION_JOIN',
  'TRIM|HARDCODE',
  '{
    "patternType": "UNION_WITH_JOINS",
    "outputColumn": "CNTCT_TYP_CD",
    "notes": "Branch 1 uses hardcoded BSE, Branch 2 uses CDE_ADDR_USAGE column",
    "userColumnsToMap": [
      {"role": "output", "originalColumn": "CDE_ADDR_USAGE", "description": "Address usage type code", "branchId": 2}
    ]
  }',
  'ACTIVE',
  0.88,
  TRUE,
  'system',
  CURRENT_TIMESTAMP(),
  'system'
);


-- ============================================================================
-- STEP 3: Create a Test Project
-- ============================================================================

-- Delete existing test project if exists
DELETE FROM ${CATALOG_SCHEMA}.mapping_suggestions 
WHERE project_id IN (SELECT project_id FROM ${CATALOG_SCHEMA}.mapping_projects WHERE project_name = 'Test: ACME Member Migration');

DELETE FROM ${CATALOG_SCHEMA}.target_table_status 
WHERE project_id IN (SELECT project_id FROM ${CATALOG_SCHEMA}.mapping_projects WHERE project_name = 'Test: ACME Member Migration');

DELETE FROM ${CATALOG_SCHEMA}.unmapped_fields 
WHERE project_id IN (SELECT project_id FROM ${CATALOG_SCHEMA}.mapping_projects WHERE project_name = 'Test: ACME Member Migration');

DELETE FROM ${CATALOG_SCHEMA}.mapping_projects 
WHERE project_name = 'Test: ACME Member Migration';

-- Create the test project
INSERT INTO ${CATALOG_SCHEMA}.mapping_projects (
  project_name,
  project_description,
  source_system_name,
  source_catalogs,
  source_schemas,
  target_domains,
  project_status,
  created_by,
  created_ts
) VALUES (
  'Test: ACME Member Migration',
  'Test project for V4 target-first workflow demonstration. Migrating ACME legacy member data to silver layer.',
  'ACME Legacy DW',
  'bronze_acme',
  'member',
  'Member',
  'NOT_STARTED',
  'david.galluzzo@gainwelltechnologies.com',
  CURRENT_TIMESTAMP()
);


-- ============================================================================
-- STEP 4: Create Unmapped Source Fields (User''s uploaded data)
-- ============================================================================

-- Get the project ID we just created
-- Note: In Databricks, you may need to run this separately or use a variable

-- Delete existing test unmapped fields
DELETE FROM ${CATALOG_SCHEMA}.unmapped_fields 
WHERE UPPER(src_table_physical_name) IN ('ACME_RECIPIENT', 'ACME_ADDR_HISTORY');

-- Insert test source fields that should match the patterns
-- These simulate what a user would upload for their ACME source system

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  project_id,
  domain,
  src_table_name,
  src_table_physical_name,
  src_column_name,
  src_column_physical_name,
  src_nullable,
  src_physical_datatype,
  src_comments,
  uploaded_by,
  uploaded_ts
)
SELECT 
  (SELECT project_id FROM ${CATALOG_SCHEMA}.mapping_projects WHERE project_name = 'Test: ACME Member Migration' LIMIT 1) as project_id,
  'Member' as domain,
  src_table_name,
  src_table_physical_name,
  src_column_name,
  src_column_physical_name,
  src_nullable,
  src_physical_datatype,
  src_comments,
  'david.galluzzo@gainwelltechnologies.com' as uploaded_by,
  CURRENT_TIMESTAMP() as uploaded_ts
FROM (VALUES
  -- ACME_RECIPIENT table (similar to T_RE_BASE)
  ('ACME Recipient', 'ACME_RECIPIENT', 'Recipient Key', 'RECIP_KEY', 'NO', 'BIGINT', 'Primary identifier for the recipient/member in ACME system. Used to link demographic and enrollment data.'),
  ('ACME Recipient', 'ACME_RECIPIENT', 'Street Address 1', 'STREET_ADDR_1', 'YES', 'STRING', 'Primary street address line for the recipient. May contain apartment numbers or suite info.'),
  ('ACME Recipient', 'ACME_RECIPIENT', 'Street Address 2', 'STREET_ADDR_2', 'YES', 'STRING', 'Secondary street address line. Used for additional address details like building names.'),
  ('ACME Recipient', 'ACME_RECIPIENT', 'City', 'CITY', 'YES', 'STRING', 'City name from the recipient mailing address.'),
  ('ACME Recipient', 'ACME_RECIPIENT', 'State', 'STATE_CD', 'YES', 'STRING', 'Two-character state code (e.g., DE, PA, NJ).'),
  ('ACME Recipient', 'ACME_RECIPIENT', 'Zip', 'ZIP', 'YES', 'STRING', 'Five or nine digit ZIP code for the address.'),
  ('ACME Recipient', 'ACME_RECIPIENT', 'County Code', 'COUNTY_CD', 'YES', 'STRING', 'County FIPS code for the recipient address.'),
  ('ACME Recipient', 'ACME_RECIPIENT', 'Current Flag', 'IS_CURRENT', 'YES', 'STRING', 'Y/N flag indicating if this is the current active record.'),
  
  -- ACME_ADDR_HISTORY table (similar to T_RE_MULTI_ADDRESS)
  ('ACME Address History', 'ACME_ADDR_HISTORY', 'Recipient Key', 'RECIP_KEY', 'NO', 'BIGINT', 'Foreign key to ACME_RECIPIENT. Links address history to the member.'),
  ('ACME Address History', 'ACME_ADDR_HISTORY', 'Address Line 1', 'ADDR_LINE_1', 'YES', 'STRING', 'First line of historical address record.'),
  ('ACME Address History', 'ACME_ADDR_HISTORY', 'Address Line 2', 'ADDR_LINE_2', 'YES', 'STRING', 'Second line of historical address record.'),
  ('ACME Address History', 'ACME_ADDR_HISTORY', 'City Name', 'CITY_NAME', 'YES', 'STRING', 'City from historical address.'),
  ('ACME Address History', 'ACME_ADDR_HISTORY', 'State', 'STATE', 'YES', 'STRING', 'State code from historical address.'),
  ('ACME Address History', 'ACME_ADDR_HISTORY', 'Postal Code', 'POSTAL_CD', 'YES', 'STRING', 'ZIP or postal code from historical address.'),
  ('ACME Address History', 'ACME_ADDR_HISTORY', 'Address Type', 'ADDR_TYPE_CD', 'YES', 'STRING', 'Type of address: R=Residence, M=Mailing, W=Work.'),
  ('ACME Address History', 'ACME_ADDR_HISTORY', 'County', 'COUNTY', 'YES', 'STRING', 'County code for the historical address.'),
  ('ACME Address History', 'ACME_ADDR_HISTORY', 'Active Indicator', 'ACTIVE_IND', 'YES', 'STRING', '1/0 indicator for current record.')
) AS t(src_table_name, src_table_physical_name, src_column_name, src_column_physical_name, src_nullable, src_physical_datatype, src_comments);


-- ============================================================================
-- STEP 5: Initialize Target Tables for the Project
-- ============================================================================

-- This would normally be done via the stored procedure, but we can do it manually
INSERT INTO ${CATALOG_SCHEMA}.target_table_status (
  project_id,
  tgt_table_name,
  tgt_table_physical_name,
  tgt_table_description,
  mapping_status,
  total_columns,
  display_order,
  created_ts
)
SELECT 
  (SELECT project_id FROM ${CATALOG_SCHEMA}.mapping_projects WHERE project_name = 'Test: ACME Member Migration' LIMIT 1),
  'MEMBER CONTACT',
  'MBR_CNTCT',
  'This entity contains the member contact information.',
  'NOT_STARTED',
  (SELECT COUNT(*) FROM ${CATALOG_SCHEMA}.semantic_fields WHERE UPPER(tgt_table_physical_name) = 'MBR_CNTCT'),
  1,
  CURRENT_TIMESTAMP();

-- Update project counters
UPDATE ${CATALOG_SCHEMA}.mapping_projects
SET 
  total_target_tables = 1,
  total_target_columns = (SELECT COUNT(*) FROM ${CATALOG_SCHEMA}.semantic_fields WHERE UPPER(tgt_table_physical_name) = 'MBR_CNTCT'),
  project_status = 'IN_PROGRESS',
  updated_ts = CURRENT_TIMESTAMP()
WHERE project_name = 'Test: ACME Member Migration';


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check semantic fields
SELECT 'Semantic Fields' as check_type, COUNT(*) as count 
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE UPPER(tgt_table_physical_name) = 'MBR_CNTCT';

-- Check mapped fields (patterns)
SELECT 'Mapped Fields (Patterns)' as check_type, COUNT(*) as count 
FROM ${CATALOG_SCHEMA}.mapped_fields 
WHERE UPPER(tgt_table_physical_name) = 'MBR_CNTCT' 
  AND project_id IS NULL 
  AND is_approved_pattern = TRUE;

-- Check project
SELECT 'Project' as check_type, project_id, project_name, project_status, total_target_tables, total_target_columns
FROM ${CATALOG_SCHEMA}.mapping_projects 
WHERE project_name = 'Test: ACME Member Migration';

-- Check unmapped fields
SELECT 'Unmapped Fields' as check_type, COUNT(*) as count, COUNT(DISTINCT src_table_physical_name) as tables
FROM ${CATALOG_SCHEMA}.unmapped_fields 
WHERE project_id = (SELECT project_id FROM ${CATALOG_SCHEMA}.mapping_projects WHERE project_name = 'Test: ACME Member Migration');

-- Check target table status
SELECT 'Target Table Status' as check_type, tgt_table_physical_name, mapping_status, total_columns
FROM ${CATALOG_SCHEMA}.target_table_status 
WHERE project_id = (SELECT project_id FROM ${CATALOG_SCHEMA}.mapping_projects WHERE project_name = 'Test: ACME Member Migration');

-- Preview patterns with join_metadata
SELECT 
  tgt_column_physical_name,
  source_relationship_type,
  transformations_applied,
  LEFT(join_metadata, 200) as join_metadata_preview
FROM ${CATALOG_SCHEMA}.mapped_fields 
WHERE UPPER(tgt_table_physical_name) = 'MBR_CNTCT' 
  AND project_id IS NULL;

