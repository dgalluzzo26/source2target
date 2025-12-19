-- ============================================================================
-- Smart Mapper V3 - Migration Script: Add Domain to Semantic Fields
-- ============================================================================
-- 
-- This script migrates existing tables to include DOMAIN in the auto-generated
-- semantic fields. Since GENERATED ALWAYS columns cannot be altered, we:
--
-- 1. Create new tables with _v3 suffix
-- 2. Insert existing records into new tables
-- 3. Drop old tables
-- 4. Rename new tables to original names
--
-- ============================================================================
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema
-- ============================================================================
-- 
-- IMPORTANT: 
-- - Run this during a maintenance window
-- - Backup your data first
-- - After running, you'll need to recreate vector search indexes
--
-- ============================================================================


-- ============================================================================
-- STEP 1: CREATE NEW semantic_fields TABLE WITH DOMAIN IN GENERATED COLUMN
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${CATALOG_SCHEMA}.semantic_fields_v3 (
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
  
  -- VECTOR SEARCH: Semantic field with DOMAIN for better disambiguation
  semantic_field STRING GENERATED ALWAYS AS (
    CONCAT(
      'DESCRIPTION: ', COALESCE(tgt_comments, tgt_column_name, ''),
      ' | TYPE: ', COALESCE(tgt_physical_datatype, 'STRING'),
      ' | DOMAIN: ', COALESCE(domain, '')
    )
  ) COMMENT 'Semantic field for vector embedding - DESCRIPTION + TYPE + DOMAIN',
  
  CONSTRAINT pk_semantic_fields_v3 PRIMARY KEY (semantic_field_id)
) 
COMMENT 'Target field definitions with semantic metadata for AI-powered mapping.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);


-- ============================================================================
-- STEP 2: INSERT EXISTING semantic_fields RECORDS INTO NEW TABLE
-- ============================================================================
-- Note: We use OVERWRITE to handle re-runs, and exclude the auto-generated columns

SET spark.databricks.delta.schema.autoMerge.enabled = true;

INSERT INTO ${CATALOG_SCHEMA}.semantic_fields_v3 (
  tgt_table_name,
  tgt_column_name,
  tgt_table_physical_name,
  tgt_column_physical_name,
  tgt_nullable,
  tgt_physical_datatype,
  tgt_comments,
  domain,
  created_by,
  created_ts,
  updated_by,
  updated_ts
)
SELECT 
  tgt_table_name,
  tgt_column_name,
  tgt_table_physical_name,
  tgt_column_physical_name,
  tgt_nullable,
  tgt_physical_datatype,
  tgt_comments,
  domain,
  created_by,
  created_ts,
  updated_by,
  updated_ts
FROM ${CATALOG_SCHEMA}.semantic_fields;


-- ============================================================================
-- STEP 3: CREATE NEW mapped_fields TABLE WITH DOMAIN IN GENERATED COLUMN
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${CATALOG_SCHEMA}.mapped_fields_v3 (
  mapped_field_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- Target field reference
  semantic_field_id BIGINT NOT NULL COMMENT 'Foreign key to semantic_fields table',
  
  -- Target field info (denormalized for performance)
  tgt_table_name STRING NOT NULL COMMENT 'Target table logical name',
  tgt_table_physical_name STRING NOT NULL COMMENT 'Target table physical name',
  tgt_column_name STRING NOT NULL COMMENT 'Target column logical name',
  tgt_column_physical_name STRING NOT NULL COMMENT 'Target column physical name',
  tgt_comments STRING COMMENT 'Target column description (denormalized for AI context)',
  
  -- SOURCE EXPRESSION - The complete SQL transformation
  source_expression STRING NOT NULL COMMENT 'Complete SQL expression for the mapping',
  
  -- SOURCE METADATA
  source_tables STRING COMMENT 'Pipe-separated source table logical names',
  source_tables_physical STRING COMMENT 'Pipe-separated source table physical names',
  source_columns STRING COMMENT 'Pipe-separated source column logical names',
  source_columns_physical STRING COMMENT 'Pipe-separated source column physical names',
  source_descriptions STRING COMMENT 'Pipe-separated source column descriptions for AI learning',
  source_datatypes STRING COMMENT 'Pipe-separated source data types',
  source_domain STRING COMMENT 'Source domain category',
  target_domain STRING COMMENT 'Target domain category (denormalized from semantic_fields)',
  
  -- How sources relate
  source_relationship_type STRING DEFAULT 'SINGLE' COMMENT 'SINGLE, JOIN, or UNION',
  
  -- Transformations applied
  transformations_applied STRING COMMENT 'Comma-separated list of transformations',
  
  -- JOIN METADATA for complex patterns
  join_metadata STRING COMMENT 'JSON metadata for JOIN/UNION patterns',
  
  -- AI/CONFIDENCE METADATA
  confidence_score DOUBLE COMMENT 'Overall confidence score (0.0 to 1.0)',
  mapping_source STRING DEFAULT 'MANUAL' COMMENT 'AI, MANUAL, or BULK_UPLOAD',
  ai_reasoning STRING COMMENT 'AI explanation for suggestion',
  ai_generated BOOLEAN DEFAULT false COMMENT 'Whether expression was AI-generated',
  
  -- Status
  mapping_status STRING DEFAULT 'ACTIVE' COMMENT 'ACTIVE, INACTIVE, PENDING_REVIEW',
  
  -- Audit fields
  mapped_by STRING COMMENT 'User who created/approved this mapping',
  mapped_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when mapping was created',
  updated_by STRING COMMENT 'User who last updated this mapping',
  updated_ts TIMESTAMP COMMENT 'Timestamp when mapping was last updated',
  
  -- VECTOR SEARCH: Source semantic field with DOMAIN
  source_semantic_field STRING GENERATED ALWAYS AS (
    CONCAT(
      'DESCRIPTION: ', COALESCE(source_descriptions, source_columns, ''),
      ' | TYPE: ', COALESCE(source_datatypes, 'STRING'),
      ' | DOMAIN: ', COALESCE(source_domain, '')
    )
  ) COMMENT 'Semantic field for pattern matching - DESCRIPTION + TYPE + DOMAIN',
  
  CONSTRAINT pk_mapped_fields_v3 PRIMARY KEY (mapped_field_id)
)
COMMENT 'Complete mappings with SQL expressions. One row = one mapping.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);


-- ============================================================================
-- STEP 4: INSERT EXISTING mapped_fields RECORDS INTO NEW TABLE
-- ============================================================================
-- Handle case where join_metadata or target_domain don't exist in old table

INSERT INTO ${CATALOG_SCHEMA}.mapped_fields_v3 (
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
  target_domain,
  source_relationship_type,
  transformations_applied,
  join_metadata,
  confidence_score,
  mapping_source,
  ai_reasoning,
  ai_generated,
  mapping_status,
  mapped_by,
  mapped_ts,
  updated_by,
  updated_ts
)
SELECT 
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
  NULL as target_domain,  -- New column, will be NULL
  source_relationship_type,
  transformations_applied,
  NULL as join_metadata,  -- New column, will be NULL
  confidence_score,
  mapping_source,
  ai_reasoning,
  ai_generated,
  mapping_status,
  mapped_by,
  mapped_ts,
  updated_by,
  updated_ts
FROM ${CATALOG_SCHEMA}.mapped_fields;


-- ============================================================================
-- STEP 5: VERIFY RECORD COUNTS BEFORE DROPPING
-- ============================================================================
-- Run these queries to verify data was copied correctly:
--
-- SELECT 'semantic_fields' as table_name, COUNT(*) as old_count FROM ${CATALOG_SCHEMA}.semantic_fields
-- UNION ALL
-- SELECT 'semantic_fields_v3' as table_name, COUNT(*) as new_count FROM ${CATALOG_SCHEMA}.semantic_fields_v3;
--
-- SELECT 'mapped_fields' as table_name, COUNT(*) as old_count FROM ${CATALOG_SCHEMA}.mapped_fields
-- UNION ALL
-- SELECT 'mapped_fields_v3' as table_name, COUNT(*) as new_count FROM ${CATALOG_SCHEMA}.mapped_fields_v3;
--
-- Verify semantic_field format includes DOMAIN:
-- SELECT semantic_field_id, tgt_column_name, domain, semantic_field 
-- FROM ${CATALOG_SCHEMA}.semantic_fields_v3 LIMIT 5;
--
-- SELECT mapped_field_id, tgt_column_name, source_domain, source_semantic_field 
-- FROM ${CATALOG_SCHEMA}.mapped_fields_v3 LIMIT 5;


-- ============================================================================
-- STEP 6: DROP OLD TABLES (RUN ONLY AFTER VERIFYING STEP 5!)
-- ============================================================================
-- IMPORTANT: Only run these after confirming data was migrated correctly!

-- DROP TABLE IF EXISTS ${CATALOG_SCHEMA}.mapped_fields;
-- DROP TABLE IF EXISTS ${CATALOG_SCHEMA}.semantic_fields;


-- ============================================================================
-- STEP 7: RENAME NEW TABLES TO ORIGINAL NAMES
-- ============================================================================
-- Run after dropping old tables

-- ALTER TABLE ${CATALOG_SCHEMA}.semantic_fields_v3 RENAME TO semantic_fields;
-- ALTER TABLE ${CATALOG_SCHEMA}.mapped_fields_v3 RENAME TO mapped_fields;


-- ============================================================================
-- STEP 8: ADD FOREIGN KEY CONSTRAINT (if supported)
-- ============================================================================
-- Delta Lake may not enforce FK but this documents the relationship

-- ALTER TABLE ${CATALOG_SCHEMA}.mapped_fields 
-- ADD CONSTRAINT fk_mapped_semantic 
-- FOREIGN KEY (semantic_field_id) REFERENCES ${CATALOG_SCHEMA}.semantic_fields(semantic_field_id);


-- ============================================================================
-- STEP 9: RECREATE VECTOR SEARCH INDEXES
-- ============================================================================
-- After renaming, recreate the vector search indexes
-- Replace 'your-endpoint' with your actual vector search endpoint name
--
-- For semantic_fields:
-- CREATE VECTOR SEARCH INDEX ${CATALOG_SCHEMA}.semantic_fields_vs_idx
-- ON ${CATALOG_SCHEMA}.semantic_fields (semantic_field)
-- USING databricks_bge_large_en
-- WITH (endpoint_name = 'your-vector-search-endpoint');
--
-- For mapped_fields:
-- CREATE VECTOR SEARCH INDEX ${CATALOG_SCHEMA}.mapped_fields_vs_idx
-- ON ${CATALOG_SCHEMA}.mapped_fields (source_semantic_field)
-- USING databricks_bge_large_en
-- WITH (endpoint_name = 'your-vector-search-endpoint');
--
-- Sync indexes after creation:
-- ALTER VECTOR SEARCH INDEX ${CATALOG_SCHEMA}.semantic_fields_vs_idx SYNC;
-- ALTER VECTOR SEARCH INDEX ${CATALOG_SCHEMA}.mapped_fields_vs_idx SYNC;


-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- 
-- Summary of changes:
-- 1. semantic_fields.semantic_field now includes DOMAIN
-- 2. mapped_fields.source_semantic_field now includes DOMAIN  
-- 3. mapped_fields has new columns: target_domain, join_metadata
-- 4. Vector search indexes need to be recreated and synced
--
-- The domain helps disambiguate similar descriptions across different domains
-- (e.g., "Member ID" in claims vs member domain)
--
-- ============================================================================

