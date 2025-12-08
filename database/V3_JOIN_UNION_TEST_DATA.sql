-- ============================================================================
-- V3 Test Data - JOIN and UNION Scenarios for Testing
-- ============================================================================
-- This script creates unmapped fields from multiple related tables to test:
-- 1. JOIN scenario: Member_Data + Member_Eligibility need to be joined
-- 2. UNION scenario: Legacy_Members + Current_Members need to be unioned
--
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema (e.g., oztest_dev.smartmapper)
-- ============================================================================

-- ============================================================================
-- SCENARIO 1: JOIN - Member_Data + Member_Eligibility
-- ============================================================================
-- Use Case: To populate "Member Enrollment Info" target fields, you need
-- member demographics from Member_Data AND eligibility details from 
-- Member_Eligibility, joined on member_id.
--
-- Example target: MEMBER_ENROLLMENT table needs:
--   - Member Name (from Member_Data)
--   - Member ID (from Member_Data)  
--   - Plan Name (from Member_Eligibility)
--   - Effective Date (from Member_Eligibility)
-- ============================================================================

-- Member_Data table fields (basic demographics)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Member Data', 'Member Identifier', 'mbr_data', 'mbr_id',
  'NO', 'VARCHAR(20)', 'Unique identifier for the member - used as join key to eligibility', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Member Data', 'Member Full Name', 'mbr_data', 'mbr_full_nm',
  'NO', 'VARCHAR(150)', 'Complete name of the member (first + middle + last)', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Member_Eligibility table fields (eligibility/plan details)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Member Eligibility', 'Member ID', 'mbr_elig', 'mbr_id',
  'NO', 'VARCHAR(20)', 'Foreign key to member data table - join key', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Member Eligibility', 'Health Plan Name', 'mbr_elig', 'hlth_pln_nm',
  'NO', 'VARCHAR(100)', 'Name of the health insurance plan the member is enrolled in', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Member Eligibility', 'Plan Effective Date', 'mbr_elig', 'pln_eff_dt',
  'NO', 'DATE', 'Date when the member eligibility for this plan becomes effective', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Member Eligibility', 'Plan Term Date', 'mbr_elig', 'pln_term_dt',
  'YES', 'DATE', 'Date when the member eligibility for this plan terminates', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Member Eligibility', 'Coverage Type', 'mbr_elig', 'cvrg_typ',
  'NO', 'VARCHAR(30)', 'Type of coverage (MEDICAL, DENTAL, VISION, PHARMACY)', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Member Eligibility', 'Benefit Package Code', 'mbr_elig', 'bnft_pkg_cd',
  'NO', 'VARCHAR(10)', 'Code identifying the benefit package level (GOLD, SILVER, BRONZE)', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- ============================================================================
-- SCENARIO 2: UNION - Legacy_Members + Current_Members
-- ============================================================================
-- Use Case: During system migration, member data exists in two tables:
-- - Legacy_Members: Historical members from old system
-- - Current_Members: Active members from new system
-- To create a complete member list, you need to UNION these tables.
--
-- Both tables have similar structure but different table names.
-- ============================================================================

-- Legacy_Members table (old system - being retired)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Legacy Members', 'Legacy Member ID', 'legacy_mbr', 'lgcy_mbr_id',
  'NO', 'VARCHAR(15)', 'Member identifier from the legacy system being migrated', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Legacy Members', 'Legacy First Name', 'legacy_mbr', 'lgcy_frst_nm',
  'NO', 'VARCHAR(50)', 'First name from legacy member records', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Legacy Members', 'Legacy Last Name', 'legacy_mbr', 'lgcy_lst_nm',
  'NO', 'VARCHAR(50)', 'Last name from legacy member records', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Legacy Members', 'Legacy DOB', 'legacy_mbr', 'lgcy_dob',
  'YES', 'DATE', 'Date of birth from legacy system', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Legacy Members', 'Legacy Status', 'legacy_mbr', 'lgcy_sts',
  'NO', 'VARCHAR(20)', 'Member status from legacy system (ACTIVE, TERMED, DECEASED)', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Current_Members table (new system - active)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Current Members', 'Current Member ID', 'curr_mbr', 'curr_mbr_id',
  'NO', 'VARCHAR(20)', 'Member identifier from the current active system', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Current Members', 'Current First Name', 'curr_mbr', 'curr_frst_nm',
  'NO', 'VARCHAR(75)', 'First name from current member records', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Current Members', 'Current Last Name', 'curr_mbr', 'curr_lst_nm',
  'NO', 'VARCHAR(75)', 'Last name from current member records', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Current Members', 'Current Birth Date', 'curr_mbr', 'curr_brth_dt',
  'YES', 'DATE', 'Date of birth from current system', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Current Members', 'Current Status', 'curr_mbr', 'curr_sts',
  'NO', 'VARCHAR(20)', 'Member status from current system (ENROLLED, DISENROLLED, PENDING)', 'MEMBER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- ============================================================================
-- SCENARIO 3: Complex JOIN - Provider + Provider_Specialty + Provider_Address
-- ============================================================================
-- Use Case: Provider data is normalized across three tables that need 
-- to be joined for a complete provider record.
-- ============================================================================

-- Provider table (basic info)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider', 'Provider NPI', 'provider', 'prov_npi',
  'NO', 'VARCHAR(10)', 'National Provider Identifier - unique 10-digit number', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider', 'Provider Name', 'provider', 'prov_nm',
  'NO', 'VARCHAR(200)', 'Full name of the provider (individual or organization)', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider', 'Provider Tax ID', 'provider', 'prov_tax_id',
  'NO', 'VARCHAR(12)', 'Tax identification number for the provider', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Provider_Specialty table (joins to Provider on NPI)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider Specialty', 'Specialty NPI', 'prov_spec', 'spec_npi',
  'NO', 'VARCHAR(10)', 'NPI - foreign key to provider table', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider Specialty', 'Specialty Code', 'prov_spec', 'spec_cd',
  'NO', 'VARCHAR(10)', 'Healthcare specialty taxonomy code', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider Specialty', 'Specialty Description', 'prov_spec', 'spec_desc',
  'NO', 'VARCHAR(200)', 'Description of the medical specialty (e.g., Family Medicine, Cardiology)', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider Specialty', 'Primary Specialty Flag', 'prov_spec', 'prim_spec_flg',
  'NO', 'CHAR(1)', 'Indicates if this is the primary specialty (Y/N)', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- Provider_Address table (joins to Provider on NPI)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider Address', 'Address NPI', 'prov_addr', 'addr_npi',
  'NO', 'VARCHAR(10)', 'NPI - foreign key to provider table', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider Address', 'Practice Address Line 1', 'prov_addr', 'prac_addr_ln1',
  'NO', 'VARCHAR(200)', 'First line of provider practice address', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider Address', 'Practice City', 'prov_addr', 'prac_city',
  'NO', 'VARCHAR(100)', 'City of provider practice location', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider Address', 'Practice State', 'prov_addr', 'prac_st',
  'NO', 'CHAR(2)', 'State of provider practice location', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider Address', 'Practice Zip', 'prov_addr', 'prac_zip',
  'NO', 'VARCHAR(10)', 'Zip code of provider practice location', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name, src_column_name, src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments, domain,
  uploaded_by, uploaded_ts, created_by, created_ts
) VALUES (
  'Provider Address', 'Address Type', 'prov_addr', 'addr_typ',
  'NO', 'VARCHAR(20)', 'Type of address (PRACTICE, MAILING, BILLING)', 'PROVIDER',
  'test_user@gainwell.com', CURRENT_TIMESTAMP(), 'system', CURRENT_TIMESTAMP()
);

-- ============================================================================
-- EXAMPLE SQL FOR TESTING
-- ============================================================================
/*
JOIN EXAMPLE (Member_Data + Member_Eligibility):
To map "Member Name with Plan" to target, select fields from both tables:

SELECT 
  md.mbr_full_nm,
  me.hlth_pln_nm,
  me.pln_eff_dt
FROM mbr_data md
JOIN mbr_elig me ON md.mbr_id = me.mbr_id
WHERE me.pln_term_dt IS NULL

---

UNION EXAMPLE (Legacy_Members + Current_Members):
To map to "All Member IDs" target, union both tables:

SELECT lgcy_mbr_id AS member_id, lgcy_frst_nm AS first_name, 'LEGACY' AS source
FROM legacy_mbr
UNION ALL
SELECT curr_mbr_id AS member_id, curr_frst_nm AS first_name, 'CURRENT' AS source
FROM curr_mbr

---

COMPLEX JOIN (Provider + Specialty + Address):
To map "Provider Full Record" target:

SELECT 
  p.prov_npi,
  p.prov_nm,
  ps.spec_desc,
  pa.prac_city,
  pa.prac_st
FROM provider p
JOIN prov_spec ps ON p.prov_npi = ps.spec_npi AND ps.prim_spec_flg = 'Y'
JOIN prov_addr pa ON p.prov_npi = pa.addr_npi AND pa.addr_typ = 'PRACTICE'
*/

