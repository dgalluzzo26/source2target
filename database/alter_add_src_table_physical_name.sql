-- ============================================================================
-- ALTER SCRIPT: Add src_table_physical_name to unmapped_fields
-- ============================================================================
-- Purpose: Add missing src_table_physical_name column to existing V2 tables
-- Run this if you already deployed V2 schema without this column
-- ============================================================================

-- Add the missing column
ALTER TABLE oztest_dev.source2target.unmapped_fields 
ADD COLUMN src_table_physical_name STRING 
COMMENT 'Source table physical name (database name, e.g., t_member)';

-- Update existing records to set physical name = logical name
UPDATE oztest_dev.source2target.unmapped_fields 
SET src_table_physical_name = src_table_name
WHERE src_table_physical_name IS NULL;

-- Make the column NOT NULL after populating
ALTER TABLE oztest_dev.source2target.unmapped_fields 
ALTER COLUMN src_table_physical_name SET NOT NULL;

-- Verify the change
SELECT 
  src_table_name,
  src_table_physical_name,
  src_column_name,
  src_column_physical_name
FROM oztest_dev.source2target.unmapped_fields
LIMIT 10;

