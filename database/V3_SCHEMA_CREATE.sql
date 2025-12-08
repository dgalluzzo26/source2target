-- ============================================================================
-- Smart Mapper V3 - Simplified Schema
-- ============================================================================
-- 
-- KEY CHANGES FROM V2:
-- 1. Single row per mapping - no more mapping_details, mapping_joins tables
-- 2. SQL expression captures all transformation/join/union logic
-- 3. mapped_fields has vector-searchable semantic field for AI learning
-- 4. mapping_feedback simplified for rejection tracking with vector search
--
-- TABLES:
-- 1. semantic_fields     - Target fields (vector indexed)
-- 2. unmapped_fields     - Source fields awaiting mapping
-- 3. mapped_fields       - Complete mappings with SQL expression (vector indexed)
-- 4. mapping_feedback    - Rejected suggestions (vector indexed)
-- 5. transformation_library - Reusable transformation templates
--
-- ============================================================================
-- REPLACE THIS WITH YOUR CATALOG.SCHEMA
-- ============================================================================
-- Find/Replace: ${CATALOG_SCHEMA} with your catalog.schema (e.g., oztest_dev.smartmapper)
-- ============================================================================


-- ============================================================================
-- TABLE 1: semantic_fields (Target Field Definitions)
-- ============================================================================
-- Purpose: Define target fields available for mapping
-- Vector Search: Yes - semantic_field column
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${CATALOG_SCHEMA}.semantic_fields (
  semantic_field_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- Logical names (for display/UI)
  tgt_table_name STRING NOT NULL COMMENT 'Target table logical name (display name)',
  tgt_column_name STRING NOT NULL COMMENT 'Target column logical name (display name)',
  
  -- Physical names (for database operations)
  tgt_table_physical_name STRING NOT NULL COMMENT 'Target table physical name (database name)',
  tgt_column_physical_name STRING NOT NULL COMMENT 'Target column physical name (database name)',
  
  -- Metadata
  tgt_nullable STRING DEFAULT 'YES' COMMENT 'Whether target field allows NULL values (YES/NO)',
  tgt_physical_datatype STRING COMMENT 'Physical data type (e.g., STRING, INT, DATE)',
  tgt_comments STRING COMMENT 'Description/comments for target field - CRITICAL for AI matching',
  
  -- Domain classification
  domain STRING COMMENT 'Domain category (e.g., claims, member, provider, finance, pharmacy)',
  
  -- Audit fields
  created_by STRING DEFAULT 'system' COMMENT 'User who created this record',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when record was created',
  updated_by STRING COMMENT 'User who last updated this record',
  updated_ts TIMESTAMP COMMENT 'Timestamp when record was last updated',
  
  -- VECTOR SEARCH: Computed semantic field for embedding
  semantic_field STRING GENERATED ALWAYS AS (
    CONCAT_WS(' | ',
      CONCAT('TABLE: ', COALESCE(tgt_table_name, '')),
      CONCAT('COLUMN: ', COALESCE(tgt_column_name, '')),
      CONCAT('TYPE: ', COALESCE(tgt_physical_datatype, '')),
      CONCAT('DESCRIPTION: ', COALESCE(tgt_comments, '')),
      CONCAT('DOMAIN: ', COALESCE(domain, ''))
    )
  ) COMMENT 'Concatenated field for vector embedding - used by AI to find matching targets',
  
  CONSTRAINT pk_semantic_fields PRIMARY KEY (semantic_field_id)
) 
COMMENT 'Target field definitions with semantic metadata for AI-powered mapping.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);


-- ============================================================================
-- TABLE 2: unmapped_fields (Source Fields Awaiting Mapping)
-- ============================================================================
-- Purpose: Store source fields that need to be mapped to target fields
-- Vector Search: No - but src_comments is critical for AI matching
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${CATALOG_SCHEMA}.unmapped_fields (
  unmapped_field_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- Logical names (for display/UI)
  src_table_name STRING NOT NULL COMMENT 'Source table logical name (display name)',
  src_column_name STRING NOT NULL COMMENT 'Source column logical name (display name)',
  
  -- Physical names (for database operations)
  src_table_physical_name STRING NOT NULL COMMENT 'Source table physical name (database name)',
  src_column_physical_name STRING NOT NULL COMMENT 'Source column physical name (database name)',
  
  -- Metadata - CRITICAL: src_comments drives AI matching
  src_nullable STRING DEFAULT 'YES' COMMENT 'Whether source field allows NULL values (YES/NO)',
  src_physical_datatype STRING COMMENT 'Physical data type (e.g., STRING, INT, DATE)',
  src_comments STRING COMMENT 'Description/comments for source field - CRITICAL for AI matching when names differ',
  
  -- Domain classification
  domain STRING COMMENT 'Domain category (e.g., claims, member, provider, finance, pharmacy)',
  
  -- Audit fields
  uploaded_by STRING COMMENT 'User who uploaded this field',
  uploaded_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when field was uploaded',
  created_by STRING DEFAULT 'system' COMMENT 'User who created this record',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when record was created',
  updated_by STRING COMMENT 'User who last updated this record',
  updated_ts TIMESTAMP COMMENT 'Timestamp when record was last updated',
  
  CONSTRAINT pk_unmapped_fields PRIMARY KEY (unmapped_field_id)
)
COMMENT 'Source fields awaiting mapping. src_comments is critical for AI matching when column names differ from targets.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);


-- ============================================================================
-- TABLE 3: mapped_fields (Complete Mappings with SQL Expression)
-- ============================================================================
-- Purpose: One row = one complete mapping (target + source expression)
-- Vector Search: Yes - source_semantic_field column
-- Key Change: SQL expression captures ALL logic (transforms, joins, unions)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${CATALOG_SCHEMA}.mapped_fields (
  mapped_field_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- Target field reference
  semantic_field_id BIGINT NOT NULL COMMENT 'Foreign key to semantic_fields table',
  
  -- Target field info (denormalized for performance)
  tgt_table_name STRING NOT NULL COMMENT 'Target table logical name',
  tgt_table_physical_name STRING NOT NULL COMMENT 'Target table physical name',
  tgt_column_name STRING NOT NULL COMMENT 'Target column logical name',
  tgt_column_physical_name STRING NOT NULL COMMENT 'Target column physical name',
  tgt_comments STRING COMMENT 'Target column description (denormalized for AI context)',
  
  -- =========================================================================
  -- SOURCE EXPRESSION - The complete SQL transformation
  -- =========================================================================
  -- This single field captures everything: columns, transforms, joins, unions
  -- Examples:
  --   Simple:     "TRIM(patient.ssn)"
  --   Multi-col:  "CONCAT(TRIM(p.first), ' ', TRIM(p.last))"
  --   With Join:  "CASE WHEN a.type='HOME' THEN TRIM(a.street) END"
  --   With Union: "SELECT city FROM curr UNION ALL SELECT city FROM hist"
  -- =========================================================================
  source_expression STRING NOT NULL COMMENT 'Complete SQL expression for the mapping (includes transforms, joins, unions)',
  
  -- =========================================================================
  -- SOURCE METADATA - For display, search, and AI learning
  -- =========================================================================
  source_tables STRING COMMENT 'Comma-separated source table names (e.g., "patient_data, address")',
  source_columns STRING COMMENT 'Comma-separated source column names (e.g., "first_name, last_name")',
  source_descriptions STRING COMMENT 'Pipe-separated source column descriptions for AI learning',
  source_datatypes STRING COMMENT 'Comma-separated source data types',
  
  -- How sources relate
  source_relationship_type STRING DEFAULT 'SINGLE' COMMENT 'SINGLE (one table), JOIN (multiple tables joined), UNION (multiple tables unioned)',
  
  -- What transformations were applied (for AI to learn patterns)
  transformations_applied STRING COMMENT 'Comma-separated list of transformations (e.g., "TRIM, UPPER, CONCAT")',
  
  -- =========================================================================
  -- AI/CONFIDENCE METADATA
  -- =========================================================================
  confidence_score DOUBLE COMMENT 'Overall confidence score for this mapping (0.0 to 1.0)',
  mapping_source STRING DEFAULT 'MANUAL' COMMENT 'How mapping was created: AI, MANUAL, BULK_UPLOAD',
  ai_reasoning STRING COMMENT 'AI explanation for why this mapping was suggested',
  ai_generated BOOLEAN DEFAULT false COMMENT 'Whether the source_expression was AI-generated',
  
  -- Status
  mapping_status STRING DEFAULT 'ACTIVE' COMMENT 'Status: ACTIVE, INACTIVE, PENDING_REVIEW',
  
  -- Audit fields
  mapped_by STRING COMMENT 'User who created/approved this mapping',
  mapped_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when mapping was created',
  updated_by STRING COMMENT 'User who last updated this mapping',
  updated_ts TIMESTAMP COMMENT 'Timestamp when mapping was last updated',
  
  -- =========================================================================
  -- VECTOR SEARCH: Semantic field for AI pattern matching
  -- =========================================================================
  -- This field must be populated on INSERT/UPDATE with concatenated source info
  -- Formula: CONCAT_WS(' | ', 'SOURCE TABLES: ' || source_tables, 'SOURCE COLUMNS: ' || source_columns, ...)
  source_semantic_field STRING COMMENT 'Concatenated field for vector embedding - populated on insert with source info for AI pattern matching',
  
  CONSTRAINT pk_mapped_fields PRIMARY KEY (mapped_field_id),
  CONSTRAINT fk_mapped_semantic FOREIGN KEY (semantic_field_id) REFERENCES ${CATALOG_SCHEMA}.semantic_fields(semantic_field_id)
)
COMMENT 'Complete mappings with SQL expressions. One row = one mapping. source_semantic_field enables AI pattern learning.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);


-- ============================================================================
-- TABLE 4: mapping_feedback (Rejection History for AI Learning)
-- ============================================================================
-- Purpose: Track rejected AI suggestions so AI learns to avoid them
-- Vector Search: Yes - source_semantic_field column
-- Note: Accepted suggestions become mapped_fields rows, so feedback is rejections
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${CATALOG_SCHEMA}.mapping_feedback (
  feedback_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- What was suggested and rejected
  suggested_src_table STRING NOT NULL COMMENT 'Source table in rejected AI suggestion',
  suggested_src_column STRING NOT NULL COMMENT 'Source column in rejected AI suggestion',
  suggested_tgt_table STRING NOT NULL COMMENT 'Target table in rejected AI suggestion',
  suggested_tgt_column STRING NOT NULL COMMENT 'Target column in rejected AI suggestion',
  
  -- Source context at time of rejection (for vector search)
  src_comments STRING COMMENT 'Source column description at time of rejection',
  src_datatype STRING COMMENT 'Source column data type at time of rejection',
  
  -- Target context at time of rejection
  tgt_comments STRING COMMENT 'Target column description at time of rejection',
  
  -- AI suggestion metadata
  ai_confidence_score DOUBLE COMMENT 'Confidence score from AI when suggestion was made',
  ai_reasoning STRING COMMENT 'AI explanation for why this was suggested',
  vector_search_score DOUBLE COMMENT 'Raw vector search similarity score',
  suggestion_rank INT COMMENT 'Rank of this suggestion (1 = top suggestion)',
  
  -- Feedback details
  feedback_action STRING NOT NULL DEFAULT 'REJECTED' COMMENT 'REJECTED, MODIFIED',
  user_comments STRING COMMENT 'User explanation for why they rejected',
  
  -- If modified (user accepted but changed something)
  modified_src_table STRING COMMENT 'If MODIFIED, the actual source table user selected',
  modified_src_column STRING COMMENT 'If MODIFIED, the actual source column user selected',
  modified_expression STRING COMMENT 'If MODIFIED, the expression user created instead',
  
  -- Context
  domain STRING COMMENT 'Domain category at time of suggestion',
  
  -- Audit fields
  feedback_by STRING COMMENT 'User who rejected this suggestion',
  feedback_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when feedback was provided',
  
  -- =========================================================================
  -- VECTOR SEARCH: For finding similar past rejections
  -- =========================================================================
  -- This field must be populated on INSERT with concatenated rejection info
  source_semantic_field STRING COMMENT 'Concatenated field for vector embedding - populated on insert for AI rejection avoidance',
  
  CONSTRAINT pk_mapping_feedback PRIMARY KEY (feedback_id)
)
COMMENT 'Rejected AI suggestions for learning. Vector search helps AI avoid repeating mistakes.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);


-- ============================================================================
-- TABLE 5: transformation_library (Reusable Transformation Templates)
-- ============================================================================
-- Purpose: Store common transformation patterns for AI suggestions and UI
-- Vector Search: No
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${CATALOG_SCHEMA}.transformation_library (
  transformation_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  transformation_name STRING NOT NULL COMMENT 'Friendly name (e.g., Standard Name Format)',
  transformation_code STRING NOT NULL COMMENT 'Short code (e.g., STD_NAME)',
  transformation_expression STRING NOT NULL COMMENT 'SQL expression template with {field} placeholder',
  transformation_description STRING COMMENT 'Description of what this transformation does',
  category STRING COMMENT 'Category: TEXT, DATE, NUMERIC, CUSTOM',
  is_system BOOLEAN DEFAULT false COMMENT 'Whether this is a system-provided transformation',
  
  -- Audit fields
  created_by STRING DEFAULT 'system' COMMENT 'User who created this transformation',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when created',
  updated_by STRING COMMENT 'User who last updated',
  updated_ts TIMESTAMP COMMENT 'Timestamp when last updated',
  
  CONSTRAINT pk_transformation_library PRIMARY KEY (transformation_id)
)
COMMENT 'Library of reusable transformation patterns for AI suggestions and user reference.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);


-- ============================================================================
-- LIQUID CLUSTERING for Performance Optimization
-- ============================================================================

ALTER TABLE ${CATALOG_SCHEMA}.semantic_fields 
CLUSTER BY (tgt_table_physical_name, domain);

ALTER TABLE ${CATALOG_SCHEMA}.unmapped_fields 
CLUSTER BY (src_table_physical_name, domain);

ALTER TABLE ${CATALOG_SCHEMA}.mapped_fields 
CLUSTER BY (tgt_table_physical_name, mapping_status);

ALTER TABLE ${CATALOG_SCHEMA}.mapping_feedback 
CLUSTER BY (feedback_action, suggested_tgt_table);

ALTER TABLE ${CATALOG_SCHEMA}.transformation_library 
CLUSTER BY (category, is_system);


-- ============================================================================
-- SEED DATA: Common Transformations
-- ============================================================================

INSERT INTO ${CATALOG_SCHEMA}.transformation_library 
  (transformation_name, transformation_code, transformation_expression, transformation_description, category, is_system)
VALUES
  ('Trim Whitespace', 'TRIM', 'TRIM({field})', 'Remove leading and trailing whitespace', 'TEXT', true),
  ('Uppercase', 'UPPER', 'UPPER({field})', 'Convert text to uppercase', 'TEXT', true),
  ('Lowercase', 'LOWER', 'LOWER({field})', 'Convert text to lowercase', 'TEXT', true),
  ('Title Case', 'INITCAP', 'INITCAP({field})', 'Convert text to title case', 'TEXT', true),
  ('Trim and Upper', 'TRIM_UPPER', 'TRIM(UPPER({field}))', 'Remove whitespace and convert to uppercase', 'TEXT', true),
  ('Trim and Lower', 'TRIM_LOWER', 'TRIM(LOWER({field}))', 'Remove whitespace and convert to lowercase', 'TEXT', true),
  ('Remove Special Chars', 'ALPHA_ONLY', 'REGEXP_REPLACE({field}, "[^a-zA-Z0-9 ]", "")', 'Remove special characters', 'TEXT', true),
  ('Remove Dashes', 'NO_DASH', 'REPLACE({field}, "-", "")', 'Remove all dashes', 'TEXT', true),
  ('Replace Null with Empty', 'COALESCE_EMPTY', 'COALESCE({field}, '''')', 'Replace NULL with empty string', 'TEXT', true),
  ('Replace Null with Zero', 'COALESCE_ZERO', 'COALESCE({field}, 0)', 'Replace NULL with zero', 'NUMERIC', true),
  ('Format SSN', 'FORMAT_SSN', 'CONCAT(SUBSTR({field}, 1, 3), "-", SUBSTR({field}, 4, 2), "-", SUBSTR({field}, 6, 4))', 'Format SSN as XXX-XX-XXXX', 'TEXT', true),
  ('Unformat SSN', 'UNFORMAT_SSN', 'REPLACE({field}, "-", "")', 'Remove dashes from SSN', 'TEXT', true),
  ('Format Phone', 'FORMAT_PHONE', 'CONCAT("(", SUBSTR({field}, 1, 3), ") ", SUBSTR({field}, 4, 3), "-", SUBSTR({field}, 7, 4))', 'Format phone as (XXX) XXX-XXXX', 'TEXT', true),
  ('Date to String', 'DATE_TO_STR', 'DATE_FORMAT({field}, "yyyy-MM-dd")', 'Convert date to YYYY-MM-DD string', 'DATE', true),
  ('String to Date', 'STR_TO_DATE', 'TO_DATE({field}, "yyyy-MM-dd")', 'Convert string to date', 'DATE', true),
  ('Extract Year', 'YEAR', 'YEAR({field})', 'Extract year from date', 'DATE', true),
  ('Extract Month', 'MONTH', 'MONTH({field})', 'Extract month from date', 'DATE', true),
  ('Round to 2 Decimals', 'ROUND_2', 'ROUND({field}, 2)', 'Round to 2 decimal places', 'NUMERIC', true),
  ('Cast to String', 'TO_STRING', 'CAST({field} AS STRING)', 'Convert to string', 'NUMERIC', true),
  ('Cast to Integer', 'TO_INT', 'CAST({field} AS INT)', 'Convert to integer', 'NUMERIC', true),
  ('Cast to Decimal', 'TO_DECIMAL', 'CAST({field} AS DECIMAL(18,2))', 'Convert to decimal(18,2)', 'NUMERIC', true),
  ('Concatenate with Space', 'CONCAT_SPACE', 'CONCAT({field1}, '' '', {field2})', 'Join two fields with space', 'TEXT', true),
  ('Concatenate with Comma', 'CONCAT_COMMA', 'CONCAT({field1}, '', '', {field2})', 'Join two fields with comma', 'TEXT', true);


-- ============================================================================
-- VECTOR SEARCH INDEXES (Run after tables have data)
-- ============================================================================
-- Note: Create these indexes in Databricks UI or via API after populating tables
-- 
-- Index 1: semantic_fields.semantic_field
--   - Purpose: Find target fields matching source descriptions
--   - Query: "Find targets similar to 'Patient social security number'"
--
-- Index 2: mapped_fields.source_semantic_field  
--   - Purpose: Find similar past mappings for AI pattern learning
--   - Query: "Find mappings with similar source characteristics"
--
-- Index 3: mapping_feedback.source_semantic_field
--   - Purpose: Find similar past rejections to avoid
--   - Query: "Has this source→target combination been rejected before?"
--
-- Example (run in Databricks):
-- CREATE VECTOR SEARCH INDEX semantic_fields_idx
--   ON ${CATALOG_SCHEMA}.semantic_fields (semantic_field)
--   USING <embedding_model>;
-- ============================================================================


-- ============================================================================
-- END OF V3 SCHEMA
-- ============================================================================
-- 
-- Summary of tables:
-- 1. semantic_fields     - 12 columns (target definitions, vector indexed)
-- 2. unmapped_fields     - 13 columns (source fields to map)
-- 3. mapped_fields       - 23 columns (complete mappings, vector indexed)
-- 4. mapping_feedback    - 18 columns (rejections, vector indexed)
-- 5. transformation_library - 10 columns (transform templates)
--
-- Eliminated from V2:
-- - mapping_details (info now in mapped_fields.source_* columns)
-- - mapping_joins (info now in mapped_fields.source_expression)
-- - mapping_unions (info now in mapped_fields.source_expression)
--
-- ============================================================================

