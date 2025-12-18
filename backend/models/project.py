"""
Pydantic models for V4 mapping projects and target table status.

V4 Target-First Workflow:
- Projects group mapping efforts for a source system
- Target tables track progress for each silver table
- Users select target tables, AI suggests mappings for all columns
- All suggestions require user approval before becoming patterns

Models:
- MappingProject: Overall mapping project
- MappingProjectCreate: Create request
- MappingProjectUpdate: Update request
- TargetTableStatus: Per-table mapping progress
- TargetTableStatusUpdate: Update request
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    """Project status values."""
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    COMPLETE = "COMPLETE"
    ARCHIVED = "ARCHIVED"


class TableMappingStatus(str, Enum):
    """Target table mapping status values."""
    NOT_STARTED = "NOT_STARTED"
    DISCOVERING = "DISCOVERING"  # AI is generating suggestions
    SUGGESTIONS_READY = "SUGGESTIONS_READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    SKIPPED = "SKIPPED"


class TablePriority(str, Enum):
    """Table priority levels."""
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


# =============================================================================
# MAPPING PROJECT MODELS
# =============================================================================

class MappingProject(BaseModel):
    """
    A mapping project tracks an overall source-to-target mapping effort.
    
    Projects can span multiple source/target catalogs and schemas.
    All mappings require user approval - no auto-approval.
    Historical mappings (loaded as patterns) are pre-approved.
    
    Attributes:
        project_id: Unique identifier
        project_name: Display name for the project
        project_description: Detailed description
        source_system_name: Name of source system (e.g., DMES, MMIS)
        source_catalogs: Pipe-separated source catalogs
        source_schemas: Pipe-separated source schemas
        target_catalogs: Pipe-separated target catalogs
        target_schemas: Pipe-separated target schemas
        target_domains: Pipe-separated domain filters
        project_status: Current status
        total_target_tables: Total tables to map
        tables_complete: Tables fully mapped
        tables_in_progress: Tables being worked on
        total_target_columns: Total columns across all tables
        columns_mapped: Columns with approved mappings
        columns_pending_review: Columns with pending suggestions
        created_by: User who created
        created_ts: Creation timestamp
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    project_id: Optional[int] = Field(None, description="Unique project identifier (auto-generated)")
    project_name: str = Field(..., description="Display name for the mapping project")
    project_description: Optional[str] = Field(None, description="Detailed description")
    
    # Source context (can have multiple)
    source_system_name: Optional[str] = Field(None, description="Name of source system (e.g., DMES)")
    source_catalogs: Optional[str] = Field(None, description="Pipe-separated source catalogs")
    source_schemas: Optional[str] = Field(None, description="Pipe-separated source schemas")
    
    # Target context (can have multiple)
    target_catalogs: Optional[str] = Field(None, description="Pipe-separated target catalogs")
    target_schemas: Optional[str] = Field(None, description="Pipe-separated target schemas")
    target_domains: Optional[str] = Field(None, description="Pipe-separated domain filters")
    
    # Status
    project_status: ProjectStatus = Field(default=ProjectStatus.NOT_STARTED, description="Project status")
    
    # Progress counters (denormalized for dashboard performance)
    total_target_tables: int = Field(default=0, description="Total target tables to map")
    tables_complete: int = Field(default=0, description="Tables fully mapped")
    tables_in_progress: int = Field(default=0, description="Tables being worked on")
    total_target_columns: int = Field(default=0, description="Total target columns")
    columns_mapped: int = Field(default=0, description="Columns with approved mappings")
    columns_pending_review: int = Field(default=0, description="Columns pending review")
    
    # Audit
    created_by: Optional[str] = Field(None, description="User who created")
    created_ts: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_by: Optional[str] = Field(None, description="User who last updated")
    updated_ts: Optional[datetime] = Field(None, description="Last update timestamp")
    completed_by: Optional[str] = Field(None, description="User who completed")
    completed_ts: Optional[datetime] = Field(None, description="Completion timestamp")


class MappingProjectCreate(BaseModel):
    """Create request for a new mapping project."""
    project_name: str = Field(..., description="Display name for the project")
    project_description: Optional[str] = None
    source_system_name: Optional[str] = None
    source_catalogs: Optional[str] = None
    source_schemas: Optional[str] = None
    target_catalogs: Optional[str] = None
    target_schemas: Optional[str] = None
    target_domains: Optional[str] = None
    created_by: Optional[str] = None


class MappingProjectUpdate(BaseModel):
    """Update request for an existing mapping project."""
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    source_system_name: Optional[str] = None
    source_catalogs: Optional[str] = None
    source_schemas: Optional[str] = None
    target_catalogs: Optional[str] = None
    target_schemas: Optional[str] = None
    target_domains: Optional[str] = None
    project_status: Optional[ProjectStatus] = None
    updated_by: Optional[str] = None


# =============================================================================
# TARGET TABLE STATUS MODELS
# =============================================================================

class TargetTableStatus(BaseModel):
    """
    Tracks mapping progress for a single target table within a project.
    
    Each row represents one target table (e.g., MBR_CNTCT).
    Contains column counts and AI processing status.
    
    Attributes:
        target_table_status_id: Unique identifier
        project_id: FK to mapping_projects
        tgt_table_name: Target table logical name
        tgt_table_physical_name: Target table physical name
        tgt_table_description: Table description
        mapping_status: Current status
        total_columns: Total columns in this table
        columns_with_pattern: Columns that have past patterns
        columns_mapped: Columns with approved mappings
        columns_pending_review: Columns with pending suggestions
        columns_no_match: Columns with no source match found
        columns_skipped: Columns user chose to skip
        ai_job_id: Job ID for async processing
        ai_started_ts: When AI started
        ai_completed_ts: When AI finished
        ai_error_message: Error if AI failed
        avg_confidence: Average confidence score
        min_confidence: Minimum confidence (flags risky mappings)
        user_notes: User notes about this table
        display_order: UI display order
        priority: HIGH, NORMAL, LOW
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    target_table_status_id: Optional[int] = Field(None, description="Unique identifier")
    project_id: int = Field(..., description="FK to mapping_projects")
    
    # Target table info
    tgt_table_name: str = Field(..., description="Target table logical name")
    tgt_table_physical_name: str = Field(..., description="Target table physical name")
    tgt_table_description: Optional[str] = Field(None, description="Table description")
    
    # Status
    mapping_status: TableMappingStatus = Field(
        default=TableMappingStatus.NOT_STARTED, 
        description="Mapping status"
    )
    
    # Column counts
    total_columns: int = Field(default=0, description="Total columns in table")
    columns_with_pattern: int = Field(default=0, description="Columns with past patterns")
    columns_mapped: int = Field(default=0, description="Columns with approved mappings")
    columns_pending_review: int = Field(default=0, description="Columns pending review")
    columns_no_match: int = Field(default=0, description="Columns with no match")
    columns_skipped: int = Field(default=0, description="Columns skipped by user")
    
    # AI processing status
    ai_job_id: Optional[str] = Field(None, description="Async job ID")
    ai_started_ts: Optional[datetime] = Field(None, description="AI start time")
    ai_completed_ts: Optional[datetime] = Field(None, description="AI completion time")
    ai_error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Confidence summary
    avg_confidence: Optional[float] = Field(None, description="Average confidence")
    min_confidence: Optional[float] = Field(None, description="Minimum confidence")
    
    # User input
    user_notes: Optional[str] = Field(None, description="User notes")
    
    # Display
    display_order: Optional[int] = Field(None, description="UI display order")
    priority: TablePriority = Field(default=TablePriority.NORMAL, description="Priority level")
    
    # Audit
    created_ts: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_ts: Optional[datetime] = Field(None, description="Last update timestamp")
    started_by: Optional[str] = Field(None, description="User who started mapping")
    started_ts: Optional[datetime] = Field(None, description="When mapping started")
    completed_by: Optional[str] = Field(None, description="User who completed")
    completed_ts: Optional[datetime] = Field(None, description="Completion timestamp")
    
    # Computed properties (not stored in DB)
    @property
    def progress_percent(self) -> float:
        """Calculate mapping progress percentage."""
        if self.total_columns == 0:
            return 0.0
        return round(self.columns_mapped * 100.0 / self.total_columns, 1)
    
    @property
    def columns_remaining(self) -> int:
        """Calculate remaining columns to map."""
        return self.total_columns - self.columns_mapped - self.columns_skipped
    
    @property
    def has_low_confidence(self) -> bool:
        """Check if any suggestion has low confidence."""
        return self.min_confidence is not None and self.min_confidence < 0.5
    
    @property
    def has_unmatched(self) -> bool:
        """Check if there are unmatched columns."""
        return self.columns_no_match > 0


class TargetTableStatusCreate(BaseModel):
    """Create request for target table status (usually batch-created from semantic_fields)."""
    project_id: int
    tgt_table_name: str
    tgt_table_physical_name: str
    tgt_table_description: Optional[str] = None
    total_columns: int = 0
    display_order: Optional[int] = None
    priority: TablePriority = TablePriority.NORMAL


class TargetTableStatusUpdate(BaseModel):
    """Update request for target table status."""
    mapping_status: Optional[TableMappingStatus] = None
    columns_with_pattern: Optional[int] = None
    columns_mapped: Optional[int] = None
    columns_pending_review: Optional[int] = None
    columns_no_match: Optional[int] = None
    columns_skipped: Optional[int] = None
    ai_job_id: Optional[str] = None
    ai_started_ts: Optional[datetime] = None
    ai_completed_ts: Optional[datetime] = None
    ai_error_message: Optional[str] = None
    avg_confidence: Optional[float] = None
    min_confidence: Optional[float] = None
    user_notes: Optional[str] = None
    priority: Optional[TablePriority] = None
    started_by: Optional[str] = None
    completed_by: Optional[str] = None


# =============================================================================
# RESPONSE MODELS (for API)
# =============================================================================

class ProjectDashboard(BaseModel):
    """Dashboard summary for a project (from v_project_dashboard view)."""
    project_id: int
    project_name: str
    project_description: Optional[str] = None
    source_system_name: Optional[str] = None
    project_status: ProjectStatus
    created_by: Optional[str] = None
    created_ts: Optional[datetime] = None
    
    # Stats
    total_tables: int = 0
    tables_complete: int = 0
    tables_in_progress: int = 0
    tables_ready_for_review: int = 0
    tables_not_started: int = 0
    total_columns: int = 0
    columns_mapped: int = 0
    columns_pending_review: int = 0
    columns_no_match: int = 0
    progress_percent: float = 0.0
    avg_confidence: Optional[float] = None


class TargetTableProgress(BaseModel):
    """Progress details for a target table (from v_target_table_progress view)."""
    target_table_status_id: int
    project_id: int
    project_name: str
    tgt_table_name: str
    tgt_table_physical_name: str
    tgt_table_description: Optional[str] = None
    mapping_status: TableMappingStatus
    priority: TablePriority
    
    # Counts
    total_columns: int = 0
    columns_with_pattern: int = 0
    columns_mapped: int = 0
    columns_pending_review: int = 0
    columns_no_match: int = 0
    columns_skipped: int = 0
    progress_percent: float = 0.0
    columns_remaining: int = 0
    
    # Confidence
    avg_confidence: Optional[float] = None
    min_confidence: Optional[float] = None
    has_low_confidence: bool = False
    has_unmatched: bool = False
    
    # Timestamps
    started_ts: Optional[datetime] = None
    completed_ts: Optional[datetime] = None
    updated_ts: Optional[datetime] = None
    
    # Notes
    user_notes: Optional[str] = None

