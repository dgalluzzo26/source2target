-- ============================================================================
-- V4 Test Data - Target-First Workflow Testing
-- ============================================================================
-- Creates test data for the MBR_CNTCT (Member Contact) table pattern
-- Based on BR Scenario file patterns
--
-- Run this after creating V4 tables and having semantic_fields populated
-- Replace ${CATALOG_SCHEMA} with your catalog.schema (e.g., oztest_dev.smartmapper)
-- ============================================================================

-- ============================================================================
-- STEP 1: INSERT PAST MAPPINGS (APPROVED PATTERNS)
-- These represent historical mappings that the AI will learn from
-- ============================================================================

-- First, get the semantic_field_id for each target column
-- We'll insert mappings that match by tgt_table_physical_name and tgt_column_physical_name

-- Pattern 1: MBR_SK - Lookup pattern with UNION
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id,
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
    confidence_score,
    ai_reasoning,
    mapping_status,
    is_approved_pattern,
    pattern_approved_by,
    pattern_approved_ts,
    mapped_by,
    mapped_ts,
    project_id
)
SELECT 
    sf.semantic_field_id,
    'MEMBER CONTACT',
    'MBR_CNTCT',
    'Member Sk',
    'MBR_SK',
    'Unique identifier for a given member. auto generated key in MEMBER CONTACT table.',
    'SELECT DISTINCT
  mf.MBR_SK
FROM ${USER_BRONZE_CATALOG}.${USER_BRONZE_SCHEMA}.t_re_base b
JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.mbr_fndtn mf ON b.SAK_RECIP = mf.SRC_KEY_ID AND b.CURR_REC_IND=''1''
LEFT JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.cnty_cd c ON b.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''
WHERE mf.CURR_REC_IND=''1''

UNION DISTINCT

SELECT DISTINCT
  mf.MBR_SK
FROM (SELECT * FROM ${USER_BRONZE_CATALOG}.${USER_BRONZE_SCHEMA}.t_re_multi_address WHERE TRIM(CDE_ADDR_USAGE) IN (''R'',''M'') AND CURR_REC_IND=''1'') a
JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.mbr_fndtn mf ON a.SAK_RECIP = mf.SRC_KEY_ID
LEFT JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.cnty_cd c ON a.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''
WHERE mf.CURR_REC_IND=''1''',
    'T_RE_BASE|T_RE_MULTI_ADDRESS|MBR_FNDTN|CNTY_CD',
    't_re_base|t_re_multi_address|mbr_fndtn|cnty_cd',
    'SAK_RECIP|CDE_COUNTY|CDE_ADDR_USAGE|CURR_REC_IND',
    'SAK_RECIP|CDE_COUNTY|CDE_ADDR_USAGE|CURR_REC_IND',
    'SAK_RECIP: Recipient identifier used to uniquely represent individuals in beneficiary tables|CDE_COUNTY: Coded field identifying the county associated with a recipient address|CDE_ADDR_USAGE: Coded field indicating the purpose or usage type of an address|CURR_REC_IND: Y/N to indicate whether this is the most current or Active record',
    'BIGINT|STRING|STRING|STRING',
    'Member',
    'MANY_TO_ONE',
    'Lookup',
    '{
  "patternType": "UNION_WITH_JOINS",
  "outputColumn": "MBR_SK",
  "description": "Lookup member SK by joining recipient base and multi-address tables to member foundation",
  "silverTables": [
    {"catalog": "silver_catalog", "schema": "silver_schema", "table": "mbr_fndtn", "alias": "mf", "role": "lookup"},
    {"catalog": "silver_catalog", "schema": "silver_schema", "table": "cnty_cd", "alias": "c", "role": "reference"}
  ],
  "bronzeTables": [
    {"catalog": "bronze_catalog", "schema": "bronze_schema", "table": "t_re_base", "alias": "b", "role": "source"},
    {"catalog": "bronze_catalog", "schema": "bronze_schema", "table": "t_re_multi_address", "alias": "a", "role": "source"}
  ],
  "unionBranches": [
    {
      "branchName": "base_address",
      "bronzeTable": "t_re_base",
      "joins": [
        {"type": "INNER", "silverTable": "mbr_fndtn", "condition": "b.SAK_RECIP = mf.SRC_KEY_ID AND b.CURR_REC_IND=''1''"},
        {"type": "LEFT", "silverTable": "cnty_cd", "condition": "b.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''"}
      ],
      "filters": ["mf.CURR_REC_IND=''1''"]
    },
    {
      "branchName": "multi_address",
      "bronzeTable": "t_re_multi_address",
      "subqueryFilter": "TRIM(CDE_ADDR_USAGE) IN (''R'',''M'') AND CURR_REC_IND=''1''",
      "joins": [
        {"type": "INNER", "silverTable": "mbr_fndtn", "condition": "a.SAK_RECIP = mf.SRC_KEY_ID"},
        {"type": "LEFT", "silverTable": "cnty_cd", "condition": "a.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''"}
      ],
      "filters": ["mf.CURR_REC_IND=''1''"]
    }
  ],
  "userColumnsToMap": [
    {"role": "join_key_source", "semanticName": "recipient_id", "description": "Source recipient/member identifier to join to member foundation"},
    {"role": "filter", "semanticName": "current_record_indicator", "description": "Flag indicating current/active record"},
    {"role": "join_key_source", "semanticName": "county_code", "description": "County code for geographic lookup"},
    {"role": "filter", "semanticName": "address_usage_code", "description": "Address usage type filter (R=Residential, M=Mailing)"}
  ],
  "userTablesToMap": [
    {"role": "primary_source", "semanticName": "recipient_base", "description": "Primary recipient/member base table with address"},
    {"role": "secondary_source", "semanticName": "recipient_multi_address", "description": "Secondary table for members with multiple addresses"}
  ]
}',
    0.95,
    'High confidence lookup pattern using member foundation join. Standard DMES pattern.',
    'ACTIVE',
    TRUE,
    'historical_load',
    CURRENT_TIMESTAMP(),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP(),
    NULL
FROM ${CATALOG_SCHEMA}.semantic_fields sf
WHERE UPPER(sf.tgt_table_physical_name) = 'MBR_CNTCT'
  AND UPPER(sf.tgt_column_physical_name) = 'MBR_SK'
LIMIT 1;


-- Pattern 2: ADDR_1_TXT - Address Line 1 with INITCAP transformation
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id,
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
    confidence_score,
    ai_reasoning,
    mapping_status,
    is_approved_pattern,
    pattern_approved_by,
    pattern_approved_ts,
    mapped_by,
    mapped_ts,
    project_id
)
SELECT 
    sf.semantic_field_id,
    'MEMBER CONTACT',
    'MBR_CNTCT',
    'Address 1 Text',
    'ADDR_1_TXT',
    'First address line of mailing address of member or recipient in MEMBER CONTACT table.',
    'SELECT DISTINCT
  INITCAP(b.ADR_STREET_1) AS ADDR_1_TXT
FROM ${USER_BRONZE_CATALOG}.${USER_BRONZE_SCHEMA}.t_re_base b
JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.mbr_fndtn mf ON b.SAK_RECIP = mf.SRC_KEY_ID AND b.CURR_REC_IND=''1''
LEFT JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.cnty_cd c ON b.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''
WHERE mf.CURR_REC_IND=''1''

UNION DISTINCT

SELECT DISTINCT
  INITCAP(a.ADR_STREET_1) AS ADDR_1_TXT
FROM (SELECT * FROM ${USER_BRONZE_CATALOG}.${USER_BRONZE_SCHEMA}.t_re_multi_address WHERE TRIM(CDE_ADDR_USAGE) IN (''R'',''M'') AND CURR_REC_IND=''1'') a
JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.mbr_fndtn mf ON a.SAK_RECIP = mf.SRC_KEY_ID
LEFT JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.cnty_cd c ON a.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''
WHERE mf.CURR_REC_IND=''1''',
    'T_RE_BASE|T_RE_MULTI_ADDRESS|MBR_FNDTN|CNTY_CD',
    't_re_base|t_re_multi_address|mbr_fndtn|cnty_cd',
    'ADR_STREET_1|SAK_RECIP|CDE_COUNTY|CDE_ADDR_USAGE|CURR_REC_IND',
    'ADR_STREET_1|SAK_RECIP|CDE_COUNTY|CDE_ADDR_USAGE|CURR_REC_IND',
    'ADR_STREET_1: Primary street address line for a recipient|SAK_RECIP: Recipient identifier|CDE_COUNTY: County code|CDE_ADDR_USAGE: Address usage type|CURR_REC_IND: Current record indicator',
    'STRING|BIGINT|STRING|STRING|STRING',
    'Member',
    'MANY_TO_ONE',
    'INITCAP',
    '{
  "patternType": "UNION_WITH_JOINS",
  "outputColumn": "ADDR_1_TXT",
  "outputTransformation": "INITCAP",
  "description": "Extract and format primary street address from base and multi-address tables",
  "silverTables": [
    {"catalog": "silver_catalog", "schema": "silver_schema", "table": "mbr_fndtn", "alias": "mf", "role": "lookup"},
    {"catalog": "silver_catalog", "schema": "silver_schema", "table": "cnty_cd", "alias": "c", "role": "reference"}
  ],
  "bronzeTables": [
    {"catalog": "bronze_catalog", "schema": "bronze_schema", "table": "t_re_base", "alias": "b", "role": "source"},
    {"catalog": "bronze_catalog", "schema": "bronze_schema", "table": "t_re_multi_address", "alias": "a", "role": "source"}
  ],
  "userColumnsToMap": [
    {"role": "output", "semanticName": "street_address_1", "description": "Primary street address line"},
    {"role": "join_key_source", "semanticName": "recipient_id", "description": "Source recipient/member identifier"},
    {"role": "filter", "semanticName": "current_record_indicator", "description": "Current record flag"},
    {"role": "join_key_source", "semanticName": "county_code", "description": "County code for lookup"},
    {"role": "filter", "semanticName": "address_usage_code", "description": "Address usage type filter"}
  ],
  "userTablesToMap": [
    {"role": "primary_source", "semanticName": "recipient_base", "description": "Primary recipient base table"},
    {"role": "secondary_source", "semanticName": "recipient_multi_address", "description": "Multi-address table"}
  ]
}',
    0.92,
    'Standard address extraction pattern with INITCAP formatting.',
    'ACTIVE',
    TRUE,
    'historical_load',
    CURRENT_TIMESTAMP(),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP(),
    NULL
FROM ${CATALOG_SCHEMA}.semantic_fields sf
WHERE UPPER(sf.tgt_table_physical_name) = 'MBR_CNTCT'
  AND UPPER(sf.tgt_column_physical_name) = 'ADDR_1_TXT'
LIMIT 1;


-- Pattern 3: ADDR_2_TXT - Address Line 2
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id,
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
    confidence_score,
    ai_reasoning,
    mapping_status,
    is_approved_pattern,
    pattern_approved_by,
    pattern_approved_ts,
    mapped_by,
    mapped_ts,
    project_id
)
SELECT 
    sf.semantic_field_id,
    'MEMBER CONTACT',
    'MBR_CNTCT',
    'Address 2 Text',
    'ADDR_2_TXT',
    'Second address line of mailing address of member or recipient in MEMBER CONTACT table.',
    'SELECT DISTINCT
  INITCAP(b.ADR_STREET_2) AS ADDR_2_TXT
FROM ${USER_BRONZE_CATALOG}.${USER_BRONZE_SCHEMA}.t_re_base b
JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.mbr_fndtn mf ON b.SAK_RECIP = mf.SRC_KEY_ID AND b.CURR_REC_IND=''1''
LEFT JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.cnty_cd c ON b.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''
WHERE mf.CURR_REC_IND=''1''

UNION DISTINCT

SELECT DISTINCT
  INITCAP(a.ADR_STREET_2) AS ADDR_2_TXT
FROM (SELECT * FROM ${USER_BRONZE_CATALOG}.${USER_BRONZE_SCHEMA}.t_re_multi_address WHERE TRIM(CDE_ADDR_USAGE) IN (''R'',''M'') AND CURR_REC_IND=''1'') a
JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.mbr_fndtn mf ON a.SAK_RECIP = mf.SRC_KEY_ID
LEFT JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.cnty_cd c ON a.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''
WHERE mf.CURR_REC_IND=''1''',
    'T_RE_BASE|T_RE_MULTI_ADDRESS|MBR_FNDTN|CNTY_CD',
    't_re_base|t_re_multi_address|mbr_fndtn|cnty_cd',
    'ADR_STREET_2|SAK_RECIP|CDE_COUNTY|CDE_ADDR_USAGE|CURR_REC_IND',
    'ADR_STREET_2|SAK_RECIP|CDE_COUNTY|CDE_ADDR_USAGE|CURR_REC_IND',
    'ADR_STREET_2: Secondary street address line for a recipient|SAK_RECIP: Recipient identifier|CDE_COUNTY: County code|CDE_ADDR_USAGE: Address usage type|CURR_REC_IND: Current record indicator',
    'STRING|BIGINT|STRING|STRING|STRING',
    'Member',
    'MANY_TO_ONE',
    'INITCAP',
    '{
  "patternType": "UNION_WITH_JOINS",
  "outputColumn": "ADDR_2_TXT",
  "outputTransformation": "INITCAP",
  "description": "Extract and format secondary street address from base and multi-address tables",
  "userColumnsToMap": [
    {"role": "output", "semanticName": "street_address_2", "description": "Secondary street address line (apt, suite, etc.)"},
    {"role": "join_key_source", "semanticName": "recipient_id", "description": "Source recipient/member identifier"},
    {"role": "filter", "semanticName": "current_record_indicator", "description": "Current record flag"}
  ],
  "userTablesToMap": [
    {"role": "primary_source", "semanticName": "recipient_base", "description": "Primary recipient base table"},
    {"role": "secondary_source", "semanticName": "recipient_multi_address", "description": "Multi-address table"}
  ]
}',
    0.92,
    'Standard address extraction pattern with INITCAP formatting.',
    'ACTIVE',
    TRUE,
    'historical_load',
    CURRENT_TIMESTAMP(),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP(),
    NULL
FROM ${CATALOG_SCHEMA}.semantic_fields sf
WHERE UPPER(sf.tgt_table_physical_name) = 'MBR_CNTCT'
  AND UPPER(sf.tgt_column_physical_name) = 'ADDR_2_TXT'
LIMIT 1;


-- Pattern 4: CITY_NM - City Name
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id,
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
    confidence_score,
    ai_reasoning,
    mapping_status,
    is_approved_pattern,
    pattern_approved_by,
    pattern_approved_ts,
    mapped_by,
    mapped_ts,
    project_id
)
SELECT 
    sf.semantic_field_id,
    'MEMBER CONTACT',
    'MBR_CNTCT',
    'City Name',
    'CITY_NM',
    'City of mailing address of member or recipient in MEMBER CONTACT table.',
    'SELECT DISTINCT
  INITCAP(b.ADR_CITY) AS CITY_NM
FROM ${USER_BRONZE_CATALOG}.${USER_BRONZE_SCHEMA}.t_re_base b
JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.mbr_fndtn mf ON b.SAK_RECIP = mf.SRC_KEY_ID AND b.CURR_REC_IND=''1''
LEFT JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.cnty_cd c ON b.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''
WHERE mf.CURR_REC_IND=''1''

UNION DISTINCT

SELECT DISTINCT
  INITCAP(a.ADR_CITY) AS CITY_NM
FROM (SELECT * FROM ${USER_BRONZE_CATALOG}.${USER_BRONZE_SCHEMA}.t_re_multi_address WHERE TRIM(CDE_ADDR_USAGE) IN (''R'',''M'') AND CURR_REC_IND=''1'') a
JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.mbr_fndtn mf ON a.SAK_RECIP = mf.SRC_KEY_ID
LEFT JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.cnty_cd c ON a.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''
WHERE mf.CURR_REC_IND=''1''',
    'T_RE_BASE|T_RE_MULTI_ADDRESS|MBR_FNDTN|CNTY_CD',
    't_re_base|t_re_multi_address|mbr_fndtn|cnty_cd',
    'ADR_CITY|SAK_RECIP|CDE_COUNTY|CDE_ADDR_USAGE|CURR_REC_IND',
    'ADR_CITY|SAK_RECIP|CDE_COUNTY|CDE_ADDR_USAGE|CURR_REC_IND',
    'ADR_CITY: City name from recipient address|SAK_RECIP: Recipient identifier|CDE_COUNTY: County code|CDE_ADDR_USAGE: Address usage type|CURR_REC_IND: Current record indicator',
    'STRING|BIGINT|STRING|STRING|STRING',
    'Member',
    'MANY_TO_ONE',
    'INITCAP',
    '{
  "patternType": "UNION_WITH_JOINS",
  "outputColumn": "CITY_NM",
  "outputTransformation": "INITCAP",
  "description": "Extract and format city name from address tables",
  "userColumnsToMap": [
    {"role": "output", "semanticName": "city_name", "description": "City name from address"},
    {"role": "join_key_source", "semanticName": "recipient_id", "description": "Source recipient/member identifier"},
    {"role": "filter", "semanticName": "current_record_indicator", "description": "Current record flag"}
  ],
  "userTablesToMap": [
    {"role": "primary_source", "semanticName": "recipient_base", "description": "Primary recipient base table"},
    {"role": "secondary_source", "semanticName": "recipient_multi_address", "description": "Multi-address table"}
  ]
}',
    0.92,
    'Standard city extraction pattern with INITCAP formatting.',
    'ACTIVE',
    TRUE,
    'historical_load',
    CURRENT_TIMESTAMP(),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP(),
    NULL
FROM ${CATALOG_SCHEMA}.semantic_fields sf
WHERE UPPER(sf.tgt_table_physical_name) = 'MBR_CNTCT'
  AND UPPER(sf.tgt_column_physical_name) = 'CITY_NM'
LIMIT 1;


-- Pattern 5: ST_CD - State Code
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id,
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
    confidence_score,
    ai_reasoning,
    mapping_status,
    is_approved_pattern,
    pattern_approved_by,
    pattern_approved_ts,
    mapped_by,
    mapped_ts,
    project_id
)
SELECT 
    sf.semantic_field_id,
    'MEMBER CONTACT',
    'MBR_CNTCT',
    'State Code',
    'ST_CD',
    'State of mailing address of member or recipient in MEMBER CONTACT table.',
    'SELECT DISTINCT
  b.ADR_STATE AS ST_CD
FROM ${USER_BRONZE_CATALOG}.${USER_BRONZE_SCHEMA}.t_re_base b
JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.mbr_fndtn mf ON b.SAK_RECIP = mf.SRC_KEY_ID AND b.CURR_REC_IND=''1''
LEFT JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.cnty_cd c ON b.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''
WHERE mf.CURR_REC_IND=''1''

UNION DISTINCT

SELECT DISTINCT
  a.ADR_STATE AS ST_CD
FROM (SELECT * FROM ${USER_BRONZE_CATALOG}.${USER_BRONZE_SCHEMA}.t_re_multi_address WHERE TRIM(CDE_ADDR_USAGE) IN (''R'',''M'') AND CURR_REC_IND=''1'') a
JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.mbr_fndtn mf ON a.SAK_RECIP = mf.SRC_KEY_ID
LEFT JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.cnty_cd c ON a.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''
WHERE mf.CURR_REC_IND=''1''',
    'T_RE_BASE|T_RE_MULTI_ADDRESS|MBR_FNDTN|CNTY_CD',
    't_re_base|t_re_multi_address|mbr_fndtn|cnty_cd',
    'ADR_STATE|SAK_RECIP|CDE_COUNTY|CDE_ADDR_USAGE|CURR_REC_IND',
    'ADR_STATE|SAK_RECIP|CDE_COUNTY|CDE_ADDR_USAGE|CURR_REC_IND',
    'ADR_STATE: State code from recipient address|SAK_RECIP: Recipient identifier|CDE_COUNTY: County code|CDE_ADDR_USAGE: Address usage type|CURR_REC_IND: Current record indicator',
    'STRING|BIGINT|STRING|STRING|STRING',
    'Member',
    'MANY_TO_ONE',
    'Direct',
    '{
  "patternType": "UNION_WITH_JOINS",
  "outputColumn": "ST_CD",
  "description": "Extract state code from address tables - no transformation needed",
  "userColumnsToMap": [
    {"role": "output", "semanticName": "state_code", "description": "Two-letter state code"},
    {"role": "join_key_source", "semanticName": "recipient_id", "description": "Source recipient/member identifier"},
    {"role": "filter", "semanticName": "current_record_indicator", "description": "Current record flag"}
  ],
  "userTablesToMap": [
    {"role": "primary_source", "semanticName": "recipient_base", "description": "Primary recipient base table"},
    {"role": "secondary_source", "semanticName": "recipient_multi_address", "description": "Multi-address table"}
  ]
}',
    0.94,
    'Standard state code extraction - direct mapping with no transformation.',
    'ACTIVE',
    TRUE,
    'historical_load',
    CURRENT_TIMESTAMP(),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP(),
    NULL
FROM ${CATALOG_SCHEMA}.semantic_fields sf
WHERE UPPER(sf.tgt_table_physical_name) = 'MBR_CNTCT'
  AND UPPER(sf.tgt_column_physical_name) = 'ST_CD'
LIMIT 1;


-- Pattern 6: CNTCT_TYP_CD - Contact Type Code (with hardcoded value for base)
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    semantic_field_id,
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
    confidence_score,
    ai_reasoning,
    mapping_status,
    is_approved_pattern,
    pattern_approved_by,
    pattern_approved_ts,
    mapped_by,
    mapped_ts,
    project_id
)
SELECT 
    sf.semantic_field_id,
    'MEMBER CONTACT',
    'MBR_CNTCT',
    'Contact Type Code',
    'CNTCT_TYP_CD',
    'Code which indicates the contact type. Reference record from contact type table.',
    'SELECT DISTINCT
  ''BSE'' AS CNTCT_TYP_CD
FROM ${USER_BRONZE_CATALOG}.${USER_BRONZE_SCHEMA}.t_re_base b
JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.mbr_fndtn mf ON b.SAK_RECIP = mf.SRC_KEY_ID AND b.CURR_REC_IND=''1''
WHERE mf.CURR_REC_IND=''1''

UNION DISTINCT

SELECT DISTINCT
  TRIM(a.CDE_ADDR_USAGE) AS CNTCT_TYP_CD
FROM (SELECT * FROM ${USER_BRONZE_CATALOG}.${USER_BRONZE_SCHEMA}.t_re_multi_address WHERE TRIM(CDE_ADDR_USAGE) IN (''R'',''M'') AND CURR_REC_IND=''1'') a
JOIN ${SILVER_CATALOG}.${SILVER_SCHEMA}.mbr_fndtn mf ON a.SAK_RECIP = mf.SRC_KEY_ID
WHERE mf.CURR_REC_IND=''1''',
    'T_RE_BASE|T_RE_MULTI_ADDRESS|MBR_FNDTN',
    't_re_base|t_re_multi_address|mbr_fndtn',
    'CDE_ADDR_USAGE|SAK_RECIP|CURR_REC_IND',
    'CDE_ADDR_USAGE|SAK_RECIP|CURR_REC_IND',
    'CDE_ADDR_USAGE: Address usage type code (R=Residential, M=Mailing)|SAK_RECIP: Recipient identifier|CURR_REC_IND: Current record indicator',
    'STRING|BIGINT|STRING',
    'Member',
    'MANY_TO_ONE',
    'Hardcoded|TRIM',
    '{
  "patternType": "UNION_WITH_JOINS",
  "outputColumn": "CNTCT_TYP_CD",
  "description": "Contact type derived from address usage code, with hardcoded BSE for base addresses",
  "notes": "First branch uses hardcoded BSE for base table, second branch uses actual address usage code",
  "userColumnsToMap": [
    {"role": "output", "semanticName": "address_usage_code", "description": "Address usage type (for multi-address only)"},
    {"role": "join_key_source", "semanticName": "recipient_id", "description": "Source recipient/member identifier"},
    {"role": "filter", "semanticName": "current_record_indicator", "description": "Current record flag"}
  ],
  "userTablesToMap": [
    {"role": "primary_source", "semanticName": "recipient_base", "description": "Primary recipient base table"},
    {"role": "secondary_source", "semanticName": "recipient_multi_address", "description": "Multi-address table"}
  ]
}',
    0.88,
    'Contact type pattern with hardcoded value for base and derived value for multi-address.',
    'ACTIVE',
    TRUE,
    'historical_load',
    CURRENT_TIMESTAMP(),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP(),
    NULL
FROM ${CATALOG_SCHEMA}.semantic_fields sf
WHERE UPPER(sf.tgt_table_physical_name) = 'MBR_CNTCT'
  AND UPPER(sf.tgt_column_physical_name) = 'CNTCT_TYP_CD'
LIMIT 1;


-- ============================================================================
-- STEP 2: CREATE A TEST PROJECT
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.mapping_projects (
    project_name,
    project_description,
    source_system_name,
    source_catalogs,
    source_schemas,
    target_catalogs,
    target_schemas,
    target_domains,
    project_status,
    created_by,
    created_ts
) VALUES (
    'ACME State Medicaid Migration',
    'Migration of member data from ACME state legacy MMIS system to Gainwell silver layer. Focus on Member Contact information.',
    'ACME_MMIS',
    'bronze_acme',
    'mmis_member',
    'silver_acme',
    'member',
    'Member',
    'NOT_STARTED',
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP()
);


-- ============================================================================
-- STEP 3: INSERT UNMAPPED SOURCE FIELDS (SIMULATING USER UPLOAD)
-- These are source fields from a hypothetical new state that need mapping
-- They have similar semantics to the original DMES fields but different names
-- ============================================================================

-- Get the project ID we just created
-- Note: In practice, you'd use the actual project_id returned from the insert

-- Source Table 1: RECIPIENT_MASTER (equivalent to t_re_base)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Master',
    'recipient_master',
    'Recipient Key',
    'RECIP_KEY',
    'NO',
    'BIGINT',
    'Unique identifier for each recipient/member in the master table. Used as primary key and for joining to other tables.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Master',
    'recipient_master',
    'Street Address Line 1',
    'STREET_ADDR_1',
    'YES',
    'STRING',
    'Primary street address of the recipient. Contains house number and street name.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Master',
    'recipient_master',
    'Street Address Line 2',
    'STREET_ADDR_2',
    'YES',
    'STRING',
    'Secondary street address line. Contains apartment number, suite, unit, etc.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Master',
    'recipient_master',
    'City',
    'CITY',
    'YES',
    'STRING',
    'City name portion of recipient mailing address.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Master',
    'recipient_master',
    'State',
    'STATE',
    'YES',
    'STRING',
    'Two-letter state code for recipient address.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Master',
    'recipient_master',
    'County Code',
    'COUNTY_CD',
    'YES',
    'STRING',
    'County FIPS code for recipient residence.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Master',
    'recipient_master',
    'Active Flag',
    'ACTIVE_FLG',
    'NO',
    'STRING',
    'Indicates if this is the current active record. Y=Active, N=Inactive.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();


-- Source Table 2: RECIPIENT_ALTERNATE_ADDRESS (equivalent to t_re_multi_address)
INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Alternate Address',
    'recipient_alt_addr',
    'Recipient Key',
    'RECIP_KEY',
    'NO',
    'BIGINT',
    'Foreign key to recipient master table. Links alternate addresses to main recipient record.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Alternate Address',
    'recipient_alt_addr',
    'Address Type',
    'ADDR_TYPE',
    'NO',
    'STRING',
    'Type of address: R=Residential, M=Mailing, W=Work, T=Temporary.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Alternate Address',
    'recipient_alt_addr',
    'Street Line 1',
    'STREET_LN_1',
    'YES',
    'STRING',
    'Primary street address for alternate address.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Alternate Address',
    'recipient_alt_addr',
    'Street Line 2',
    'STREET_LN_2',
    'YES',
    'STRING',
    'Secondary street address for alternate address.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Alternate Address',
    'recipient_alt_addr',
    'City Name',
    'CITY_NM',
    'YES',
    'STRING',
    'City for alternate address.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Alternate Address',
    'recipient_alt_addr',
    'State Code',
    'STATE_CD',
    'YES',
    'STRING',
    'Two-letter state code for alternate address.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Alternate Address',
    'recipient_alt_addr',
    'County',
    'COUNTY',
    'YES',
    'STRING',
    'County code for alternate address.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
    src_table_name,
    src_table_physical_name,
    src_column_name,
    src_column_physical_name,
    src_nullable,
    src_physical_datatype,
    src_comments,
    domain,
    mapping_status,
    project_id,
    uploaded_by,
    uploaded_ts
)
SELECT 
    'Recipient Alternate Address',
    'recipient_alt_addr',
    'Current Indicator',
    'CURR_IND',
    'NO',
    'STRING',
    'Indicates if this alternate address is current. Y=Current, N=Historical.',
    'Member',
    'UNMAPPED',
    (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects),
    'david.galluzzo@gainwelltechnologies.com',
    CURRENT_TIMESTAMP();


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check mapped_fields patterns created
SELECT 
    mapped_field_id,
    tgt_table_physical_name,
    tgt_column_physical_name,
    source_relationship_type,
    transformations_applied,
    confidence_score,
    is_approved_pattern
FROM ${CATALOG_SCHEMA}.mapped_fields
WHERE tgt_table_physical_name = 'MBR_CNTCT'
ORDER BY tgt_column_physical_name;

-- Check project created
SELECT * FROM ${CATALOG_SCHEMA}.mapping_projects;

-- Check unmapped fields created
SELECT 
    unmapped_field_id,
    src_table_physical_name,
    src_column_physical_name,
    src_comments,
    project_id
FROM ${CATALOG_SCHEMA}.unmapped_fields
WHERE project_id = (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects)
ORDER BY src_table_physical_name, src_column_physical_name;

-- Summary
SELECT 
    'mapped_fields patterns' as data_type, 
    COUNT(*) as count 
FROM ${CATALOG_SCHEMA}.mapped_fields 
WHERE tgt_table_physical_name = 'MBR_CNTCT'
UNION ALL
SELECT 
    'projects' as data_type, 
    COUNT(*) as count 
FROM ${CATALOG_SCHEMA}.mapping_projects
UNION ALL
SELECT 
    'unmapped source fields' as data_type, 
    COUNT(*) as count 
FROM ${CATALOG_SCHEMA}.unmapped_fields 
WHERE project_id = (SELECT MAX(project_id) FROM ${CATALOG_SCHEMA}.mapping_projects);

