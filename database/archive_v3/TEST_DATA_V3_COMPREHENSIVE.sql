-- ============================================================================
-- V3 COMPREHENSIVE TEST DATA
-- ============================================================================
-- 
-- Updated for new unmapped_fields schema with:
--   - mapping_status (PENDING, MAPPED, ARCHIVED)
--   - mapped_field_id (FK reference when MAPPED)
--   - source_semantic_field (auto-generated for vector search)
--
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema
-- ============================================================================


-- ============================================================================
-- STEP 1: CLEAN EXISTING DATA
-- ============================================================================

DELETE FROM ${CATALOG_SCHEMA}.mapped_fields WHERE mapped_by = 'test@gainwell.com';
DELETE FROM ${CATALOG_SCHEMA}.unmapped_fields WHERE uploaded_by = 'test@gainwell.com';


-- ============================================================================
-- STEP 2: INSERT UNMAPPED FIELDS
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name, src_table_physical_name,
    src_column_name, src_column_physical_name,
    src_nullable, src_physical_datatype, src_comments, domain,
    mapping_status, mapped_field_id, uploaded_by
) VALUES

-- MEMBER DOMAIN
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

-- Member Address
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

-- Member Enrollment
('Member Enrollment', 'member_enrollment', 'Plan Code', 'plan_cd', 'NO', 'STRING', 
 'Health plan code for member enrollment', 'member', 'PENDING', NULL, 'test@gainwell.com'),
('Member Enrollment', 'member_enrollment', 'Enrollment Key', 'enroll_key', 'NO', 'BIGINT', 
 'Surrogate key for enrollment record', 'member', 'PENDING', NULL, 'test@gainwell.com'),
('Member Enrollment', 'member_enrollment', 'Effective Date', 'eff_dt', 'NO', 'DATE', 
 'Coverage effective start date', 'member', 'PENDING', NULL, 'test@gainwell.com'),
('Member Enrollment', 'member_enrollment', 'Term Date', 'term_dt', 'YES', 'DATE', 
 'Coverage termination date if applicable', 'member', 'PENDING', NULL, 'test@gainwell.com'),

-- CLAIMS DOMAIN
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

-- PROVIDER DOMAIN
('Provider Master', 'provider_master', 'Provider NPI', 'provider_npi', 'NO', 'STRING', 
 'National Provider Identifier 10-digit', 'provider', 'PENDING', NULL, 'test@gainwell.com'),
('Provider Master', 'provider_master', 'Provider First Name', 'prov_first_name', 'YES', 'STRING', 
 'Provider first name for individual providers', 'provider', 'PENDING', NULL, 'test@gainwell.com'),
('Provider Master', 'provider_master', 'Provider Last Name', 'prov_last_name', 'YES', 'STRING', 
 'Provider last name or organization name', 'provider', 'PENDING', NULL, 'test@gainwell.com'),
('Provider Master', 'provider_master', 'Provider Specialty', 'specialty_cd', 'YES', 'STRING', 
 'Provider specialty code', 'provider', 'PENDING', NULL, 'test@gainwell.com'),

-- EMPLOYEE DOMAIN (for source-to-source JOIN testing)
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

-- PHARMACY DOMAIN (for UNION testing)
('Pharmacy Claims A', 'pharmacy_claims_a', 'Drug Code', 'drug_cd', 'NO', 'STRING', 
 'NDC drug code from Part A', 'pharmacy', 'PENDING', NULL, 'test@gainwell.com'),
('Pharmacy Claims B', 'pharmacy_claims_b', 'Medication Code', 'med_cd', 'NO', 'STRING', 
 'NDC medication code from Part B', 'pharmacy', 'PENDING', NULL, 'test@gainwell.com'),
('Pharmacy Claims D', 'pharmacy_claims_d', 'Rx Code', 'rx_cd', 'NO', 'STRING', 
 'NDC prescription code from Part D', 'pharmacy', 'PENDING', NULL, 'test@gainwell.com'),

-- FINANCE DOMAIN (different domain for disambiguation)
('Invoice', 'invoice', 'First Name', 'contact_first_name', 'YES', 'STRING', 
 'Contact first name on invoice (billing contact)', 'finance', 'PENDING', NULL, 'test@gainwell.com'),
('Invoice', 'invoice', 'Last Name', 'contact_last_name', 'YES', 'STRING', 
 'Contact last name on invoice (billing contact)', 'finance', 'PENDING', NULL, 'test@gainwell.com'),
('Invoice', 'invoice', 'Invoice Number', 'invoice_nbr', 'NO', 'STRING', 
 'Unique invoice identifier', 'finance', 'PENDING', NULL, 'test@gainwell.com');


-- ============================================================================
-- STEP 3: INSERT MAPPED FIELDS (Historical patterns)
-- ============================================================================

-- Define column list for reuse (27 columns, excluding auto-generated ones)
-- mapped_field_id = auto-generated
-- source_semantic_field = auto-generated

-- ============================================================================
-- SCENARIO A: Single-field mappings
-- ============================================================================

-- A1: First Name (3 patterns for frequency boost)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(1, 'Member', 'member', 'First Name', 'first_name', 'Member legal first name',
 'SELECT TRIM(UPPER(first_name)) AS first_name', 'Member Info', 'member_info',
 'First Name', 'first_name', 'Member given name', 'STRING', 'member', 'member',
 'SINGLE', 'TRIM, UPPER', NULL, 0.95, 'AI_ASSISTED', 'Standard name formatting', true,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(1, 'Member', 'member', 'First Name', 'first_name', 'Member legal first name',
 'SELECT TRIM(INITCAP(fname)) AS first_name', 'Enrollment', 'enrollment',
 'First Name', 'fname', 'Enrollee first name', 'STRING', 'member', 'member',
 'SINGLE', 'TRIM, INITCAP', NULL, 0.92, 'AI_ASSISTED', 'Proper case formatting', true,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(1, 'Member', 'member', 'First Name', 'first_name', 'Member legal first name',
 'SELECT TRIM(given_name) AS first_name', 'Person', 'person',
 'Given Name', 'given_name', 'Person given/first name', 'STRING', 'member', 'member',
 'SINGLE', 'TRIM', NULL, 0.88, 'MANUAL', 'Simple trim only', false,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);

-- A2: Last Name (2 patterns)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(2, 'Member', 'member', 'Last Name', 'last_name', 'Member legal surname',
 'SELECT TRIM(UPPER(last_name)) AS last_name', 'Member Info', 'member_info',
 'Last Name', 'last_name', 'Member family name', 'STRING', 'member', 'member',
 'SINGLE', 'TRIM, UPPER', NULL, 0.94, 'AI_ASSISTED', 'Uppercase surname', true,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(2, 'Member', 'member', 'Last Name', 'last_name', 'Member legal surname',
 'SELECT TRIM(surname) AS last_name', 'Person', 'person',
 'Surname', 'surname', 'Person surname', 'STRING', 'member', 'member',
 'SINGLE', 'TRIM', NULL, 0.90, 'MANUAL', NULL, false,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);


-- ============================================================================
-- SCENARIO B: Multi-field CONCAT patterns
-- ============================================================================

-- B1: Full Name = First + Last (3 patterns)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(3, 'Member', 'member', 'Full Name', 'full_name', 'Member complete full name',
 'SELECT CONCAT_WS('' '', TRIM(UPPER(first_name)), TRIM(UPPER(last_name))) AS full_name',
 'Member Info | Member Info', 'member_info | member_info',
 'First Name | Last Name', 'first_name | last_name', 'Member first name | Member last name',
 'STRING | STRING', 'member', 'member',
 'CONCAT', 'TRIM, UPPER, CONCAT', NULL, 0.96, 'AI_ASSISTED', 'Concatenate first and last name', true,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(3, 'Member', 'member', 'Full Name', 'full_name', 'Member complete full name',
 'SELECT CONCAT_WS('' '', TRIM(INITCAP(fname)), TRIM(INITCAP(lname))) AS full_name',
 'Enrollment | Enrollment', 'enrollment | enrollment',
 'First Name | Last Name', 'fname | lname', 'Enrollee first | Enrollee last',
 'STRING | STRING', 'member', 'member',
 'CONCAT', 'TRIM, INITCAP, CONCAT', NULL, 0.93, 'AI_ASSISTED', 'Proper case name combination', true,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(3, 'Member', 'member', 'Full Name', 'full_name', 'Member complete full name',
 'SELECT CONCAT_WS('' '', TRIM(given_nm), TRIM(family_nm)) AS full_name',
 'Person | Person', 'person | person',
 'Given Name | Family Name', 'given_nm | family_nm', 'Given name | Family name',
 'STRING | STRING', 'member', 'member',
 'CONCAT', 'TRIM, CONCAT', NULL, 0.89, 'MANUAL', NULL, false,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);

-- B2: Address Line 1 = Street Num + Street Name (2 patterns)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(4, 'Member', 'member', 'Address Line 1', 'address_line_1', 'Member street address',
 'SELECT CONCAT_WS('' '', TRIM(street_num), TRIM(UPPER(street_name))) AS address_line_1',
 'Member Address | Member Address', 'member_address | member_address',
 'Street Number | Street Name', 'street_num | street_name', 'Street number | Street name',
 'STRING | STRING', 'member', 'member',
 'CONCAT', 'TRIM, UPPER, CONCAT', NULL, 0.94, 'AI_ASSISTED', 'Combine street number and name', true,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(4, 'Member', 'member', 'Address Line 1', 'address_line_1', 'Member street address',
 'SELECT CONCAT_WS('' '', TRIM(addr_num), TRIM(addr_street)) AS address_line_1',
 'Location | Location', 'location | location',
 'Address Number | Address Street', 'addr_num | addr_street', 'Address number | Street',
 'STRING | STRING', 'member', 'member',
 'CONCAT', 'TRIM, CONCAT', NULL, 0.91, 'MANUAL', NULL, false,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);


-- ============================================================================
-- SCENARIO C: UNION pattern
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(10, 'Pharmacy', 'pharmacy', 'Drug Code', 'drug_code', 'National Drug Code from all sources',
 'SELECT TRIM(drug_cd) AS drug_code FROM pharmacy_claims_a UNION ALL SELECT TRIM(med_cd) FROM pharmacy_claims_b UNION ALL SELECT TRIM(rx_cd) FROM pharmacy_claims_d',
 'Pharmacy A | Pharmacy B | Pharmacy D', 'pharmacy_claims_a | pharmacy_claims_b | pharmacy_claims_d',
 'Drug Code | Medication Code | Rx Code', 'drug_cd | med_cd | rx_cd',
 'Drug code Part A | Medication code Part B | Rx code Part D',
 'STRING | STRING | STRING', 'pharmacy', 'pharmacy',
 'UNION', 'TRIM, UNION', '{"is_union": true, "union_type": "UNION ALL", "source_count": 3}',
 0.97, 'AI_ASSISTED', 'Combine drug codes from all pharmacy parts', true,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);


-- ============================================================================
-- SCENARIO D: LOOKUP patterns (silver table joins)
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(11, 'Member Enrollment', 'member_enrollment', 'Plan Name', 'plan_name', 'Health plan name from reference',
 'SELECT p.plan_name FROM member_enrollment e JOIN ref_plan p ON e.plan_cd = p.plan_cd',
 'Member Enrollment', 'member_enrollment',
 'Plan Code', 'plan_cd', 'Health plan code',
 'STRING', 'member', 'member',
 'LOOKUP', 'LOOKUP', '{"is_lookup": true, "lookup_table": "ref_plan", "lookup_key": "plan_cd", "lookup_value": "plan_name"}',
 0.95, 'AI_ASSISTED', 'Lookup plan name from reference table', true,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(12, 'Member', 'member', 'Member SK', 'member_sk', 'Member surrogate key from dimension',
 'SELECT m.member_sk FROM source_member s JOIN dim_member m ON s.member_id = m.member_id',
 'Source Member', 'source_member',
 'Member ID', 'member_id', 'Source member identifier',
 'STRING', 'member', 'member',
 'LOOKUP', 'LOOKUP', '{"is_lookup": true, "lookup_table": "dim_member", "lookup_key": "member_id", "lookup_value": "member_sk"}',
 0.96, 'AI_ASSISTED', 'Lookup member SK from dimension', true,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);


-- ============================================================================
-- SCENARIO E: Source-to-source JOIN patterns
-- ============================================================================

-- E1: Employee with Department (3 patterns for boost)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(20, 'Managing Employee', 'managing_employee', 'Title', 'title', 'Title of managing employee with department',
 'SELECT CONCAT_WS('' - '', TRIM(d.dept_name), TRIM(e.position_title)) AS title FROM employee e INNER JOIN department d ON e.dept_cd = d.dept_cd',
 'Employee | Department', 'employee | department',
 'Position Title | Department Name', 'position_title | dept_name', 'Job title | Department name',
 'STRING | STRING', 'employee', 'employee',
 'JOIN', 'TRIM, CONCAT, JOIN',
 '{"is_source_join": true, "join_type": "INNER", "source_tables": ["employee", "department"], "primary_table": "employee", "join_conditions": [{"left_table": "employee", "left_alias": "e", "left_column": "dept_cd", "right_table": "department", "right_alias": "d", "right_column": "dept_cd"}]}',
 0.94, 'AI_ASSISTED', 'Join employee with department for full title', true,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(20, 'Managing Employee', 'managing_employee', 'Title', 'title', 'Title of managing employee with department',
 'SELECT CONCAT_WS('' - '', TRIM(UPPER(o.org_name)), TRIM(UPPER(p.role_title))) AS title FROM person p INNER JOIN organization o ON p.org_id = o.org_id',
 'Person | Organization', 'person | organization',
 'Role Title | Org Name', 'role_title | org_name', 'Role/position title | Organization name',
 'STRING | STRING', 'employee', 'employee',
 'JOIN', 'TRIM, UPPER, CONCAT, JOIN',
 '{"is_source_join": true, "join_type": "INNER", "source_tables": ["person", "organization"], "primary_table": "person", "join_conditions": [{"left_table": "person", "left_alias": "p", "left_column": "org_id", "right_table": "organization", "right_alias": "o", "right_column": "org_id"}]}',
 0.91, 'AI_ASSISTED', 'Join person with org for title', true,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(20, 'Managing Employee', 'managing_employee', 'Title', 'title', 'Title of managing employee with department',
 'SELECT CONCAT_WS('' - '', TRIM(l.level_title), TRIM(e.position_title)) AS title FROM employee e INNER JOIN job_level l ON e.level_cd = l.level_cd',
 'Employee | Job Level', 'employee | job_level',
 'Position Title | Level Title', 'position_title | level_title', 'Position title | Job level title',
 'STRING | STRING', 'employee', 'employee',
 'JOIN', 'TRIM, CONCAT, JOIN',
 '{"is_source_join": true, "join_type": "INNER", "source_tables": ["employee", "job_level"], "primary_table": "employee", "join_conditions": [{"left_table": "employee", "left_alias": "e", "left_column": "level_cd", "right_table": "job_level", "right_alias": "l", "right_column": "level_cd"}]}',
 0.89, 'MANUAL', NULL, false,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);


-- ============================================================================
-- SCENARIO F: Provider domain (for domain disambiguation)
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id, tgt_table_name, tgt_table_physical_name,
    tgt_column_name, tgt_column_physical_name, tgt_comments,
    source_expression, source_tables, source_tables_physical,
    source_columns, source_columns_physical, source_descriptions,
    source_datatypes, source_domain, target_domain,
    source_relationship_type, transformations_applied, join_metadata,
    confidence_score, mapping_source, ai_reasoning, ai_generated,
    mapping_status, mapped_by, mapped_ts, updated_by, updated_ts
) VALUES
(30, 'Provider', 'provider', 'Provider Full Name', 'provider_full_name', 'Provider complete name',
 'SELECT CONCAT_WS('' '', TRIM(prov_first_name), TRIM(prov_last_name)) AS provider_full_name',
 'Provider Master | Provider Master', 'provider_master | provider_master',
 'Provider First Name | Provider Last Name', 'prov_first_name | prov_last_name',
 'Provider first name | Provider last name',
 'STRING | STRING', 'provider', 'provider',
 'CONCAT', 'TRIM, CONCAT', NULL, 0.95, 'AI_ASSISTED', 'Combine provider names', true,
 'ACTIVE', 'test@gainwell.com', CURRENT_TIMESTAMP(), NULL, NULL);


-- ============================================================================
-- STEP 4: VERIFY DATA
-- ============================================================================

SELECT 'Unmapped Fields' as table_name, mapping_status, COUNT(*) as count 
FROM ${CATALOG_SCHEMA}.unmapped_fields 
WHERE uploaded_by = 'test@gainwell.com'
GROUP BY mapping_status;

SELECT 'Mapped Fields' as table_name, source_relationship_type, COUNT(*) as count 
FROM ${CATALOG_SCHEMA}.mapped_fields 
WHERE mapped_by = 'test@gainwell.com'
GROUP BY source_relationship_type;

SELECT 
    tgt_table_name || '.' || tgt_column_name as target_field,
    COUNT(*) as pattern_count
FROM ${CATALOG_SCHEMA}.mapped_fields 
WHERE mapped_by = 'test@gainwell.com'
GROUP BY tgt_table_name, tgt_column_name
ORDER BY pattern_count DESC;


-- ============================================================================
-- TEST SCENARIOS
-- ============================================================================
-- 
-- TEST 1: Select "First Name" from member_demographics
--   Expected: 3 patterns to First Name, ~1.8x boost
--
-- TEST 2: Select "First Name" + "Last Name" from member_demographics
--   Expected: 3 CONCAT patterns to Full Name, 2-slot template
--
-- TEST 3: Select "Street Number" from member_address
--   Expected: 2 patterns to Address Line 1, prompts for street_name
--
-- TEST 4: Select "Drug Code" from pharmacy_claims_a
--   Expected: UNION pattern, 3-way template
--
-- TEST 5: Select "Plan Code" from member_enrollment
--   Expected: LOOKUP pattern with join
--
-- TEST 6: Select "Position Title" from employee
--   Expected: 3 JOIN patterns, ~1.8x boost, join slot needed
--
-- TEST 7: Select "First Name" from invoice (finance domain)
--   Expected: Lower ranking (finance != member domain)
--
-- ============================================================================
