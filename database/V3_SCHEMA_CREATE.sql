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
  
  -- VECTOR SEARCH: Semantic field for embedding with domain context
  -- DESCRIPTION + TYPE + DOMAIN - domain helps disambiguate similar descriptions across domains
  -- Domain is a soft signal (empty string if NULL) - helps but doesn't strictly filter
  semantic_field STRING GENERATED ALWAYS AS (
    CONCAT(
      'DESCRIPTION: ', COALESCE(tgt_comments, tgt_column_name, ''),
      ' | TYPE: ', COALESCE(tgt_physical_datatype, 'STRING'),
      ' | DOMAIN: ', COALESCE(domain, '')
    )
  ) COMMENT 'Semantic field for vector embedding - DESCRIPTION + TYPE + DOMAIN for context-aware matching',
  
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
-- TABLE 2: unmapped_fields (Source Fields for Mapping)
-- ============================================================================
-- Purpose: Store source fields - both pending and mapped (not deleted when used)
-- Vector Search: Yes - source_semantic_field column for AI matching
-- Key Design: Fields are marked MAPPED, not deleted, to preserve join key searchability
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
  src_comments STRING COMMENT 'Description/comments for source field - CRITICAL for AI matching',
  
  -- Domain classification
  domain STRING COMMENT 'Domain category (e.g., claims, member, provider, finance, pharmacy)',
  
  -- Mapping Status - tracks whether field has been used in a mapping
  -- PENDING  = Field is available for mapping (shown in UI)
  -- MAPPED   = Field has been used in a mapping (hidden from "to map" list, but searchable for joins)
  -- ARCHIVED = Field removed by user (not shown, not searchable)
  mapping_status STRING DEFAULT 'PENDING' COMMENT 'Status: PENDING (to map), MAPPED (used), ARCHIVED (removed)',
  
  -- Reference to mapped_field if this field was mapped
  mapped_field_id BIGINT COMMENT 'Reference to mapped_fields.mapped_field_id if status is MAPPED',
  
  -- Vector Search: Auto-generated semantic field for AI matching
  -- Format matches mapped_fields.source_semantic_field for consistent vector search
  source_semantic_field STRING GENERATED ALWAYS AS (
    CONCAT(
      'DESCRIPTION: ', COALESCE(src_comments, src_column_name, ''),
      ' | TYPE: ', COALESCE(src_physical_datatype, 'STRING'),
      ' | DOMAIN: ', COALESCE(domain, '')
    )
  ) COMMENT 'Auto-generated semantic field for vector search - DESCRIPTION + TYPE + DOMAIN',
  
  -- Audit fields
  uploaded_by STRING COMMENT 'User who uploaded this field',
  uploaded_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when field was uploaded',
  created_by STRING DEFAULT 'system' COMMENT 'User who created this record',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when record was created',
  updated_by STRING COMMENT 'User who last updated this record',
  updated_ts TIMESTAMP COMMENT 'Timestamp when record was last updated',
  
  CONSTRAINT pk_unmapped_fields PRIMARY KEY (unmapped_field_id)
)
COMMENT 'Source fields for mapping. Vector search enabled. Fields marked MAPPED when used but not deleted.'
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
  source_tables STRING COMMENT 'Pipe-separated source table logical names (e.g., "Patient Data | Address")',
  source_tables_physical STRING COMMENT 'Pipe-separated source table physical names (e.g., "patient_data | address")',
  source_columns STRING COMMENT 'Pipe-separated source column logical names (e.g., "First Name | Last Name")',
  source_columns_physical STRING COMMENT 'Pipe-separated source column physical names (e.g., "first_name | last_name")',
  source_descriptions STRING COMMENT 'Pipe-separated source column descriptions for AI learning',
  source_datatypes STRING COMMENT 'Pipe-separated source data types',
  source_domain STRING COMMENT 'Domain category from original unmapped fields (for restore on delete)',
  target_domain STRING COMMENT 'Target domain category (denormalized from semantic_fields for pattern learning)',
  
  -- How sources relate
  source_relationship_type STRING DEFAULT 'SINGLE' COMMENT 'SINGLE (one table), JOIN (multiple tables joined), UNION (multiple tables unioned)',
  
  -- What transformations were applied (for AI to learn patterns)
  transformations_applied STRING COMMENT 'Comma-separated list of transformations (e.g., "TRIM, UPPER, CONCAT")',
  
  -- =========================================================================
  -- JOIN METADATA - Structured info for complex JOIN/UNION patterns
  -- =========================================================================
  -- Stores parsed join structure as JSON for template UI to render wizards
  -- See V3_ADD_JOIN_METADATA.sql for full JSON schema documentation
  join_metadata STRING COMMENT 'JSON metadata for JOIN/UNION patterns - enables template UI to understand complex SQL structure',
  
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
  -- VECTOR SEARCH: Semantic field for AI pattern matching (AUTO-GENERATED)
  -- DESCRIPTION + TYPE + DOMAIN - domain helps find patterns from same domain
  -- =========================================================================
  source_semantic_field STRING GENERATED ALWAYS AS (
    CONCAT(
      'DESCRIPTION: ', COALESCE(source_descriptions, source_columns, ''),
      ' | TYPE: ', COALESCE(source_datatypes, 'STRING'),
      ' | DOMAIN: ', COALESCE(source_domain, '')
    )
  ) COMMENT 'Semantic field for pattern matching - DESCRIPTION + TYPE + DOMAIN for context-aware matching',
  
  CONSTRAINT pk_mapped_fields PRIMARY KEY (mapped_field_id),
  CONSTRAINT fk_mapped_semantic FOREIGN KEY (semantic_field_id) REFERENCES ${CATALOG_SCHEMA}.semantic_fields(semantic_field_id)
)
COMMENT 'Complete mappings with SQL expressions. One row = one mapping. source_semantic_field auto-generates for AI pattern learning.'
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
  -- VECTOR SEARCH: For finding similar past rejections (AUTO-GENERATED)
  -- =========================================================================
  source_semantic_field STRING GENERATED ALWAYS AS (
    CONCAT_WS(' | ',
      COALESCE(suggested_src_table, ''),
      COALESCE(suggested_src_column, ''),
      COALESCE(suggested_tgt_table, ''),
      COALESCE(suggested_tgt_column, ''),
      COALESCE(src_comments, ''),
      COALESCE(user_comments, '')
    )
  ) COMMENT 'Auto-generated concatenated field for vector embedding - enables AI rejection avoidance',
  
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
-- Index 3: unmapped_fields.source_semantic_field (NEW)
--   - Purpose: Find unmapped source fields for template slot filling
--   - Query: "Find unmapped fields similar to 'Position title description'"
--   - Use cases:
--     a) Suggest additional columns when completing multi-field patterns
--     b) Suggest join key fields from user's selected tables
--   - Filter support: Filter by src_table_physical_name for join field matching
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
-- 2. unmapped_fields     - 14 columns (source fields to map, vector indexed)
-- 3. mapped_fields       - 24 columns (complete mappings, vector indexed) - includes source_domain
-- 4. mapping_feedback    - 18 columns (rejections, vector indexed)
--
-- Vector Search Indexes Required:
-- 1. semantic_fields_vs_index       on semantic_field column
-- 2. mapped_fields_vs_index         on source_semantic_field column
-- 3. unmapped_fields_vs_index       on source_semantic_field column (NEW)
-- 4. mapping_feedback_vs_index      on embedding column
--
-- Eliminated from V2:
-- - mapping_details (info now in mapped_fields.source_* columns)
-- - mapping_joins (info now in mapped_fields.source_expression)
-- - mapping_unions (info now in mapped_fields.source_expression)
-- - transformation_library (AI generates transformations dynamically)
--
-- ============================================================================

