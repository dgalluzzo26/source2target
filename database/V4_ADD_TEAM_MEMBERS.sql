-- ============================================================================
-- V4 Migration: Add team_members column to mapping_projects
-- ============================================================================
-- Run this script to add team access support to existing mapping_projects table.
--
-- Usage:
--   Replace ${CATALOG_SCHEMA} with your actual catalog.schema (e.g., oztest_dev.smartmapper)
-- ============================================================================

-- Add team_members column to mapping_projects
ALTER TABLE ${CATALOG_SCHEMA}.mapping_projects
ADD COLUMN IF NOT EXISTS team_members STRING 
COMMENT 'Comma-separated emails of team members with access (creator always has access)';

-- Verify the column was added
DESCRIBE TABLE ${CATALOG_SCHEMA}.mapping_projects;

