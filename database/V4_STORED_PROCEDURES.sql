-- ============================================================================
-- V4 STORED PROCEDURES - Target-First Workflow
-- ============================================================================
-- 
-- These stored procedures use dynamic SQL (EXECUTE IMMEDIATE) so they work
-- with any catalog and schema configuration.
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
  DECLARE v_full_schema STRING;
  DECLARE v_sql STRING;
  
  SET v_full_schema = p_catalog || '.' || p_schema;
  
  -- Insert target_table_status rows from semantic_fields
  SET v_sql = '
    INSERT INTO ' || v_full_schema || '.target_table_status (
      project_id,
      tgt_table_name,
      tgt_table_physical_name,
      tgt_table_description,
      mapping_status,
      total_columns,
      display_order
    )
    SELECT 
      ' || p_project_id || ' AS project_id,
      tgt_table_name,
      tgt_table_physical_name,
      MIN(tgt_comments) AS tgt_table_description,
      ''NOT_STARTED'' AS mapping_status,
      COUNT(*) AS total_columns,
      ROW_NUMBER() OVER (ORDER BY tgt_table_name) AS display_order
    FROM ' || v_full_schema || '.semantic_fields
    WHERE (' || COALESCE('''' || p_domain_filter || '''', 'NULL') || ' IS NULL 
           OR ' || COALESCE('''' || p_domain_filter || '''', 'NULL') || ' = '''' 
           OR INSTR(' || COALESCE('''' || p_domain_filter || '''', 'NULL') || ', domain) > 0)
    GROUP BY tgt_table_name, tgt_table_physical_name
    ORDER BY tgt_table_name
  ';
  
  EXECUTE IMMEDIATE v_sql;
  
  -- Update project counters
  SET v_sql = '
    UPDATE ' || v_full_schema || '.mapping_projects
    SET 
      total_target_tables = (
        SELECT COUNT(*) 
        FROM ' || v_full_schema || '.target_table_status 
        WHERE project_id = ' || p_project_id || '
      ),
      total_target_columns = (
        SELECT COALESCE(SUM(total_columns), 0) 
        FROM ' || v_full_schema || '.target_table_status 
        WHERE project_id = ' || p_project_id || '
      ),
      project_status = ''ACTIVE'',
      updated_ts = CURRENT_TIMESTAMP()
    WHERE project_id = ' || p_project_id;
  
  EXECUTE IMMEDIATE v_sql;
  
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
  DECLARE v_full_schema STRING;
  DECLARE v_sql STRING;
  
  SET v_full_schema = p_catalog || '.' || p_schema;
  
  SET v_sql = '
    UPDATE ' || v_full_schema || '.mapping_projects
    SET 
      total_target_tables = (
        SELECT COUNT(*) 
        FROM ' || v_full_schema || '.target_table_status 
        WHERE project_id = ' || p_project_id || '
      ),
      tables_complete = (
        SELECT COUNT(*) 
        FROM ' || v_full_schema || '.target_table_status 
        WHERE project_id = ' || p_project_id || ' AND mapping_status = ''COMPLETE''
      ),
      tables_in_progress = (
        SELECT COUNT(*) 
        FROM ' || v_full_schema || '.target_table_status 
        WHERE project_id = ' || p_project_id || ' 
          AND mapping_status IN (''DISCOVERING'', ''SUGGESTIONS_READY'', ''IN_REVIEW'')
      ),
      total_target_columns = (
        SELECT COALESCE(SUM(total_columns), 0) 
        FROM ' || v_full_schema || '.target_table_status 
        WHERE project_id = ' || p_project_id || '
      ),
      columns_mapped = (
        SELECT COALESCE(SUM(columns_mapped), 0) 
        FROM ' || v_full_schema || '.target_table_status 
        WHERE project_id = ' || p_project_id || '
      ),
      columns_pending_review = (
        SELECT COALESCE(SUM(columns_pending_review), 0) 
        FROM ' || v_full_schema || '.target_table_status 
        WHERE project_id = ' || p_project_id || '
      ),
      updated_ts = CURRENT_TIMESTAMP()
    WHERE project_id = ' || p_project_id;
  
  EXECUTE IMMEDIATE v_sql;
  
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
  DECLARE v_full_schema STRING;
  DECLARE v_sql STRING;
  DECLARE v_project_id BIGINT;
  
  SET v_full_schema = p_catalog || '.' || p_schema;
  
  -- Get project_id for later use
  EXECUTE IMMEDIATE '
    SELECT project_id 
    FROM ' || v_full_schema || '.target_table_status 
    WHERE target_table_status_id = ' || p_target_table_status_id
  INTO v_project_id;
  
  -- Update table status with counts from suggestions
  SET v_sql = '
    UPDATE ' || v_full_schema || '.target_table_status tts
    SET 
      columns_with_pattern = (
        SELECT COUNT(*) 
        FROM ' || v_full_schema || '.mapping_suggestions 
        WHERE target_table_status_id = ' || p_target_table_status_id || '
          AND pattern_mapped_field_id IS NOT NULL
      ),
      columns_mapped = (
        SELECT COUNT(*) 
        FROM ' || v_full_schema || '.mapping_suggestions 
        WHERE target_table_status_id = ' || p_target_table_status_id || '
          AND suggestion_status IN (''APPROVED'', ''EDITED'')
      ),
      columns_pending_review = (
        SELECT COUNT(*) 
        FROM ' || v_full_schema || '.mapping_suggestions 
        WHERE target_table_status_id = ' || p_target_table_status_id || '
          AND suggestion_status = ''PENDING''
      ),
      columns_no_match = (
        SELECT COUNT(*) 
        FROM ' || v_full_schema || '.mapping_suggestions 
        WHERE target_table_status_id = ' || p_target_table_status_id || '
          AND suggestion_status IN (''NO_MATCH'', ''NO_PATTERN'')
      ),
      columns_skipped = (
        SELECT COUNT(*) 
        FROM ' || v_full_schema || '.mapping_suggestions 
        WHERE target_table_status_id = ' || p_target_table_status_id || '
          AND suggestion_status IN (''SKIPPED'', ''REJECTED'')
      ),
      avg_confidence = (
        SELECT AVG(confidence_score) 
        FROM ' || v_full_schema || '.mapping_suggestions 
        WHERE target_table_status_id = ' || p_target_table_status_id || '
          AND confidence_score IS NOT NULL
      ),
      min_confidence = (
        SELECT MIN(confidence_score) 
        FROM ' || v_full_schema || '.mapping_suggestions 
        WHERE target_table_status_id = ' || p_target_table_status_id || '
          AND confidence_score IS NOT NULL
      ),
      mapping_status = CASE 
        WHEN (SELECT COUNT(*) FROM ' || v_full_schema || '.mapping_suggestions 
              WHERE target_table_status_id = ' || p_target_table_status_id || '
                AND suggestion_status IN (''PENDING'', ''NO_MATCH'', ''NO_PATTERN'')) = 0 
        THEN ''COMPLETE''
        WHEN (SELECT COUNT(*) FROM ' || v_full_schema || '.mapping_suggestions 
              WHERE target_table_status_id = ' || p_target_table_status_id || '
                AND suggestion_status IN (''APPROVED'', ''EDITED'', ''SKIPPED'', ''REJECTED'')) > 0 
        THEN ''IN_REVIEW''
        ELSE tts.mapping_status
      END,
      completed_ts = CASE 
        WHEN (SELECT COUNT(*) FROM ' || v_full_schema || '.mapping_suggestions 
              WHERE target_table_status_id = ' || p_target_table_status_id || '
                AND suggestion_status IN (''PENDING'', ''NO_MATCH'', ''NO_PATTERN'')) = 0 
        THEN CURRENT_TIMESTAMP()
        ELSE tts.completed_ts
      END,
      updated_ts = CURRENT_TIMESTAMP()
    WHERE target_table_status_id = ' || p_target_table_status_id;
  
  EXECUTE IMMEDIATE v_sql;
  
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
  DECLARE v_full_schema STRING;
  DECLARE v_sql STRING;
  
  SET v_full_schema = p_catalog || '.' || p_schema;
  
  SET v_sql = '
    UPDATE ' || v_full_schema || '.mapped_fields
    SET 
      is_approved_pattern = true,
      pattern_approved_by = ''' || p_approved_by || ''',
      pattern_approved_ts = CURRENT_TIMESTAMP()
    WHERE mapped_field_id = ' || p_mapped_field_id;
  
  EXECUTE IMMEDIATE v_sql;
  
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

