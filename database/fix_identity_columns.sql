-- ============================================================================
-- Fix IDENTITY Columns for Auto-Generated IDs
-- ============================================================================
-- This script ensures all IDENTITY columns are properly configured
-- Run this if you're getting errors about ID columns not being specified
-- ============================================================================

-- Drop and recreate semantic_fields with correct IDENTITY syntax
-- NOTE: This will preserve data if you use CREATE OR REPLACE

-- First, backup data if the table exists
CREATE TABLE IF NOT EXISTS oztest_dev.source2target.semantic_fields_backup AS 
SELECT * FROM oztest_dev.source2target.semantic_fields;

-- Drop the existing table
DROP TABLE IF EXISTS oztest_dev.source2target.semantic_fields;

-- Recreate with explicit IDENTITY settings
CREATE TABLE oztest_dev.source2target.semantic_fields (
  semantic_field_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- Logical names (for display/UI)
  tgt_table_name STRING NOT NULL COMMENT 'Target table logical name (display name, e.g., Member Table)',
  tgt_column_name STRING NOT NULL COMMENT 'Target column logical name (display name, e.g., First Name)',
  
  -- Physical names (for database operations)
  tgt_table_physical_name STRING NOT NULL COMMENT 'Target table physical name (database name, e.g., slv_member)',
  tgt_column_physical_name STRING NOT NULL COMMENT 'Target column physical name (database name, e.g., first_name)',
  
  -- Metadata
  tgt_nullable STRING DEFAULT 'YES' COMMENT 'Whether target field allows NULL values (YES/NO)',
  tgt_physical_datatype STRING COMMENT 'Physical data type (e.g., STRING, INT, DATE)',
  tgt_comments STRING COMMENT 'Description/comments for target field',
  
  -- Domain classification for enhanced AI recommendations
  domain STRING COMMENT 'Domain category (e.g., claims, member, provider, finance, pharmacy)',
  
  -- Audit fields
  created_by STRING DEFAULT 'system' COMMENT 'User who created this record',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when record was created',
  updated_by STRING COMMENT 'User who last updated this record',
  updated_ts TIMESTAMP COMMENT 'Timestamp when record was last updated',
  
  -- Computed semantic field for vector search
  semantic_field STRING GENERATED ALWAYS AS (
    CONCAT_WS(' | ',
      CONCAT('TABLE NAME: ', COALESCE(tgt_table_name, '')),
      CONCAT('COLUMN NAME: ', COALESCE(tgt_column_name, '')),
      CONCAT('TYPE: ', COALESCE(tgt_physical_datatype, '')),
      CONCAT('DESCRIPTION: ', COALESCE(tgt_comments, '')),
      CONCAT('DOMAIN: ', COALESCE(domain, ''))
    )
  ) COMMENT 'Concatenated field for vector embedding',
  
  CONSTRAINT pk_semantic_fields PRIMARY KEY (semantic_field_id)
) 
COMMENT 'Target field definitions with semantic metadata for AI-powered mapping'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);

-- Restore data if backup exists
INSERT INTO oztest_dev.source2target.semantic_fields (
  tgt_table_name,
  tgt_table_physical_name,
  tgt_column_name,
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
  tgt_table_physical_name,
  tgt_column_name,
  tgt_column_physical_name,
  tgt_nullable,
  tgt_physical_datatype,
  tgt_comments,
  domain,
  created_by,
  created_ts,
  updated_by,
  updated_ts
FROM oztest_dev.source2target.semantic_fields_backup
WHERE EXISTS (SELECT 1 FROM oztest_dev.source2target.semantic_fields_backup LIMIT 1);

-- Clean up backup
-- DROP TABLE IF EXISTS oztest_dev.source2target.semantic_fields_backup;

-- ============================================================================
-- Alternative: If you just want to test the INSERT syntax works
-- ============================================================================
-- You can try this simpler approach:

-- Test insert without specifying semantic_field_id
INSERT INTO oztest_dev.source2target.semantic_fields (
  tgt_table_name,
  tgt_table_physical_name,
  tgt_column_name,
  tgt_column_physical_name,
  tgt_nullable,
  tgt_physical_datatype,
  tgt_comments
) VALUES (
  'Test Table',
  'test_table',
  'Test Column',
  'test_column',
  'YES',
  'STRING',
  'This is a test to verify IDENTITY column works'
);

-- If the above works, you can delete the test record:
-- DELETE FROM oztest_dev.source2target.semantic_fields WHERE tgt_table_name = 'Test Table';

