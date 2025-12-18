-- ============================================================================
-- V4 STORED PROCEDURES - Target-First Workflow
-- ============================================================================
-- 
-- These stored procedures use IDENTIFIER() for dynamic table references,
-- allowing them to work with any catalog and schema configuration.
--
-- USAGE:
--   CALL oztest_dev.smartmapper.sp_initialize_target_tables(
--     'oztest_dev', 'smartmapper', 1, 'Member'
--   );
--
-- The catalog/schema parameters allow these procedures to work with
-- different environments (dev, test, prod) without modification.
--
-- Reference: https://www.databricks.com/blog/introducing-sql-stored-procedures-databricks
-- ============================================================================


-- ============================================================================
-- STORED PROCEDURE: Initialize target tables for a project
-- ============================================================================
-- Populates target_table_status from semantic_fields when starting a project.
-- 
-- Parameters:
--   p_catalog       - Catalog name (e.g., 'oztest_dev')
--   p_schema        - Schema name (e.g., 'smartmapper')
--   p_project_id    - Project ID to initialize
--   p_domain_filter - Domain filter (NULL for all, or 'Member', 'Member|Claims')
--
-- Example:
--   CALL oztest_dev.smartmapper.sp_initialize_target_tables(
--     'oztest_dev', 'smartmapper', 1, 'Member'
--   );
-- ============================================================================

CREATE OR REPLACE PROCEDURE oztest_dev.smartmapper.sp_initialize_target_tables(
  IN p_catalog STRING,
  IN p_schema STRING,
  IN p_project_id BIGINT,
  IN p_domain_filter STRING
)
LANGUAGE SQL
AS
BEGIN
  DECLARE v_tables_created INT DEFAULT 0;
  DECLARE v_columns_total BIGINT DEFAULT 0;
  
  -- Insert target_table_status rows from semantic_fields
  INSERT INTO IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'target_table_status') (
    project_id,
    tgt_table_name,
    tgt_table_physical_name,
    tgt_table_description,
    mapping_status,
    total_columns,
    display_order
  )
  SELECT 
    p_project_id AS project_id,
    tgt_table_name,
    tgt_table_physical_name,
    MIN(tgt_comments) AS tgt_table_description,
    'NOT_STARTED' AS mapping_status,
    COUNT(*) AS total_columns,
    ROW_NUMBER() OVER (ORDER BY tgt_table_name) AS display_order
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'semantic_fields')
  WHERE (p_domain_filter IS NULL 
         OR p_domain_filter = '' 
         OR INSTR(p_domain_filter, domain) > 0)
  GROUP BY tgt_table_name, tgt_table_physical_name
  ORDER BY tgt_table_name;
  
  -- Get counts for project update
  SELECT COUNT(*) INTO v_tables_created
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'target_table_status')
  WHERE project_id = p_project_id;
  
  SELECT COALESCE(SUM(total_columns), 0) INTO v_columns_total
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'target_table_status')
  WHERE project_id = p_project_id;
  
  -- Update project counters
  UPDATE IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'mapping_projects')
  SET 
    total_target_tables = v_tables_created,
    total_target_columns = v_columns_total,
    project_status = 'ACTIVE',
    updated_ts = CURRENT_TIMESTAMP()
  WHERE project_id = p_project_id;
  
END;


-- ============================================================================
-- STORED PROCEDURE: Update project counters
-- ============================================================================
-- Recalculates all project-level counters from target_table_status.
-- Call after approving/rejecting suggestions or completing tables.
--
-- Parameters:
--   p_catalog    - Catalog name
--   p_schema     - Schema name
--   p_project_id - Project ID to update
--
-- Example:
--   CALL oztest_dev.smartmapper.sp_update_project_counters(
--     'oztest_dev', 'smartmapper', 1
--   );
-- ============================================================================

CREATE OR REPLACE PROCEDURE oztest_dev.smartmapper.sp_update_project_counters(
  IN p_catalog STRING,
  IN p_schema STRING,
  IN p_project_id BIGINT
)
LANGUAGE SQL
AS
BEGIN
  DECLARE v_total_tables INT;
  DECLARE v_tables_complete INT;
  DECLARE v_tables_in_progress INT;
  DECLARE v_total_columns BIGINT;
  DECLARE v_columns_mapped BIGINT;
  DECLARE v_columns_pending BIGINT;
  
  -- Calculate table counts
  SELECT COUNT(*) INTO v_total_tables
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'target_table_status')
  WHERE project_id = p_project_id;
  
  SELECT COUNT(*) INTO v_tables_complete
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'target_table_status')
  WHERE project_id = p_project_id AND mapping_status = 'COMPLETE';
  
  SELECT COUNT(*) INTO v_tables_in_progress
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'target_table_status')
  WHERE project_id = p_project_id 
    AND mapping_status IN ('DISCOVERING', 'SUGGESTIONS_READY', 'IN_REVIEW');
  
  -- Calculate column counts
  SELECT COALESCE(SUM(total_columns), 0) INTO v_total_columns
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'target_table_status')
  WHERE project_id = p_project_id;
  
  SELECT COALESCE(SUM(columns_mapped), 0) INTO v_columns_mapped
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'target_table_status')
  WHERE project_id = p_project_id;
  
  SELECT COALESCE(SUM(columns_pending_review), 0) INTO v_columns_pending
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'target_table_status')
  WHERE project_id = p_project_id;
  
  -- Update project
  UPDATE IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'mapping_projects')
  SET 
    total_target_tables = v_total_tables,
    tables_complete = v_tables_complete,
    tables_in_progress = v_tables_in_progress,
    total_target_columns = v_total_columns,
    columns_mapped = v_columns_mapped,
    columns_pending_review = v_columns_pending,
    updated_ts = CURRENT_TIMESTAMP()
  WHERE project_id = p_project_id;
  
END;


-- ============================================================================
-- STORED PROCEDURE: Recalculate table counters from suggestions
-- ============================================================================
-- Recalculates column counts for a target table based on suggestion statuses.
-- Call after approving/rejecting/skipping suggestions.
--
-- Parameters:
--   p_catalog                - Catalog name
--   p_schema                 - Schema name
--   p_target_table_status_id - Target table status ID to update
--
-- Example:
--   CALL oztest_dev.smartmapper.sp_recalculate_table_counters(
--     'oztest_dev', 'smartmapper', 5
--   );
-- ============================================================================

CREATE OR REPLACE PROCEDURE oztest_dev.smartmapper.sp_recalculate_table_counters(
  IN p_catalog STRING,
  IN p_schema STRING,
  IN p_target_table_status_id BIGINT
)
LANGUAGE SQL
AS
BEGIN
  DECLARE v_project_id BIGINT;
  DECLARE v_with_pattern INT;
  DECLARE v_mapped INT;
  DECLARE v_pending INT;
  DECLARE v_no_match INT;
  DECLARE v_skipped INT;
  DECLARE v_avg_conf DOUBLE;
  DECLARE v_min_conf DOUBLE;
  
  -- Get project_id
  SELECT project_id INTO v_project_id
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'target_table_status')
  WHERE target_table_status_id = p_target_table_status_id;
  
  -- Count suggestions by status
  SELECT COUNT(*) INTO v_with_pattern
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'mapping_suggestions')
  WHERE target_table_status_id = p_target_table_status_id 
    AND pattern_mapped_field_id IS NOT NULL;
  
  SELECT COUNT(*) INTO v_mapped
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'mapping_suggestions')
  WHERE target_table_status_id = p_target_table_status_id 
    AND suggestion_status IN ('APPROVED', 'EDITED');
  
  SELECT COUNT(*) INTO v_pending
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'mapping_suggestions')
  WHERE target_table_status_id = p_target_table_status_id 
    AND suggestion_status = 'PENDING';
  
  SELECT COUNT(*) INTO v_no_match
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'mapping_suggestions')
  WHERE target_table_status_id = p_target_table_status_id 
    AND suggestion_status IN ('NO_MATCH', 'NO_PATTERN');
  
  SELECT COUNT(*) INTO v_skipped
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'mapping_suggestions')
  WHERE target_table_status_id = p_target_table_status_id 
    AND suggestion_status IN ('SKIPPED', 'REJECTED');
  
  -- Calculate confidence stats
  SELECT AVG(confidence_score) INTO v_avg_conf
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'mapping_suggestions')
  WHERE target_table_status_id = p_target_table_status_id 
    AND confidence_score IS NOT NULL;
  
  SELECT MIN(confidence_score) INTO v_min_conf
  FROM IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'mapping_suggestions')
  WHERE target_table_status_id = p_target_table_status_id 
    AND confidence_score IS NOT NULL;
  
  -- Update table status
  UPDATE IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'target_table_status')
  SET 
    columns_with_pattern = v_with_pattern,
    columns_mapped = v_mapped,
    columns_pending_review = v_pending,
    columns_no_match = v_no_match,
    columns_skipped = v_skipped,
    avg_confidence = v_avg_conf,
    min_confidence = v_min_conf,
    mapping_status = CASE 
      WHEN v_pending = 0 AND v_no_match = 0 THEN 'COMPLETE'
      WHEN v_mapped > 0 OR v_skipped > 0 THEN 'IN_REVIEW'
      ELSE mapping_status
    END,
    completed_ts = CASE 
      WHEN v_pending = 0 AND v_no_match = 0 THEN CURRENT_TIMESTAMP()
      ELSE completed_ts
    END,
    updated_ts = CURRENT_TIMESTAMP()
  WHERE target_table_status_id = p_target_table_status_id;
  
  -- Also update project counters
  CALL oztest_dev.smartmapper.sp_update_project_counters(p_catalog, p_schema, v_project_id);
  
END;


-- ============================================================================
-- STORED PROCEDURE: Approve mapping as pattern
-- ============================================================================
-- Marks a mapped_field as an approved pattern for future AI suggestions.
--
-- Parameters:
--   p_catalog         - Catalog name
--   p_schema          - Schema name
--   p_mapped_field_id - Mapped field ID to approve as pattern
--   p_approved_by     - User email approving
--
-- Example:
--   CALL oztest_dev.smartmapper.sp_approve_as_pattern(
--     'oztest_dev', 'smartmapper', 42, 'user@company.com'
--   );
-- ============================================================================

CREATE OR REPLACE PROCEDURE oztest_dev.smartmapper.sp_approve_as_pattern(
  IN p_catalog STRING,
  IN p_schema STRING,
  IN p_mapped_field_id BIGINT,
  IN p_approved_by STRING
)
LANGUAGE SQL
AS
BEGIN
  UPDATE IDENTIFIER(p_catalog || '.' || p_schema || '.' || 'mapped_fields')
  SET 
    is_approved_pattern = true,
    pattern_approved_by = p_approved_by,
    pattern_approved_ts = CURRENT_TIMESTAMP()
  WHERE mapped_field_id = p_mapped_field_id;
END;


-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================
-- 
-- All procedures take catalog and schema as the first two parameters.
-- This allows them to work with any environment configuration.
--
-- Initialize tables for a new project (Member domain):
--   CALL oztest_dev.smartmapper.sp_initialize_target_tables(
--     'oztest_dev', 'smartmapper', 1, 'Member'
--   );
--
-- Initialize tables for all domains:
--   CALL oztest_dev.smartmapper.sp_initialize_target_tables(
--     'oztest_dev', 'smartmapper', 2, NULL
--   );
--
-- Update project counters after changes:
--   CALL oztest_dev.smartmapper.sp_update_project_counters(
--     'oztest_dev', 'smartmapper', 1
--   );
--
-- Recalculate table counters after suggestion review:
--   CALL oztest_dev.smartmapper.sp_recalculate_table_counters(
--     'oztest_dev', 'smartmapper', 5
--   );
--
-- Approve a mapping as a pattern:
--   CALL oztest_dev.smartmapper.sp_approve_as_pattern(
--     'oztest_dev', 'smartmapper', 42, 'user@company.com'
--   );
--
-- ============================================================================
