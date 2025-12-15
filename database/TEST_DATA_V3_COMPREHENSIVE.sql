-- ============================================================================
-- V3 COMPREHENSIVE TEST DATA
-- ============================================================================
-- 
-- Updated for new unmapped_fields schema with:
--   - mapping_status (PENDING, MAPPED, ARCHIVED)
--   - mapped_field_id (FK reference when MAPPED)
--   - source_semantic_field (auto-generated for vector search)
--
-- Test Scenarios:
--   A. Single-field mappings (basic transformations)
--   B. Multi-field CONCAT mappings (combining columns)
--   C. UNION patterns (combining rows from different sources)
--   D. JOIN patterns (silver table lookups)
--   E. Source-to-source JOIN patterns (joining source tables)
--   F. Frequency boosting (multiple similar patterns)
--   G. Transformation voting (different transform combos)
--   H. Domain-aware matching
--
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema
-- ============================================================================


-- ============================================================================
-- STEP 1: CLEAN EXISTING DATA
-- ============================================================================

DELETE FROM ${CATALOG_SCHEMA}.mapped_fields WHERE mapped_by = 'test@gainwell.com';
DELETE FROM ${CATALOG_SCHEMA}.unmapped_fields WHERE uploaded_by = 'test@gainwell.com';


-- ============================================================================
-- STEP 2: INSERT UNMAPPED FIELDS (Source fields for testing)
-- ============================================================================
-- These represent source system columns that need to be mapped
-- Status: PENDING = available to map, MAPPED = already used, ARCHIVED = hidden

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name, src_table_physical_name,
    src_column_name, src_column_physical_name,
    src_nullable, src_physical_datatype, src_comments, domain,
    mapping_status, mapped_field_id, uploaded_by
) VALUES

-- ============================================================================
-- MEMBER DOMAIN - Core member/enrollment fields
-- ============================================================================

-- Member Name Fields (for testing CONCAT patterns)
('Member Demographics', 'member_demographics', 'First Name', 'first_name', 'NO', 'STRING', 
 'Member legal first name as recorded in enrollment', 'member', 'PENDING', NULL, 'test@gainwell.com'),

('Member Demographics', 'member_demographics', 'Last Name', 'last_name', 'NO', 'STRING', 
 'Member legal surname/family name', 'member', 'PENDING', NULL, 'test@gainwell.com'),

('Member Demographics', 'member_demographics', 'Middle Initial', 'middle_init', 'YES', 'STRING', 
 'Member middle name initial', 'member', 'PENDING', NULL, 'test@gainwell.com'),

('Member Demographics', 'member_demographics', 'Date of Birth', 'dob', 'NO', 'DATE', 
 'Member date of birth for age calculation', 'member', 'PENDING', NULL, 'test@gainwell.com'),

('Member Demographics', 'member_demographics', 'Gender Code', 'gender_cd', 'YES', 'STRING', 
 'Member gender M/F/U code', 'member', 'PENDING', NULL, 'test@gainwell.com'),

('Member Demographics', 'member_demographics', 'Member ID', 'member_id', 'NO', 'STRING', 
 'Unique member identifier in source system', 'member', 'PENDING', NULL, 'test@gainwell.com'),

-- Member Address Fields (for testing multi-field address patterns)
('Member Address', 'member_address', 'Street Number', 'street_num', 'YES', 'STRING', 
 'Street number portion of address', 'member', 'PENDING', NULL, 'test@gainwell.com'),

('Member Address', 'member_address', 'Street Name', 'street_name', 'YES', 'STRING', 
 'Street name portion of mailing address', 'member', 'PENDING', NULL, 'test@gainwell.com'),

('Member Address', 'member_address', 'City Name', 'city', 'YES', 'STRING', 
 'City of residence', 'member', 'PENDING', NULL, 'test@gainwell.com'),

('Member Address', 'member_address', 'State Code', 'state_cd', 'YES', 'STRING', 
 'Two letter state abbreviation', 'member', 'PENDING', NULL, 'test@gainwell.com'),

('Member Address', 'member_address', 'ZIP Code', 'zip_code', 'YES', 'STRING', 
 'Five digit postal ZIP code', 'member', 'PENDING', NULL, 'test@gainwell.com'),

-- Member Enrollment Fields (for testing LOOKUP/JOIN patterns)
('Member Enrollment', 'member_enrollment', 'Plan Code', 'plan_cd', 'NO', 'STRING', 
 'Health plan code for member enrollment', 'member', 'PENDING', NULL, 'test@gainwell.com'),

('Member Enrollment', 'member_enrollment', 'Enrollment Key', 'enroll_key', 'NO', 'BIGINT', 
 'Surrogate key for enrollment record', 'member', 'PENDING', NULL, 'test@gainwell.com'),

('Member Enrollment', 'member_enrollment', 'Effective Date', 'eff_dt', 'NO', 'DATE', 
 'Coverage effective start date', 'member', 'PENDING', NULL, 'test@gainwell.com'),

('Member Enrollment', 'member_enrollment', 'Term Date', 'term_dt', 'YES', 'DATE', 
 'Coverage termination date if applicable', 'member', 'PENDING', NULL, 'test@gainwell.com'),

-- ============================================================================
-- CLAIMS DOMAIN - Medical claims fields
-- ============================================================================

('Claims Header', 'claims_header', 'Claim Number', 'claim_nbr', 'NO', 'STRING', 
 'Unique claim identifier', 'claims', 'PENDING', NULL, 'test@gainwell.com'),

('Claims Header', 'claims_header', 'Service Date', 'svc_dt', 'NO', 'DATE', 
 'Date of service on claim', 'claims', 'PENDING', NULL, 'test@gainwell.com'),

('Claims Header', 'claims_header', 'Billed Amount', 'billed_amt', 'NO', 'DECIMAL', 
 'Total amount billed by provider', 'claims', 'PENDING', NULL, 'test@gainwell.com'),

('Claims Header', 'claims_header', 'Paid Amount', 'paid_amt', 'YES', 'DECIMAL', 
 'Amount paid after adjudication', 'claims', 'PENDING', NULL, 'test@gainwell.com'),

('Claims Header', 'claims_header', 'Provider NPI', 'prov_npi', 'YES', 'STRING', 
 'National Provider Identifier', 'claims', 'PENDING', NULL, 'test@gainwell.com'),

('Claims Detail', 'claims_detail', 'Procedure Code', 'proc_cd', 'NO', 'STRING', 
 'CPT or HCPCS procedure code', 'claims', 'PENDING', NULL, 'test@gainwell.com'),

('Claims Detail', 'claims_detail', 'Diagnosis Code', 'diag_cd', 'NO', 'STRING', 
 'ICD-10 diagnosis code', 'claims', 'PENDING', NULL, 'test@gainwell.com'),

-- ============================================================================
-- PROVIDER DOMAIN - Provider information
-- ============================================================================

('Provider Master', 'provider_master', 'Provider NPI', 'provider_npi', 'NO', 'STRING', 
 'National Provider Identifier 10-digit', 'provider', 'PENDING', NULL, 'test@gainwell.com'),

('Provider Master', 'provider_master', 'Provider First Name', 'prov_first_name', 'YES', 'STRING', 
 'Provider first name for individual providers', 'provider', 'PENDING', NULL, 'test@gainwell.com'),

('Provider Master', 'provider_master', 'Provider Last Name', 'prov_last_name', 'YES', 'STRING', 
 'Provider last name or organization name', 'provider', 'PENDING', NULL, 'test@gainwell.com'),

('Provider Master', 'provider_master', 'Provider Specialty', 'specialty_cd', 'YES', 'STRING', 
 'Provider specialty code', 'provider', 'PENDING', NULL, 'test@gainwell.com'),

-- ============================================================================
-- EMPLOYEE DOMAIN - For source-to-source JOIN testing
-- ============================================================================

('Employee', 'employee', 'Employee ID', 'emp_id', 'NO', 'BIGINT', 
 'Unique employee identifier', 'employee', 'PENDING', NULL, 'test@gainwell.com'),

('Employee', 'employee', 'Position Title', 'position_title', 'YES', 'STRING', 
 'Job title of the employee', 'employee', 'PENDING', NULL, 'test@gainwell.com'),

('Employee', 'employee', 'Department Code', 'dept_cd', 'NO', 'STRING', 
 'Department code for employee', 'employee', 'PENDING', NULL, 'test@gainwell.com'),

('Department', 'department', 'Department Code', 'dept_cd', 'NO', 'STRING', 
 'Unique department identifier', 'employee', 'PENDING', NULL, 'test@gainwell.com'),

('Department', 'department', 'Department Name', 'dept_name', 'NO', 'STRING', 
 'Full name of the department', 'employee', 'PENDING', NULL, 'test@gainwell.com'),

('Job Level', 'job_level', 'Level Code', 'level_cd', 'NO', 'STRING', 
 'Job level/grade code', 'employee', 'PENDING', NULL, 'test@gainwell.com'),

('Job Level', 'job_level', 'Level Title', 'level_title', 'NO', 'STRING', 
 'Job level title description', 'employee', 'PENDING', NULL, 'test@gainwell.com'),

-- ============================================================================
-- PHARMACY DOMAIN - For UNION pattern testing
-- ============================================================================

('Pharmacy Claims A', 'pharmacy_claims_a', 'Drug Code', 'drug_cd', 'NO', 'STRING', 
 'NDC drug code from Part A', 'pharmacy', 'PENDING', NULL, 'test@gainwell.com'),

('Pharmacy Claims B', 'pharmacy_claims_b', 'Medication Code', 'med_cd', 'NO', 'STRING', 
 'NDC medication code from Part B', 'pharmacy', 'PENDING', NULL, 'test@gainwell.com'),

('Pharmacy Claims D', 'pharmacy_claims_d', 'Rx Code', 'rx_cd', 'NO', 'STRING', 
 'NDC prescription code from Part D', 'pharmacy', 'PENDING', NULL, 'test@gainwell.com'),

-- ============================================================================
-- FINANCE DOMAIN - Different domain for disambiguation testing
-- ============================================================================

('Invoice', 'invoice', 'First Name', 'contact_first_name', 'YES', 'STRING', 
 'Contact first name on invoice (billing contact)', 'finance', 'PENDING', NULL, 'test@gainwell.com'),

('Invoice', 'invoice', 'Last Name', 'contact_last_name', 'YES', 'STRING', 
 'Contact last name on invoice (billing contact)', 'finance', 'PENDING', NULL, 'test@gainwell.com'),

('Invoice', 'invoice', 'Invoice Number', 'invoice_nbr', 'NO', 'STRING', 
 'Unique invoice identifier', 'finance', 'PENDING', NULL, 'test@gainwell.com');


-- ============================================================================
-- STEP 3: INSERT MAPPED FIELDS (Historical patterns for AI learning)
-- ============================================================================
-- These represent past mappings that the AI uses to learn patterns
-- Multiple mappings to same target = frequency boosting
-- Different transformations = voting

-- ============================================================================
-- SCENARIO A: Single-field mappings with various transformations
-- ============================================================================

-- A1: First Name -> First Name (3 patterns for frequency boost, different transforms)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    1 as semantic_field_id,
    'Member' as tgt_table_name, 'member' as tgt_table_physical_name,
    'First Name' as tgt_column_name, 'first_name' as tgt_column_physical_name,
    'Member legal first name' as tgt_comments,
    'SELECT TRIM(UPPER(first_name)) AS first_name' as source_expression,
    'Member Info' as source_tables, 'member_info' as source_tables_physical,
    'First Name' as source_columns, 'first_name' as source_columns_physical,
    'Member given name' as source_descriptions,
    'STRING' as source_datatypes, 'member' as source_domain, 'member' as target_domain,
    'SINGLE' as source_relationship_type,
    'TRIM, UPPER' as transformations_applied,
    NULL as join_metadata,
    0.95 as confidence_score, 'AI_ASSISTED' as mapping_source,
    'Standard name formatting' as ai_reasoning, true as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    1 as semantic_field_id,
    'Member' as tgt_table_name, 'member' as tgt_table_physical_name,
    'First Name' as tgt_column_name, 'first_name' as tgt_column_physical_name,
    'Member legal first name' as tgt_comments,
    'SELECT TRIM(INITCAP(fname)) AS first_name' as source_expression,
    'Enrollment' as source_tables, 'enrollment' as source_tables_physical,
    'First Name' as source_columns, 'fname' as source_columns_physical,
    'Enrollee first name' as source_descriptions,
    'STRING' as source_datatypes, 'member' as source_domain, 'member' as target_domain,
    'SINGLE' as source_relationship_type,
    'TRIM, INITCAP' as transformations_applied,
    NULL as join_metadata,
    0.92 as confidence_score, 'AI_ASSISTED' as mapping_source,
    'Proper case formatting' as ai_reasoning, true as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    1 as semantic_field_id,
    'Member' as tgt_table_name, 'member' as tgt_table_physical_name,
    'First Name' as tgt_column_name, 'first_name' as tgt_column_physical_name,
    'Member legal first name' as tgt_comments,
    'SELECT TRIM(given_name) AS first_name' as source_expression,
    'Person' as source_tables, 'person' as source_tables_physical,
    'Given Name' as source_columns, 'given_name' as source_columns_physical,
    'Person given/first name' as source_descriptions,
    'STRING' as source_datatypes, 'member' as source_domain, 'member' as target_domain,
    'SINGLE' as source_relationship_type,
    'TRIM' as transformations_applied,
    NULL as join_metadata,
    0.88 as confidence_score, 'MANUAL' as mapping_source,
    'Simple trim only' as ai_reasoning, false as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;

-- A2: Last Name -> Last Name (2 patterns)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    2 as semantic_field_id,
    'Member' as tgt_table_name, 'member' as tgt_table_physical_name,
    'Last Name' as tgt_column_name, 'last_name' as tgt_column_physical_name,
    'Member legal surname' as tgt_comments,
    'SELECT TRIM(UPPER(last_name)) AS last_name' as source_expression,
    'Member Info' as source_tables, 'member_info' as source_tables_physical,
    'Last Name' as source_columns, 'last_name' as source_columns_physical,
    'Member family name' as source_descriptions,
    'STRING' as source_datatypes, 'member' as source_domain, 'member' as target_domain,
    'SINGLE' as source_relationship_type,
    'TRIM, UPPER' as transformations_applied,
    NULL as join_metadata,
    0.94 as confidence_score, 'AI_ASSISTED' as mapping_source,
    'Uppercase surname' as ai_reasoning, true as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    2 as semantic_field_id,
    'Member' as tgt_table_name, 'member' as tgt_table_physical_name,
    'Last Name' as tgt_column_name, 'last_name' as tgt_column_physical_name,
    'Member legal surname' as tgt_comments,
    'SELECT TRIM(surname) AS last_name' as source_expression,
    'Person' as source_tables, 'person' as source_tables_physical,
    'Surname' as source_columns, 'surname' as source_columns_physical,
    'Person surname' as source_descriptions,
    'STRING' as source_datatypes, 'member' as source_domain, 'member' as target_domain,
    'SINGLE' as source_relationship_type,
    'TRIM' as transformations_applied,
    NULL as join_metadata,
    0.90 as confidence_score, 'MANUAL' as mapping_source,
    NULL as ai_reasoning, false as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;


-- ============================================================================
-- SCENARIO B: Multi-field CONCAT patterns (2-3 fields combined)
-- ============================================================================

-- B1: Full Name = First + Last (3 patterns, different transforms)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    3 as semantic_field_id,
    'Member' as tgt_table_name, 'member' as tgt_table_physical_name,
    'Full Name' as tgt_column_name, 'full_name' as tgt_column_physical_name,
    'Member complete full name' as tgt_comments,
    'SELECT CONCAT_WS('' '', TRIM(UPPER(first_name)), TRIM(UPPER(last_name))) AS full_name' as source_expression,
    'Member Info | Member Info' as source_tables, 'member_info | member_info' as source_tables_physical,
    'First Name | Last Name' as source_columns, 'first_name | last_name' as source_columns_physical,
    'Member first name | Member last name' as source_descriptions,
    'STRING | STRING' as source_datatypes, 'member' as source_domain, 'member' as target_domain,
    'CONCAT' as source_relationship_type,
    'TRIM, UPPER, CONCAT' as transformations_applied,
    NULL as join_metadata,
    0.96 as confidence_score, 'AI_ASSISTED' as mapping_source,
    'Concatenate first and last name with space' as ai_reasoning, true as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    3 as semantic_field_id,
    'Member' as tgt_table_name, 'member' as tgt_table_physical_name,
    'Full Name' as tgt_column_name, 'full_name' as tgt_column_physical_name,
    'Member complete full name' as tgt_comments,
    'SELECT CONCAT_WS('' '', TRIM(INITCAP(fname)), TRIM(INITCAP(lname))) AS full_name' as source_expression,
    'Enrollment | Enrollment' as source_tables, 'enrollment | enrollment' as source_tables_physical,
    'First Name | Last Name' as source_columns, 'fname | lname' as source_columns_physical,
    'Enrollee first | Enrollee last' as source_descriptions,
    'STRING | STRING' as source_datatypes, 'member' as source_domain, 'member' as target_domain,
    'CONCAT' as source_relationship_type,
    'TRIM, INITCAP, CONCAT' as transformations_applied,
    NULL as join_metadata,
    0.93 as confidence_score, 'AI_ASSISTED' as mapping_source,
    'Proper case name combination' as ai_reasoning, true as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    3 as semantic_field_id,
    'Member' as tgt_table_name, 'member' as tgt_table_physical_name,
    'Full Name' as tgt_column_name, 'full_name' as tgt_column_physical_name,
    'Member complete full name' as tgt_comments,
    'SELECT CONCAT_WS('' '', TRIM(given_nm), TRIM(family_nm)) AS full_name' as source_expression,
    'Person | Person' as source_tables, 'person | person' as source_tables_physical,
    'Given Name | Family Name' as source_columns, 'given_nm | family_nm' as source_columns_physical,
    'Given name | Family name' as source_descriptions,
    'STRING | STRING' as source_datatypes, 'member' as source_domain, 'member' as target_domain,
    'CONCAT' as source_relationship_type,
    'TRIM, CONCAT' as transformations_applied,
    NULL as join_metadata,
    0.89 as confidence_score, 'MANUAL' as mapping_source,
    NULL as ai_reasoning, false as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;

-- B2: Full Address = Street Num + Street Name (2 patterns)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    4 as semantic_field_id,
    'Member' as tgt_table_name, 'member' as tgt_table_physical_name,
    'Address Line 1' as tgt_column_name, 'address_line_1' as tgt_column_physical_name,
    'Member street address first line' as tgt_comments,
    'SELECT CONCAT_WS('' '', TRIM(street_num), TRIM(UPPER(street_name))) AS address_line_1' as source_expression,
    'Member Address | Member Address' as source_tables, 'member_address | member_address' as source_tables_physical,
    'Street Number | Street Name' as source_columns, 'street_num | street_name' as source_columns_physical,
    'Street number | Street name' as source_descriptions,
    'STRING | STRING' as source_datatypes, 'member' as source_domain, 'member' as target_domain,
    'CONCAT' as source_relationship_type,
    'TRIM, UPPER, CONCAT' as transformations_applied,
    NULL as join_metadata,
    0.94 as confidence_score, 'AI_ASSISTED' as mapping_source,
    'Combine street number and name' as ai_reasoning, true as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    4 as semantic_field_id,
    'Member' as tgt_table_name, 'member' as tgt_table_physical_name,
    'Address Line 1' as tgt_column_name, 'address_line_1' as tgt_column_physical_name,
    'Member street address first line' as tgt_comments,
    'SELECT CONCAT_WS('' '', TRIM(addr_num), TRIM(addr_street)) AS address_line_1' as source_expression,
    'Location | Location' as source_tables, 'location | location' as source_tables_physical,
    'Address Number | Address Street' as source_columns, 'addr_num | addr_street' as source_columns_physical,
    'Address number | Street' as source_descriptions,
    'STRING | STRING' as source_datatypes, 'member' as source_domain, 'member' as target_domain,
    'CONCAT' as source_relationship_type,
    'TRIM, CONCAT' as transformations_applied,
    NULL as join_metadata,
    0.91 as confidence_score, 'MANUAL' as mapping_source,
    NULL as ai_reasoning, false as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;


-- ============================================================================
-- SCENARIO C: UNION patterns (combining from multiple sources)
-- ============================================================================

-- C1: Drug Code from multiple pharmacy sources
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    10 as semantic_field_id,
    'Pharmacy' as tgt_table_name, 'pharmacy' as tgt_table_physical_name,
    'Drug Code' as tgt_column_name, 'drug_code' as tgt_column_physical_name,
    'National Drug Code from all sources' as tgt_comments,
    'SELECT TRIM(drug_cd) AS drug_code FROM pharmacy_claims_a
UNION ALL
SELECT TRIM(med_cd) AS drug_code FROM pharmacy_claims_b
UNION ALL
SELECT TRIM(rx_cd) AS drug_code FROM pharmacy_claims_d' as source_expression,
    'Pharmacy A | Pharmacy B | Pharmacy D' as source_tables, 
    'pharmacy_claims_a | pharmacy_claims_b | pharmacy_claims_d' as source_tables_physical,
    'Drug Code | Medication Code | Rx Code' as source_columns, 
    'drug_cd | med_cd | rx_cd' as source_columns_physical,
    'Drug code Part A | Medication code Part B | Rx code Part D' as source_descriptions,
    'STRING | STRING | STRING' as source_datatypes, 'pharmacy' as source_domain, 'pharmacy' as target_domain,
    'UNION' as source_relationship_type,
    'TRIM, UNION' as transformations_applied,
    '{"is_union": true, "union_type": "UNION ALL", "source_count": 3}' as join_metadata,
    0.97 as confidence_score, 'AI_ASSISTED' as mapping_source,
    'Combine drug codes from all pharmacy parts' as ai_reasoning, true as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;


-- ============================================================================
-- SCENARIO D: JOIN patterns (lookup to silver/reference tables)
-- ============================================================================

-- D1: Plan Name lookup from reference table
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    11 as semantic_field_id,
    'Member Enrollment' as tgt_table_name, 'member_enrollment' as tgt_table_physical_name,
    'Plan Name' as tgt_column_name, 'plan_name' as tgt_column_physical_name,
    'Health plan name from reference lookup' as tgt_comments,
    'SELECT p.plan_name AS plan_name
FROM member_enrollment e
JOIN ref_plan p ON e.plan_cd = p.plan_cd' as source_expression,
    'Member Enrollment' as source_tables, 'member_enrollment' as source_tables_physical,
    'Plan Code' as source_columns, 'plan_cd' as source_columns_physical,
    'Health plan code' as source_descriptions,
    'STRING' as source_datatypes, 'member' as source_domain, 'member' as target_domain,
    'LOOKUP' as source_relationship_type,
    'LOOKUP' as transformations_applied,
    '{"is_lookup": true, "lookup_table": "ref_plan", "lookup_key": "plan_cd", "lookup_value": "plan_name"}' as join_metadata,
    0.95 as confidence_score, 'AI_ASSISTED' as mapping_source,
    'Lookup plan name from reference table' as ai_reasoning, true as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;

-- D2: Member surrogate key lookup
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    12 as semantic_field_id,
    'Member' as tgt_table_name, 'member' as tgt_table_physical_name,
    'Member SK' as tgt_column_name, 'member_sk' as tgt_column_physical_name,
    'Member surrogate key from dimension lookup' as tgt_comments,
    'SELECT m.member_sk AS member_sk
FROM source_member s
JOIN dim_member m ON s.member_id = m.member_id' as source_expression,
    'Source Member' as source_tables, 'source_member' as source_tables_physical,
    'Member ID' as source_columns, 'member_id' as source_columns_physical,
    'Source member identifier' as source_descriptions,
    'STRING' as source_datatypes, 'member' as source_domain, 'member' as target_domain,
    'LOOKUP' as source_relationship_type,
    'LOOKUP' as transformations_applied,
    '{"is_lookup": true, "lookup_table": "dim_member", "lookup_key": "member_id", "lookup_value": "member_sk"}' as join_metadata,
    0.96 as confidence_score, 'AI_ASSISTED' as mapping_source,
    'Lookup member SK from dimension' as ai_reasoning, true as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;


-- ============================================================================
-- SCENARIO E: Source-to-source JOIN patterns
-- ============================================================================

-- E1: Employee Title with Department (joining two source tables)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    20 as semantic_field_id,
    'Managing Employee' as tgt_table_name, 'managing_employee' as tgt_table_physical_name,
    'Title' as tgt_column_name, 'title' as tgt_column_physical_name,
    'Title of managing employee with department' as tgt_comments,
    'SELECT CONCAT_WS('' - '', TRIM(d.dept_name), TRIM(e.position_title)) AS title
FROM employee e
INNER JOIN department d ON e.dept_cd = d.dept_cd' as source_expression,
    'Employee | Department' as source_tables, 'employee | department' as source_tables_physical,
    'Position Title | Department Name' as source_columns, 'position_title | dept_name' as source_columns_physical,
    'Job title | Department name' as source_descriptions,
    'STRING | STRING' as source_datatypes, 'employee' as source_domain, 'employee' as target_domain,
    'JOIN' as source_relationship_type,
    'TRIM, CONCAT, JOIN' as transformations_applied,
    '{"is_source_join": true, "join_type": "INNER", "source_tables": ["employee", "department"], "primary_table": "employee", "join_conditions": [{"left_table": "employee", "left_alias": "e", "left_column": "dept_cd", "right_table": "department", "right_alias": "d", "right_column": "dept_cd"}], "select_columns": [{"table": "department", "alias": "d", "column": "dept_name"}, {"table": "employee", "alias": "e", "column": "position_title"}]}' as join_metadata,
    0.94 as confidence_score, 'AI_ASSISTED' as mapping_source,
    'Join employee with department for full title' as ai_reasoning, true as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;

-- E2: Another source-to-source join pattern (for boosting)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    20 as semantic_field_id,
    'Managing Employee' as tgt_table_name, 'managing_employee' as tgt_table_physical_name,
    'Title' as tgt_column_name, 'title' as tgt_column_physical_name,
    'Title of managing employee with department' as tgt_comments,
    'SELECT CONCAT_WS('' - '', TRIM(UPPER(o.org_name)), TRIM(UPPER(p.role_title))) AS title
FROM person p
INNER JOIN organization o ON p.org_id = o.org_id' as source_expression,
    'Person | Organization' as source_tables, 'person | organization' as source_tables_physical,
    'Role Title | Org Name' as source_columns, 'role_title | org_name' as source_columns_physical,
    'Role/position title | Organization name' as source_descriptions,
    'STRING | STRING' as source_datatypes, 'employee' as source_domain, 'employee' as target_domain,
    'JOIN' as source_relationship_type,
    'TRIM, UPPER, CONCAT, JOIN' as transformations_applied,
    '{"is_source_join": true, "join_type": "INNER", "source_tables": ["person", "organization"], "primary_table": "person", "join_conditions": [{"left_table": "person", "left_alias": "p", "left_column": "org_id", "right_table": "organization", "right_alias": "o", "right_column": "org_id"}], "select_columns": [{"table": "organization", "alias": "o", "column": "org_name"}, {"table": "person", "alias": "p", "column": "role_title"}]}' as join_metadata,
    0.91 as confidence_score, 'AI_ASSISTED' as mapping_source,
    'Join person with org for title' as ai_reasoning, true as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;

-- E3: Level with title (another 2-table join)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    20 as semantic_field_id,
    'Managing Employee' as tgt_table_name, 'managing_employee' as tgt_table_physical_name,
    'Title' as tgt_column_name, 'title' as tgt_column_physical_name,
    'Title of managing employee with department' as tgt_comments,
    'SELECT CONCAT_WS('' - '', TRIM(l.level_title), TRIM(e.position_title)) AS title
FROM employee e
INNER JOIN job_level l ON e.level_cd = l.level_cd' as source_expression,
    'Employee | Job Level' as source_tables, 'employee | job_level' as source_tables_physical,
    'Position Title | Level Title' as source_columns, 'position_title | level_title' as source_columns_physical,
    'Position title | Job level title' as source_descriptions,
    'STRING | STRING' as source_datatypes, 'employee' as source_domain, 'employee' as target_domain,
    'JOIN' as source_relationship_type,
    'TRIM, CONCAT, JOIN' as transformations_applied,
    '{"is_source_join": true, "join_type": "INNER", "source_tables": ["employee", "job_level"], "primary_table": "employee", "join_conditions": [{"left_table": "employee", "left_alias": "e", "left_column": "level_cd", "right_table": "job_level", "right_alias": "l", "right_column": "level_cd"}], "select_columns": [{"table": "job_level", "alias": "l", "column": "level_title"}, {"table": "employee", "alias": "e", "column": "position_title"}]}' as join_metadata,
    0.89 as confidence_score, 'MANUAL' as mapping_source,
    NULL as ai_reasoning, false as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;


-- ============================================================================
-- SCENARIO F: Provider domain (different domain for disambiguation)
-- ============================================================================

-- F1: Provider Full Name (same pattern as member but different domain)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields
SELECT 
    30 as semantic_field_id,
    'Provider' as tgt_table_name, 'provider' as tgt_table_physical_name,
    'Provider Full Name' as tgt_column_name, 'provider_full_name' as tgt_column_physical_name,
    'Provider complete name' as tgt_comments,
    'SELECT CONCAT_WS('' '', TRIM(prov_first_name), TRIM(prov_last_name)) AS provider_full_name' as source_expression,
    'Provider Master | Provider Master' as source_tables, 'provider_master | provider_master' as source_tables_physical,
    'Provider First Name | Provider Last Name' as source_columns, 'prov_first_name | prov_last_name' as source_columns_physical,
    'Provider first name | Provider last name' as source_descriptions,
    'STRING | STRING' as source_datatypes, 'provider' as source_domain, 'provider' as target_domain,
    'CONCAT' as source_relationship_type,
    'TRIM, CONCAT' as transformations_applied,
    NULL as join_metadata,
    0.95 as confidence_score, 'AI_ASSISTED' as mapping_source,
    'Combine provider names' as ai_reasoning, true as ai_generated,
    'ACTIVE' as mapping_status, 'test@gainwell.com' as mapped_by,
    CURRENT_TIMESTAMP() as mapped_ts, NULL as updated_by, NULL as updated_ts;


-- ============================================================================
-- STEP 4: VERIFY DATA
-- ============================================================================

-- Count unmapped fields by status
SELECT 'Unmapped Fields' as table_name, mapping_status, COUNT(*) as count 
FROM ${CATALOG_SCHEMA}.unmapped_fields 
WHERE uploaded_by = 'test@gainwell.com'
GROUP BY mapping_status;

-- Count mapped fields by relationship type
SELECT 'Mapped Fields' as table_name, source_relationship_type, COUNT(*) as count 
FROM ${CATALOG_SCHEMA}.mapped_fields 
WHERE mapped_by = 'test@gainwell.com'
GROUP BY source_relationship_type;

-- Show pattern frequency (for boost testing)
SELECT 
    tgt_table_name || '.' || tgt_column_name as target_field,
    COUNT(*) as pattern_count,
    COLLECT_SET(transformations_applied) as unique_transforms
FROM ${CATALOG_SCHEMA}.mapped_fields 
WHERE mapped_by = 'test@gainwell.com'
GROUP BY tgt_table_name, tgt_column_name
ORDER BY pattern_count DESC;


-- ============================================================================
-- TEST SCENARIOS EXPECTED RESULTS
-- ============================================================================
-- 
-- When testing in the app with user test@gainwell.com:
--
-- TEST 1: Select "First Name" from member_demographics
--   Expected: Find 3 patterns to "First Name" with boost ~1.8x
--   Voted transforms: TRIM (3/3=100%), UPPER (1/3=33%), INITCAP (1/3=33%)
--   Winner: TRIM (majority vote)
--
-- TEST 2: Select "First Name" + "Last Name" from member_demographics
--   Expected: Find 3 patterns to "Full Name" (CONCAT patterns) with boost ~1.8x
--   Should show template with 2 slots
--
-- TEST 3: Select "Street Number" from member_address
--   Expected: Find 2 patterns to "Address Line 1" (CONCAT with street_name)
--   Should prompt to add "Street Name" to complete template
--
-- TEST 4: Select "Drug Code" from pharmacy_claims_a
--   Expected: Find UNION pattern for drug codes
--   Should show 3-way UNION template
--
-- TEST 5: Select "Plan Code" from member_enrollment
--   Expected: Find LOOKUP pattern
--   Should show join to ref_plan table
--
-- TEST 6: Select "Position Title" from employee
--   Expected: Find 3 source-to-source JOIN patterns with boost
--   Should show JOIN template with department/job_level options
--
-- TEST 7: Select "First Name" from invoice (finance domain)
--   Expected: Lower ranking than member domain matches
--   Domain signal should help disambiguate
--
-- ============================================================================

