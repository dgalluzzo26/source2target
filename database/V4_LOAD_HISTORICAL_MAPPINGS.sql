-- ============================================================================
-- V4 HISTORICAL MAPPINGS LOAD
-- ============================================================================
-- This SQL transforms uploaded mapping spreadsheet data into the V4 
-- mapped_fields table format.
--
-- V4 KEY CHANGES:
-- - project_id = NULL (historical patterns are shared globally)
-- - is_approved_pattern = TRUE (so patterns are used for AI suggestions)
-- - pattern_approved_by / pattern_approved_ts populated
--
-- PREREQUISITES:
-- 1. Upload your mapping spreadsheet to Databricks as a table
-- 2. Replace ${CATALOG_SCHEMA} with your catalog.schema (e.g., oztest_dev.smartmapper)
-- 3. Replace ${STAGING_TABLE} with your staging table name
--
-- USAGE:
-- 1. Run the SELECT first to verify the transformation
-- 2. Once satisfied, run the INSERT statement
-- ============================================================================


-- ============================================================================
-- STEP 1: PREVIEW THE TRANSFORMATION
-- ============================================================================

SELECT
    -- Target Field Info
    `Silver_TABLE NAME` AS tgt_table_name,
    `Silver Table Physical Name` AS tgt_table_physical_name,
    `Silver Attribute Column  Name` AS tgt_column_name,
    `Silver Attribute Column Physical Name` AS tgt_column_physical_name,
    `Silver Attribute Column Definition` AS tgt_comments,
    
    -- Source Expression (the complete SQL)
    CASE 
        WHEN `Transformation Logic (Describe in english or pseudocode)` IS NOT NULL 
             AND TRIM(`Transformation Logic (Describe in english or pseudocode)`) != ''
             AND UPPER(`Transformation Logic (Describe in english or pseudocode)`) NOT LIKE 'AUTO GENERATED%'
             AND UPPER(`Transformation Logic (Describe in english or pseudocode)`) NOT LIKE 'HARD CODED%'
             AND UPPER(`Transformation Logic (Describe in english or pseudocode)`) NOT LIKE 'CURRENT TIME%'
             AND UPPER(`Transformation Logic (Describe in english or pseudocode)`) NOT LIKE 'PLEASE CHECK%'
        THEN `Transformation Logic (Describe in english or pseudocode)`
        -- Build simple expression from physical column name(s)
        WHEN `Bronze_Attribute Column Physical Name` IS NOT NULL 
        THEN CONCAT('TRIM(', REPLACE(`Bronze_Attribute Column Physical Name`, '|', '), TRIM('), ')')
        ELSE NULL
    END AS source_expression,
    
    -- Source Field Info (pipe-delimited)
    `BRONZE_TABLE NAME` AS source_tables,
    `Bronze_Attribute Column Name` AS source_columns,
    `Bronze_Attribute Column Physical Name` AS source_columns_physical,
    `Bronze_Attribute Column Description` AS source_descriptions,
    
    -- Relationship type derived from Function column
    CASE 
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%JOIN%' AND UPPER(COALESCE(`Function`, '')) LIKE '%UNION%' THEN 'UNION'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%UNION%' THEN 'UNION'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%JOIN%' THEN 'JOIN'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%CONCAT%' THEN 'CONCAT'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%LOOKUP%' THEN 'JOIN'
        WHEN `Bronze_Attribute Column Physical Name` LIKE '%|%' THEN 'CONCAT'
        ELSE 'SINGLE'
    END AS source_relationship_type,
    
    -- Domain
    `Subject Area` AS domain,
    
    -- V4 Pattern Fields (NEW)
    NULL AS project_id,                          -- Global pattern, not project-specific
    TRUE AS is_approved_pattern,                 -- Available for AI to use
    'historical_import@gainwell.com' AS pattern_approved_by,
    
    -- Metadata
    'HISTORICAL' AS mapping_source,
    FALSE AS ai_generated,
    'ACTIVE' AS mapping_status,
    0.95 AS confidence_score                     -- High confidence for historical

FROM ${CATALOG_SCHEMA}.${STAGING_TABLE}
WHERE `Silver Attribute Column Physical Name` IS NOT NULL
  AND TRIM(`Silver Attribute Column Physical Name`) != ''
ORDER BY `Silver_TABLE NAME`, `Silver Attribute Column Physical Name`;


-- ============================================================================
-- STEP 2: CHECK COUNTS
-- ============================================================================
/*
-- Total row count
SELECT COUNT(*) AS total_mappings 
FROM ${CATALOG_SCHEMA}.${STAGING_TABLE}
WHERE `Silver Attribute Column Physical Name` IS NOT NULL;

-- By relationship type
SELECT 
    CASE 
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%JOIN%' AND UPPER(COALESCE(`Function`, '')) LIKE '%UNION%' THEN 'UNION'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%UNION%' THEN 'UNION'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%JOIN%' THEN 'JOIN'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%CONCAT%' THEN 'CONCAT'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%LOOKUP%' THEN 'JOIN'
        WHEN `Bronze_Attribute Column Physical Name` LIKE '%|%' THEN 'CONCAT'
        ELSE 'SINGLE'
    END AS relationship_type,
    COUNT(*) AS count
FROM ${CATALOG_SCHEMA}.${STAGING_TABLE}
WHERE `Silver Attribute Column Physical Name` IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC;

-- By target table
SELECT 
    `Silver_TABLE NAME` AS target_table,
    COUNT(*) AS column_count
FROM ${CATALOG_SCHEMA}.${STAGING_TABLE}
WHERE `Silver Attribute Column Physical Name` IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC;
*/


-- ============================================================================
-- STEP 3: INSERT INTO mapped_fields (V4 Schema)
-- ============================================================================
/*
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    -- Target Info
    semantic_field_id,
    tgt_table_name,
    tgt_table_physical_name,
    tgt_column_name,
    tgt_column_physical_name,
    tgt_comments,
    
    -- Source Expression & Fields
    source_expression,
    source_tables,
    source_tables_physical,
    source_columns,
    source_columns_physical,
    source_descriptions,
    source_datatypes,
    source_domain,
    source_relationship_type,
    transformations_applied,
    
    -- Join Metadata (NULL for now, can be populated later via LLM)
    join_metadata,
    
    -- V4 Project & Pattern Fields (NEW)
    project_id,
    is_approved_pattern,
    pattern_approved_by,
    pattern_approved_ts,
    
    -- Confidence & Metadata
    confidence_score,
    mapping_source,
    ai_reasoning,
    ai_generated,
    mapping_status,
    mapped_by,
    mapped_ts
)
SELECT
    -- Semantic field lookup
    COALESCE(
        (SELECT sf.semantic_field_id 
         FROM ${CATALOG_SCHEMA}.semantic_fields sf 
         WHERE UPPER(sf.tgt_column_physical_name) = UPPER(stg.`Silver Attribute Column Physical Name`)
           AND UPPER(sf.tgt_table_physical_name) = UPPER(stg.`Silver Table Physical Name`)
         LIMIT 1),
        0
    ) AS semantic_field_id,
    
    -- Target fields
    stg.`Silver_TABLE NAME` AS tgt_table_name,
    stg.`Silver Table Physical Name` AS tgt_table_physical_name,
    stg.`Silver Attribute Column  Name` AS tgt_column_name,
    stg.`Silver Attribute Column Physical Name` AS tgt_column_physical_name,
    stg.`Silver Attribute Column Definition` AS tgt_comments,
    
    -- Source expression
    CASE 
        WHEN stg.`Transformation Logic (Describe in english or pseudocode)` IS NOT NULL 
             AND TRIM(stg.`Transformation Logic (Describe in english or pseudocode)`) != ''
             AND UPPER(stg.`Transformation Logic (Describe in english or pseudocode)`) NOT LIKE 'AUTO GENERATED%'
             AND UPPER(stg.`Transformation Logic (Describe in english or pseudocode)`) NOT LIKE 'HARD CODED%'
             AND UPPER(stg.`Transformation Logic (Describe in english or pseudocode)`) NOT LIKE 'CURRENT TIME%'
             AND UPPER(stg.`Transformation Logic (Describe in english or pseudocode)`) NOT LIKE 'PLEASE CHECK%'
        THEN stg.`Transformation Logic (Describe in english or pseudocode)`
        WHEN stg.`Bronze_Attribute Column Physical Name` IS NOT NULL 
        THEN CONCAT('TRIM(', REPLACE(stg.`Bronze_Attribute Column Physical Name`, '|', '), TRIM('), ')')
        ELSE 'N/A'
    END AS source_expression,
    
    -- Source metadata
    stg.`BRONZE_TABLE NAME` AS source_tables,
    stg.`Bronze_Attribute Column Physical Name` AS source_tables_physical,
    stg.`Bronze_Attribute Column Name` AS source_columns,
    stg.`Bronze_Attribute Column Physical Name` AS source_columns_physical,
    stg.`Bronze_Attribute Column Description` AS source_descriptions,
    NULL AS source_datatypes,
    stg.`Subject Area` AS source_domain,
    
    -- Relationship type
    CASE 
        WHEN UPPER(COALESCE(stg.`Function`, '')) LIKE '%JOIN%' AND UPPER(COALESCE(stg.`Function`, '')) LIKE '%UNION%' THEN 'UNION'
        WHEN UPPER(COALESCE(stg.`Function`, '')) LIKE '%UNION%' THEN 'UNION'
        WHEN UPPER(COALESCE(stg.`Function`, '')) LIKE '%JOIN%' THEN 'JOIN'
        WHEN UPPER(COALESCE(stg.`Function`, '')) LIKE '%CONCAT%' THEN 'CONCAT'
        WHEN UPPER(COALESCE(stg.`Function`, '')) LIKE '%LOOKUP%' THEN 'JOIN'
        WHEN stg.`Bronze_Attribute Column Physical Name` LIKE '%|%' THEN 'CONCAT'
        ELSE 'SINGLE'
    END AS source_relationship_type,
    
    -- Transformations
    CASE 
        WHEN UPPER(COALESCE(stg.`Function`, '')) LIKE '%INITCAP%' THEN 'INITCAP'
        WHEN UPPER(COALESCE(stg.`Function`, '')) LIKE '%CONCAT%' THEN 'CONCAT'
        WHEN UPPER(COALESCE(stg.`Function`, '')) LIKE '%DRIVED%' OR UPPER(COALESCE(stg.`Function`, '')) LIKE '%DERIVED%' THEN 'DERIVED'
        WHEN UPPER(COALESCE(stg.`Function`, '')) LIKE '%LOOKUP%' OR UPPER(COALESCE(stg.`Function`, '')) LIKE '%LOOK%' THEN 'LOOKUP'
        ELSE NULL
    END AS transformations_applied,
    
    -- Join metadata (can be populated later via LLM parsing)
    NULL AS join_metadata,
    
    -- V4 NEW: Project and Pattern fields
    NULL AS project_id,                          -- NULL = global pattern (shared)
    TRUE AS is_approved_pattern,                 -- TRUE = available for AI to use
    'historical_import@gainwell.com' AS pattern_approved_by,
    CURRENT_TIMESTAMP() AS pattern_approved_ts,
    
    -- Confidence & Metadata
    0.95 AS confidence_score,                    -- High confidence for historical
    'HISTORICAL' AS mapping_source,
    CONCAT('Imported from historical mapping specification. Original logic: ', 
           COALESCE(stg.`Transformation Logic (Describe in english or pseudocode)`, 'N/A')) AS ai_reasoning,
    FALSE AS ai_generated,
    'ACTIVE' AS mapping_status,
    'historical_import@gainwell.com' AS mapped_by,
    CURRENT_TIMESTAMP() AS mapped_ts

FROM ${CATALOG_SCHEMA}.${STAGING_TABLE} stg
WHERE stg.`Silver Attribute Column Physical Name` IS NOT NULL
  AND TRIM(stg.`Silver Attribute Column Physical Name`) != '';
*/


-- ============================================================================
-- STEP 4 (OPTIONAL): Generate join_metadata via LLM
-- ============================================================================
-- After importing, you can use an LLM to parse complex SQL expressions and
-- populate the join_metadata JSON column. This helps the AI suggest better
-- SQL rewrites for new projects.
--
-- See V4_GENERATE_JOIN_METADATA.sql for the LLM-based metadata generation.
-- ============================================================================


-- ============================================================================
-- STEP 5: VERIFY IMPORT
-- ============================================================================
/*
-- Check imported patterns
SELECT 
    tgt_table_name,
    COUNT(*) AS pattern_count,
    COUNT(CASE WHEN is_approved_pattern THEN 1 END) AS approved_patterns,
    AVG(confidence_score) AS avg_confidence
FROM ${CATALOG_SCHEMA}.mapped_fields
WHERE project_id IS NULL  -- Only global patterns
  AND mapping_source = 'HISTORICAL'
GROUP BY tgt_table_name
ORDER BY pattern_count DESC;

-- Check relationship type distribution
SELECT 
    source_relationship_type,
    COUNT(*) AS count
FROM ${CATALOG_SCHEMA}.mapped_fields
WHERE project_id IS NULL
GROUP BY source_relationship_type
ORDER BY count DESC;
*/


-- ============================================================================
-- NOTES ON V4 PATTERN USAGE
-- ============================================================================
-- 
-- How patterns are used in V4 Target-First workflow:
--
-- 1. User creates a new project → project_id assigned
-- 2. User uploads source fields → unmapped_fields with project_id
-- 3. User selects a target table → AI discovery starts
-- 4. For each target column, the system:
--    a) Queries mapped_fields for patterns where:
--       - tgt_table_physical_name and tgt_column_physical_name match
--       - is_approved_pattern = TRUE (or NULL for historical)
--       - mapping_status = 'ACTIVE'
--    b) Finds the best pattern (highest confidence)
--    c) Vector searches user's source fields for matches
--    d) LLM rewrites the pattern SQL with user's columns
--    e) Creates a suggestion for user review
--
-- 5. When user approves a suggestion:
--    a) New row in mapped_fields WITH project_id (project-specific)
--    b) is_approved_pattern = FALSE (not a global pattern yet)
--    c) User can later promote it to a pattern via sp_approve_as_pattern
--
-- ============================================================================

