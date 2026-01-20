-- ============================================================================
-- V4 UNMAPPED_FIELDS TABLE - With Project in Vector Search
-- ============================================================================
-- 
-- Changes from V3:
-- 1. Added project_id column (required)
-- 2. Updated source_semantic_field to include PROJECT_ID for vector search
--    Format: PROJECT: {project_id} | DESCRIPTION: ... | TYPE: ... | DOMAIN: ...
-- 3. This allows vector search to naturally boost same-project results
--
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema (e.g., oz_dev.silver_dmes_de)
-- ============================================================================


-- ============================================================================
-- STEP 1: Drop existing table (CAUTION: Data will be lost)
-- ============================================================================
-- UNCOMMENT THE NEXT LINE TO DROP AND RECREATE
-- DROP TABLE IF EXISTS ${CATALOG_SCHEMA}.unmapped_fields;


-- ============================================================================
-- STEP 2: Create new table with project_id in vector search semantic field
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${CATALOG_SCHEMA}.unmapped_fields (
  unmapped_field_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- Project association (NEW - required for filtering)
  project_id BIGINT NOT NULL COMMENT 'FK to mapping_projects - which project this field belongs to',
  
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
  -- NEW FORMAT: Includes PROJECT_ID at the start for better same-project matching
  -- When searching, query should also include "PROJECT: {id}" to boost same-project results
  source_semantic_field STRING GENERATED ALWAYS AS (
    CONCAT(
      'PROJECT: ', CAST(project_id AS STRING),
      ' | DESCRIPTION: ', COALESCE(src_comments, src_column_name, ''),
      ' | TYPE: ', COALESCE(src_physical_datatype, 'STRING'),
      ' | DOMAIN: ', COALESCE(domain, '')
    )
  ) COMMENT 'Auto-generated semantic field for vector search - PROJECT + DESCRIPTION + TYPE + DOMAIN',
  
  -- Audit fields
  uploaded_by STRING COMMENT 'User who uploaded this field',
  uploaded_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when field was uploaded',
  created_by STRING DEFAULT 'system' COMMENT 'User who created this record',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when record was created',
  updated_by STRING COMMENT 'User who last updated this record',
  updated_ts TIMESTAMP COMMENT 'Timestamp when record was last updated',
  
  CONSTRAINT pk_unmapped_fields PRIMARY KEY (unmapped_field_id)
)
COMMENT 'Source fields for mapping. Vector search enabled with project_id for same-project boosting.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);


-- ============================================================================
-- STEP 3: Optimize table for common queries
-- ============================================================================

OPTIMIZE ${CATALOG_SCHEMA}.unmapped_fields
ZORDER BY (project_id, mapping_status, src_table_physical_name);


-- ============================================================================
-- STEP 4: Verify table structure
-- ============================================================================

DESCRIBE ${CATALOG_SCHEMA}.unmapped_fields;

-- Check the generated semantic field format
SELECT 
  unmapped_field_id,
  project_id,
  src_column_physical_name,
  source_semantic_field
FROM ${CATALOG_SCHEMA}.unmapped_fields
LIMIT 5;


-- ============================================================================
-- STEP 5: Create Vector Search Index
-- ============================================================================
-- Run this in Databricks UI after table is created and has data
--
-- Index Configuration:
--   Endpoint: (your existing vector search endpoint)
--   Index Name: unmapped_fields_vs_index (or unmapped_fields_index)
--   Source Table: ${CATALOG_SCHEMA}.unmapped_fields
--   
--   Primary Key: unmapped_field_id
--   Embedding Source Column: source_semantic_field
--   Embedding Model: databricks-bge-large-en
--   Sync Mode: TRIGGERED (recommended for control)
--
--   Columns to Include (for retrieval):
--     - unmapped_field_id (for lookup)
--     - project_id (for filtering)
--     - src_table_name, src_column_name (display)
--     - src_table_physical_name, src_column_physical_name (SQL generation)
--     - src_physical_datatype (type matching)
--     - src_comments (context for LLM)
--     - domain (domain context)
--     - mapping_status (filtering)
--     - source_semantic_field (for debug)


-- ============================================================================
-- MIGRATION: If you have existing data, migrate it
-- ============================================================================
-- 
-- If migrating from V3 (without project_id), you'll need to:
-- 1. Create a new table with the new schema
-- 2. Insert data with a default project_id
-- 3. Swap tables
--
-- Example migration:
-- 
-- INSERT INTO ${CATALOG_SCHEMA}.unmapped_fields_v4 (
--   project_id,
--   src_table_name, src_column_name,
--   src_table_physical_name, src_column_physical_name,
--   src_nullable, src_physical_datatype, src_comments,
--   domain, mapping_status, mapped_field_id,
--   uploaded_by, uploaded_ts, created_by, created_ts
-- )
-- SELECT 
--   1 AS project_id,  -- Default project ID for existing data
--   src_table_name, src_column_name,
--   src_table_physical_name, src_column_physical_name,
--   src_nullable, src_physical_datatype, src_comments,
--   domain, mapping_status, mapped_field_id,
--   uploaded_by, uploaded_ts, created_by, created_ts
-- FROM ${CATALOG_SCHEMA}.unmapped_fields;


-- ============================================================================
-- VECTOR SEARCH QUERY EXAMPLES
-- ============================================================================

-- Search with project context (new format)
-- The query should include PROJECT: {id} to boost same-project results
--
-- Example query string:
--   "PROJECT: 5 | DESCRIPTION: Current record indicator active flag | TYPE: STRING"
--
-- This naturally gives higher similarity to fields from project 5

-- Using Python SDK:
-- results = workspace_client.vector_search_indexes.query_index(
--     index_name="catalog.schema.unmapped_fields_index",
--     columns=["unmapped_field_id", "project_id", "src_column_physical_name", "src_comments"],
--     query_text="PROJECT: 5 | DESCRIPTION: Current record indicator | TYPE: STRING",
--     num_results=10
-- )
-- 
-- # Then filter by project_id for exact match (belt and suspenders)
-- filtered = [r for r in results if r['project_id'] == 5]


-- ============================================================================
-- END OF SCRIPT
-- ============================================================================

