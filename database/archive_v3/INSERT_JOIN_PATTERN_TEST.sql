-- ============================================================================
-- Smart Mapper V3 - Test Data for Complex JOIN/UNION Pattern
-- ============================================================================
-- 
-- This script inserts:
-- 1. A complex mapped_field with JOIN/UNION pattern (for AI to learn from)
-- 2. Unmapped fields that should match this pattern (for testing)
--
-- ============================================================================
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema
-- ============================================================================


-- ============================================================================
-- STEP 1: Insert the Complex JOIN/UNION Pattern into mapped_fields
-- ============================================================================
-- This represents a previous client's mapping that used JOINs and UNION
-- to derive MBR_SK in MBR_CNTCT from source tables

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
  confidence_score,
  mapping_source,
  ai_reasoning,
  ai_generated,
  mapping_status,
  mapped_by,
  join_metadata
)
VALUES (
  -- Get the semantic_field_id for MBR_CNTCT.MBR_SK
  (SELECT semantic_field_id FROM ${CATALOG_SCHEMA}.semantic_fields 
   WHERE tgt_table_physical_name = 'MBR_CNTCT' AND tgt_column_physical_name = 'MBR_SK' LIMIT 1),
  
  -- Target field info (denormalized)
  'MEMBER CONTACT',
  'MBR_CNTCT',
  'Member Sk',
  'MBR_SK',
  'Unique identifier for a given member. Auto generated key in MEMBER CONTACT table.',
  
  -- The complete SQL expression
  'SELECT DISTINCT
  mf.MBR_SK
FROM oz_dev.bronze_dmes_de.t_re_base b
join oz_dev.silver_dmes_de.mbr_fndtn mf on b.SAK_RECIP = mf.SRC_KEY_ID AND b.CURR_REC_IND=''1''
LEFT JOIN oz_dev.silver_dmes_de.cnty_cd c on b.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''
where mf.CURR_REC_IND=''1''

UNION DISTINCT

SELECT DISTINCT
  mf.MBR_SK
FROM (select * from oz_dev.bronze_dmes_de.t_re_multi_address where trim(CDE_ADDR_USAGE) in (''R'',''M'') and CURR_REC_IND=''1'')a
join oz_dev.silver_dmes_de.mbr_fndtn mf on a.SAK_RECIP = mf.SRC_KEY_ID
LEFT JOIN oz_dev.silver_dmes_de.cnty_cd c on a.CDE_COUNTY = c.CNTY_ID AND c.CURR_REC_IND=''1''
where mf.CURR_REC_IND=''1''',
  
  -- Source tables (pipe-separated)
  'Recipient Base | Multi Address | Member Foundation | County Code',
  't_re_base | t_re_multi_address | mbr_fndtn | cnty_cd',
  
  -- Source columns (pipe-separated)
  'SAK_RECIP | CDE_COUNTY | CDE_ADDR_USAGE | CURR_REC_IND',
  'SAK_RECIP | CDE_COUNTY | CDE_ADDR_USAGE | CURR_REC_IND',
  
  -- Source descriptions
  'Recipient surrogate key for joining to member foundation | County code for county lookup | Address usage type code (R=Residential, M=Mailing) | Current record indicator flag',
  
  -- Source datatypes
  'BIGINT | STRING | STRING | STRING',
  
  -- Domain
  'member',
  
  -- Relationship type
  'UNION',
  
  -- Transformations
  'LOOKUP, JOIN, UNION, FILTER',
  
  -- Confidence
  0.95,
  
  -- Mapping source
  'MANUAL',
  
  -- AI reasoning
  'Complex pattern: Union of two source tables joined to member foundation to derive MBR_SK. Both branches use SAK_RECIP to join to mbr_fndtn.SRC_KEY_ID.',
  
  -- AI generated
  false,
  
  -- Status
  'ACTIVE',
  
  -- Mapped by
  'data_engineer',
  
  -- JOIN METADATA (structured JSON for template UI)
  '{
    "patternType": "UNION_WITH_JOINS",
    "outputColumn": "MBR_SK",
    "outputTable": "mbr_fndtn",
    "outputAlias": "mf",
    
    "unionBranches": [
      {
        "branchIndex": 1,
        "branchName": "Base Records",
        
        "userSourceTable": {
          "originalName": "t_re_base",
          "alias": "b",
          "schema": "bronze_dmes_de",
          "description": "Primary recipient base table with core member info"
        },
        
        "joins": [
          {
            "joinType": "INNER",
            "targetTable": {
              "name": "mbr_fndtn",
              "alias": "mf",
              "schema": "silver_dmes_de",
              "isSharedSilver": true
            },
            "conditions": [
              {
                "type": "column_match",
                "sourceColumn": "SAK_RECIP",
                "sourceDescription": "Recipient surrogate key",
                "targetColumn": "SRC_KEY_ID",
                "targetDescription": "Source system key ID in member foundation"
              },
              {
                "type": "filter",
                "sourceColumn": "CURR_REC_IND",
                "operator": "=",
                "value": "1",
                "description": "Current record indicator"
              }
            ]
          },
          {
            "joinType": "LEFT",
            "targetTable": {
              "name": "cnty_cd",
              "alias": "c",
              "schema": "silver_dmes_de",
              "isSharedSilver": true
            },
            "conditions": [
              {
                "type": "column_match",
                "sourceColumn": "CDE_COUNTY",
                "sourceDescription": "County code",
                "targetColumn": "CNTY_ID",
                "targetDescription": "County identifier"
              },
              {
                "type": "filter",
                "targetColumn": "CURR_REC_IND",
                "operator": "=",
                "value": "1"
              }
            ]
          }
        ],
        
        "whereFilters": ["mf.CURR_REC_IND=''1''"]
      },
      
      {
        "branchIndex": 2,
        "branchName": "Multi-Address Records",
        
        "userSourceTable": {
          "originalName": "t_re_multi_address",
          "alias": "a",
          "schema": "bronze_dmes_de",
          "description": "Multi-address table for alternate addresses",
          "subqueryFilter": "trim(CDE_ADDR_USAGE) in (''R'',''M'') and CURR_REC_IND=''1''"
        },
        
        "joins": [
          {
            "joinType": "INNER",
            "targetTable": {
              "name": "mbr_fndtn",
              "alias": "mf",
              "schema": "silver_dmes_de",
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
          },
          {
            "joinType": "LEFT",
            "targetTable": {
              "name": "cnty_cd",
              "alias": "c",
              "schema": "silver_dmes_de",
              "isSharedSilver": true
            },
            "conditions": [
              {
                "type": "column_match",
                "sourceColumn": "CDE_COUNTY",
                "targetColumn": "CNTY_ID"
              },
              {
                "type": "filter",
                "targetColumn": "CURR_REC_IND",
                "operator": "=",
                "value": "1"
              }
            ]
          }
        ],
        
        "whereFilters": ["mf.CURR_REC_IND=''1''"]
      }
    ],
    
    "userColumnsToMap": [
      {
        "placeholder": "SAK_RECIP",
        "description": "Recipient/Member surrogate key - joins to mbr_fndtn.SRC_KEY_ID",
        "usedInBranches": [1, 2],
        "required": true,
        "joinTarget": "mbr_fndtn.SRC_KEY_ID"
      },
      {
        "placeholder": "CDE_COUNTY",
        "description": "County code for optional county lookup",
        "usedInBranches": [1, 2],
        "required": false,
        "joinTarget": "cnty_cd.CNTY_ID"
      },
      {
        "placeholder": "CDE_ADDR_USAGE",
        "description": "Address usage type filter (R=Residential, M=Mailing)",
        "usedInBranches": [2],
        "required": true,
        "filterValues": ["R", "M"]
      },
      {
        "placeholder": "CURR_REC_IND",
        "description": "Current record indicator flag",
        "usedInBranches": [1, 2],
        "required": true,
        "filterValue": "1"
      }
    ],
    
    "userTablesToMap": [
      {
        "placeholder": "t_re_base",
        "description": "Primary source table with member base information",
        "usedInBranch": 1,
        "required": true
      },
      {
        "placeholder": "t_re_multi_address",
        "description": "Secondary source table with address records",
        "usedInBranch": 2,
        "required": true
      }
    ],
    
    "sharedSilverTables": [
      {
        "name": "mbr_fndtn",
        "schema": "silver_dmes_de",
        "description": "Member Foundation - master member record",
        "keyColumn": "SRC_KEY_ID"
      },
      {
        "name": "cnty_cd",
        "schema": "silver_dmes_de",
        "description": "County Code lookup table",
        "keyColumn": "CNTY_ID"
      }
    ]
  }'
);


-- ============================================================================
-- STEP 2: Insert Unmapped Fields for Testing
-- ============================================================================
-- These are fields from a NEW client that should match the pattern above
-- Names are DIFFERENT but descriptions are SIMILAR

-- Test Client: "wellness_claims" system
-- Has similar tables/columns with different names

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields (
  src_table_name,
  src_table_physical_name,
  src_column_name,
  src_column_physical_name,
  src_physical_datatype,
  src_comments,
  domain,
  uploaded_by
) VALUES
-- Primary table: patient_base (equivalent to t_re_base)
(
  'Patient Base',
  'patient_base',
  'Patient Key',
  'patient_key',
  'BIGINT',
  'Unique patient identifier used for joining to member foundation tables',
  'member',
  'test_user'
),
(
  'Patient Base',
  'patient_base',
  'County Code',
  'county_cd',
  'STRING',
  'County code for geographic classification and county lookup',
  'member',
  'test_user'
),
(
  'Patient Base',
  'patient_base',
  'Active Record Flag',
  'active_rec_flg',
  'STRING',
  'Indicator showing if this is the current active record (Y/N or 1/0)',
  'member',
  'test_user'
),

-- Secondary table: patient_addresses (equivalent to t_re_multi_address)
(
  'Patient Addresses',
  'patient_addresses',
  'Patient Key',
  'patient_key',
  'BIGINT',
  'Patient identifier linking to member foundation',
  'member',
  'test_user'
),
(
  'Patient Addresses',
  'patient_addresses',
  'County Code',
  'county_cd',
  'STRING',
  'County code for the address location',
  'member',
  'test_user'
),
(
  'Patient Addresses',
  'patient_addresses',
  'Address Type',
  'addr_type_cd',
  'STRING',
  'Type of address - Residential, Mailing, Work, etc.',
  'member',
  'test_user'
),
(
  'Patient Addresses',
  'patient_addresses',
  'Current Flag',
  'curr_flg',
  'STRING',
  'Flag indicating if this is a current record',
  'member',
  'test_user'
);


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify the mapped pattern was inserted
-- SELECT mapped_field_id, tgt_column_name, source_relationship_type, 
--        LENGTH(join_metadata) as metadata_length
-- FROM ${CATALOG_SCHEMA}.mapped_fields 
-- WHERE tgt_column_physical_name = 'MBR_SK' 
--   AND tgt_table_physical_name = 'MBR_CNTCT'
--   AND source_relationship_type = 'UNION';

-- Verify the unmapped test fields were inserted
-- SELECT src_table_physical_name, src_column_physical_name, src_comments
-- FROM ${CATALOG_SCHEMA}.unmapped_fields
-- WHERE src_table_physical_name IN ('patient_base', 'patient_addresses')
-- ORDER BY src_table_physical_name, src_column_physical_name;

-- ============================================================================
-- EXPECTED AI BEHAVIOR
-- ============================================================================
-- 
-- When user selects "patient_key" from "patient_base":
-- 1. Vector search should find MBR_CNTCT.MBR_SK as a target
-- 2. Pattern search should find this UNION pattern
-- 3. Template UI should show:
--    - Pattern type: UNION_WITH_JOINS
--    - Branch 1: Map patient_base → t_re_base
--    - Branch 2: Map patient_addresses → t_re_multi_address
--    - Column mappings: patient_key → SAK_RECIP, county_cd → CDE_COUNTY, etc.
--    - Silver joins are auto-configured (mbr_fndtn, cnty_cd)
-- 4. Generated SQL should substitute user's table/column names
--
-- ============================================================================

