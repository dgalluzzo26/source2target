-- ============================================================================
-- Source-to-Target Mapping Platform V2 - Data Migration Script
-- ============================================================================
-- 
-- PURPOSE:
-- Migrate existing data from V1 schema to V2 schema while preserving all
-- historical mappings and metadata.
--
-- MIGRATION STRATEGY:
-- 1. Backup existing V1 tables
-- 2. Migrate semantic_table → semantic_fields (add domain column)
-- 3. Migrate unmapped fields → unmapped_fields (split from combined table)
-- 4. Migrate mapped fields → mapped_fields + mapping_details
-- 5. Initialize feedback table (empty, for future use)
--
-- IMPORTANT: Run this AFTER creating V2 schema (migration_v2_schema.sql)
-- ============================================================================

-- ============================================================================
-- STEP 0: Backup V1 Tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS main.source2target.semantic_table_v1_backup
DEEP CLONE main.source2target.semantic_table;

CREATE TABLE IF NOT EXISTS main.source2target.combined_fields_v1_backup
DEEP CLONE main.source2target.combined_fields;

SELECT 'V1 tables backed up successfully' AS status;

-- ============================================================================
-- STEP 1: Migrate semantic_table → semantic_fields
-- ============================================================================
-- Changes:
-- - Add semantic_field_id (auto-generated)
-- - Add domain column (NULL initially, can be populated later)
-- - Preserve all audit fields
-- ============================================================================

INSERT INTO main.source2target.semantic_fields (
  tgt_table,
  tgt_column,
  tgt_data_type,
  tgt_is_nullable,
  tgt_comments,
  domain,
  created_by,
  created_ts,
  updated_by,
  updated_ts
)
SELECT 
  tgt_table,
  tgt_column,
  tgt_data_type,
  tgt_is_nullable,
  tgt_comments,
  NULL AS domain,  -- TODO: Can be populated based on table naming conventions or manual review
  COALESCE(created_by, 'system') AS created_by,
  COALESCE(created_ts, CURRENT_TIMESTAMP()) AS created_ts,
  updated_by,
  updated_ts
FROM main.source2target.semantic_table
WHERE NOT EXISTS (
  -- Avoid duplicates if migration is re-run
  SELECT 1 FROM main.source2target.semantic_fields sf
  WHERE sf.tgt_table = semantic_table.tgt_table
    AND sf.tgt_column = semantic_table.tgt_column
);

SELECT 
  'semantic_fields' AS table_name,
  COUNT(*) AS migrated_records
FROM main.source2target.semantic_fields;

-- ============================================================================
-- STEP 2: Migrate Unmapped Fields → unmapped_fields
-- ============================================================================
-- V1 Schema: combined_fields table had both mapped and unmapped fields
-- V2 Schema: Split into separate unmapped_fields and mapped_fields tables
--
-- Strategy:
-- - Unmapped fields: Records where tgt_table IS NULL
-- - Mapped fields: Records where tgt_table IS NOT NULL (handled in Step 3)
-- ============================================================================

INSERT INTO main.source2target.unmapped_fields (
  src_table,
  src_column,
  src_data_type,
  src_is_nullable,
  src_comments,
  domain,
  created_by,
  created_ts,
  updated_by,
  updated_ts
)
SELECT 
  src_table,
  src_column,
  src_data_type,
  src_is_nullable,
  src_comments,
  NULL AS domain,  -- TODO: Can be populated based on table naming conventions
  COALESCE(created_by, 'system') AS created_by,
  COALESCE(created_ts, CURRENT_TIMESTAMP()) AS created_ts,
  updated_by,
  updated_ts
FROM main.source2target.combined_fields
WHERE tgt_table IS NULL  -- Unmapped fields only
  AND NOT EXISTS (
    -- Avoid duplicates if migration is re-run
    SELECT 1 FROM main.source2target.unmapped_fields uf
    WHERE uf.src_table = combined_fields.src_table
      AND uf.src_column = combined_fields.src_column
  );

SELECT 
  'unmapped_fields' AS table_name,
  COUNT(*) AS migrated_records
FROM main.source2target.unmapped_fields;

-- ============================================================================
-- STEP 3: Migrate Mapped Fields → mapped_fields + mapping_details
-- ============================================================================
-- V1 Schema: One record per source field in combined_fields
-- V2 Schema: One record per TARGET field in mapped_fields + detail records
--
-- Challenge: V1 had 1:1 mappings, V2 supports many:1
-- Strategy: Create one mapped_field record per target, with one mapping_detail
-- ============================================================================

-- First, insert into mapped_fields (one record per unique target)
INSERT INTO main.source2target.mapped_fields (
  semantic_field_id,
  tgt_table,
  tgt_column,
  concat_strategy,
  concat_separator,
  transformation_expression,
  confidence_score,
  mapping_source,
  ai_reasoning,
  mapping_status,
  mapped_by,
  mapped_ts,
  updated_by,
  updated_ts
)
SELECT 
  sf.semantic_field_id,
  cf.tgt_table,
  cf.tgt_column,
  'NONE' AS concat_strategy,  -- V1 had single field mappings
  NULL AS concat_separator,
  -- Build simple transformation expression from V1 data
  CONCAT(cf.src_table, '.', cf.src_column) AS transformation_expression,
  cf.confidence_score,
  CASE 
    WHEN cf.mapping_source IS NOT NULL THEN cf.mapping_source
    WHEN cf.confidence_score IS NOT NULL THEN 'AI'
    ELSE 'MANUAL'
  END AS mapping_source,
  cf.ai_reasoning,
  'ACTIVE' AS mapping_status,
  COALESCE(cf.created_by, 'system') AS mapped_by,
  COALESCE(cf.created_ts, CURRENT_TIMESTAMP()) AS mapped_ts,
  cf.updated_by,
  cf.updated_ts
FROM main.source2target.combined_fields cf
INNER JOIN main.source2target.semantic_fields sf
  ON cf.tgt_table = sf.tgt_table
  AND cf.tgt_column = sf.tgt_column
WHERE cf.tgt_table IS NOT NULL  -- Only mapped fields
  AND NOT EXISTS (
    -- Avoid duplicates if migration is re-run
    SELECT 1 FROM main.source2target.mapped_fields mf
    WHERE mf.tgt_table = cf.tgt_table
      AND mf.tgt_column = cf.tgt_column
  );

SELECT 
  'mapped_fields' AS table_name,
  COUNT(*) AS migrated_records
FROM main.source2target.mapped_fields;

-- Second, insert into mapping_details (one record per source field)
INSERT INTO main.source2target.mapping_details (
  mapped_field_id,
  unmapped_field_id,
  src_table,
  src_column,
  field_order,
  transformations,
  default_value,
  field_confidence_score,
  created_by,
  created_ts,
  updated_by,
  updated_ts
)
SELECT 
  mf.mapped_field_id,
  NULL AS unmapped_field_id,  -- Source no longer in unmapped_fields since it's mapped
  cf.src_table,
  cf.src_column,
  1 AS field_order,  -- V1 had single field mappings, so always order 1
  NULL AS transformations,  -- V1 didn't track transformations explicitly
  NULL AS default_value,
  cf.confidence_score AS field_confidence_score,
  COALESCE(cf.created_by, 'system') AS created_by,
  COALESCE(cf.created_ts, CURRENT_TIMESTAMP()) AS created_ts,
  cf.updated_by,
  cf.updated_ts
FROM main.source2target.combined_fields cf
INNER JOIN main.source2target.mapped_fields mf
  ON cf.tgt_table = mf.tgt_table
  AND cf.tgt_column = mf.tgt_column
WHERE cf.tgt_table IS NOT NULL  -- Only mapped fields
  AND NOT EXISTS (
    -- Avoid duplicates if migration is re-run
    SELECT 1 FROM main.source2target.mapping_details md
    WHERE md.mapped_field_id = mf.mapped_field_id
      AND md.src_table = cf.src_table
      AND md.src_column = cf.src_column
  );

SELECT 
  'mapping_details' AS table_name,
  COUNT(*) AS migrated_records
FROM main.source2target.mapping_details;

-- ============================================================================
-- STEP 4: Data Quality Checks
-- ============================================================================

-- Check 1: Verify all V1 semantic fields were migrated
SELECT 
  'semantic_fields_migration_check' AS check_name,
  v1_count,
  v2_count,
  CASE WHEN v1_count = v2_count THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
  SELECT 
    COUNT(*) AS v1_count 
  FROM main.source2target.semantic_table
) v1
CROSS JOIN (
  SELECT 
    COUNT(*) AS v2_count 
  FROM main.source2target.semantic_fields
) v2;

-- Check 2: Verify all V1 unmapped fields were migrated
SELECT 
  'unmapped_fields_migration_check' AS check_name,
  v1_count,
  v2_count,
  CASE WHEN v1_count = v2_count THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
  SELECT 
    COUNT(*) AS v1_count 
  FROM main.source2target.combined_fields
  WHERE tgt_table IS NULL
) v1
CROSS JOIN (
  SELECT 
    COUNT(*) AS v2_count 
  FROM main.source2target.unmapped_fields
) v2;

-- Check 3: Verify all V1 mapped fields were migrated
SELECT 
  'mapped_fields_migration_check' AS check_name,
  v1_count,
  v2_mapped_count,
  v2_detail_count,
  CASE WHEN v1_count = v2_mapped_count AND v1_count = v2_detail_count THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
  SELECT 
    COUNT(*) AS v1_count 
  FROM main.source2target.combined_fields
  WHERE tgt_table IS NOT NULL
) v1
CROSS JOIN (
  SELECT 
    COUNT(*) AS v2_mapped_count 
  FROM main.source2target.mapped_fields
) v2_mapped
CROSS JOIN (
  SELECT 
    COUNT(*) AS v2_detail_count 
  FROM main.source2target.mapping_details
) v2_detail;

-- Check 4: Verify referential integrity
SELECT 
  'referential_integrity_check' AS check_name,
  orphan_count,
  CASE WHEN orphan_count = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
  SELECT COUNT(*) AS orphan_count
  FROM main.source2target.mapping_details md
  LEFT JOIN main.source2target.mapped_fields mf ON md.mapped_field_id = mf.mapped_field_id
  WHERE mf.mapped_field_id IS NULL
);

-- ============================================================================
-- STEP 5: Summary Report
-- ============================================================================

SELECT 
  'MIGRATION SUMMARY' AS section,
  '==================' AS divider;

SELECT 
  'semantic_fields' AS table_name,
  COUNT(*) AS total_records,
  COUNT(DISTINCT tgt_table) AS unique_tables,
  COUNT(DISTINCT domain) AS unique_domains,
  SUM(CASE WHEN domain IS NOT NULL THEN 1 ELSE 0 END) AS records_with_domain
FROM main.source2target.semantic_fields

UNION ALL

SELECT 
  'unmapped_fields' AS table_name,
  COUNT(*) AS total_records,
  COUNT(DISTINCT src_table) AS unique_tables,
  COUNT(DISTINCT domain) AS unique_domains,
  SUM(CASE WHEN domain IS NOT NULL THEN 1 ELSE 0 END) AS records_with_domain
FROM main.source2target.unmapped_fields

UNION ALL

SELECT 
  'mapped_fields' AS table_name,
  COUNT(*) AS total_records,
  COUNT(DISTINCT tgt_table) AS unique_tables,
  COUNT(DISTINCT mapping_source) AS unique_mapping_sources,
  SUM(CASE WHEN confidence_score IS NOT NULL THEN 1 ELSE 0 END) AS records_with_confidence
FROM main.source2target.mapped_fields

UNION ALL

SELECT 
  'mapping_details' AS table_name,
  COUNT(*) AS total_records,
  COUNT(DISTINCT src_table) AS unique_src_tables,
  COUNT(DISTINCT mapped_field_id) AS unique_mappings,
  SUM(CASE WHEN transformations IS NOT NULL THEN 1 ELSE 0 END) AS records_with_transformations
FROM main.source2target.mapping_details

UNION ALL

SELECT 
  'transformation_library' AS table_name,
  COUNT(*) AS total_records,
  COUNT(DISTINCT category) AS unique_categories,
  SUM(CASE WHEN is_system = true THEN 1 ELSE 0 END) AS system_transformations,
  SUM(CASE WHEN is_system = false THEN 1 ELSE 0 END) AS custom_transformations
FROM main.source2target.transformation_library;

-- ============================================================================
-- STEP 6: Post-Migration Tasks (TODO)
-- ============================================================================

SELECT 
  'POST-MIGRATION TODO' AS section,
  '====================' AS divider;

SELECT 'TODO' AS task, '1. Populate domain field in semantic_fields based on table naming conventions' AS description
UNION ALL
SELECT 'TODO', '2. Populate domain field in unmapped_fields based on table naming conventions'
UNION ALL
SELECT 'TODO', '3. Review and update transformation_expression in mapped_fields if needed'
UNION ALL
SELECT 'TODO', '4. Configure Vector Search on semantic_fields table'
UNION ALL
SELECT 'TODO', '5. Update application config to use new table names'
UNION ALL
SELECT 'TODO', '6. Test AI suggestions with new schema'
UNION ALL
SELECT 'TODO', '7. Consider dropping V1 tables once migration is validated: combined_fields, semantic_table';

-- ============================================================================
-- OPTIONAL: Domain Classification Helper Query
-- ============================================================================
-- This query suggests domains based on table name patterns
-- Uncomment and customize based on your naming conventions
-- ============================================================================

/*
-- Example: Auto-populate domain based on table name prefixes
UPDATE main.source2target.semantic_fields
SET domain = CASE
  WHEN LOWER(tgt_table) LIKE '%claim%' OR LOWER(tgt_table) LIKE '%clm%' THEN 'claims'
  WHEN LOWER(tgt_table) LIKE '%member%' OR LOWER(tgt_table) LIKE '%mbr%' THEN 'member'
  WHEN LOWER(tgt_table) LIKE '%provider%' OR LOWER(tgt_table) LIKE '%prov%' THEN 'provider'
  WHEN LOWER(tgt_table) LIKE '%financial%' OR LOWER(tgt_table) LIKE '%fin%' THEN 'finance'
  WHEN LOWER(tgt_table) LIKE '%pharmacy%' OR LOWER(tgt_table) LIKE '%rx%' THEN 'pharmacy'
  WHEN LOWER(tgt_table) LIKE '%eligibility%' OR LOWER(tgt_table) LIKE '%elig%' THEN 'member'
  WHEN LOWER(tgt_table) LIKE '%auth%' THEN 'prior_auth'
  ELSE NULL
END
WHERE domain IS NULL;

UPDATE main.source2target.unmapped_fields
SET domain = CASE
  WHEN LOWER(src_table) LIKE '%claim%' OR LOWER(src_table) LIKE '%clm%' THEN 'claims'
  WHEN LOWER(src_table) LIKE '%member%' OR LOWER(src_table) LIKE '%mbr%' THEN 'member'
  WHEN LOWER(src_table) LIKE '%provider%' OR LOWER(src_table) LIKE '%prov%' THEN 'provider'
  WHEN LOWER(src_table) LIKE '%financial%' OR LOWER(src_table) LIKE '%fin%' THEN 'finance'
  WHEN LOWER(src_table) LIKE '%pharmacy%' OR LOWER(src_table) LIKE '%rx%' THEN 'pharmacy'
  WHEN LOWER(src_table) LIKE '%eligibility%' OR LOWER(src_table) LIKE '%elig%' THEN 'member'
  WHEN LOWER(src_table) LIKE '%auth%' THEN 'prior_auth'
  ELSE NULL
END
WHERE domain IS NULL;
*/

-- ============================================================================
-- END OF DATA MIGRATION
-- ============================================================================

