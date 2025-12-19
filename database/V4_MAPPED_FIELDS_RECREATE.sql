-- ============================================================================
-- V4 Schema Updates - Team Access & Pattern Approval
-- ============================================================================


-- ============================================================================
-- ADD TEAM MEMBERS TO MAPPING_PROJECTS
-- ============================================================================
-- Allows project creators to share projects with team members

ALTER TABLE ${CATALOG_SCHEMA}.mapping_projects 
ADD COLUMN IF NOT EXISTS team_members STRING 
COMMENT 'Pipe-separated list of team member emails who can access this project';

-- Example: 'john@company.com|jane@company.com|bob@company.com'


-- ============================================================================
-- V4 mapped_fields Table - Complete Recreation
-- ============================================================================
-- 
-- This script recreates the mapped_fields table with all V4 columns.
-- 
-- NEW V4 COLUMNS:
--   - project_id: Links mapping to a project (NULL = global pattern)
--   - is_approved_pattern: Whether this mapping is approved for AI to use
--   - pattern_approved_by: User who approved as pattern
--   - pattern_approved_ts: When pattern was approved
--
-- IMPORTANT: This will DROP and recreate the table! Back up data first.
--
-- Replace ${CATALOG_SCHEMA} with your catalog.schema (e.g., oztest_dev.smartmapper)
-- ============================================================================


-- ============================================================================
-- OPTION 1: ALTER TABLE (if you want to preserve existing data)
-- ============================================================================
-- Run these ALTER statements to add new columns to existing table:

ALTER TABLE ${CATALOG_SCHEMA}.mapped_fields ADD COLUMN IF NOT EXISTS project_id BIGINT COMMENT 'FK to mapping_projects. NULL means global pattern not tied to project';

ALTER TABLE ${CATALOG_SCHEMA}.mapped_fields ADD COLUMN IF NOT EXISTS is_approved_pattern BOOLEAN DEFAULT FALSE COMMENT 'Whether this mapping is approved for AI to use as a pattern';

ALTER TABLE ${CATALOG_SCHEMA}.mapped_fields ADD COLUMN IF NOT EXISTS pattern_approved_by STRING COMMENT 'User who approved this as a pattern for AI learning';

ALTER TABLE ${CATALOG_SCHEMA}.mapped_fields ADD COLUMN IF NOT EXISTS pattern_approved_ts TIMESTAMP COMMENT 'Timestamp when pattern was approved';


-- ============================================================================
-- OPTION 2: CREATE OR REPLACE (if you want a fresh table)
-- ============================================================================
-- Uncomment and run this if you want to recreate the table completely.
-- WARNING: This will DELETE all existing data!

/*
CREATE OR REPLACE TABLE ${CATALOG_SCHEMA}.mapped_fields (
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
  source_expression STRING NOT NULL COMMENT 'Complete SQL expression for the mapping (includes transforms, joins, unions)',
  
  -- =========================================================================
  -- SOURCE METADATA - For display, search, and AI learning
  -- =========================================================================
  source_tables STRING COMMENT 'Pipe-separated source table logical names',
  source_tables_physical STRING COMMENT 'Pipe-separated source table physical names',
  source_columns STRING COMMENT 'Pipe-separated source column logical names',
  source_columns_physical STRING COMMENT 'Pipe-separated source column physical names',
  source_descriptions STRING COMMENT 'Pipe-separated source column descriptions for AI learning',
  source_datatypes STRING COMMENT 'Pipe-separated source data types',
  source_domain STRING COMMENT 'Domain category from original unmapped fields',
  target_domain STRING COMMENT 'Target domain category (denormalized from semantic_fields)',
  
  -- How sources relate
  source_relationship_type STRING DEFAULT 'SINGLE' COMMENT 'SINGLE, JOIN, UNION',
  
  -- What transformations were applied
  transformations_applied STRING COMMENT 'Comma-separated list of transformations',
  
  -- =========================================================================
  -- JOIN METADATA - Structured info for complex JOIN/UNION patterns
  -- =========================================================================
  join_metadata STRING COMMENT 'JSON metadata for JOIN/UNION patterns',
  
  -- =========================================================================
  -- AI/CONFIDENCE METADATA
  -- =========================================================================
  confidence_score DOUBLE COMMENT 'Overall confidence score (0.0 to 1.0)',
  mapping_source STRING DEFAULT 'MANUAL' COMMENT 'AI, MANUAL, BULK_UPLOAD',
  ai_reasoning STRING COMMENT 'AI explanation for the mapping',
  ai_generated BOOLEAN DEFAULT FALSE COMMENT 'Whether source_expression was AI-generated',
  
  -- Status
  mapping_status STRING DEFAULT 'ACTIVE' COMMENT 'ACTIVE, INACTIVE, PENDING_REVIEW',
  
  -- =========================================================================
  -- V4: PROJECT AND PATTERN APPROVAL
  -- =========================================================================
  project_id BIGINT COMMENT 'FK to mapping_projects. NULL = global pattern not tied to project',
  is_approved_pattern BOOLEAN DEFAULT FALSE COMMENT 'Whether approved for AI to use as pattern',
  pattern_approved_by STRING COMMENT 'User who approved as pattern',
  pattern_approved_ts TIMESTAMP COMMENT 'When pattern was approved',
  
  -- Audit fields
  mapped_by STRING COMMENT 'User who created/approved this mapping',
  mapped_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'When mapping was created',
  updated_by STRING COMMENT 'User who last updated this mapping',
  updated_ts TIMESTAMP COMMENT 'When mapping was last updated',
  
  -- =========================================================================
  -- VECTOR SEARCH: Semantic field for AI pattern matching (AUTO-GENERATED)
  -- =========================================================================
  source_semantic_field STRING GENERATED ALWAYS AS (
    CONCAT(
      'DESCRIPTION: ', COALESCE(source_descriptions, source_columns, ''),
      ' | TYPE: ', COALESCE(source_datatypes, 'STRING'),
      ' | DOMAIN: ', COALESCE(source_domain, '')
    )
  ) COMMENT 'Auto-generated semantic field for vector search',
  
  CONSTRAINT pk_mapped_fields PRIMARY KEY (mapped_field_id),
  CONSTRAINT fk_mapped_semantic FOREIGN KEY (semantic_field_id) REFERENCES ${CATALOG_SCHEMA}.semantic_fields(semantic_field_id)
)
COMMENT 'Complete mappings with SQL expressions. V4 adds project_id and pattern approval tracking.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);
*/


-- ============================================================================
-- VERIFICATION: Check table structure
-- ============================================================================

DESCRIBE TABLE ${CATALOG_SCHEMA}.mapped_fields;

-- Check for new V4 columns
SELECT 
  column_name,
  data_type,
  comment
FROM information_schema.columns
WHERE table_schema = '${SCHEMA}'
  AND table_name = 'mapped_fields'
  AND column_name IN ('project_id', 'is_approved_pattern', 'pattern_approved_by', 'pattern_approved_ts')
ORDER BY column_name;

