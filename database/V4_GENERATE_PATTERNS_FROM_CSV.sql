-- ============================================================================
-- V4 GENERATE PATTERNS FROM CSV USING LLM
-- ============================================================================
-- 
-- This script transforms uploaded mapping spreadsheet data (like BR Scenario)
-- into complete mapped_fields rows using ai_query() to parse SQL expressions
-- and generate structured metadata.
--
-- INPUT: Your CSV uploaded as a Unity Catalog table with columns like:
--   - Subject Area
--   - BRONZE_TABLE NAME
--   - Bronze_Attribute Column Physical Name
--   - Bronze_Attribute Column Description
--   - Transformation Logic
--   - Silver_TABLE NAME
--   - Silver Table Physical Name
--   - Silver Attribute Column Physical Name
--   - Silver Attribute Column Definition
--   - Function
--   - Join Column Description
--
-- OUTPUT: Complete rows in mapped_fields table with:
--   - All target/source metadata
--   - source_expression
--   - join_metadata (LLM-generated JSON)
--   - source_relationship_type
--   - transformations_applied
--   - is_approved_pattern = TRUE
--
-- USAGE:
--   1. Upload your CSV to Databricks as a table
--   2. Replace ${CATALOG_SCHEMA} with your catalog.schema
--   3. Replace ${STAGING_TABLE} with your staging table name
--   4. Run STEP 1 to preview
--   5. Run STEP 2 to insert
--
-- ============================================================================

-- ============================================================================
-- STEP 1: GENERATE PATTERNS WITH LLM (PREVIEW)
-- ============================================================================
-- This uses ai_query() to parse the Transformation Logic SQL and generate
-- the complete join_metadata JSON structure.

SELECT 
    -- Target Info (from Silver columns)
    stg.`Silver_TABLE NAME` AS tgt_table_name,
    stg.`Silver Table Physical Name` AS tgt_table_physical_name,
    stg.`Silver Attribute Column  Name` AS tgt_column_name,
    stg.`Silver Attribute Column Physical Name` AS tgt_column_physical_name,
    stg.`Silver Attribute Column Definition` AS tgt_comments,
    
    -- Source Expression (the complete SQL)
    stg.`Transformation Logic` AS source_expression,
    
    -- Source Tables (pipe-delimited from BRONZE_TABLE NAME)
    stg.`BRONZE_TABLE NAME` AS source_tables,
    LOWER(REPLACE(stg.`BRONZE_TABLE NAME`, ' ', '_')) AS source_tables_physical,
    
    -- Source Columns (pipe-delimited)
    stg.`Bronze_Attribute Column Name` AS source_columns,
    stg.`Bronze_Attribute Column Physical Name` AS source_columns_physical,
    
    -- Source Descriptions
    stg.`Bronze_Attribute Column Description` AS source_descriptions,
    
    -- Join Column Description (important for understanding joins)
    stg.`Join Column Description` AS join_descriptions,
    
    -- Domain
    stg.`Subject Area` AS source_domain,
    
    -- Relationship Type (derived from Function or SQL structure)
    CASE 
        WHEN stg.`Transformation Logic` LIKE '%UNION%' AND stg.`Transformation Logic` LIKE '%JOIN%' THEN 'UNION_JOIN'
        WHEN stg.`Transformation Logic` LIKE '%UNION%' THEN 'UNION'
        WHEN stg.`Transformation Logic` LIKE '%JOIN%' THEN 'JOIN'
        WHEN stg.`Bronze_Attribute Column Physical Name` LIKE '%|%' THEN 'CONCAT'
        ELSE 'SINGLE'
    END AS source_relationship_type,
    
    -- Transformations Applied (derived from Function column)
    stg.`Function` AS transformations_applied,
    
    -- LLM-Generated join_metadata
    ai_query(
        'databricks-meta-llama-3-3-70b-instruct',
        CONCAT(
            'Parse this SQL expression and generate a JSON metadata object for a data mapping tool.

SQL EXPRESSION:
```sql
', COALESCE(stg.`Transformation Logic`, 'N/A'), '
```

CONTEXT:
- Target Column: ', COALESCE(stg.`Silver Attribute Column Physical Name`, 'UNKNOWN'), '
- Target Table: ', COALESCE(stg.`Silver Table Physical Name`, 'UNKNOWN'), '
- Source Tables: ', COALESCE(stg.`BRONZE_TABLE NAME`, 'UNKNOWN'), '
- Join Descriptions: ', COALESCE(stg.`Join Column Description`, 'N/A'), '
- Function Type: ', COALESCE(stg.`Function`, 'Direct'), '

Generate a JSON object with this structure:
{
  "patternType": "SINGLE|JOIN|UNION|UNION_JOIN|CONCAT",
  "outputColumn": "<the column being selected>",
  "description": "<brief description of what this mapping does>",
  "silverTables": [
    {"alias": "<alias>", "physicalName": "<full table name>", "isConstant": true, "description": "<table purpose>"}
  ],
  "bronzeTables": [
    {"alias": "<alias>", "physicalName": "<full table name>", "isConstant": false, "description": "<table purpose>"}
  ],
  "unionBranches": [
    {
      "branchId": 1,
      "description": "<what this branch does>",
      "bronzeTable": {"alias": "<alias>", "physicalName": "<table>", "isConstant": false},
      "joins": [
        {"type": "INNER|LEFT|RIGHT", "toTable": "<alias>", "onCondition": "<join condition>"}
      ],
      "whereClause": "<where clause if any>"
    }
  ],
  "userColumnsToMap": [
    {"role": "join_key|output|filter", "originalColumn": "<column>", "description": "<what user needs to provide>"}
  ],
  "userTablesToMap": [
    {"role": "bronze_primary|bronze_secondary", "originalTable": "<table>", "description": "<what user replaces>"}
  ],
  "transformations": ["<TRIM|INITCAP|UPPER|etc>"]
}

Rules:
1. silverTables are tables from silver_* schemas - these are CONSTANT (user does not replace)
2. bronzeTables are tables from bronze_* schemas - these are what user REPLACES
3. For UNION patterns, create separate unionBranches for each SELECT
4. userColumnsToMap lists columns user must provide (join keys, output columns)
5. userTablesToMap lists tables user must replace (bronze tables only)
6. If no JOINs or UNIONs, patternType is "SINGLE" and omit unionBranches

Return ONLY the JSON object, no explanation.'
        )
    ) AS join_metadata_raw

FROM ${CATALOG_SCHEMA}.${STAGING_TABLE} stg
WHERE stg.`Silver Attribute Column Physical Name` IS NOT NULL
  AND TRIM(stg.`Silver Attribute Column Physical Name`) != ''
  AND stg.`Transformation Logic` IS NOT NULL
  AND TRIM(stg.`Transformation Logic`) != ''
ORDER BY stg.`Silver_TABLE NAME`, stg.`Silver Attribute Column Physical Name`
LIMIT 10;  -- Start with 10 to test


-- ============================================================================
-- STEP 2: INSERT INTO mapped_fields (Full Insert)
-- ============================================================================
-- Uncomment and run after verifying STEP 1 looks correct
/*
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (
    -- Target Info
    semantic_field_id,
    project_id,
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
    join_metadata,
    
    -- V4 Pattern Fields
    is_approved_pattern,
    pattern_approved_by,
    pattern_approved_ts,
    
    -- Metadata
    confidence_score,
    mapping_source,
    ai_reasoning,
    ai_generated,
    mapping_status,
    mapped_by,
    mapped_ts
)
SELECT
    -- Semantic field lookup (link to target definition)
    COALESCE(
        (SELECT sf.semantic_field_id 
         FROM ${CATALOG_SCHEMA}.semantic_fields sf 
         WHERE UPPER(sf.tgt_column_physical_name) = UPPER(stg.`Silver Attribute Column Physical Name`)
           AND UPPER(sf.tgt_table_physical_name) = UPPER(stg.`Silver Table Physical Name`)
         LIMIT 1),
        0
    ) AS semantic_field_id,
    
    -- V4: NULL project_id = global pattern (shared across all projects)
    NULL AS project_id,
    
    -- Target fields
    stg.`Silver_TABLE NAME` AS tgt_table_name,
    stg.`Silver Table Physical Name` AS tgt_table_physical_name,
    stg.`Silver Attribute Column  Name` AS tgt_column_name,
    stg.`Silver Attribute Column Physical Name` AS tgt_column_physical_name,
    stg.`Silver Attribute Column Definition` AS tgt_comments,
    
    -- Source expression (the complete SQL)
    stg.`Transformation Logic` AS source_expression,
    
    -- Source metadata
    stg.`BRONZE_TABLE NAME` AS source_tables,
    LOWER(REPLACE(COALESCE(stg.`BRONZE_TABLE NAME`, ''), ' ', '_')) AS source_tables_physical,
    stg.`Bronze_Attribute Column Name` AS source_columns,
    stg.`Bronze_Attribute Column Physical Name` AS source_columns_physical,
    COALESCE(stg.`Bronze_Attribute Column Description`, '') || 
        CASE WHEN stg.`Join Column Description` IS NOT NULL 
             THEN ' | Join Info: ' || stg.`Join Column Description` 
             ELSE '' 
        END AS source_descriptions,
    NULL AS source_datatypes,
    stg.`Subject Area` AS source_domain,
    
    -- Relationship type
    CASE 
        WHEN stg.`Transformation Logic` LIKE '%UNION%' AND stg.`Transformation Logic` LIKE '%JOIN%' THEN 'UNION_JOIN'
        WHEN stg.`Transformation Logic` LIKE '%UNION%' THEN 'UNION'
        WHEN stg.`Transformation Logic` LIKE '%JOIN%' THEN 'JOIN'
        WHEN stg.`Bronze_Attribute Column Physical Name` LIKE '%|%' THEN 'CONCAT'
        ELSE 'SINGLE'
    END AS source_relationship_type,
    
    -- Transformations
    COALESCE(stg.`Function`, 'Direct') AS transformations_applied,
    
    -- LLM-Generated join_metadata (the complex JSON structure)
    ai_query(
        'databricks-meta-llama-3-3-70b-instruct',
        CONCAT(
            'Parse this SQL and generate a JSON metadata object.

SQL:
```sql
', COALESCE(stg.`Transformation Logic`, 'N/A'), '
```

Target: ', COALESCE(stg.`Silver Attribute Column Physical Name`, '?'), ' in ', COALESCE(stg.`Silver Table Physical Name`, '?'), '
Sources: ', COALESCE(stg.`BRONZE_TABLE NAME`, '?'), '
Joins: ', COALESCE(stg.`Join Column Description`, 'N/A'), '

Generate JSON:
{
  "patternType": "SINGLE|JOIN|UNION|UNION_JOIN",
  "outputColumn": "<column>",
  "description": "<what this does>",
  "silverTables": [{"alias":"<>","physicalName":"<>","isConstant":true,"description":"<>"}],
  "unionBranches": [{"branchId":1,"description":"<>","bronzeTable":{"alias":"<>","physicalName":"<>"},"joins":[{"type":"<>","toTable":"<>","onCondition":"<>"}],"whereClause":"<>"}],
  "userColumnsToMap": [{"role":"<>","originalColumn":"<>","description":"<>"}],
  "userTablesToMap": [{"role":"<>","originalTable":"<>","description":"<>"}]
}

Silver tables (silver_*) are CONSTANT. Bronze tables are what user REPLACES.
Return ONLY JSON.'
        )
    ) AS join_metadata,
    
    -- V4 Pattern fields - mark as approved for AI usage
    TRUE AS is_approved_pattern,
    'historical_import@gainwell.com' AS pattern_approved_by,
    CURRENT_TIMESTAMP() AS pattern_approved_ts,
    
    -- Confidence & metadata
    0.95 AS confidence_score,
    'HISTORICAL' AS mapping_source,
    CONCAT('Imported from historical mapping. Function: ', COALESCE(stg.`Function`, 'Direct'), 
           '. Join info: ', COALESCE(stg.`Join Column Description`, 'N/A')) AS ai_reasoning,
    FALSE AS ai_generated,
    'ACTIVE' AS mapping_status,
    'historical_import@gainwell.com' AS mapped_by,
    CURRENT_TIMESTAMP() AS mapped_ts

FROM ${CATALOG_SCHEMA}.${STAGING_TABLE} stg
WHERE stg.`Silver Attribute Column Physical Name` IS NOT NULL
  AND TRIM(stg.`Silver Attribute Column Physical Name`) != ''
  AND stg.`Transformation Logic` IS NOT NULL
  AND TRIM(stg.`Transformation Logic`) != '';
*/


-- ============================================================================
-- STEP 3: VERIFY IMPORT
-- ============================================================================
/*
-- Count imported patterns
SELECT 
    'Total Patterns' AS metric,
    COUNT(*) AS value
FROM ${CATALOG_SCHEMA}.mapped_fields
WHERE mapping_source = 'HISTORICAL'
  AND project_id IS NULL

UNION ALL

-- Count by relationship type
SELECT 
    source_relationship_type AS metric,
    COUNT(*) AS value
FROM ${CATALOG_SCHEMA}.mapped_fields
WHERE mapping_source = 'HISTORICAL'
GROUP BY source_relationship_type

UNION ALL

-- Count with valid join_metadata
SELECT 
    'Has join_metadata' AS metric,
    COUNT(*) AS value
FROM ${CATALOG_SCHEMA}.mapped_fields
WHERE mapping_source = 'HISTORICAL'
  AND join_metadata IS NOT NULL
  AND join_metadata != '';
  
-- Preview a few patterns
SELECT 
    tgt_table_physical_name,
    tgt_column_physical_name,
    source_relationship_type,
    LEFT(source_expression, 100) AS sql_preview,
    LEFT(join_metadata, 200) AS metadata_preview
FROM ${CATALOG_SCHEMA}.mapped_fields
WHERE mapping_source = 'HISTORICAL'
  AND project_id IS NULL
LIMIT 10;
*/


-- ============================================================================
-- ALTERNATIVE: STEP-BY-STEP FOR LARGE DATASETS
-- ============================================================================
-- If you have many rows, run in batches to avoid LLM timeout:
/*
-- Batch 1: First 100 rows
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (...)
SELECT ... 
FROM ${CATALOG_SCHEMA}.${STAGING_TABLE} stg
WHERE stg.`Silver Attribute Column Physical Name` IS NOT NULL
ORDER BY stg.`Silver_TABLE NAME`, stg.`Silver Attribute Column Physical Name`
LIMIT 100 OFFSET 0;

-- Batch 2: Next 100 rows
INSERT INTO ${CATALOG_SCHEMA}.mapped_fields (...)
SELECT ... 
FROM ${CATALOG_SCHEMA}.${STAGING_TABLE} stg
WHERE stg.`Silver Attribute Column Physical Name` IS NOT NULL
ORDER BY stg.`Silver_TABLE NAME`, stg.`Silver Attribute Column Physical Name`
LIMIT 100 OFFSET 100;

-- etc.
*/


-- ============================================================================
-- NOTES
-- ============================================================================
-- 
-- 1. The ai_query() function calls Databricks Foundation Model to parse SQL
-- 2. join_metadata JSON helps the AI understand complex patterns for rewriting
-- 3. is_approved_pattern = TRUE makes patterns available for AI suggestions
-- 4. project_id = NULL means global pattern (shared across all projects)
-- 5. source_descriptions should include join column info for semantic matching
--
-- CSV Column Mapping (BR Scenario format):
--   Subject Area           → source_domain
--   BRONZE_TABLE NAME      → source_tables
--   Bronze_Attribute Column Physical Name → source_columns_physical  
--   Bronze_Attribute Column Description   → source_descriptions
--   Transformation Logic   → source_expression
--   Join Column Description → appended to source_descriptions
--   Function               → transformations_applied
--   Silver_TABLE NAME      → tgt_table_name
--   Silver Table Physical Name → tgt_table_physical_name
--   Silver Attribute Column Physical Name → tgt_column_physical_name
--   Silver Attribute Column Definition    → tgt_comments
--
-- ============================================================================


