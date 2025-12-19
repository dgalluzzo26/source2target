-- ============================================================================
-- V3 MIGRATION: Add Vector Search to unmapped_fields
-- ============================================================================
-- 
-- Purpose: Add source_semantic_field column to unmapped_fields for vector search
-- This enables AI-powered matching for:
--   1. Template slot suggestions (finding similar unmapped fields)
--   2. Join field suggestions (filtering to specific tables)
--
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema
-- ============================================================================


-- ============================================================================
-- STEP 1: Check current schema
-- ============================================================================

DESCRIBE ${CATALOG_SCHEMA}.unmapped_fields;

-- Check if column already exists (this will error if it doesn't - that's expected)
-- SELECT source_semantic_field FROM ${CATALOG_SCHEMA}.unmapped_fields LIMIT 1;


-- ============================================================================
-- STEP 2: Create new table with source_semantic_field column
-- ============================================================================
-- Note: Cannot ALTER TABLE to add GENERATED column, must recreate

CREATE TABLE IF NOT EXISTS ${CATALOG_SCHEMA}.unmapped_fields_v3 (
  unmapped_field_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- Logical names (for display/UI)
  src_table_name STRING NOT NULL COMMENT 'Source table logical name (display name)',
  src_column_name STRING NOT NULL COMMENT 'Source column logical name (display name)',
  
  -- Physical names (for database operations)
  src_table_physical_name STRING NOT NULL COMMENT 'Source table physical name (database name)',
  src_column_physical_name STRING NOT NULL COMMENT 'Source column physical name (database name)',
  
  -- Metadata
  src_nullable STRING DEFAULT 'YES' COMMENT 'Whether source field allows NULL values (YES/NO)',
  src_physical_datatype STRING COMMENT 'Physical data type (e.g., STRING, INT, DATE)',
  src_comments STRING COMMENT 'Description/comments for source field - CRITICAL for AI matching when names differ',
  
  -- Domain classification
  domain STRING COMMENT 'Domain category (e.g., claims, member, provider, finance, pharmacy)',
  
  -- Vector Search: Auto-generated semantic field for AI matching
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
  
  CONSTRAINT pk_unmapped_fields_v3 PRIMARY KEY (unmapped_field_id)
)
COMMENT 'Source fields awaiting mapping. Vector search enabled via source_semantic_field for AI template matching.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);


-- ============================================================================
-- STEP 3: Copy existing data to new table
-- ============================================================================
-- Note: Excludes unmapped_field_id (will be regenerated) and source_semantic_field (auto-generated)

INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields_v3 (
  src_table_name, src_column_name,
  src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments,
  domain,
  uploaded_by, uploaded_ts, created_by, created_ts, updated_by, updated_ts
)
SELECT 
  src_table_name, src_column_name,
  src_table_physical_name, src_column_physical_name,
  src_nullable, src_physical_datatype, src_comments,
  domain,
  uploaded_by, uploaded_ts, created_by, created_ts, updated_by, updated_ts
FROM ${CATALOG_SCHEMA}.unmapped_fields;


-- ============================================================================
-- STEP 4: Verify data migration
-- ============================================================================

SELECT 'Old table count' as check_type, COUNT(*) as cnt FROM ${CATALOG_SCHEMA}.unmapped_fields
UNION ALL
SELECT 'New table count' as check_type, COUNT(*) as cnt FROM ${CATALOG_SCHEMA}.unmapped_fields_v3;

-- Verify source_semantic_field is populated
SELECT 
  unmapped_field_id,
  src_column_name,
  src_comments,
  domain,
  source_semantic_field
FROM ${CATALOG_SCHEMA}.unmapped_fields_v3
LIMIT 5;


-- ============================================================================
-- STEP 5: Swap tables (RUN ONLY AFTER VERIFYING STEP 4)
-- ============================================================================
-- CAUTION: This will drop the old table - ensure backup if needed

-- DROP TABLE ${CATALOG_SCHEMA}.unmapped_fields;
-- ALTER TABLE ${CATALOG_SCHEMA}.unmapped_fields_v3 RENAME TO unmapped_fields;


-- ============================================================================
-- STEP 6: Create Vector Search Index
-- ============================================================================
-- Run this in Databricks UI or via SDK after table swap
--
-- Endpoint: Use existing vector search endpoint
-- Index Name: unmapped_fields_vs_index
-- Source Table: ${CATALOG_SCHEMA}.unmapped_fields
-- Embedding Column: source_semantic_field
-- Embedding Model: databricks-bge-large-en (same as other indexes)
-- Sync Mode: TRIGGERED (manual sync) or CONTINUOUS
--
-- Recommended columns to include in index:
--   - unmapped_field_id (for lookup)
--   - src_table_name, src_column_name (display)
--   - src_table_physical_name, src_column_physical_name (filtering, database ops)
--   - src_physical_datatype (for type matching)
--   - src_comments (for context)
--   - domain (for domain boosting)


-- ============================================================================
-- STEP 7: Test Vector Search
-- ============================================================================
-- After creating the index, test with a query:

-- SELECT * FROM VECTOR_SEARCH(
--   index => '${CATALOG_SCHEMA}.unmapped_fields_vs_index',
--   query => 'DESCRIPTION: Title of the job position | TYPE: VARCHAR(100) | DOMAIN: employee',
--   num_results => 5
-- );


-- ============================================================================
-- CLEANUP: Remove temporary table if created
-- ============================================================================
-- Only run if you created a v3 table and want to remove it without swapping

-- DROP TABLE IF EXISTS ${CATALOG_SCHEMA}.unmapped_fields_v3;


-- ============================================================================
-- END OF MIGRATION
-- ============================================================================

