-- ============================================================================
-- HISTORICAL MAPPINGS LOAD - SELECT Statement
-- ============================================================================
-- This SQL transforms the uploaded Mapping_spec_template_V1.xlsx data
-- into the mapped_fields table format.
--
-- PREREQUISITES:
-- 1. Upload Mapping_spec_template_V1.xlsx to Databricks as a table
-- 2. Replace ${CATALOG_SCHEMA} with your catalog.schema (e.g., oztest_dev.smartmapper)
-- 3. Replace ${STAGING_TABLE} with your staging table name
--
-- USAGE:
-- 1. Run the SELECT first to verify the transformation
-- 2. Once satisfied, uncomment the INSERT INTO statement
-- ============================================================================

-- ============================================================================
-- STEP 1: PREVIEW THE TRANSFORMATION (Run this first)
-- ============================================================================

SELECT
    -- Target Field Info
    `Silver_TABLE NAME` AS tgt_table_name,
    `Silver Table Physical Name` AS tgt_table_physical_name,
    `Silver Attribute Column  Name` AS tgt_column_name,
    `Silver Attribute Column Physical Name` AS tgt_column_physical_name,
    `Silver Attribute Column Definition` AS tgt_comments,
    
    -- Source Field Info (already pipe-delimited in Excel)
    `BRONZE_TABLE NAME` AS source_tables,
    `Bronze_Attribute Column Physical Name` AS source_tables_physical,
    `Bronze_Attribute Column Name` AS source_columns,
    `Bronze_Attribute Column Physical Name` AS source_columns_physical,
    `Bronze_Attribute Column Description` AS source_descriptions,
    
    -- Domain
    `Subject Area` AS source_domain,
    
    -- Derive source_relationship_type from Function column
    CASE 
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%JOIN%' AND UPPER(COALESCE(`Function`, '')) LIKE '%UNION%' THEN 'UNION'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%UNION%' THEN 'UNION'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%JOIN%' THEN 'JOIN'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%CONCAT%' THEN 'CONCAT'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%LOOKUP%' THEN 'JOIN'
        WHEN `Bronze_Attribute Column Physical Name` LIKE '%|%' THEN 'CONCAT'
        ELSE 'SINGLE'
    END AS source_relationship_type,
    
    -- Derive transformations_applied from Function column
    CASE 
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%INITCAP%' THEN 'INITCAP'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%CONCAT%' THEN 'CONCAT'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%DRIVED%' OR UPPER(COALESCE(`Function`, '')) LIKE '%DERIVED%' THEN 'DERIVED'
        WHEN UPPER(COALESCE(`Function`, '')) LIKE '%LOOKUP%' OR UPPER(COALESCE(`Function`, '')) LIKE '%LOOK%' THEN 'LOOKUP'
        ELSE NULL
    END AS transformations_applied,
    
    -- Source Expression - use Transformation Logic or build from columns
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
    
    -- Store original transformation logic as AI reasoning for reference
    `Transformation Logic (Describe in english or pseudocode)` AS ai_reasoning,
    
    -- Function column for reference
    `Function` AS function_ref,
    
    -- Comments
    `Comments` AS comments_ref,
    
    -- Metadata defaults (will be set in INSERT)
    'HISTORICAL' AS mapping_source,
    FALSE AS ai_generated,
    'ACTIVE' AS mapping_status,
    0.90 AS confidence_score,  -- High confidence for historical mappings
    
    -- Count source columns (for verification)
    SIZE(SPLIT(`Bronze_Attribute Column Physical Name`, '\\|')) AS source_column_count

FROM ${CATALOG_SCHEMA}.${STAGING_TABLE}

-- Filter out rows without target column (header rows, etc.)
WHERE `Silver Attribute Column Physical Name` IS NOT NULL
  AND TRIM(`Silver Attribute Column Physical Name`) != ''

ORDER BY 
    `Silver_TABLE NAME`,
    `Silver Attribute Column Physical Name`;


-- ============================================================================
-- STEP 2: CHECK COUNTS AND DISTRIBUTION
-- ============================================================================

-- Uncomment to run these checks:

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

-- Multi-column mappings
SELECT 
    `Silver Attribute Column Physical Name` AS target_column,
    `Bronze_Attribute Column Physical Name` AS source_columns,
    `Function`,
    `Transformation Logic (Describe in english or pseudocode)` AS transform_logic
FROM ${CATALOG_SCHEMA}.${STAGING_TABLE}
WHERE `Bronze_Attribute Column Physical Name` LIKE '%|%'
LIMIT 20;
*/


-- ============================================================================
-- STEP 3: INSERT INTO mapped_fields (Run after verifying SELECT)
-- ============================================================================

/*
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
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
    source_relationship_type,
    transformations_applied,
    confidence_score,
    mapping_source,
    ai_reasoning,
    ai_generated,
    mapping_status,
    mapped_by,
    mapped_ts
)
SELECT
    -- semantic_field_id: Look up from semantic_fields table or use 0
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
    
    -- Source tables
    stg.`BRONZE_TABLE NAME` AS source_tables,
    stg.`Bronze_Attribute Column Physical Name` AS source_tables_physical,  -- Using physical col as proxy
    stg.`Bronze_Attribute Column Name` AS source_columns,
    stg.`Bronze_Attribute Column Physical Name` AS source_columns_physical,
    stg.`Bronze_Attribute Column Description` AS source_descriptions,
    NULL AS source_datatypes,  -- Not in Excel
    
    -- Domain
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
    
    -- Metadata
    0.90 AS confidence_score,
    'HISTORICAL' AS mapping_source,
    CONCAT('Imported from Mapping_spec_template_V1.xlsx. Original logic: ', 
           COALESCE(stg.`Transformation Logic (Describe in english or pseudocode)`, 'N/A')) AS ai_reasoning,
    FALSE AS ai_generated,
    'ACTIVE' AS mapping_status,
    'historical_import@gainwell.com' AS mapped_by,
    CURRENT_TIMESTAMP() AS mapped_ts

FROM ${CATALOG_SCHEMA}.${STAGING_TABLE} stg
WHERE stg.`Silver Attribute Column Physical Name` IS NOT NULL
  AND TRIM(stg.`Silver Attribute Column Physical Name`) != '';
*/

