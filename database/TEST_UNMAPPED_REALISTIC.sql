-- ============================================================================
-- Test Unmapped Fields - Realistic Scenarios Based on Historical Mappings
-- ============================================================================
-- These fields are designed to test AI matching against existing mapped_fields
-- by using SIMILAR but not identical names and descriptions.
--
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema (e.g., oztest_dev.smartmapper)
-- ============================================================================

-- ============================================================================
-- SCENARIO 1: SINGLE FIELD MAPPINGS - Similar to existing mapped patterns
-- ============================================================================

-- Similar to: SAK_RECIP -> SRC_KEY_ID (member foundation source key)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Recipient Base', 'Recipient Key', 't_recip_base', 'recip_key',
  'NO', 'VARCHAR(50)', 'The unique identifier for the recipient in the state Medicaid program. Used as primary key for member records.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Similar to: DTE_CHANGED -> CHG_DT (change date field)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Member Assignment', 'Last Modified Date', 'mbr_assign', 'lst_mod_dt',
  'YES', 'DATE', 'Date when this assignment record was last updated in the source system.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Similar to: CDE_STATUS1 -> STS_CD (status code)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'PCP Assignment', 'Assignment Status', 'pcp_assign', 'asgn_sts',
  'NO', 'VARCHAR(10)', 'Current status of the member PCP assignment (ACTIVE, INACTIVE, PENDING).',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Similar to: DTE_EFFECTIVE -> SRC_EFF_DT (effective date)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Enrollment Record', 'Coverage Start Date', 'enrl_rec', 'cvrg_strt_dt',
  'NO', 'DATE', 'The date when member coverage becomes effective under this enrollment.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Similar to: NAM_FIRST -> FIRST_NM (first name)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Case Record', 'Given Name', 'case_rec', 'given_nm',
  'NO', 'VARCHAR(50)', 'The member first name or given name from case management.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Similar to: NAM_LAST -> LAST_NM (last name)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Case Record', 'Surname', 'case_rec', 'surname',
  'NO', 'VARCHAR(50)', 'The member family name or surname from the case file.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Similar to: NUM_PHONE -> PHONE_NUM (phone number)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Contact Info', 'Primary Telephone', 'cntct_info', 'prim_tel',
  'YES', 'VARCHAR(15)', 'The main phone number used to contact the member.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Similar to: DTE_TERMED -> TERM_DT (termination date)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Eligibility Span', 'Disenrollment Date', 'elig_span', 'disenrl_dt',
  'YES', 'DATE', 'Date when the member was terminated from coverage or disenrolled.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- ============================================================================
-- SCENARIO 2: JOIN/LOOKUP PATTERNS - Surrogate key lookups
-- ============================================================================

-- Similar to: MBR_SK lookup from member foundation
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Claims Detail', 'Claimant ID', 'clm_dtl', 'claimant_id',
  'NO', 'VARCHAR(20)', 'Member identifier on the claim - needs to join to member foundation to get surrogate key.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Similar to: PLAN_SK lookup from plan foundation  
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Enrollment Detail', 'Enrolled Plan ID', 'enrl_dtl', 'enrl_plan_id',
  'NO', 'VARCHAR(20)', 'The plan identifier from enrollment - used to lookup the plan surrogate key from plan foundation.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Similar to: PROV_SK lookup from provider foundation
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'PCP Selection', 'Selected Provider ID', 'pcp_sel', 'sel_prov_id',
  'NO', 'VARCHAR(20)', 'Provider identifier that needs to be looked up in provider foundation to get PROV_SK.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- ============================================================================
-- SCENARIO 3: CONCAT/DERIVED - Multi-field SSK patterns
-- ============================================================================

-- Similar to: TENANT_CD|SRC_SYS_CD|SRC_KEY_ID -> MBR_FNDTN_SSK
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Member Demographics', 'Client Code', 'mbr_demo', 'clnt_cd',
  'NO', 'VARCHAR(10)', 'Tenant or client code identifying the state/organization.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Member Demographics', 'System Source Code', 'mbr_demo', 'sys_src_cd',
  'NO', 'VARCHAR(10)', 'Code identifying the source system (e.g., MMIS, HIX).',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Member Demographics', 'Member Source Key', 'mbr_demo', 'mbr_src_key',
  'NO', 'VARCHAR(50)', 'The original member identifier from the source system.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- ============================================================================
-- SCENARIO 4: UNION PATTERN - Similar fields from different source tables
-- ============================================================================

-- Medicare Part A table
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Medicare Part A', 'Part A Recipient ID', 'mc_part_a', 'parta_recip_id',
  'NO', 'VARCHAR(20)', 'Member identifier from Medicare Part A eligibility records.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Medicare Part B table (same concept, different source)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Medicare Part B', 'Part B Beneficiary ID', 'mc_part_b', 'partb_bene_id',
  'NO', 'VARCHAR(20)', 'Member identifier from Medicare Part B eligibility file.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Medicare Part D table (same concept, different source)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Medicare Part D', 'Part D Member ID', 'mc_part_d', 'partd_mbr_id',
  'NO', 'VARCHAR(20)', 'Member identifier from Medicare Part D pharmacy benefits.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- ============================================================================
-- SCENARIO 5: ADDITIONAL VARIETY - Other common patterns
-- ============================================================================

-- Income/financial field similar to AMT_INCOME
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Eligibility Determination', 'Household Income', 'elig_determ', 'hh_income',
  'YES', 'DECIMAL(12,2)', 'Total household income used for Medicaid eligibility determination.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Case worker similar to ID_CASE_WORKER
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Case Management', 'Assigned Worker ID', 'case_mgmt', 'wrkr_id',
  'YES', 'VARCHAR(20)', 'Identifier for the caseworker assigned to manage this members case.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Managed care region similar to CDE_MC_REGION
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'MCO Assignment', 'Service Region', 'mco_assign', 'svc_region',
  'NO', 'VARCHAR(10)', 'Geographic region code for managed care organization assignment.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Latitude similar to NUM_LATITUDE
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Address Geocode', 'Geo Latitude', 'addr_geo', 'geo_lat',
  'YES', 'DECIMAL(10,6)', 'Latitude coordinate of member residence for geographic analysis.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Longitude similar to NUM_LONGITUDE
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Address Geocode', 'Geo Longitude', 'addr_geo', 'geo_lng',
  'YES', 'DECIMAL(10,6)', 'Longitude coordinate of member residence for geographic analysis.',
  'Member', 'test_mapper@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- ============================================================================
-- EXPECTED AI MATCHING RESULTS:
-- ============================================================================
/*
Field                      | Expected Pattern Match                    | Type
---------------------------|-------------------------------------------|-------
Recipient Key              | SAK_RECIP -> SRC_KEY_ID                  | SINGLE
Last Modified Date         | DTE_CHANGED -> CHG_DT                    | SINGLE
Assignment Status          | CDE_STATUS1 -> STS_CD                    | SINGLE
Coverage Start Date        | DTE_EFFECTIVE -> SRC_EFF_DT              | SINGLE
Given Name                 | NAM_FIRST -> FIRST_NM                    | SINGLE
Surname                    | NAM_LAST -> LAST_NM                      | SINGLE
Primary Telephone          | NUM_PHONE -> PHONE_NUM                   | CONCAT
Disenrollment Date         | DTE_TERMED -> TERM_DT                    | SINGLE
Claimant ID                | Member SK lookup                         | JOIN
Enrolled Plan ID           | Plan SK lookup                           | JOIN
Selected Provider ID       | Provider SK lookup                       | JOIN
Client Code + Sys Source + Key | SSK pattern                          | CONCAT
Part A/B/D IDs             | Medicare union pattern                   | UNION
Household Income           | AMT_INCOME -> INCM_AMT                   | SINGLE
Assigned Worker ID         | ID_CASE_WORKER -> CASE_WRK_ID            | SINGLE
Service Region             | CDE_MC_REGION -> MNGD_CARE_REG_CD        | SINGLE
Geo Latitude               | NUM_LATITUDE -> LATTD_NUM                | SINGLE
Geo Longitude              | NUM_LONGITUDE -> LNGTD_NUM               | SINGLE
*/



