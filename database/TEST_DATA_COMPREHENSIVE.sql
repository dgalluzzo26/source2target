-- ============================================================================
-- Smart Mapper V3 - Comprehensive Test Data
-- ============================================================================
-- 
-- This script creates test data for:
-- 1. Pattern Aggregation & Frequency Boosting
-- 2. Transformation Voting (multiple patterns, different transforms)
-- 3. Similar but different column matching
-- 4. All relationship types: SINGLE, CONCAT, JOIN, UNION
--
-- ============================================================================
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema
-- ============================================================================


-- ============================================================================
-- PART 1: MAPPED_FIELDS - Historical Patterns for AI to Learn From
-- ============================================================================


-- ============================================================================
-- SCENARIO A: FIRST NAME (SINGLE FIELD) - 5 Different Client Mappings
-- ============================================================================
-- Target: CASE.FIRST_NM
-- Expected: TRIM wins (5/5), INITCAP wins (3/5), UPPER loses (1/5)

-- Client A: Uses TRIM only
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'CASE', 'CASE', 'First Name', 'FIRST_NM', 'Member first name or given name',
  'TRIM(NAM_FIRST)', 'Recipient Base', 't_re_base', 'First Name', 'NAM_FIRST',
  'The first name of the recipient member', 'STRING', 'member', 'member',
  'SINGLE', 'TRIM', 0.95, 'MANUAL', 'test_client_a'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'FIRST_NM' AND tgt_table_physical_name = 'CASE' LIMIT 1;

-- Client B: Uses TRIM + INITCAP
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'CASE', 'CASE', 'First Name', 'FIRST_NM', 'Member first name or given name',
  'INITCAP(TRIM(FIRST_NAME))', 'Patient Demographics', 'patient_demo', 'Given Name', 'FIRST_NAME',
  'Patient given name from demographics file', 'STRING', 'member', 'member',
  'SINGLE', 'TRIM, INITCAP', 0.92, 'MANUAL', 'test_client_b'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'FIRST_NM' AND tgt_table_physical_name = 'CASE' LIMIT 1;

-- Client C: Uses TRIM + INITCAP
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'CASE', 'CASE', 'First Name', 'FIRST_NM', 'Member first name or given name',
  'INITCAP(TRIM(mbr_fname))', 'Member File', 'mbr_file', 'Member First', 'mbr_fname',
  'First name of the member from member file', 'STRING', 'member', 'member',
  'SINGLE', 'TRIM, INITCAP', 0.90, 'MANUAL', 'test_client_c'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'FIRST_NM' AND tgt_table_physical_name = 'CASE' LIMIT 1;

-- Client D: Uses TRIM + UPPER
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'CASE', 'CASE', 'First Name', 'FIRST_NM', 'Member first name or given name',
  'UPPER(TRIM(fname))', 'Client Data', 'client_data', 'First', 'fname',
  'Client first name', 'STRING', 'member', 'member',
  'SINGLE', 'TRIM, UPPER', 0.88, 'MANUAL', 'test_client_d'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'FIRST_NM' AND tgt_table_physical_name = 'CASE' LIMIT 1;

-- Client E: Uses TRIM + INITCAP
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'CASE', 'CASE', 'First Name', 'FIRST_NM', 'Member first name or given name',
  'INITCAP(TRIM(given_nm))', 'Enrollee Data', 'enrollee_data', 'Given Name', 'given_nm',
  'Given name of the enrollee', 'STRING', 'member', 'member',
  'SINGLE', 'TRIM, INITCAP', 0.91, 'MANUAL', 'test_client_e'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'FIRST_NM' AND tgt_table_physical_name = 'CASE' LIMIT 1;


-- ============================================================================
-- SCENARIO B: LAST NAME (SINGLE FIELD) - 4 Different Client Mappings
-- ============================================================================
-- Target: CASE.LAST_NM
-- Expected: TRIM wins (4/4), UPPER wins (3/4)

-- Client A: TRIM + UPPER
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'CASE', 'CASE', 'Last Name', 'LAST_NM', 'Member last name or surname',
  'UPPER(TRIM(NAM_LAST))', 'Recipient Base', 't_re_base', 'Last Name', 'NAM_LAST',
  'The last name or surname of the recipient', 'STRING', 'member', 'member',
  'SINGLE', 'TRIM, UPPER', 0.94, 'MANUAL', 'test_client_a'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'LAST_NM' AND tgt_table_physical_name = 'CASE' LIMIT 1;

-- Client B: TRIM + UPPER
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'CASE', 'CASE', 'Last Name', 'LAST_NM', 'Member last name or surname',
  'UPPER(TRIM(surname))', 'Patient Demo', 'patient_demo', 'Surname', 'surname',
  'Patient family name or surname', 'STRING', 'member', 'member',
  'SINGLE', 'TRIM, UPPER', 0.92, 'MANUAL', 'test_client_b'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'LAST_NM' AND tgt_table_physical_name = 'CASE' LIMIT 1;

-- Client C: TRIM only
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'CASE', 'CASE', 'Last Name', 'LAST_NM', 'Member last name or surname',
  'TRIM(family_name)', 'Member File', 'mbr_file', 'Family Name', 'family_name',
  'Family name of the member', 'STRING', 'member', 'member',
  'SINGLE', 'TRIM', 0.90, 'MANUAL', 'test_client_c'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'LAST_NM' AND tgt_table_physical_name = 'CASE' LIMIT 1;

-- Client D: TRIM + UPPER
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'CASE', 'CASE', 'Last Name', 'LAST_NM', 'Member last name or surname',
  'UPPER(TRIM(lname))', 'Client Data', 'client_data', 'Last', 'lname',
  'Client last name', 'STRING', 'member', 'member',
  'SINGLE', 'TRIM, UPPER', 0.89, 'MANUAL', 'test_client_d'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'LAST_NM' AND tgt_table_physical_name = 'CASE' LIMIT 1;


-- ============================================================================
-- SCENARIO C: FULL ADDRESS (CONCAT) - 4 Different Client Mappings
-- ============================================================================
-- Target: MBR_CNTCT.ADDR_LN_1
-- All use CONCAT of street number + street name

-- Client A: CONCAT with TRIM
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER CONTACT', 'MBR_CNTCT', 'Address Line 1', 'ADDR_LN_1', 'Primary address line including street number and name',
  'CONCAT_WS('' '', TRIM(street_num), TRIM(street_name))', 'Address Table', 't_address', 'Street Number | Street Name', 'street_num | street_name',
  'Street number of residence | Street name of residence', 'STRING | STRING', 'member', 'member',
  'CONCAT', 'CONCAT, TRIM', 0.93, 'MANUAL', 'test_client_a'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'ADDR_LN_1' AND tgt_table_physical_name = 'MBR_CNTCT' LIMIT 1;

-- Client B: CONCAT with TRIM + UPPER
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER CONTACT', 'MBR_CNTCT', 'Address Line 1', 'ADDR_LN_1', 'Primary address line including street number and name',
  'CONCAT_WS('' '', UPPER(TRIM(addr_no)), UPPER(TRIM(addr_street)))', 'Patient Address', 'patient_addr', 'Address No | Address Street', 'addr_no | addr_street',
  'Patient address number | Patient street name', 'STRING | STRING', 'member', 'member',
  'CONCAT', 'CONCAT, TRIM, UPPER', 0.91, 'MANUAL', 'test_client_b'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'ADDR_LN_1' AND tgt_table_physical_name = 'MBR_CNTCT' LIMIT 1;

-- Client C: CONCAT with TRIM
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER CONTACT', 'MBR_CNTCT', 'Address Line 1', 'ADDR_LN_1', 'Primary address line including street number and name',
  'CONCAT_WS('' '', TRIM(house_no), TRIM(road_name))', 'Client Address', 'client_addr', 'House Number | Road Name', 'house_no | road_name',
  'House number | Road or street name', 'STRING | STRING', 'member', 'member',
  'CONCAT', 'CONCAT, TRIM', 0.90, 'MANUAL', 'test_client_c'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'ADDR_LN_1' AND tgt_table_physical_name = 'MBR_CNTCT' LIMIT 1;

-- Client D: CONCAT with TRIM
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER CONTACT', 'MBR_CNTCT', 'Address Line 1', 'ADDR_LN_1', 'Primary address line including street number and name',
  'CONCAT_WS('' '', TRIM(bldg_num), TRIM(street_nm))', 'Enrollee Addr', 'enrl_addr', 'Building Num | Street Nm', 'bldg_num | street_nm',
  'Building number | Street name', 'STRING | STRING', 'member', 'member',
  'CONCAT', 'CONCAT, TRIM', 0.88, 'MANUAL', 'test_client_d'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'ADDR_LN_1' AND tgt_table_physical_name = 'MBR_CNTCT' LIMIT 1;


-- ============================================================================
-- SCENARIO D: SOURCE KEY ID (SINGLE) - 4 Different Client Mappings
-- ============================================================================
-- Target: MBR_FNDTN.SRC_KEY_ID

-- Client A: TRIM
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER FOUNDATION', 'MBR_FNDTN', 'Source Key ID', 'SRC_KEY_ID', 'Source system unique identifier for the member',
  'TRIM(SAK_RECIP)', 'Recipient Base', 't_re_base', 'Recipient Key', 'SAK_RECIP',
  'Surrogate key for the recipient in source system', 'BIGINT', 'member', 'member',
  'SINGLE', 'TRIM', 0.95, 'MANUAL', 'test_client_a'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'SRC_KEY_ID' AND tgt_table_physical_name = 'MBR_FNDTN' LIMIT 1;

-- Client B: TRIM + CAST
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER FOUNDATION', 'MBR_FNDTN', 'Source Key ID', 'SRC_KEY_ID', 'Source system unique identifier for the member',
  'CAST(TRIM(member_id) AS STRING)', 'Patient Data', 'patient_data', 'Member ID', 'member_id',
  'Unique member identifier from patient system', 'BIGINT', 'member', 'member',
  'SINGLE', 'TRIM, CAST', 0.93, 'MANUAL', 'test_client_b'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'SRC_KEY_ID' AND tgt_table_physical_name = 'MBR_FNDTN' LIMIT 1;

-- Client C: TRIM
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER FOUNDATION', 'MBR_FNDTN', 'Source Key ID', 'SRC_KEY_ID', 'Source system unique identifier for the member',
  'TRIM(recip_key)', 'Member Master', 'mbr_master', 'Recipient Key', 'recip_key',
  'Key identifier for the recipient record', 'BIGINT', 'member', 'member',
  'SINGLE', 'TRIM', 0.92, 'MANUAL', 'test_client_c'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'SRC_KEY_ID' AND tgt_table_physical_name = 'MBR_FNDTN' LIMIT 1;

-- Client D: TRIM
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER FOUNDATION', 'MBR_FNDTN', 'Source Key ID', 'SRC_KEY_ID', 'Source system unique identifier for the member',
  'TRIM(mbr_key)', 'Enrollee File', 'enrollee_file', 'Member Key', 'mbr_key',
  'Member unique key identifier', 'BIGINT', 'member', 'member',
  'SINGLE', 'TRIM', 0.90, 'MANUAL', 'test_client_d'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'SRC_KEY_ID' AND tgt_table_physical_name = 'MBR_FNDTN' LIMIT 1;


-- ============================================================================
-- SCENARIO E: EFFECTIVE DATE (SINGLE) - 4 Different Client Mappings
-- ============================================================================
-- Target: MBR_ASSGN_PCP.SRC_EFF_DT

-- Client A
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER ASSIGNED PRIMARY CARE PHYSICIAN', 'MBR_ASSGN_PCP', 'Source Effective Date', 'SRC_EFF_DT', 'Date when the record became effective',
  'TRIM(DTE_EFFECTIVE)', 'Assignment', 't_assign', 'Effective Date', 'DTE_EFFECTIVE',
  'Date the assignment became effective', 'DATE', 'member', 'member',
  'SINGLE', 'TRIM', 0.94, 'MANUAL', 'test_client_a'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'SRC_EFF_DT' AND tgt_table_physical_name = 'MBR_ASSGN_PCP' LIMIT 1;

-- Client B
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER ASSIGNED PRIMARY CARE PHYSICIAN', 'MBR_ASSGN_PCP', 'Source Effective Date', 'SRC_EFF_DT', 'Date when the record became effective',
  'TRIM(eff_dt)', 'PCP Assign', 'pcp_assign', 'Eff Date', 'eff_dt',
  'Effective date of PCP assignment', 'DATE', 'member', 'member',
  'SINGLE', 'TRIM', 0.92, 'MANUAL', 'test_client_b'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'SRC_EFF_DT' AND tgt_table_physical_name = 'MBR_ASSGN_PCP' LIMIT 1;

-- Client C
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER ASSIGNED PRIMARY CARE PHYSICIAN', 'MBR_ASSGN_PCP', 'Source Effective Date', 'SRC_EFF_DT', 'Date when the record became effective',
  'TRIM(start_date)', 'Provider Assign', 'prov_assign', 'Start Date', 'start_date',
  'Start date of the provider assignment', 'DATE', 'member', 'member',
  'SINGLE', 'TRIM', 0.91, 'MANUAL', 'test_client_c'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'SRC_EFF_DT' AND tgt_table_physical_name = 'MBR_ASSGN_PCP' LIMIT 1;

-- Client D
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER ASSIGNED PRIMARY CARE PHYSICIAN', 'MBR_ASSGN_PCP', 'Source Effective Date', 'SRC_EFF_DT', 'Date when the record became effective',
  'TRIM(coverage_start)', 'Enrollment', 'enrollment', 'Coverage Start', 'coverage_start',
  'Date coverage starts', 'DATE', 'member', 'member',
  'SINGLE', 'TRIM', 0.89, 'MANUAL', 'test_client_d'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'SRC_EFF_DT' AND tgt_table_physical_name = 'MBR_ASSGN_PCP' LIMIT 1;


-- ============================================================================
-- SCENARIO F: MEDICARE UNION (UNION) - 3 Historical Patterns
-- ============================================================================
-- Target: MBR_FNDTN.SRC_KEY_ID (via union of Part A/B/D)

-- Client A: Union of 3 Medicare parts
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER FOUNDATION', 'MBR_FNDTN', 'Source Key ID', 'SRC_KEY_ID', 'Source system unique identifier for the member',
  'SELECT TRIM(parta_id) FROM mc_part_a UNION ALL SELECT TRIM(partb_id) FROM mc_part_b UNION ALL SELECT TRIM(partd_id) FROM mc_part_d',
  'Medicare Part A | Medicare Part B | Medicare Part D', 'mc_part_a | mc_part_b | mc_part_d',
  'Part A ID | Part B ID | Part D ID', 'parta_id | partb_id | partd_id',
  'Medicare Part A beneficiary ID | Medicare Part B beneficiary ID | Medicare Part D member ID',
  'STRING | STRING | STRING', 'member', 'member',
  'UNION', 'UNION, TRIM', 0.90, 'MANUAL', 'test_client_a'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'SRC_KEY_ID' AND tgt_table_physical_name = 'MBR_FNDTN' LIMIT 1;

-- Client B: Union pattern
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER FOUNDATION', 'MBR_FNDTN', 'Source Key ID', 'SRC_KEY_ID', 'Source system unique identifier for the member',
  'SELECT TRIM(medicare_a_id) FROM medicare_a UNION ALL SELECT TRIM(medicare_b_id) FROM medicare_b UNION ALL SELECT TRIM(medicare_d_id) FROM medicare_d',
  'Medicare A | Medicare B | Medicare D', 'medicare_a | medicare_b | medicare_d',
  'Medicare A ID | Medicare B ID | Medicare D ID', 'medicare_a_id | medicare_b_id | medicare_d_id',
  'Medicare Part A identifier | Medicare Part B identifier | Medicare Part D identifier',
  'STRING | STRING | STRING', 'member', 'member',
  'UNION', 'UNION, TRIM', 0.88, 'MANUAL', 'test_client_b'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'SRC_KEY_ID' AND tgt_table_physical_name = 'MBR_FNDTN' LIMIT 1;

-- Client C: Union pattern
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by
)
SELECT 
  semantic_field_id, 'MEMBER FOUNDATION', 'MBR_FNDTN', 'Source Key ID', 'SRC_KEY_ID', 'Source system unique identifier for the member',
  'SELECT TRIM(mcare_a) FROM mcare_parta UNION ALL SELECT TRIM(mcare_b) FROM mcare_partb UNION ALL SELECT TRIM(mcare_d) FROM mcare_partd',
  'MCare Part A | MCare Part B | MCare Part D', 'mcare_parta | mcare_partb | mcare_partd',
  'MCare A | MCare B | MCare D', 'mcare_a | mcare_b | mcare_d',
  'Medicare A beneficiary | Medicare B beneficiary | Medicare D beneficiary',
  'STRING | STRING | STRING', 'member', 'member',
  'UNION', 'UNION, TRIM', 0.86, 'MANUAL', 'test_client_c'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'SRC_KEY_ID' AND tgt_table_physical_name = 'MBR_FNDTN' LIMIT 1;


-- ============================================================================
-- SCENARIO G: JOIN/LOOKUP PATTERNS - 3 Historical Patterns with join_metadata
-- ============================================================================
-- Target: MBR_CNTCT.MBR_SK (lookup to member foundation)
-- These patterns include join_metadata for template UI testing

-- Client A: Simple lookup join
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by,
  join_metadata
)
SELECT 
  semantic_field_id, 'MEMBER CONTACT', 'MBR_CNTCT', 'Member SK', 'MBR_SK', 'Unique identifier for a given member',
  'SELECT mf.MBR_SK FROM t_re_base b JOIN mbr_fndtn mf ON b.SAK_RECIP = mf.SRC_KEY_ID WHERE mf.CURR_REC_IND=''1''',
  'Recipient Base | Member Foundation', 't_re_base | mbr_fndtn',
  'Recipient Key', 'SAK_RECIP',
  'Surrogate key for the recipient to join to member foundation', 'BIGINT', 'member', 'member',
  'JOIN', 'LOOKUP, JOIN', 0.92, 'MANUAL', 'test_client_a',
  '{
    "patternType": "JOIN_LOOKUP",
    "outputColumn": "MBR_SK",
    "outputTable": "mbr_fndtn",
    "outputAlias": "mf",
    "userSourceTable": {
      "originalName": "t_re_base",
      "alias": "b",
      "description": "Primary recipient base table"
    },
    "joins": [
      {
        "joinType": "INNER",
        "targetTable": {
          "name": "mbr_fndtn",
          "alias": "mf",
          "isSharedSilver": true
        },
        "conditions": [
          {
            "type": "column_match",
            "sourceColumn": "SAK_RECIP",
            "sourceDescription": "Recipient surrogate key",
            "targetColumn": "SRC_KEY_ID",
            "targetDescription": "Source system key ID"
          }
        ]
      }
    ],
    "whereFilters": ["mf.CURR_REC_IND=''1''"],
    "userColumnsToMap": [
      {
        "placeholder": "SAK_RECIP",
        "description": "Recipient key to join to mbr_fndtn.SRC_KEY_ID",
        "required": true,
        "joinTarget": "mbr_fndtn.SRC_KEY_ID"
      }
    ],
    "userTablesToMap": [
      {
        "placeholder": "t_re_base",
        "description": "Primary source table with member info",
        "required": true
      }
    ],
    "sharedSilverTables": [
      {
        "name": "mbr_fndtn",
        "description": "Member Foundation lookup",
        "keyColumn": "SRC_KEY_ID"
      }
    ]
  }'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'MBR_SK' AND tgt_table_physical_name = 'MBR_CNTCT' LIMIT 1;

-- Client B: Similar lookup join
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by,
  join_metadata
)
SELECT 
  semantic_field_id, 'MEMBER CONTACT', 'MBR_CNTCT', 'Member SK', 'MBR_SK', 'Unique identifier for a given member',
  'SELECT mf.MBR_SK FROM patient_demo p JOIN mbr_fndtn mf ON p.patient_id = mf.SRC_KEY_ID WHERE mf.CURR_REC_IND=''1''',
  'Patient Demographics | Member Foundation', 'patient_demo | mbr_fndtn',
  'Patient ID', 'patient_id',
  'Patient identifier to join to member foundation', 'BIGINT', 'member', 'member',
  'JOIN', 'LOOKUP, JOIN', 0.90, 'MANUAL', 'test_client_b',
  '{
    "patternType": "JOIN_LOOKUP",
    "outputColumn": "MBR_SK",
    "outputTable": "mbr_fndtn",
    "outputAlias": "mf",
    "userSourceTable": {
      "originalName": "patient_demo",
      "alias": "p",
      "description": "Patient demographics table"
    },
    "joins": [
      {
        "joinType": "INNER",
        "targetTable": {
          "name": "mbr_fndtn",
          "alias": "mf",
          "isSharedSilver": true
        },
        "conditions": [
          {
            "type": "column_match",
            "sourceColumn": "patient_id",
            "sourceDescription": "Patient identifier",
            "targetColumn": "SRC_KEY_ID",
            "targetDescription": "Source system key ID"
          }
        ]
      }
    ],
    "whereFilters": ["mf.CURR_REC_IND=''1''"],
    "userColumnsToMap": [
      {
        "placeholder": "patient_id",
        "description": "Patient key to join to mbr_fndtn.SRC_KEY_ID",
        "required": true,
        "joinTarget": "mbr_fndtn.SRC_KEY_ID"
      }
    ],
    "userTablesToMap": [
      {
        "placeholder": "patient_demo",
        "description": "Patient demographics source table",
        "required": true
      }
    ],
    "sharedSilverTables": [
      {
        "name": "mbr_fndtn",
        "description": "Member Foundation lookup",
        "keyColumn": "SRC_KEY_ID"
      }
    ]
  }'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'MBR_SK' AND tgt_table_physical_name = 'MBR_CNTCT' LIMIT 1;

-- Client C: Lookup join with additional filter
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_tables_physical, source_columns, source_columns_physical,
  source_descriptions, source_datatypes, source_domain, target_domain,
  source_relationship_type, transformations_applied, confidence_score, mapping_source, mapped_by,
  join_metadata
)
SELECT 
  semantic_field_id, 'MEMBER CONTACT', 'MBR_CNTCT', 'Member SK', 'MBR_SK', 'Unique identifier for a given member',
  'SELECT mf.MBR_SK FROM enrollee_file e JOIN mbr_fndtn mf ON e.mbr_key = mf.SRC_KEY_ID WHERE mf.CURR_REC_IND=''1''',
  'Enrollee File | Member Foundation', 'enrollee_file | mbr_fndtn',
  'Member Key', 'mbr_key',
  'Member key identifier to join to member foundation', 'BIGINT', 'member', 'member',
  'JOIN', 'LOOKUP, JOIN', 0.88, 'MANUAL', 'test_client_c',
  '{
    "patternType": "JOIN_LOOKUP",
    "outputColumn": "MBR_SK",
    "outputTable": "mbr_fndtn",
    "outputAlias": "mf",
    "userSourceTable": {
      "originalName": "enrollee_file",
      "alias": "e",
      "description": "Enrollee file table"
    },
    "joins": [
      {
        "joinType": "INNER",
        "targetTable": {
          "name": "mbr_fndtn",
          "alias": "mf",
          "isSharedSilver": true
        },
        "conditions": [
          {
            "type": "column_match",
            "sourceColumn": "mbr_key",
            "sourceDescription": "Member key identifier",
            "targetColumn": "SRC_KEY_ID",
            "targetDescription": "Source system key ID"
          }
        ]
      }
    ],
    "whereFilters": ["mf.CURR_REC_IND=''1''"],
    "userColumnsToMap": [
      {
        "placeholder": "mbr_key",
        "description": "Member key to join to mbr_fndtn.SRC_KEY_ID",
        "required": true,
        "joinTarget": "mbr_fndtn.SRC_KEY_ID"
      }
    ],
    "userTablesToMap": [
      {
        "placeholder": "enrollee_file",
        "description": "Enrollee source table",
        "required": true
      }
    ],
    "sharedSilverTables": [
      {
        "name": "mbr_fndtn",
        "description": "Member Foundation lookup",
        "keyColumn": "SRC_KEY_ID"
      }
    ]
  }'
FROM ${CATALOG_SCHEMA}.semantic_fields 
WHERE tgt_column_physical_name = 'MBR_SK' AND tgt_table_physical_name = 'MBR_CNTCT' LIMIT 1;


-- ============================================================================
-- PART 2: UNMAPPED_FIELDS - Test Cases to Match Against Patterns
-- ============================================================================


-- ============================================================================
-- TEST CASE SET 1: Single Field Mappings
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_table_physical_name, src_column_name, src_column_physical_name,
  src_physical_datatype, src_comments, domain, uploaded_by
) VALUES
('Member Demographics', 'mbr_demographics', 'Given Name', 'given_nm', 'STRING',
 'The given name or first name of the member from demographics system', 'member', 'test_user'),
('Member Demographics', 'mbr_demographics', 'Family Name', 'family_nm', 'STRING',
 'The family name or surname of the member', 'member', 'test_user'),
('Member Demographics', 'mbr_demographics', 'Member Key', 'mbr_key_id', 'BIGINT',
 'Unique identifier for the member in the source system', 'member', 'test_user'),
('PCP Assignment', 'pcp_assignment', 'Assignment Start', 'assign_start_dt', 'DATE',
 'The date when the PCP assignment became effective', 'member', 'test_user'),
('Member Demographics', 'mbr_demographics', 'First', 'first', 'STRING',
 'Member first name field', 'member', 'test_user'),
('Member Demographics', 'mbr_demographics', 'Middle Initial', 'mid_init', 'STRING',
 'Middle initial of the member', 'member', 'test_user');


-- ============================================================================
-- TEST CASE SET 2: CONCAT Mappings (Address)
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_table_physical_name, src_column_name, src_column_physical_name,
  src_physical_datatype, src_comments, domain, uploaded_by
) VALUES
('Address Info', 'address_info', 'Street Number', 'st_num', 'STRING',
 'The street number portion of the address', 'member', 'test_user'),
('Address Info', 'address_info', 'Street Name', 'st_name', 'STRING',
 'The street name portion of the member address', 'member', 'test_user'),
('Address Info', 'address_info', 'Full Street Address', 'full_addr', 'STRING',
 'Complete street address line with number and name', 'member', 'test_user'),
('Address Info', 'address_info', 'City Name', 'city_nm', 'STRING',
 'City name for the member address', 'member', 'test_user');


-- ============================================================================
-- TEST CASE SET 3: UNION Mappings (Medicare)
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_table_physical_name, src_column_name, src_column_physical_name,
  src_physical_datatype, src_comments, domain, uploaded_by
) VALUES
('Medicare Part A Eligibility', 'mcare_elig_a', 'Part A Beneficiary ID', 'part_a_bene_id', 'STRING',
 'Medicare Part A beneficiary identifier', 'member', 'test_user'),
('Medicare Part B Eligibility', 'mcare_elig_b', 'Part B Member ID', 'part_b_mbr_id', 'STRING',
 'Medicare Part B member identifier', 'member', 'test_user'),
('Medicare Part D Pharmacy', 'mcare_pharm_d', 'Part D Enrollee ID', 'part_d_enrl_id', 'STRING',
 'Medicare Part D pharmacy benefit enrollee ID', 'member', 'test_user');


-- ============================================================================
-- TEST CASE SET 4: JOIN/LOOKUP Mappings
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_table_physical_name, src_column_name, src_column_physical_name,
  src_physical_datatype, src_comments, domain, uploaded_by
) VALUES
-- Should match MBR_SK JOIN patterns (3 historical with join_metadata)
('Member Base', 'member_base', 'Recipient Key', 'recip_key', 'BIGINT',
 'Recipient surrogate key used to join to member foundation tables', 'member', 'test_user'),
('Member Base', 'member_base', 'Current Record Flag', 'curr_rec_ind', 'STRING',
 'Indicator for current record status', 'member', 'test_user');


-- ============================================================================
-- TEST CASE SET 5: Different Domain (Claims)
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_table_physical_name, src_column_name, src_column_physical_name,
  src_physical_datatype, src_comments, domain, uploaded_by
) VALUES
('Claims Header', 'claims_header', 'Member ID', 'clm_mbr_id', 'STRING',
 'Member identifier on the claim record', 'claims', 'test_user'),
('Claims Header', 'claims_header', 'Service Start Date', 'svc_start_dt', 'DATE',
 'Date the service was rendered', 'claims', 'test_user'),
('Claims Header', 'claims_header', 'Service Location Address', 'svc_addr', 'STRING',
 'Street address where service was provided', 'claims', 'test_user');


-- ============================================================================
-- TEST CASE SET 6: Edge Cases
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_table_physical_name, src_column_name, src_column_physical_name,
  src_physical_datatype, src_comments, domain, uploaded_by
) VALUES
('Misc Data', 'misc_data', 'Name', 'name_field', 'STRING',
 'Name field', 'member', 'test_user'),
('Misc Data', 'misc_data', 'Unknown Field', 'unk_fld', 'STRING',
 '', 'member', 'test_user'),
('Provider Data', 'provider_data', 'NPI Number', 'npi', 'STRING',
 'National Provider Identifier 10-digit number', 'provider', 'test_user');


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check mapped_fields patterns by target
-- SELECT tgt_column_physical_name, tgt_table_physical_name, 
--        COUNT(*) as pattern_count,
--        COLLECT_LIST(transformations_applied) as transforms
-- FROM ${CATALOG_SCHEMA}.mapped_fields 
-- WHERE mapped_by LIKE 'test_client_%'
-- GROUP BY tgt_column_physical_name, tgt_table_physical_name
-- ORDER BY pattern_count DESC;

-- Check unmapped_fields test cases
-- SELECT src_column_physical_name, src_comments, domain
-- FROM ${CATALOG_SCHEMA}.unmapped_fields
-- WHERE uploaded_by = 'test_user'
-- ORDER BY domain, src_table_physical_name;
