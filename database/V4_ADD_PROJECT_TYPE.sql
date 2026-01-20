-- ============================================================================
-- V4 Migration: Add project_type column to projects and patterns
-- ============================================================================
-- This migration adds project_type filtering capability:
-- 1. Projects have a type (e.g., DMES, MMIS, CLAIMS)
-- 2. Patterns (mapped_fields) have a type
-- 3. Pattern matching only uses patterns of the same type
-- ============================================================================

-- Add project_type to mapping_projects
ALTER TABLE ${catalog}.${schema}.mapping_projects 
ADD COLUMN project_type STRING COMMENT 'Project type for pattern filtering (e.g., DMES, MMIS)';

-- Add project_type to mapped_fields (patterns)
ALTER TABLE ${catalog}.${schema}.mapped_fields 
ADD COLUMN project_type STRING COMMENT 'Project type - patterns only match within same type';

-- ============================================================================
-- After running this migration:
-- 1. Update existing projects with appropriate project_type values
-- 2. Update existing mapped_fields (patterns) with project_type values
-- 
-- Example:
-- UPDATE ${catalog}.${schema}.mapping_projects SET project_type = 'DMES' WHERE project_id = 1;
-- UPDATE ${catalog}.${schema}.mapped_fields SET project_type = 'DMES' WHERE project_id = 1;
-- ============================================================================

