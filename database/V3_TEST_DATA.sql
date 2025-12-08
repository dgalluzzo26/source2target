-- ============================================================================
-- V3 Test Data - Dummy Mapped Fields for AI Testing
-- ============================================================================
-- This script creates test mappings to populate mapped_fields for:
-- 1. Single column mappings with various transformations
-- 2. Multi-column mappings (concatenation)
-- 3. JOIN-based mappings (multiple source tables)
-- 4. UNION-based mappings (combining rows from multiple tables)
--
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema (e.g., oztest_dev.smartmapper)
-- ============================================================================

-- ============================================================================
-- SCENARIO 1: SIMPLE SINGLE-COLUMN MAPPINGS WITH TRANSFORMATIONS
-- ============================================================================

-- 1.1 Simple TRIM transformation - SSN
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  32, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Ssn Number', 'SSN_NUM', 'Social security number of the managing employee.',
  'TRIM(employee_source.emp_ssn)',
  'employee_source',
  'emp_ssn',
  'Employee social security number from source system',
  'VARCHAR(15)',
  'SINGLE', 'TRIM',
  0.95, 'AI', 'High confidence match based on SSN description similarity. TRIM applied to remove whitespace.', true, 'ACTIVE',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);

-- 1.2 UPPER + TRIM transformation - First Name  
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  44, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'First Name', 'FIRST_NM', 'First name of the managing employee.',
  'TRIM(UPPER(hr_employees.first_name))',
  'hr_employees',
  'first_name',
  'First name of the employee from HR system',
  'VARCHAR(100)',
  'SINGLE', 'TRIM, UPPER',
  0.92, 'AI', 'First name fields match semantically. Applied UPPER for standardization based on 12 similar past mappings.', true, 'ACTIVE',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);

-- 1.3 LOWER + TRIM transformation - Last Name
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  37, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Last Name', 'LAST_NM', 'Last name of the managing employ',
  'TRIM(INITCAP(hr_employees.surname))',
  'hr_employees',
  'surname',
  'Surname/family name of the employee',
  'VARCHAR(100)',
  'SINGLE', 'TRIM, INITCAP',
  0.89, 'AI', 'Surname maps to Last Name. INITCAP applied for proper name formatting.', true, 'ACTIVE',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);

-- 1.4 Date format transformation - DOB
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  34, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Date Of Birth', 'DOB', 'Date of birth of the managing employee.',
  'TO_DATE(personnel.birth_date, ''yyyy-MM-dd'')',
  'personnel',
  'birth_date',
  'Employee birth date in string format YYYY-MM-DD',
  'VARCHAR(10)',
  'SINGLE', 'TO_DATE',
  0.94, 'MANUAL', 'Date of birth fields match. Converted from string to DATE format.', false, 'ACTIVE',
  'admin@gainwell.com', CURRENT_TIMESTAMP()
);

-- 1.5 Simple direct mapping - State
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  48, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'State', 'ST', 'Two digit state code of the managing employee.',
  'UPPER(address_data.state_code)',
  'address_data',
  'state_code',
  'Two letter state abbreviation',
  'CHAR(2)',
  'SINGLE', 'UPPER',
  0.97, 'AI', 'Exact semantic match for state code. UPPER ensures consistency.', true, 'ACTIVE',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);

-- ============================================================================
-- SCENARIO 2: MULTI-COLUMN MAPPINGS (CONCATENATION)
-- ============================================================================

-- 2.1 Full Address - Concatenating address lines
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  39, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Address Street 1', 'ADDR_STR_1', 'Street address line one of the managing employee.',
  'CONCAT(TRIM(addr.street_num), '' '', TRIM(addr.street_name))',
  'addr',
  'street_num, street_name',
  'House/building number | Street name from address table',
  'VARCHAR(10), VARCHAR(100)',
  'SINGLE', 'TRIM, CONCAT',
  0.88, 'AI', 'Combined street number and name into single address line. Pattern seen in 8 previous mappings.', true, 'ACTIVE',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);

-- 2.2 Full Zip - Concatenating zip and zip+4
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  31, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Zipcode', 'ZIPCD', 'Five digit zip code of the managing employee.',
  'SUBSTR(location.postal_code, 1, 5)',
  'location',
  'postal_code',
  'Full postal code including extension (12345-6789 format)',
  'VARCHAR(10)',
  'SINGLE', 'SUBSTR',
  0.91, 'AI', 'Extracted 5-digit zip from full postal code using SUBSTR.', true, 'ACTIVE',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);

-- 2.3 Zip+4 extension
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  29, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Zipcode 4', 'ZIPCD_4', 'Four digit zip code extension of the managing employee.',
  'CASE WHEN LENGTH(location.postal_code) > 5 THEN SUBSTR(location.postal_code, 7, 4) ELSE NULL END',
  'location',
  'postal_code',
  'Full postal code including extension (12345-6789 format)',
  'VARCHAR(10)',
  'SINGLE', 'SUBSTR, CASE',
  0.85, 'AI', 'Extracted zip+4 extension with CASE to handle missing extensions.', true, 'ACTIVE',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);

-- ============================================================================
-- SCENARIO 3: JOIN-BASED MAPPINGS (Multiple Source Tables)
-- ============================================================================

-- 3.1 City from joined address table
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  35, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'City', 'CITY', 'City of the managing employee.',
  'TRIM(UPPER(a.city_name)) -- FROM employees e JOIN addresses a ON e.address_id = a.id',
  'employees, addresses',
  'city_name',
  'City name from address lookup table',
  'VARCHAR(100)',
  'JOIN', 'TRIM, UPPER',
  0.87, 'AI', 'City obtained by joining employees to addresses table. Applied standardization transforms.', true, 'ACTIVE',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);

-- 3.2 Title from reference table join
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  47, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Title', 'TITLE', 'The title of the managing employee.',
  'COALESCE(t.title_desc, ''Unknown'') -- FROM employees e LEFT JOIN title_ref t ON e.title_cd = t.title_cd',
  'employees, title_ref',
  'title_desc',
  'Title description from title reference lookup | Employee title code',
  'VARCHAR(50), VARCHAR(5)',
  'JOIN', 'COALESCE',
  0.82, 'AI', 'Title requires lookup join to reference table. COALESCE handles missing titles.', true, 'ACTIVE',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);

-- 3.3 Complex join with conditional logic
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  49, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Address Street 2', 'ADDR_STR_2', 'Street address line two of the managing employee.',
  'CASE WHEN a.unit_num IS NOT NULL THEN CONCAT(''Unit '', a.unit_num) ELSE a.addr_line_2 END -- FROM employees e JOIN addresses a ON e.addr_id = a.id',
  'employees, addresses',
  'unit_num, addr_line_2',
  'Unit/apartment number | Secondary address line',
  'VARCHAR(10), VARCHAR(100)',
  'JOIN', 'CASE, CONCAT',
  0.79, 'MANUAL', 'Address line 2 uses CASE to prefer unit number format when available.', false, 'ACTIVE',
  'admin@gainwell.com', CURRENT_TIMESTAMP()
);

-- ============================================================================
-- SCENARIO 4: UNION-BASED MAPPINGS (Combining Rows from Multiple Tables)
-- ============================================================================

-- 4.1 Middle Initial from union of current and historical records
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  52, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Middle Name Initial', 'MDL_NM_INIT', 'Middle initial of the managing employee',
  'SELECT UPPER(SUBSTR(middle_name, 1, 1)) FROM current_employees UNION ALL SELECT UPPER(SUBSTR(mid_nm, 1, 1)) FROM historical_employees',
  'current_employees, historical_employees',
  'middle_name, mid_nm',
  'Full middle name from current system | Middle name from legacy system',
  'VARCHAR(50), VARCHAR(30)',
  'UNION', 'UPPER, SUBSTR',
  0.76, 'AI', 'Middle initial derived from two source systems via UNION. SUBSTR extracts first character.', true, 'ACTIVE',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);

-- 4.2 Begin Effective Date from union of systems
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  40, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Begin Effective Date', 'BEG_EFF_DT', 'Begin Effective Date',
  'SELECT hire_date FROM new_hires WHERE hire_date >= ''2020-01-01'' UNION ALL SELECT start_dt FROM legacy_employees WHERE start_dt < ''2020-01-01''',
  'new_hires, legacy_employees',
  'hire_date, start_dt',
  'Hire date from new HR system | Start date from legacy system',
  'DATE, DATE',
  'UNION', 'NONE',
  0.84, 'MANUAL', 'Effective date combines records from two systems based on cutover date.', false, 'ACTIVE',
  'admin@gainwell.com', CURRENT_TIMESTAMP()
);

-- ============================================================================
-- SCENARIO 5: ADDITIONAL VARIETY FOR VECTOR SEARCH TESTING
-- ============================================================================

-- 5.1 Tenant Code - System field
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  45, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Tenant_Cd', 'TENANT_CD', 'Tenant Code',
  '''GAINWELL''',
  '',
  '',
  'Hardcoded tenant identifier',
  '',
  'SINGLE', 'LITERAL',
  1.0, 'MANUAL', 'Static value - all records belong to GAINWELL tenant.', false, 'ACTIVE',
  'admin@gainwell.com', CURRENT_TIMESTAMP()
);

-- 5.2 Source System Code
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  33, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Src_Sys_Cd', 'SRC_SYS_CD', 'Source Sytem Code',
  'COALESCE(src.system_code, ''UNKNOWN'')',
  'src',
  'system_code',
  'Source system identifier code',
  'VARCHAR(20)',
  'SINGLE', 'COALESCE',
  0.93, 'AI', 'Source system code with COALESCE default for missing values.', true, 'ACTIVE',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);

-- 5.3 Current Record Indicator
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
  semantic_field_id, tgt_table_name, tgt_table_physical_name, 
  tgt_column_name, tgt_column_physical_name, tgt_comments,
  source_expression, source_tables, source_columns, source_descriptions, source_datatypes,
  source_relationship_type, transformations_applied,
  confidence_score, mapping_source, ai_reasoning, ai_generated, mapping_status,
  mapped_by, mapped_ts
) VALUES (
  46, 'MANAGING EMPLOYEE', 'MNGN_EMP',
  'Curr_Rec_Ind', 'CURR_REC_IND', 'Y/N to indicate whether this is the most current ot Active record.',
  'CASE WHEN emp.status = ''ACTIVE'' THEN ''Y'' ELSE ''N'' END',
  'emp',
  'status',
  'Employee status (ACTIVE, TERMINATED, etc.)',
  'VARCHAR(20)',
  'SINGLE', 'CASE',
  0.90, 'AI', 'Converted status to Y/N indicator using CASE expression.', true, 'ACTIVE',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);


-- ============================================================================
-- ALSO ADD SOME REJECTION FEEDBACK FOR TESTING
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.mapping_feedback (
  suggested_src_table, suggested_src_column, suggested_tgt_table, suggested_tgt_column,
  src_comments, src_datatype, tgt_comments,
  ai_confidence_score, ai_reasoning, vector_search_score, suggestion_rank,
  feedback_action, user_comments, domain, feedback_by, feedback_ts
) VALUES (
  'phone_records', 'phone_number', 'MNGN_EMP', 'SSN_NUM',
  'Primary phone number of the employee', 'VARCHAR(15)', 'Social security number of the managing employee.',
  0.45, 'Both are numeric identifiers for employees.', 0.52, 3,
  'REJECTED', 'Phone number is not SSN - completely different data types and purposes.', 'MANAGING',
  'test_user@gainwell.com', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.mapping_feedback (
  suggested_src_table, suggested_src_column, suggested_tgt_table, suggested_tgt_column,
  src_comments, src_datatype, tgt_comments,
  ai_confidence_score, ai_reasoning, vector_search_score, suggestion_rank,
  feedback_action, user_comments, domain, feedback_by, feedback_ts
) VALUES (
  'hr_data', 'employee_id', 'MNGN_EMP', 'FIRST_NM',
  'Unique employee identifier number', 'BIGINT', 'First name of the managing employee.',
  0.35, 'Both relate to employee identification.', 0.38, 5,
  'REJECTED', 'Employee ID is not a name field - wrong data type entirely.', 'MANAGING',
  'admin@gainwell.com', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.mapping_feedback (
  suggested_src_table, suggested_src_column, suggested_tgt_table, suggested_tgt_column,
  src_comments, src_datatype, tgt_comments,
  ai_confidence_score, ai_reasoning, vector_search_score, suggestion_rank,
  feedback_action, user_comments, modified_src_table, modified_src_column, modified_expression,
  domain, feedback_by, feedback_ts
) VALUES (
  'addresses', 'zip_code', 'MNGN_EMP', 'CITY',
  'Postal zip code', 'VARCHAR(10)', 'City of the managing employee.',
  0.55, 'Both are location-related fields.', 0.58, 2,
  'MODIFIED', 'Zip code is not city - selected city_name instead.', 'addresses', 'city_name', 'TRIM(UPPER(addresses.city_name))',
  'MANAGING', 'test_user@gainwell.com', CURRENT_TIMESTAMP()
);


-- ============================================================================
-- SUMMARY OF TEST DATA
-- ============================================================================
-- 
-- Mapped Fields Created:
-- - 5 SINGLE column mappings with various transformations (TRIM, UPPER, TO_DATE, etc.)
-- - 3 SINGLE mappings with multi-column expressions (CONCAT, SUBSTR, CASE)
-- - 3 JOIN-based mappings (employees + addresses, reference lookups)
-- - 2 UNION-based mappings (current + historical systems)
-- - 3 Additional variety mappings (literals, COALESCE, CASE)
--
-- Mapping Feedback (Rejections):
-- - 2 REJECTED suggestions (wrong data types)
-- - 1 MODIFIED suggestion (user selected different column)
--
-- This provides good coverage for testing:
-- - Vector search on source_semantic_field
-- - Pattern matching for transformations
-- - Multi-table relationship detection
-- - Rejection avoidance
--
-- ============================================================================

