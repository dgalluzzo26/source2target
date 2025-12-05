-- ============================================================================
-- Source-to-Target Mapping Platform V3 - Schema Additions
-- ============================================================================
-- 
-- NEW TABLES:
-- 1. mapping_patterns - Complete mapping history for AI learning (vector-searchable)
-- 2. mapping_unions - Union relationships for multi-table mappings
--
-- ALTERATIONS:
-- 1. mapped_fields - Add source_relationship_type column
-- 2. mapping_feedback - Add source description columns for vector search
--
-- ============================================================================

-- ============================================================================
-- TABLE 1: mapping_patterns (Complete Mapping History for AI Learning)
-- ============================================================================
-- Purpose: Store complete mappings as single rows for vector search.
-- Each row represents a FULL mapping with all source fields, transformations,
-- and join conditions - like the "export mapping" output.
--
-- This enables:
-- 1. Vector search on past mappings using source descriptions
-- 2. AI to learn from complete patterns (not just column pairs)
-- 3. Suggest multi-field mappings and transformations based on history
-- ============================================================================

CREATE TABLE IF NOT EXISTS oztest_dev.source2target.mapping_patterns (
  pattern_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- Link to actual mapping (for reference, may be NULL if mapping was deleted)
  mapped_field_id BIGINT COMMENT 'FK to mapped_fields (NULL if deleted)',
  
  -- ========== SOURCE SIDE (Complete Picture) ==========
  -- JSON array of all source fields with their details
  source_fields_json STRING NOT NULL COMMENT 'JSON array: [{table, column, description, datatype, transformations, order}, ...]',
  
  -- Flattened source info for vector search
  source_tables STRING NOT NULL COMMENT 'Comma-separated source table names',
  source_columns STRING NOT NULL COMMENT 'Comma-separated source column names',
  source_descriptions STRING COMMENT 'Combined source column descriptions (for vector search)',
  source_datatypes STRING COMMENT 'Comma-separated source data types',
  
  -- Number of source fields (for multi-field detection)
  source_field_count INT NOT NULL DEFAULT 1 COMMENT 'Number of source fields in this mapping',
  
  -- ========== TARGET SIDE ==========
  tgt_table_name STRING NOT NULL COMMENT 'Target table name',
  tgt_column_name STRING NOT NULL COMMENT 'Target column name',
  tgt_table_physical_name STRING NOT NULL COMMENT 'Target table physical name',
  tgt_column_physical_name STRING NOT NULL COMMENT 'Target column physical name',
  tgt_description STRING COMMENT 'Target column description',
  tgt_datatype STRING COMMENT 'Target column data type',
  
  -- ========== TRANSFORMATION DETAILS ==========
  concat_strategy STRING COMMENT 'How sources are combined: NONE, SPACE, COMMA, PIPE, CUSTOM',
  concat_separator STRING COMMENT 'Custom separator if strategy is CUSTOM',
  transformation_expression STRING COMMENT 'Full SQL transformation expression',
  transformations_applied STRING COMMENT 'Comma-separated list of transformations used (TRIM, UPPER, etc)',
  
  -- ========== RELATIONSHIP TYPE ==========
  source_relationship_type STRING DEFAULT 'SINGLE' COMMENT 'How sources relate: SINGLE, JOIN, UNION',
  
  -- ========== JOIN DETAILS (if multi-table with joins) ==========
  has_joins BOOLEAN DEFAULT false COMMENT 'Whether this mapping requires joins',
  joins_json STRING COMMENT 'JSON array of join conditions: [{left_table, left_col, right_table, right_col, join_type}, ...]',
  
  -- ========== UNION DETAILS (if multi-table with unions) ==========
  has_unions BOOLEAN DEFAULT false COMMENT 'Whether this mapping uses unions',
  unions_json STRING COMMENT 'JSON array of union details: [{table, column, union_type, order}, ...]',
  
  -- ========== SEMANTIC FIELD FOR VECTOR SEARCH ==========
  -- This is the key field for vector search - combines all source info
  source_semantic_field STRING GENERATED ALWAYS AS (
    CONCAT_WS(' | ',
      CONCAT('SOURCE TABLES: ', COALESCE(source_tables, '')),
      CONCAT('SOURCE COLUMNS: ', COALESCE(source_columns, '')),
      CONCAT('SOURCE DESCRIPTIONS: ', COALESCE(source_descriptions, '')),
      CONCAT('SOURCE TYPES: ', COALESCE(source_datatypes, '')),
      CONCAT('TRANSFORMATIONS: ', COALESCE(transformations_applied, '')),
      CONCAT('RELATIONSHIP: ', COALESCE(source_relationship_type, 'SINGLE')),
      CONCAT('MULTI-FIELD: ', CAST(source_field_count > 1 AS STRING))
    )
  ) COMMENT 'Combined source semantic field for vector embedding',
  
  -- ========== AUDIT FIELDS ==========
  domain STRING COMMENT 'Domain category',
  created_by STRING COMMENT 'User who created this mapping',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'When pattern was recorded',
  
  CONSTRAINT pk_mapping_patterns PRIMARY KEY (pattern_id)
)
COMMENT 'Complete mapping patterns for AI learning. Each row = one full mapping with all context.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);

-- Enable Liquid Clustering for performance
ALTER TABLE oztest_dev.source2target.mapping_patterns 
CLUSTER BY (domain, source_field_count, source_relationship_type);


-- ============================================================================
-- TABLE 2: mapping_unions (Union Relationships for Multi-Table Mappings)
-- ============================================================================
-- Purpose: Define union relationships when source fields come from multiple 
-- tables that should be stacked vertically (rather than joined horizontally).
--
-- Use Case: Combining data from multiple years/sources
-- Example: claims_2022 UNION ALL claims_2023 → target.claims
-- ============================================================================

CREATE TABLE IF NOT EXISTS oztest_dev.source2target.mapping_unions (
  mapping_union_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- Parent mapping reference
  mapped_field_id BIGINT NOT NULL COMMENT 'Foreign key to mapped_fields table',
  
  -- Source table being unioned
  source_table_name STRING NOT NULL COMMENT 'Source table logical name',
  source_table_physical_name STRING NOT NULL COMMENT 'Source table physical name',
  
  -- Which column from this table maps to the target
  source_column_name STRING NOT NULL COMMENT 'Column from this table for the target',
  source_column_physical_name STRING NOT NULL COMMENT 'Physical column name',
  
  -- Union type and ordering
  union_type STRING DEFAULT 'UNION ALL' COMMENT 'UNION (removes duplicates) or UNION ALL (keeps all)',
  union_order INT NOT NULL COMMENT 'Order of tables in the union (1, 2, 3...)',
  
  -- Optional filter for this table in the union
  where_clause STRING COMMENT 'Optional WHERE clause for this table (e.g., year = 2023)',
  
  -- Audit fields
  created_by STRING COMMENT 'User who defined this union',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'When union was created',
  updated_by STRING COMMENT 'User who last updated',
  updated_ts TIMESTAMP COMMENT 'When last updated',
  
  CONSTRAINT pk_mapping_unions PRIMARY KEY (mapping_union_id),
  CONSTRAINT fk_union_mapped FOREIGN KEY (mapped_field_id) REFERENCES oztest_dev.source2target.mapped_fields(mapped_field_id)
  -- Note: FOREIGN KEY is informational only (not enforced by Databricks)
)
COMMENT 'Union relationships for mappings that combine data from multiple source tables vertically. Foreign key is informational only.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);

-- Enable Liquid Clustering for performance
ALTER TABLE oztest_dev.source2target.mapping_unions 
CLUSTER BY (mapped_field_id, union_order);


-- ============================================================================
-- ALTERATION 1: Add source_relationship_type to mapped_fields
-- ============================================================================
-- Purpose: Track how multiple source tables/columns relate in a mapping
-- Values: SINGLE (default), JOIN, UNION
-- ============================================================================

ALTER TABLE oztest_dev.source2target.mapped_fields 
ADD COLUMN source_relationship_type STRING DEFAULT 'SINGLE' 
COMMENT 'How multiple sources relate: SINGLE (one source), JOIN (horizontal), UNION (vertical)';


-- ============================================================================
-- ALTERATION 2: Add source descriptions to mapping_feedback for vector search
-- ============================================================================
-- Purpose: Enable semantic vector search on rejection history
-- These fields capture the source context at time of rejection
-- ============================================================================

ALTER TABLE oztest_dev.source2target.mapping_feedback 
ADD COLUMN src_comments STRING COMMENT 'Source column description at time of feedback';

ALTER TABLE oztest_dev.source2target.mapping_feedback 
ADD COLUMN src_datatype STRING COMMENT 'Source column data type at time of feedback';

ALTER TABLE oztest_dev.source2target.mapping_feedback 
ADD COLUMN tgt_comments STRING COMMENT 'Target column description at time of feedback';

-- Add computed semantic field for vector search on rejections
-- Note: Databricks may require this as a separate UPDATE or view
-- ALTER TABLE oztest_dev.source2target.mapping_feedback 
-- ADD COLUMN source_semantic_field STRING GENERATED ALWAYS AS (
--   CONCAT_WS(' | ',
--     CONCAT('TABLE: ', COALESCE(suggested_src_table, '')),
--     CONCAT('COLUMN: ', COALESCE(suggested_src_column, '')),
--     CONCAT('DESCRIPTION: ', COALESCE(src_comments, '')),
--     CONCAT('TYPE: ', COALESCE(src_datatype, ''))
--   )
-- ) COMMENT 'Combined semantic field for vector search on rejections';


-- ============================================================================
-- VECTOR SEARCH INDEXES (Run after tables are created and have data)
-- ============================================================================
-- 
-- Index 1: mapping_patterns (for historical pattern search)
-- CREATE VECTOR SEARCH INDEX mapping_patterns_semantic_idx
-- ON oztest_dev.source2target.mapping_patterns (source_semantic_field)
-- USING delta_sync
-- WITH (pipeline_type = "TRIGGERED");
--
-- Index 2: mapping_feedback (for rejection avoidance search)
-- CREATE VECTOR SEARCH INDEX feedback_rejection_idx
-- ON oztest_dev.source2target.mapping_feedback (source_semantic_field)
-- USING delta_sync
-- WITH (pipeline_type = "TRIGGERED");
--
-- ============================================================================


-- ============================================================================
-- EXAMPLE DATA: What a mapping_patterns row looks like
-- ============================================================================
-- 
-- pattern_id: 1
-- mapped_field_id: 42
-- source_fields_json: '[
--   {"table": "member", "column": "first_name", "description": "Member first name", 
--    "datatype": "STRING", "transformations": "TRIM,UPPER", "order": 1},
--   {"table": "member", "column": "last_name", "description": "Member last name", 
--    "datatype": "STRING", "transformations": "TRIM,UPPER", "order": 2}
-- ]'
-- source_tables: "member"
-- source_columns: "first_name, last_name"
-- source_descriptions: "Member first name, Member last name"
-- source_datatypes: "STRING, STRING"
-- source_field_count: 2
-- tgt_table_name: "Member"
-- tgt_column_name: "Full Name"
-- tgt_description: "Complete member name"
-- concat_strategy: "SPACE"
-- transformation_expression: "CONCAT(TRIM(UPPER(first_name)), ' ', TRIM(UPPER(last_name)))"
-- transformations_applied: "TRIM, UPPER"
-- source_relationship_type: "SINGLE"
-- has_joins: false
-- has_unions: false
-- source_semantic_field: "SOURCE TABLES: member | SOURCE COLUMNS: first_name, last_name | 
--                         SOURCE DESCRIPTIONS: Member first name, Member last name | ..."
--
-- ============================================================================


-- ============================================================================
-- EXAMPLE DATA: What a mapping_unions row looks like (for UNION mappings)
-- ============================================================================
-- 
-- Example: Combining claims from multiple years
--
-- mapping_union_id: 1
-- mapped_field_id: 100
-- source_table_name: "Claims 2022"
-- source_table_physical_name: "claims_2022"
-- source_column_name: "claim_amount"
-- source_column_physical_name: "claim_amt"
-- union_type: "UNION ALL"
-- union_order: 1
-- where_clause: NULL
--
-- mapping_union_id: 2
-- mapped_field_id: 100 (same mapping)
-- source_table_name: "Claims 2023"
-- source_table_physical_name: "claims_2023"
-- source_column_name: "claim_amount"
-- source_column_physical_name: "claim_amt"
-- union_type: "UNION ALL"
-- union_order: 2
-- where_clause: NULL
--
-- Generated SQL:
-- SELECT claim_amt FROM claims_2022
-- UNION ALL
-- SELECT claim_amt FROM claims_2023
--
-- ============================================================================


-- ============================================================================
-- CONFIG ADDITIONS (Add to app_config.json)
-- ============================================================================
-- 
-- {
--   "database": {
--     "mapping_patterns_table": "mapping_patterns",
--     "mapping_unions_table": "mapping_unions"
--   },
--   "vector_search": {
--     "patterns_index_name": "oztest_dev.source2target.mapping_patterns_semantic_idx",
--     "feedback_index_name": "oztest_dev.source2target.feedback_rejection_idx"
--   }
-- }
--
-- ============================================================================


-- ============================================================================
-- END OF V3 SCHEMA ADDITIONS
-- ============================================================================

