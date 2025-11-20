-- ============================================================================
-- Source-to-Target Mapping Platform V2 - Database Migration
-- ============================================================================
-- 
-- MAJOR CHANGES:
-- 1. Support multiple source fields mapping to single target field
-- 2. Add field ordering and concatenation strategies
-- 3. Add per-field transformations (TRIM, UPPER, LOWER, etc.)
-- 4. Add feedback/audit trail for AI suggestions
-- 5. Enhanced confidence scoring
--
-- ============================================================================

-- ============================================================================
-- TABLE 1: semantic_fields (Enhanced Target Field Definitions)
-- ============================================================================
-- Purpose: Define target fields available for mapping
-- Changes from V1: Added domain-specific columns for enhanced vector search
-- ============================================================================

CREATE TABLE IF NOT EXISTS main.source2target.semantic_fields (
  semantic_field_id BIGINT GENERATED ALWAYS AS IDENTITY,
  tgt_table STRING NOT NULL COMMENT 'Target table name (e.g., slv_member)',
  tgt_column STRING NOT NULL COMMENT 'Target column name (e.g., first_name)',
  tgt_data_type STRING COMMENT 'Target data type (e.g., STRING, INT, DATE)',
  tgt_is_nullable BOOLEAN DEFAULT true COMMENT 'Whether target field allows NULL values',
  tgt_comments STRING COMMENT 'Description/comments for target field',
  
  -- Domain classification for enhanced AI recommendations
  domain STRING COMMENT 'Domain category (e.g., claims, member, provider, finance, pharmacy)',
  
  -- Audit fields
  created_by STRING DEFAULT 'system' COMMENT 'User who created this record',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when record was created',
  updated_by STRING COMMENT 'User who last updated this record',
  updated_ts TIMESTAMP COMMENT 'Timestamp when record was last updated',
  
  -- Computed semantic field for vector search (same as V1)
  semantic_field STRING GENERATED ALWAYS AS (
    CONCAT_WS(' | ',
      CONCAT('table:', COALESCE(tgt_table, '')),
      CONCAT('column:', COALESCE(tgt_column, '')),
      CONCAT('type:', COALESCE(tgt_data_type, '')),
      CONCAT('description:', COALESCE(tgt_comments, '')),
      CONCAT('domain:', COALESCE(domain, ''))
    )
  ) COMMENT 'Concatenated field for vector embedding',
  
  CONSTRAINT pk_semantic_fields PRIMARY KEY (semantic_field_id)
  -- Note: UNIQUE constraint on (tgt_table, tgt_column) enforced at application level
  -- Databricks Delta tables don't support UNIQUE constraints
) 
COMMENT 'Target field definitions with semantic metadata for AI-powered mapping. Uniqueness on (tgt_table, tgt_column) must be enforced at application level.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);

-- ============================================================================
-- TABLE 2: unmapped_fields (Source Fields Awaiting Mapping)
-- ============================================================================
-- Purpose: Store source fields that need to be mapped to target fields
-- Changes from V1: Added domain, removed mapping-related columns
-- ============================================================================

CREATE TABLE IF NOT EXISTS main.source2target.unmapped_fields (
  unmapped_field_id BIGINT GENERATED ALWAYS AS IDENTITY,
  src_table STRING NOT NULL COMMENT 'Source table name (e.g., T_MEMBER)',
  src_column STRING NOT NULL COMMENT 'Source column name (e.g., SSN)',
  src_data_type STRING COMMENT 'Source data type (e.g., STRING, INT, DATE)',
  src_is_nullable BOOLEAN DEFAULT true COMMENT 'Whether source field allows NULL values',
  src_comments STRING COMMENT 'Description/comments for source field',
  
  -- Domain classification for enhanced AI recommendations
  domain STRING COMMENT 'Domain category (e.g., claims, member, provider, finance, pharmacy)',
  
  -- Audit fields
  created_by STRING DEFAULT 'system' COMMENT 'User who created this record',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when record was created',
  updated_by STRING COMMENT 'User who last updated this record',
  updated_ts TIMESTAMP COMMENT 'Timestamp when record was last updated',
  
  CONSTRAINT pk_unmapped_fields PRIMARY KEY (unmapped_field_id)
  -- Note: UNIQUE constraint on (src_table, src_column) enforced at application level
  -- Databricks Delta tables don't support UNIQUE constraints
)
COMMENT 'Source fields awaiting mapping to target fields. Uniqueness on (src_table, src_column) must be enforced at application level.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);

-- ============================================================================
-- TABLE 3: mapped_fields (Target Fields with Mappings)
-- ============================================================================
-- Purpose: One record per TARGET field, supporting multiple source fields
-- Key Feature: Multiple source fields can map to single target field
-- ============================================================================

CREATE TABLE IF NOT EXISTS main.source2target.mapped_fields (
  mapped_field_id BIGINT GENERATED ALWAYS AS IDENTITY,
  
  -- Target field reference
  semantic_field_id BIGINT NOT NULL COMMENT 'Foreign key to semantic_fields table',
  tgt_table STRING NOT NULL COMMENT 'Target table name (denormalized for performance)',
  tgt_column STRING NOT NULL COMMENT 'Target column name (denormalized for performance)',
  
  -- Multi-source concatenation strategy
  concat_strategy STRING DEFAULT 'NONE' COMMENT 'How to combine multiple source fields: NONE, SPACE, COMMA, PIPE, CONCAT, CUSTOM',
  concat_separator STRING COMMENT 'Custom separator if concat_strategy = CUSTOM (e.g., " - ", "_")',
  
  -- Complete transformation expression
  transformation_expression STRING COMMENT 'Full SQL expression showing the transformation (e.g., CONCAT(TRIM(UPPER(src1)), " ", src2))',
  
  -- Confidence and mapping metadata
  confidence_score DOUBLE COMMENT 'Overall confidence score for this mapping (0.0 to 1.0)',
  mapping_source STRING DEFAULT 'MANUAL' COMMENT 'How mapping was created: AI, MANUAL, BULK_UPLOAD, SYSTEM',
  ai_reasoning STRING COMMENT 'AI explanation for why this mapping was suggested',
  
  -- Status tracking
  mapping_status STRING DEFAULT 'ACTIVE' COMMENT 'Status: ACTIVE, INACTIVE, PENDING_REVIEW',
  
  -- Audit fields
  mapped_by STRING COMMENT 'User who created/approved this mapping',
  mapped_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when mapping was created',
  updated_by STRING COMMENT 'User who last updated this mapping',
  updated_ts TIMESTAMP COMMENT 'Timestamp when mapping was last updated',
  
  CONSTRAINT pk_mapped_fields PRIMARY KEY (mapped_field_id)
  -- Note: UNIQUE constraint on (tgt_table, tgt_column) enforced at application level
  -- Note: FOREIGN KEY to semantic_fields enforced at application level
  -- Databricks Delta tables don't support UNIQUE or FOREIGN KEY constraints
)
COMMENT 'Target fields with their source field mappings (one record per target field, supporting multiple sources). Uniqueness on (tgt_table, tgt_column) and foreign key to semantic_fields must be enforced at application level.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);

-- ============================================================================
-- TABLE 4: mapping_details (Source Fields in Each Mapping)
-- ============================================================================
-- Purpose: Store individual source fields that contribute to a target mapping
-- Key Feature: Ordering and per-field transformations
-- ============================================================================

CREATE TABLE IF NOT EXISTS main.source2target.mapping_details (
  mapping_detail_id BIGINT GENERATED ALWAYS AS IDENTITY,
  
  -- Parent mapping reference
  mapped_field_id BIGINT NOT NULL COMMENT 'Foreign key to mapped_fields table',
  
  -- Source field reference
  unmapped_field_id BIGINT COMMENT 'Foreign key to unmapped_fields table (NULL if field was removed from unmapped)',
  src_table STRING NOT NULL COMMENT 'Source table name (denormalized)',
  src_column STRING NOT NULL COMMENT 'Source column name (denormalized)',
  
  -- Ordering and transformations
  field_order INT NOT NULL COMMENT 'Order of this field in concatenation (1-based)',
  transformations STRING COMMENT 'Comma-separated list of transformations to apply (e.g., TRIM,UPPER,COALESCE)',
  default_value STRING COMMENT 'Default value if source is NULL (for COALESCE)',
  
  -- Field-level confidence
  field_confidence_score DOUBLE COMMENT 'Confidence score for this specific field mapping (0.0 to 1.0)',
  
  -- Audit fields
  created_by STRING COMMENT 'User who added this field to the mapping',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when field was added',
  updated_by STRING COMMENT 'User who last updated this field',
  updated_ts TIMESTAMP COMMENT 'Timestamp when field was last updated',
  
  CONSTRAINT pk_mapping_details PRIMARY KEY (mapping_detail_id)
  -- Note: UNIQUE constraint on (mapped_field_id, src_table, src_column) enforced at application level
  -- Note: FOREIGN KEY to mapped_fields and unmapped_fields enforced at application level
  -- Note: CASCADE and SET NULL behaviors must be handled in application code
  -- Databricks Delta tables don't support UNIQUE or FOREIGN KEY constraints
)
COMMENT 'Individual source fields that contribute to each target field mapping, with ordering and transformations. Uniqueness on (mapped_field_id, src_table, src_column) and foreign keys must be enforced at application level.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);

-- ============================================================================
-- TABLE 5: mapping_feedback (Audit Trail for AI Suggestions)
-- ============================================================================
-- Purpose: Capture user feedback on AI suggestions for model improvement
-- Key Feature: Track accepted/rejected/modified suggestions with reasoning
-- ============================================================================

CREATE TABLE IF NOT EXISTS main.source2target.mapping_feedback (
  feedback_id BIGINT GENERATED ALWAYS AS IDENTITY,
  
  -- What was suggested
  suggested_src_table STRING NOT NULL COMMENT 'Source table in AI suggestion',
  suggested_src_column STRING NOT NULL COMMENT 'Source column in AI suggestion',
  suggested_tgt_table STRING NOT NULL COMMENT 'Target table in AI suggestion',
  suggested_tgt_column STRING NOT NULL COMMENT 'Target column in AI suggestion',
  
  -- AI suggestion metadata
  ai_confidence_score DOUBLE COMMENT 'Confidence score from AI (0.0 to 1.0)',
  ai_reasoning STRING COMMENT 'AI explanation for why this was suggested',
  vector_search_score DOUBLE COMMENT 'Raw vector search similarity score',
  suggestion_rank INT COMMENT 'Rank of this suggestion (1 = top suggestion)',
  
  -- User feedback
  feedback_action STRING NOT NULL COMMENT 'User action: ACCEPTED, REJECTED, MODIFIED',
  user_comments STRING COMMENT 'User explanation for their decision',
  
  -- If modified, what changed
  modified_src_table STRING COMMENT 'If MODIFIED, the actual source table user selected',
  modified_src_column STRING COMMENT 'If MODIFIED, the actual source column user selected',
  modified_transformations STRING COMMENT 'If MODIFIED, transformations user applied',
  
  -- Final mapping reference (if accepted or modified)
  mapped_field_id BIGINT COMMENT 'Foreign key to mapped_fields if suggestion was accepted/modified',
  
  -- Context
  domain STRING COMMENT 'Domain category at time of suggestion',
  
  -- Audit fields
  feedback_by STRING COMMENT 'User who provided feedback',
  feedback_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when feedback was provided',
  
  CONSTRAINT pk_mapping_feedback PRIMARY KEY (feedback_id)
  -- Note: FOREIGN KEY to mapped_fields enforced at application level
  -- Note: SET NULL behavior must be handled in application code
  -- Databricks Delta tables don't support FOREIGN KEY constraints
)
COMMENT 'User feedback on AI mapping suggestions for model improvement and analytics. Foreign key to mapped_fields must be enforced at application level.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);

-- ============================================================================
-- TABLE 6: transformation_library (Reusable Transformation Templates)
-- ============================================================================
-- Purpose: Store common transformation patterns for reuse
-- Key Feature: Template library for standardization
-- ============================================================================

CREATE TABLE IF NOT EXISTS main.source2target.transformation_library (
  transformation_id BIGINT GENERATED ALWAYS AS IDENTITY,
  transformation_name STRING NOT NULL COMMENT 'Friendly name (e.g., "Standard Name Format")',
  transformation_code STRING NOT NULL COMMENT 'Short code (e.g., "STD_NAME")',
  transformation_expression STRING NOT NULL COMMENT 'SQL expression template (e.g., "TRIM(UPPER({field}))")',
  transformation_description STRING COMMENT 'Description of what this transformation does',
  category STRING COMMENT 'Category (e.g., TEXT, DATE, NUMERIC, CUSTOM)',
  is_system BOOLEAN DEFAULT false COMMENT 'Whether this is a system-provided transformation',
  
  -- Audit fields
  created_by STRING DEFAULT 'system' COMMENT 'User who created this transformation',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when created',
  updated_by STRING COMMENT 'User who last updated',
  updated_ts TIMESTAMP COMMENT 'Timestamp when last updated',
  
  CONSTRAINT pk_transformation_library PRIMARY KEY (transformation_id)
  -- Note: UNIQUE constraint on transformation_code enforced at application level
  -- Databricks Delta tables don't support UNIQUE constraints
)
COMMENT 'Library of reusable transformation patterns. Uniqueness on transformation_code must be enforced at application level.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);

-- ============================================================================
-- INDEXES for Performance
-- ============================================================================

-- Semantic fields indexes
CREATE INDEX IF NOT EXISTS idx_semantic_domain ON main.source2target.semantic_fields(domain);
CREATE INDEX IF NOT EXISTS idx_semantic_table ON main.source2target.semantic_fields(tgt_table);

-- Unmapped fields indexes
CREATE INDEX IF NOT EXISTS idx_unmapped_domain ON main.source2target.unmapped_fields(domain);
CREATE INDEX IF NOT EXISTS idx_unmapped_table ON main.source2target.unmapped_fields(src_table);

-- Mapped fields indexes
CREATE INDEX IF NOT EXISTS idx_mapped_semantic ON main.source2target.mapped_fields(semantic_field_id);
CREATE INDEX IF NOT EXISTS idx_mapped_status ON main.source2target.mapped_fields(mapping_status);
CREATE INDEX IF NOT EXISTS idx_mapped_confidence ON main.source2target.mapped_fields(confidence_score);

-- Mapping details indexes
CREATE INDEX IF NOT EXISTS idx_detail_mapped ON main.source2target.mapping_details(mapped_field_id);
CREATE INDEX IF NOT EXISTS idx_detail_unmapped ON main.source2target.mapping_details(unmapped_field_id);
CREATE INDEX IF NOT EXISTS idx_detail_order ON main.source2target.mapping_details(mapped_field_id, field_order);

-- Feedback indexes
CREATE INDEX IF NOT EXISTS idx_feedback_action ON main.source2target.mapping_feedback(feedback_action);
CREATE INDEX IF NOT EXISTS idx_feedback_mapped ON main.source2target.mapping_feedback(mapped_field_id);
CREATE INDEX IF NOT EXISTS idx_feedback_ts ON main.source2target.mapping_feedback(feedback_ts);

-- ============================================================================
-- SEED DATA: Common Transformations
-- ============================================================================

INSERT INTO main.source2target.transformation_library 
  (transformation_name, transformation_code, transformation_expression, transformation_description, category, is_system)
VALUES
  ('Trim Whitespace', 'TRIM', 'TRIM({field})', 'Remove leading and trailing whitespace', 'TEXT', true),
  ('Uppercase', 'UPPER', 'UPPER({field})', 'Convert text to uppercase', 'TEXT', true),
  ('Lowercase', 'LOWER', 'LOWER({field})', 'Convert text to lowercase', 'TEXT', true),
  ('Title Case', 'INITCAP', 'INITCAP({field})', 'Convert text to title case (first letter capitalized)', 'TEXT', true),
  ('Trim and Upper', 'TRIM_UPPER', 'TRIM(UPPER({field}))', 'Remove whitespace and convert to uppercase', 'TEXT', true),
  ('Trim and Lower', 'TRIM_LOWER', 'TRIM(LOWER({field}))', 'Remove whitespace and convert to lowercase', 'TEXT', true),
  ('Remove Special Chars', 'ALPHA_ONLY', 'REGEXP_REPLACE({field}, "[^a-zA-Z0-9 ]", "")', 'Remove all special characters, keep alphanumeric only', 'TEXT', true),
  ('Remove Dashes', 'NO_DASH', 'REPLACE({field}, "-", "")', 'Remove all dashes', 'TEXT', true),
  ('Replace Null with Empty', 'COALESCE_EMPTY', 'COALESCE({field}, '''')', 'Replace NULL with empty string', 'TEXT', true),
  ('Replace Null with Zero', 'COALESCE_ZERO', 'COALESCE({field}, 0)', 'Replace NULL with zero', 'NUMERIC', true),
  ('Format SSN', 'FORMAT_SSN', 'CONCAT(SUBSTR({field}, 1, 3), "-", SUBSTR({field}, 4, 2), "-", SUBSTR({field}, 6, 4))', 'Format SSN as XXX-XX-XXXX', 'TEXT', true),
  ('Remove SSN Dashes', 'UNFORMAT_SSN', 'REPLACE({field}, "-", "")', 'Remove dashes from SSN', 'TEXT', true),
  ('Format Phone', 'FORMAT_PHONE', 'CONCAT("(", SUBSTR({field}, 1, 3), ") ", SUBSTR({field}, 4, 3), "-", SUBSTR({field}, 7, 4))', 'Format phone as (XXX) XXX-XXXX', 'TEXT', true),
  ('Date to String', 'DATE_TO_STR', 'DATE_FORMAT({field}, "yyyy-MM-dd")', 'Convert date to string format YYYY-MM-DD', 'DATE', true),
  ('String to Date', 'STR_TO_DATE', 'TO_DATE({field}, "yyyy-MM-dd")', 'Convert string to date', 'DATE', true),
  ('Extract Year', 'YEAR', 'YEAR({field})', 'Extract year from date', 'DATE', true),
  ('Extract Month', 'MONTH', 'MONTH({field})', 'Extract month from date', 'DATE', true),
  ('Round to 2 Decimals', 'ROUND_2', 'ROUND({field}, 2)', 'Round numeric value to 2 decimal places', 'NUMERIC', true),
  ('Cast to String', 'TO_STRING', 'CAST({field} AS STRING)', 'Convert to string data type', 'NUMERIC', true),
  ('Cast to Integer', 'TO_INT', 'CAST({field} AS INT)', 'Convert to integer data type', 'NUMERIC', true),
  ('Cast to Decimal', 'TO_DECIMAL', 'CAST({field} AS DECIMAL(18,2))', 'Convert to decimal data type', 'NUMERIC', true);

-- ============================================================================
-- END OF SCHEMA CREATION
-- ============================================================================

