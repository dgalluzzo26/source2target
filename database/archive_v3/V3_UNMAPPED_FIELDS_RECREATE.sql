-- ============================================================================
-- V3 UNMAPPED_FIELDS TABLE - Complete Recreate Script
-- ============================================================================
-- 
-- Changes from previous version:
-- 1. Added source_semantic_field (GENERATED) for vector search
-- 2. Added mapping_status to track field state (PENDING/MAPPED/ARCHIVED)
-- 3. Fields are NO LONGER deleted when mapped - status changes instead
--
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema
-- ============================================================================


-- ============================================================================
-- STEP 1: Drop existing table (CAUTION: Data will be lost)
-- ============================================================================

DROP TABLE IF EXISTS ${CATALOG_SCHEMA}.unmapped_fields;


-- ============================================================================
-- STEP 2: Create new table with vector search and status columns
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
  
  -- Mapping Status (NEW) - tracks whether field has been used in a mapping
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
-- STEP 3: Create indexes for common queries
-- ============================================================================

-- Index for filtering by status and user (UI queries)
-- Note: Databricks Delta tables don't support traditional indexes
-- The following is a Z-ORDER optimization for common query patterns

OPTIMIZE ${CATALOG_SCHEMA}.unmapped_fields
ZORDER BY (mapping_status, uploaded_by, src_table_physical_name);


-- ============================================================================
-- STEP 4: Verify table structure
-- ============================================================================

DESCRIBE ${CATALOG_SCHEMA}.unmapped_fields;


-- ============================================================================
-- STEP 5: Create Vector Search Index
-- ============================================================================
-- Run this in Databricks UI after table is created and has data
--
-- Index Configuration:
--   Endpoint: (your existing vector search endpoint)
--   Index Name: unmapped_fields_vs_index
--   Source Table: ${CATALOG_SCHEMA}.unmapped_fields
--   
--   Primary Key: unmapped_field_id
--   Embedding Source Column: source_semantic_field
--   Embedding Model: databricks-bge-large-en
--   Sync Mode: TRIGGERED (recommended for control)
--
--   Columns to Include:
--     - unmapped_field_id (for lookup)
--     - src_table_name, src_column_name (display)
--     - src_table_physical_name, src_column_physical_name (filtering, SQL)
--     - src_physical_datatype (type matching)
--     - src_comments (context)
--     - domain (domain boosting)
--     - mapping_status (filtering)
--     - uploaded_by (user filtering)


-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- Get fields pending mapping for a user (UI display)
-- SELECT * FROM ${CATALOG_SCHEMA}.unmapped_fields
-- WHERE mapping_status = 'PENDING' 
--   AND uploaded_by = 'current_user'
-- ORDER BY src_table_name, src_column_name;

-- Search for join key candidates from user's tables
-- (Vector search with filter)
-- SELECT * FROM VECTOR_SEARCH(
--   index => '${CATALOG_SCHEMA}.unmapped_fields_vs_index',
--   query => 'DESCRIPTION: identifier key for joining | TYPE: INT | DOMAIN: employee',
--   filters => 'uploaded_by = "user@example.com" AND src_table_physical_name IN ("table1", "table2")',
--   num_results => 10
-- );

-- Mark field as mapped (instead of deleting)
-- UPDATE ${CATALOG_SCHEMA}.unmapped_fields
-- SET mapping_status = 'MAPPED',
--     mapped_field_id = 12345,
--     updated_by = 'current_user',
--     updated_ts = CURRENT_TIMESTAMP()
-- WHERE unmapped_field_id = 100;

-- Restore field to pending (when mapping is deleted)
-- UPDATE ${CATALOG_SCHEMA}.unmapped_fields
-- SET mapping_status = 'PENDING',
--     mapped_field_id = NULL,
--     updated_by = 'current_user',
--     updated_ts = CURRENT_TIMESTAMP()
-- WHERE mapped_field_id = 12345;


-- ============================================================================
-- END OF SCRIPT
-- ============================================================================

