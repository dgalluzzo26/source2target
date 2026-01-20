-- ============================================================================
-- Smart Mapper V4 - Target-First Workflow Schema
-- ============================================================================
-- 
-- PURPOSE: Enable target-first mapping workflow where users:
-- 1. Upload source fields
-- 2. Select a target table
-- 3. System auto-suggests mappings for ALL columns in that table
-- 4. User reviews, edits, and approves
-- 5. Track progress by table and overall project
--
-- NEW TABLES:
-- 1. mapping_projects         - Track overall mapping projects
-- 2. target_table_status      - Track progress per target table
-- 3. mapping_suggestions      - Store AI suggestions before approval
--
-- MODIFIED TABLES:
-- 1. unmapped_fields          - Add project_id
-- 2. mapped_fields            - Add project_id (for new mappings)
--
-- ============================================================================
-- REPLACE ${CATALOG_SCHEMA} with your catalog.schema
-- ============================================================================


-- ============================================================================
-- TABLE 1: mapping_projects (Mapping Project Tracking)
-- ============================================================================
-- Purpose: Track overall mapping projects/sessions
-- A project represents a complete mapping effort (e.g., "DMES Member Migration")
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${CATALOG_SCHEMA}.mapping_projects (
  project_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- Project identification
  project_name STRING NOT NULL COMMENT 'Display name for the mapping project',
  project_description STRING COMMENT 'Detailed description of the mapping project',
  
  -- Source context (can have multiple catalogs/schemas)
  source_system_name STRING COMMENT 'Name of the source system being mapped (e.g., DMES, MMIS)',
  source_catalogs STRING COMMENT 'Pipe-separated Databricks catalogs containing source tables (e.g., "bronze_dmes|bronze_mmis")',
  source_schemas STRING COMMENT 'Pipe-separated Databricks schemas containing source tables (e.g., "member|claims")',
  
  -- Target context (can have multiple catalogs/schemas)
  target_catalogs STRING COMMENT 'Pipe-separated Databricks catalogs for target tables (e.g., "silver_dmes|gold_dmes")',
  target_schemas STRING COMMENT 'Pipe-separated Databricks schemas for target tables (e.g., "member|claims")',
  target_domains STRING COMMENT 'Pipe-separated domain filters for semantic_fields (e.g., "Member|Claims")',
  
  -- Status
  -- NOT_STARTED  = Project created but no work done
  -- IN_PROGRESS  = Mapping work in progress
  -- REVIEW       = All tables mapped, pending final review
  -- COMPLETE     = All mappings approved and finalized
  -- ARCHIVED     = Project archived/inactive
  project_status STRING DEFAULT 'NOT_STARTED' COMMENT 'Status: NOT_STARTED, IN_PROGRESS, REVIEW, COMPLETE, ARCHIVED',
  
  -- Progress counters (denormalized for performance on dashboard)
  total_target_tables INT DEFAULT 0 COMMENT 'Total number of target tables to map',
  tables_complete INT DEFAULT 0 COMMENT 'Number of tables fully mapped',
  tables_in_progress INT DEFAULT 0 COMMENT 'Number of tables currently being mapped',
  total_target_columns INT DEFAULT 0 COMMENT 'Total target columns across all tables',
  columns_mapped INT DEFAULT 0 COMMENT 'Number of columns with approved mappings',
  columns_pending_review INT DEFAULT 0 COMMENT 'Number of columns with suggestions pending review',
  
  -- Settings
  -- Note: All mappings require user approval - no auto-approval
  -- Historical mappings (loaded as patterns) are pre-approved
  -- New mappings from this project require approval before becoming patterns
  
  -- Team access
  team_members STRING COMMENT 'Comma-separated emails of team members with access (creator always has access)',
  
  -- Audit fields
  created_by STRING NOT NULL COMMENT 'User who created the project',
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Timestamp when project was created',
  updated_by STRING COMMENT 'User who last updated the project',
  updated_ts TIMESTAMP COMMENT 'Timestamp when project was last updated',
  completed_by STRING COMMENT 'User who marked project complete',
  completed_ts TIMESTAMP COMMENT 'Timestamp when project was completed',
  
  CONSTRAINT pk_mapping_projects PRIMARY KEY (project_id)
)
COMMENT 'Mapping projects track overall progress of source-to-target mapping efforts.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);


-- ============================================================================
-- TABLE 2: target_table_status (Target Table Mapping Progress)
-- ============================================================================
-- Purpose: Track mapping progress for each target table within a project
-- One row per target table per project
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${CATALOG_SCHEMA}.target_table_status (
  target_table_status_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- Links
  project_id BIGINT NOT NULL COMMENT 'FK to mapping_projects',
  
  -- Target table identification (from semantic_fields)
  tgt_table_name STRING NOT NULL COMMENT 'Target table logical name',
  tgt_table_physical_name STRING NOT NULL COMMENT 'Target table physical name',
  tgt_table_description STRING COMMENT 'Description of the target table',
  
  -- Status
  -- NOT_STARTED      = Table not yet worked on
  -- DISCOVERING      = AI is searching for source field matches (async)
  -- SUGGESTIONS_READY = AI suggestions available for review
  -- IN_PROGRESS      = User is reviewing/editing mappings
  -- COMPLETE         = All columns mapped and approved
  -- SKIPPED          = User chose to skip this table
  mapping_status STRING DEFAULT 'NOT_STARTED' COMMENT 'Status: NOT_STARTED, DISCOVERING, SUGGESTIONS_READY, IN_PROGRESS, COMPLETE, SKIPPED',
  
  -- Progress counters
  total_columns INT DEFAULT 0 COMMENT 'Total columns in this target table',
  columns_with_pattern INT DEFAULT 0 COMMENT 'Columns that have past mapping patterns',
  columns_mapped INT DEFAULT 0 COMMENT 'Columns with approved mappings',
  columns_pending_review INT DEFAULT 0 COMMENT 'Columns with AI suggestions pending review',
  columns_no_match INT DEFAULT 0 COMMENT 'Columns where no source match was found',
  columns_skipped INT DEFAULT 0 COMMENT 'Columns user chose to skip',
  
  -- AI processing
  ai_job_id STRING COMMENT 'Job ID for async AI suggestion generation',
  ai_started_ts TIMESTAMP COMMENT 'When AI suggestion generation started',
  ai_completed_ts TIMESTAMP COMMENT 'When AI suggestion generation completed',
  ai_error_message STRING COMMENT 'Error message if AI suggestion failed',
  
  -- Confidence summary
  avg_confidence DOUBLE COMMENT 'Average confidence score across all suggestions',
  min_confidence DOUBLE COMMENT 'Minimum confidence score (flags risky mappings)',
  
  -- User notes
  user_notes STRING COMMENT 'User notes about this table mapping',
  
  -- Priority/ordering
  display_order INT COMMENT 'Order to display tables in UI',
  priority STRING DEFAULT 'NORMAL' COMMENT 'Priority: HIGH, NORMAL, LOW',
  
  -- Audit fields
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'When record was created',
  updated_ts TIMESTAMP COMMENT 'When record was last updated',
  started_by STRING COMMENT 'User who started mapping this table',
  started_ts TIMESTAMP COMMENT 'When user started working on this table',
  completed_by STRING COMMENT 'User who marked table complete',
  completed_ts TIMESTAMP COMMENT 'When table was marked complete',
  
  CONSTRAINT pk_target_table_status PRIMARY KEY (target_table_status_id),
  CONSTRAINT fk_tts_project FOREIGN KEY (project_id) REFERENCES ${CATALOG_SCHEMA}.mapping_projects(project_id)
)
COMMENT 'Tracks mapping progress for each target table within a project.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);

-- Index for quick lookups by project
ALTER TABLE ${CATALOG_SCHEMA}.target_table_status
CLUSTER BY (project_id, mapping_status);


-- ============================================================================
-- TABLE 3: mapping_suggestions (AI-Generated Mapping Suggestions)
-- ============================================================================
-- Purpose: Store AI suggestions before user approval
-- Allows async processing - AI generates suggestions in background
-- User reviews and approves/rejects/edits
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${CATALOG_SCHEMA}.mapping_suggestions (
  suggestion_id BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
  
  -- Links
  project_id BIGINT NOT NULL COMMENT 'FK to mapping_projects',
  target_table_status_id BIGINT NOT NULL COMMENT 'FK to target_table_status',
  semantic_field_id BIGINT NOT NULL COMMENT 'FK to semantic_fields (target column)',
  
  -- Target field info (denormalized for performance)
  tgt_table_name STRING NOT NULL COMMENT 'Target table logical name',
  tgt_table_physical_name STRING NOT NULL COMMENT 'Target table physical name',
  tgt_column_name STRING NOT NULL COMMENT 'Target column logical name',
  tgt_column_physical_name STRING NOT NULL COMMENT 'Target column physical name',
  tgt_comments STRING COMMENT 'Target column description',
  tgt_physical_datatype STRING COMMENT 'Target column data type',
  
  -- Pattern used (from historical mapped_fields)
  pattern_mapped_field_id BIGINT COMMENT 'FK to mapped_fields if using past pattern',
  pattern_type STRING COMMENT 'Pattern type: SINGLE, CONCAT, JOIN, UNION, UNION_WITH_JOINS',
  pattern_sql STRING COMMENT 'Original SQL from past pattern (before rewrite)',
  
  -- Matched source fields (JSON array)
  -- Format: [{"unmapped_field_id": 123, "column": "COL_NAME", "table": "TABLE", "score": 0.95, "role": "output"}]
  matched_source_fields STRING COMMENT 'JSON array of matched source fields with scores',
  
  -- Generated SQL
  suggested_sql STRING COMMENT 'AI-generated SQL expression (rewritten from pattern)',
  sql_changes STRING COMMENT 'JSON array of changes made to pattern SQL',
  
  -- Confidence and reasoning
  confidence_score DOUBLE COMMENT 'AI confidence in this suggestion (0.0-1.0)',
  ai_reasoning STRING COMMENT 'AI explanation for why this mapping was suggested',
  warnings STRING COMMENT 'JSON array of warnings (unmatched columns, low confidence, etc.)',
  
  -- Status
  -- PENDING         = Suggestion ready for user review
  -- APPROVED        = User approved as-is
  -- EDITED          = User edited and approved
  -- REJECTED        = User rejected suggestion
  -- SKIPPED         = User skipped this column
  -- NO_PATTERN      = No past pattern found
  -- NO_MATCH        = Pattern found but no source match
  -- PROCESSING      = AI is still generating suggestion
  -- ERROR           = AI generation failed
  suggestion_status STRING DEFAULT 'PROCESSING' COMMENT 'Status: PROCESSING, PENDING, APPROVED, EDITED, REJECTED, SKIPPED, NO_PATTERN, NO_MATCH, ERROR',
  
  -- If user edited the suggestion
  edited_sql STRING COMMENT 'User-edited SQL (if status is EDITED)',
  edited_source_fields STRING COMMENT 'User-modified source fields JSON',
  edit_notes STRING COMMENT 'User notes about edits made',
  
  -- If rejected
  rejection_reason STRING COMMENT 'Why user rejected this suggestion',
  
  -- Reference to created mapping (after approval)
  created_mapped_field_id BIGINT COMMENT 'FK to mapped_fields after approval',
  
  -- Audit fields
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'When suggestion was generated',
  reviewed_by STRING COMMENT 'User who reviewed this suggestion',
  reviewed_ts TIMESTAMP COMMENT 'When suggestion was reviewed',
  
  CONSTRAINT pk_mapping_suggestions PRIMARY KEY (suggestion_id),
  CONSTRAINT fk_ms_project FOREIGN KEY (project_id) REFERENCES ${CATALOG_SCHEMA}.mapping_projects(project_id),
  CONSTRAINT fk_ms_table_status FOREIGN KEY (target_table_status_id) REFERENCES ${CATALOG_SCHEMA}.target_table_status(target_table_status_id),
  CONSTRAINT fk_ms_semantic FOREIGN KEY (semantic_field_id) REFERENCES ${CATALOG_SCHEMA}.semantic_fields(semantic_field_id)
)
COMMENT 'AI-generated mapping suggestions for user review. Enables async processing and edit tracking.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.feature.allowColumnDefaults' = 'supported'
);

-- Index for quick lookups
ALTER TABLE ${CATALOG_SCHEMA}.mapping_suggestions
CLUSTER BY (project_id, target_table_status_id, suggestion_status);


-- ============================================================================
-- MODIFY TABLE: unmapped_fields (Add project_id)
-- ============================================================================
-- Add project_id to link source fields to a specific mapping project
-- ============================================================================

ALTER TABLE ${CATALOG_SCHEMA}.unmapped_fields
ADD COLUMN project_id BIGINT COMMENT 'FK to mapping_projects - which project these source fields belong to';

-- Add index for project lookups
-- Note: Run this after adding the column
-- ALTER TABLE ${CATALOG_SCHEMA}.unmapped_fields CLUSTER BY (project_id, src_table_physical_name, mapping_status);


-- ============================================================================
-- MODIFY TABLE: mapped_fields (Add project_id and pattern approval)
-- ============================================================================
-- Add project_id to link new mappings to their project
-- Historical mappings (loaded from past) will have project_id = NULL
-- Add is_approved_pattern to control what can be used as AI patterns
-- ============================================================================

ALTER TABLE ${CATALOG_SCHEMA}.mapped_fields
ADD COLUMN project_id BIGINT COMMENT 'FK to mapping_projects - NULL for historical/pattern mappings';

ALTER TABLE ${CATALOG_SCHEMA}.mapped_fields
ADD COLUMN is_approved_pattern BOOLEAN DEFAULT false COMMENT 'Whether this mapping can be used as a pattern for AI suggestions. Historical=true, new mappings start false until approved';

-- Ensure join_metadata column exists (from V3)
-- ALTER TABLE ${CATALOG_SCHEMA}.mapped_fields
-- ADD COLUMN IF NOT EXISTS join_metadata STRING COMMENT 'JSON metadata for JOIN/UNION patterns';

-- For historical mappings, set as approved patterns
-- UPDATE ${CATALOG_SCHEMA}.mapped_fields SET is_approved_pattern = true WHERE project_id IS NULL;


-- ============================================================================
-- VIEW: v_project_dashboard (Project Progress Dashboard)
-- ============================================================================
-- Aggregated view for main dashboard showing project progress
-- ============================================================================

CREATE OR REPLACE VIEW ${CATALOG_SCHEMA}.v_project_dashboard AS
SELECT 
  p.project_id,
  p.project_name,
  p.project_description,
  p.source_system_name,
  p.project_status,
  p.created_by,
  p.created_ts,
  
  -- Table counts
  COUNT(DISTINCT tts.target_table_status_id) AS total_tables,
  COUNT(DISTINCT CASE WHEN tts.mapping_status = 'COMPLETE' THEN tts.target_table_status_id END) AS tables_complete,
  COUNT(DISTINCT CASE WHEN tts.mapping_status = 'IN_PROGRESS' THEN tts.target_table_status_id END) AS tables_in_progress,
  COUNT(DISTINCT CASE WHEN tts.mapping_status = 'SUGGESTIONS_READY' THEN tts.target_table_status_id END) AS tables_ready_for_review,
  COUNT(DISTINCT CASE WHEN tts.mapping_status = 'NOT_STARTED' THEN tts.target_table_status_id END) AS tables_not_started,
  
  -- Column counts  
  SUM(COALESCE(tts.total_columns, 0)) AS total_columns,
  SUM(COALESCE(tts.columns_mapped, 0)) AS columns_mapped,
  SUM(COALESCE(tts.columns_pending_review, 0)) AS columns_pending_review,
  SUM(COALESCE(tts.columns_no_match, 0)) AS columns_no_match,
  
  -- Progress percentage
  CASE 
    WHEN SUM(COALESCE(tts.total_columns, 0)) > 0 
    THEN ROUND(SUM(COALESCE(tts.columns_mapped, 0)) * 100.0 / SUM(tts.total_columns), 1)
    ELSE 0 
  END AS progress_percent,
  
  -- Confidence summary
  AVG(tts.avg_confidence) AS avg_confidence
  
FROM ${CATALOG_SCHEMA}.mapping_projects p
LEFT JOIN ${CATALOG_SCHEMA}.target_table_status tts ON p.project_id = tts.project_id
WHERE p.project_status != 'ARCHIVED'
GROUP BY 
  p.project_id, p.project_name, p.project_description, 
  p.source_system_name, p.project_status, p.created_by, p.created_ts;


-- ============================================================================
-- VIEW: v_target_table_progress (Target Table Progress)
-- ============================================================================
-- Detailed view of each target table's mapping progress within a project
-- ============================================================================

CREATE OR REPLACE VIEW ${CATALOG_SCHEMA}.v_target_table_progress AS
SELECT 
  tts.target_table_status_id,
  tts.project_id,
  p.project_name,
  tts.tgt_table_name,
  tts.tgt_table_physical_name,
  tts.tgt_table_description,
  tts.mapping_status,
  tts.priority,
  
  -- Column counts
  tts.total_columns,
  tts.columns_with_pattern,
  tts.columns_mapped,
  tts.columns_pending_review,
  tts.columns_no_match,
  tts.columns_skipped,
  
  -- Progress percentage
  CASE 
    WHEN tts.total_columns > 0 
    THEN ROUND(tts.columns_mapped * 100.0 / tts.total_columns, 1)
    ELSE 0 
  END AS progress_percent,
  
  -- Remaining columns
  tts.total_columns - tts.columns_mapped - tts.columns_skipped AS columns_remaining,
  
  -- Confidence
  tts.avg_confidence,
  tts.min_confidence,
  
  -- Status indicators
  CASE WHEN tts.min_confidence < 0.5 THEN true ELSE false END AS has_low_confidence,
  CASE WHEN tts.columns_no_match > 0 THEN true ELSE false END AS has_unmatched,
  
  -- Timestamps
  tts.started_ts,
  tts.completed_ts,
  tts.updated_ts,
  
  -- User notes
  tts.user_notes
  
FROM ${CATALOG_SCHEMA}.target_table_status tts
JOIN ${CATALOG_SCHEMA}.mapping_projects p ON tts.project_id = p.project_id
ORDER BY tts.display_order, tts.tgt_table_name;


-- ============================================================================
-- VIEW: v_suggestion_review (Suggestions Ready for Review)
-- ============================================================================
-- Shows all suggestions pending review for a given project/table
-- ============================================================================

CREATE OR REPLACE VIEW ${CATALOG_SCHEMA}.v_suggestion_review AS
SELECT 
  ms.suggestion_id,
  ms.project_id,
  ms.target_table_status_id,
  ms.semantic_field_id,
  
  -- Target info
  ms.tgt_table_name,
  ms.tgt_table_physical_name,
  ms.tgt_column_name,
  ms.tgt_column_physical_name,
  ms.tgt_comments,
  ms.tgt_physical_datatype,
  
  -- Pattern info
  ms.pattern_type,
  ms.pattern_sql,
  
  -- Suggestion
  ms.matched_source_fields,
  ms.suggested_sql,
  ms.confidence_score,
  ms.ai_reasoning,
  ms.warnings,
  
  -- Status
  ms.suggestion_status,
  
  -- Confidence indicator
  CASE 
    WHEN ms.confidence_score >= 0.9 THEN 'HIGH'
    WHEN ms.confidence_score >= 0.7 THEN 'MEDIUM'
    WHEN ms.confidence_score >= 0.5 THEN 'LOW'
    ELSE 'VERY_LOW'
  END AS confidence_level,
  
  -- Has warnings?
  CASE WHEN ms.warnings IS NOT NULL AND ms.warnings != '[]' THEN true ELSE false END AS has_warnings,
  
  -- Edits
  ms.edited_sql,
  ms.edit_notes,
  
  -- Audit
  ms.created_ts,
  ms.reviewed_by,
  ms.reviewed_ts

FROM ${CATALOG_SCHEMA}.mapping_suggestions ms
WHERE ms.suggestion_status IN ('PENDING', 'PROCESSING')
ORDER BY ms.confidence_score DESC;


-- ============================================================================
-- STORED PROCEDURE: Initialize target tables for a project
-- ============================================================================
-- Call after creating a project to populate target_table_status
-- from semantic_fields based on domain filter.
-- 
-- Uses SQL Stored Procedures (ANSI/PSM standard) available in Databricks SQL.
-- Reference: https://www.databricks.com/blog/introducing-sql-stored-procedures-databricks
-- ============================================================================

CREATE OR REPLACE PROCEDURE ${CATALOG_SCHEMA}.sp_initialize_target_tables(
  IN p_project_id BIGINT,
  IN p_domain_filter STRING
)
LANGUAGE SQL
AS
BEGIN
  -- Declare variables
  DECLARE v_tables_created INT DEFAULT 0;
  DECLARE v_columns_total BIGINT DEFAULT 0;
  
  -- Insert target_table_status rows from semantic_fields
  -- Filter by domain if provided (pipe-separated for multiple)
  INSERT INTO ${CATALOG_SCHEMA}.target_table_status (
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
  FROM ${CATALOG_SCHEMA}.semantic_fields
  WHERE (p_domain_filter IS NULL OR p_domain_filter = '' 
         OR INSTR(p_domain_filter, domain) > 0)
  GROUP BY tgt_table_name, tgt_table_physical_name
  ORDER BY tgt_table_name;
  
  -- Get counts for project update
  SET v_tables_created = (
    SELECT COUNT(*) 
    FROM ${CATALOG_SCHEMA}.target_table_status 
    WHERE project_id = p_project_id
  );
  
  SET v_columns_total = (
    SELECT COALESCE(SUM(total_columns), 0) 
    FROM ${CATALOG_SCHEMA}.target_table_status 
    WHERE project_id = p_project_id
  );
  
  -- Update project counters
  UPDATE ${CATALOG_SCHEMA}.mapping_projects
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
-- Recalculates all project-level counters from target_table_status
-- Call after approving/rejecting suggestions or completing tables
-- ============================================================================

CREATE OR REPLACE PROCEDURE ${CATALOG_SCHEMA}.sp_update_project_counters(
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
  SET v_total_tables = (
    SELECT COUNT(*) 
    FROM ${CATALOG_SCHEMA}.target_table_status 
    WHERE project_id = p_project_id
  );
  
  SET v_tables_complete = (
    SELECT COUNT(*) 
    FROM ${CATALOG_SCHEMA}.target_table_status 
    WHERE project_id = p_project_id AND mapping_status = 'COMPLETE'
  );
  
  SET v_tables_in_progress = (
    SELECT COUNT(*) 
    FROM ${CATALOG_SCHEMA}.target_table_status 
    WHERE project_id = p_project_id 
      AND mapping_status IN ('DISCOVERING', 'SUGGESTIONS_READY', 'IN_REVIEW')
  );
  
  -- Calculate column counts
  SET v_total_columns = (
    SELECT COALESCE(SUM(total_columns), 0) 
    FROM ${CATALOG_SCHEMA}.target_table_status 
    WHERE project_id = p_project_id
  );
  
  SET v_columns_mapped = (
    SELECT COALESCE(SUM(columns_mapped), 0) 
    FROM ${CATALOG_SCHEMA}.target_table_status 
    WHERE project_id = p_project_id
  );
  
  SET v_columns_pending = (
    SELECT COALESCE(SUM(columns_pending_review), 0) 
    FROM ${CATALOG_SCHEMA}.target_table_status 
    WHERE project_id = p_project_id
  );
  
  -- Update project
  UPDATE ${CATALOG_SCHEMA}.mapping_projects
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
-- Recalculates column counts for a target table based on suggestion statuses
-- Call after approving/rejecting/skipping suggestions
-- ============================================================================

CREATE OR REPLACE PROCEDURE ${CATALOG_SCHEMA}.sp_recalculate_table_counters(
  IN p_target_table_status_id BIGINT
)
LANGUAGE SQL
AS
BEGIN
  DECLARE v_project_id BIGINT;
  DECLARE v_total_columns INT;
  DECLARE v_with_pattern INT;
  DECLARE v_mapped INT;
  DECLARE v_pending INT;
  DECLARE v_no_match INT;
  DECLARE v_skipped INT;
  DECLARE v_avg_conf DOUBLE;
  DECLARE v_min_conf DOUBLE;
  
  -- Get project_id
  SET v_project_id = (
    SELECT project_id 
    FROM ${CATALOG_SCHEMA}.target_table_status 
    WHERE target_table_status_id = p_target_table_status_id
  );
  
  -- Count suggestions by status
  SET v_total_columns = (
    SELECT COUNT(*) 
    FROM ${CATALOG_SCHEMA}.mapping_suggestions 
    WHERE target_table_status_id = p_target_table_status_id
  );
  
  SET v_with_pattern = (
    SELECT COUNT(*) 
    FROM ${CATALOG_SCHEMA}.mapping_suggestions 
    WHERE target_table_status_id = p_target_table_status_id 
      AND pattern_mapped_field_id IS NOT NULL
  );
  
  SET v_mapped = (
    SELECT COUNT(*) 
    FROM ${CATALOG_SCHEMA}.mapping_suggestions 
    WHERE target_table_status_id = p_target_table_status_id 
      AND suggestion_status IN ('APPROVED', 'EDITED')
  );
  
  SET v_pending = (
    SELECT COUNT(*) 
    FROM ${CATALOG_SCHEMA}.mapping_suggestions 
    WHERE target_table_status_id = p_target_table_status_id 
      AND suggestion_status = 'PENDING'
  );
  
  SET v_no_match = (
    SELECT COUNT(*) 
    FROM ${CATALOG_SCHEMA}.mapping_suggestions 
    WHERE target_table_status_id = p_target_table_status_id 
      AND suggestion_status IN ('NO_MATCH', 'NO_PATTERN')
  );
  
  SET v_skipped = (
    SELECT COUNT(*) 
    FROM ${CATALOG_SCHEMA}.mapping_suggestions 
    WHERE target_table_status_id = p_target_table_status_id 
      AND suggestion_status IN ('SKIPPED', 'REJECTED')
  );
  
  -- Calculate confidence stats
  SET v_avg_conf = (
    SELECT AVG(confidence_score) 
    FROM ${CATALOG_SCHEMA}.mapping_suggestions 
    WHERE target_table_status_id = p_target_table_status_id 
      AND confidence_score IS NOT NULL
  );
  
  SET v_min_conf = (
    SELECT MIN(confidence_score) 
    FROM ${CATALOG_SCHEMA}.mapping_suggestions 
    WHERE target_table_status_id = p_target_table_status_id 
      AND confidence_score IS NOT NULL
  );
  
  -- Update table status
  UPDATE ${CATALOG_SCHEMA}.target_table_status
  SET 
    total_columns = COALESCE(v_total_columns, total_columns),
    columns_with_pattern = COALESCE(v_with_pattern, 0),
    columns_mapped = COALESCE(v_mapped, 0),
    columns_pending_review = COALESCE(v_pending, 0),
    columns_no_match = COALESCE(v_no_match, 0),
    columns_skipped = COALESCE(v_skipped, 0),
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
  CALL ${CATALOG_SCHEMA}.sp_update_project_counters(v_project_id);
  
END;


-- ============================================================================
-- STORED PROCEDURE: Mark pattern as approved
-- ============================================================================
-- Marks a mapped_field as an approved pattern for future use
-- ============================================================================

CREATE OR REPLACE PROCEDURE ${CATALOG_SCHEMA}.sp_approve_as_pattern(
  IN p_mapped_field_id BIGINT,
  IN p_approved_by STRING
)
LANGUAGE SQL
AS
BEGIN
  UPDATE ${CATALOG_SCHEMA}.mapped_fields
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
-- Initialize tables for a new project:
--   CALL oz_dev.silver_mapping.sp_initialize_target_tables(1, 'Member');
--   CALL oz_dev.silver_mapping.sp_initialize_target_tables(2, 'Member|Claims');
--   CALL oz_dev.silver_mapping.sp_initialize_target_tables(3, NULL);  -- All domains
--
-- Update project counters after changes:
--   CALL oz_dev.silver_mapping.sp_update_project_counters(1);
--
-- Recalculate table counters after suggestion review:
--   CALL oz_dev.silver_mapping.sp_recalculate_table_counters(5);
--
-- Approve a mapping as a pattern:
--   CALL oz_dev.silver_mapping.sp_approve_as_pattern(42, 'user@company.com');
--
-- ============================================================================


-- ============================================================================
-- SUMMARY
-- ============================================================================
-- 
-- New Tables:
-- 1. mapping_projects         - Track overall mapping projects
-- 2. target_table_status      - Track progress per target table  
-- 3. mapping_suggestions      - Store AI suggestions for review
--
-- Modified Tables:
-- 1. unmapped_fields          - Added project_id column
-- 2. mapped_fields            - Added project_id, is_approved_pattern columns
--
-- New Views:
-- 1. v_project_dashboard      - Main dashboard stats
-- 2. v_target_table_progress  - Per-table progress details
-- 3. v_suggestion_review      - Suggestions pending review
--
-- Stored Procedures (ANSI/PSM SQL standard):
-- 1. sp_initialize_target_tables(project_id, domain_filter)
--    - Populates target_table_status from semantic_fields
-- 2. sp_update_project_counters(project_id)
--    - Recalculates project-level stats from target tables
-- 3. sp_recalculate_table_counters(target_table_status_id)
--    - Recalculates table stats from suggestions
-- 4. sp_approve_as_pattern(mapped_field_id, approved_by)
--    - Marks a mapping as an approved pattern for reuse
--
-- ============================================================================

