"""
Pydantic models for V4 mapping suggestions.

V4 Target-First Workflow:
- AI generates suggestions for all columns in a target table
- Suggestions are stored before user review
- Users approve, edit, reject, or skip each suggestion
- Approved suggestions become mappings
- Rejected suggestions inform future AI (via mapping_feedback)

Models:
- MappingSuggestion: AI-generated suggestion for review
- MappingSuggestionUpdate: Update request (approve/reject/edit)
- MatchedSourceField: A source field matched to a pattern slot
- SQLChange: A change made to the pattern SQL
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class SuggestionStatus(str, Enum):
    """Suggestion status values."""
    PROCESSING = "PROCESSING"       # AI is still generating
    PENDING = "PENDING"             # Ready for user review
    APPROVED = "APPROVED"           # User approved as-is
    EDITED = "EDITED"               # User edited and approved
    REJECTED = "REJECTED"           # User rejected
    SKIPPED = "SKIPPED"             # User skipped this column
    AUTO_MAPPED = "AUTO_MAPPED"     # Auto-generated column - no SQL needed
    NO_PATTERN = "NO_PATTERN"       # No past pattern found
    NO_MATCH = "NO_MATCH"           # Pattern found but no source match
    ERROR = "ERROR"                 # AI generation failed


class ConfidenceLevel(str, Enum):
    """Confidence level categories."""
    HIGH = "HIGH"           # >= 0.9
    MEDIUM = "MEDIUM"       # >= 0.7
    LOW = "LOW"             # >= 0.5
    VERY_LOW = "VERY_LOW"   # < 0.5


# =============================================================================
# HELPER MODELS
# =============================================================================

class MatchedSourceField(BaseModel):
    """
    A source field matched to a pattern slot.
    
    Used in the matched_source_fields JSON array.
    """
    unmapped_field_id: int = Field(..., description="FK to unmapped_fields")
    src_table_name: str = Field(..., description="Source table logical name")
    src_table_physical_name: str = Field(..., description="Source table physical name")
    src_column_name: str = Field(..., description="Source column logical name")
    src_column_physical_name: str = Field(..., description="Source column physical name")
    src_comments: Optional[str] = Field(None, description="Source column description")
    src_physical_datatype: Optional[str] = Field(None, description="Source data type")
    
    # Matching info
    pattern_column: Optional[str] = Field(None, description="Original column in pattern")
    column_role: Optional[str] = Field(None, description="Role: output, join_key, filter, etc.")
    match_score: float = Field(default=0.0, description="Similarity score (0.0-1.0)")
    match_reasoning: Optional[str] = Field(None, description="Why this field was matched")


class SQLChange(BaseModel):
    """
    A change made to the pattern SQL during rewriting.
    
    Used in the sql_changes JSON array.
    """
    change_type: str = Field(..., description="Type: table_replace, column_replace, etc.")
    original: str = Field(..., description="Original text in pattern SQL")
    replaced_with: str = Field(..., description="New text in rewritten SQL")
    line_number: Optional[int] = Field(None, description="Approximate line number")
    description: Optional[str] = Field(None, description="Human-readable description")


class SuggestionWarning(BaseModel):
    """
    A warning about a suggestion.
    
    Used in the warnings JSON array.
    """
    warning_type: str = Field(..., description="Type: no_match, low_confidence, filter_mismatch")
    column: Optional[str] = Field(None, description="Column this warning applies to")
    message: str = Field(..., description="Warning message")
    severity: str = Field(default="warning", description="warning, error, info")


# =============================================================================
# MAPPING SUGGESTION MODELS
# =============================================================================

class MappingSuggestion(BaseModel):
    """
    An AI-generated mapping suggestion for a single target column.
    
    Created during the DISCOVERING phase, reviewed by user.
    Contains the suggested SQL, matched source fields, and confidence.
    
    Attributes:
        suggestion_id: Unique identifier
        project_id: FK to mapping_projects
        target_table_status_id: FK to target_table_status
        semantic_field_id: FK to semantic_fields (target column)
        
        Target field info (denormalized):
        tgt_table_name, tgt_column_name, etc.
        
        Pattern info (from historical mapped_fields):
        pattern_mapped_field_id, pattern_type, pattern_sql
        
        Suggestion:
        matched_source_fields, suggested_sql, sql_changes
        
        Confidence:
        confidence_score, ai_reasoning, warnings
        
        Status:
        suggestion_status
        
        User edits (if status is EDITED):
        edited_sql, edited_source_fields, edit_notes
        
        Rejection (if status is REJECTED):
        rejection_reason
        
        Result (if APPROVED or EDITED):
        created_mapped_field_id
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    suggestion_id: Optional[int] = Field(None, description="Unique identifier")
    project_id: int = Field(..., description="FK to mapping_projects")
    target_table_status_id: int = Field(..., description="FK to target_table_status")
    semantic_field_id: int = Field(..., description="FK to semantic_fields")
    
    # Target field info (denormalized for performance)
    tgt_table_name: str = Field(..., description="Target table logical name")
    tgt_table_physical_name: str = Field(..., description="Target table physical name")
    tgt_column_name: str = Field(..., description="Target column logical name")
    tgt_column_physical_name: str = Field(..., description="Target column physical name")
    tgt_comments: Optional[str] = Field(None, description="Target column description")
    tgt_physical_datatype: Optional[str] = Field(None, description="Target data type")
    
    # Pattern info (from historical mapped_fields)
    pattern_mapped_field_id: Optional[int] = Field(None, description="FK to pattern mapping")
    pattern_type: Optional[str] = Field(None, description="SINGLE, CONCAT, JOIN, UNION, etc.")
    pattern_sql: Optional[str] = Field(None, description="Original SQL from pattern")
    
    # Matched source fields (JSON array of MatchedSourceField)
    # Stored as JSON string in DB, parsed for API responses
    matched_source_fields: Optional[str] = Field(None, description="JSON array of matched fields")
    
    # Generated SQL
    suggested_sql: Optional[str] = Field(None, description="AI-generated SQL expression")
    sql_changes: Optional[str] = Field(None, description="JSON array of SQLChange")
    
    # Confidence and reasoning
    confidence_score: Optional[float] = Field(None, description="AI confidence (0.0-1.0)")
    ai_reasoning: Optional[str] = Field(None, description="AI explanation")
    warnings: Optional[str] = Field(None, description="JSON array of SuggestionWarning")
    
    # Status
    suggestion_status: SuggestionStatus = Field(
        default=SuggestionStatus.PROCESSING,
        description="Current status"
    )
    
    # User edits (if EDITED)
    edited_sql: Optional[str] = Field(None, description="User-edited SQL")
    edited_source_fields: Optional[str] = Field(None, description="User-modified source fields JSON")
    edit_notes: Optional[str] = Field(None, description="User notes about edits")
    
    # Rejection (if REJECTED)
    rejection_reason: Optional[str] = Field(None, description="Why user rejected")
    
    # Result (if APPROVED or EDITED)
    created_mapped_field_id: Optional[int] = Field(None, description="FK to created mapping")
    
    # Audit
    created_ts: Optional[datetime] = Field(None, description="When suggestion was generated")
    reviewed_by: Optional[str] = Field(None, description="User who reviewed")
    reviewed_ts: Optional[datetime] = Field(None, description="When reviewed")
    
    # Computed properties
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Categorize confidence score."""
        if self.confidence_score is None:
            return ConfidenceLevel.VERY_LOW
        if self.confidence_score >= 0.9:
            return ConfidenceLevel.HIGH
        if self.confidence_score >= 0.7:
            return ConfidenceLevel.MEDIUM
        if self.confidence_score >= 0.5:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return self.warnings is not None and self.warnings != "[]"
    
    def get_matched_source_fields_list(self) -> List[MatchedSourceField]:
        """Parse matched_source_fields JSON to list of objects."""
        if not self.matched_source_fields:
            return []
        import json
        try:
            data = json.loads(self.matched_source_fields)
            return [MatchedSourceField(**item) for item in data]
        except:
            return []
    
    def get_warnings_list(self) -> List[SuggestionWarning]:
        """Parse warnings JSON to list of objects."""
        if not self.warnings:
            return []
        import json
        try:
            data = json.loads(self.warnings)
            return [SuggestionWarning(**item) for item in data]
        except:
            return []


class MappingSuggestionCreate(BaseModel):
    """Create request for a mapping suggestion (usually created by AI service)."""
    project_id: int
    target_table_status_id: int
    semantic_field_id: int
    
    # Target info
    tgt_table_name: str
    tgt_table_physical_name: str
    tgt_column_name: str
    tgt_column_physical_name: str
    tgt_comments: Optional[str] = None
    tgt_physical_datatype: Optional[str] = None
    
    # Pattern info
    pattern_mapped_field_id: Optional[int] = None
    pattern_type: Optional[str] = None
    pattern_sql: Optional[str] = None
    
    # Suggestion
    matched_source_fields: Optional[str] = None  # JSON string
    suggested_sql: Optional[str] = None
    sql_changes: Optional[str] = None  # JSON string
    
    # Confidence
    confidence_score: Optional[float] = None
    ai_reasoning: Optional[str] = None
    warnings: Optional[str] = None  # JSON string
    
    # Status
    suggestion_status: SuggestionStatus = SuggestionStatus.PROCESSING


class SuggestionApproveRequest(BaseModel):
    """Request to approve a suggestion as-is."""
    reviewed_by: str = Field(..., description="User approving the suggestion")
    notes: Optional[str] = Field(None, description="Optional notes")


class SuggestionEditRequest(BaseModel):
    """Request to edit and approve a suggestion."""
    reviewed_by: str = Field(..., description="User approving the suggestion")
    edited_sql: str = Field(..., description="User's edited SQL")
    edited_source_fields: Optional[str] = Field(None, description="Modified source fields JSON")
    edit_notes: Optional[str] = Field(None, description="Notes about edits made")


class SuggestionRejectRequest(BaseModel):
    """Request to reject a suggestion."""
    reviewed_by: str = Field(..., description="User rejecting")
    rejection_reason: str = Field(..., description="Why the suggestion was rejected")


class SuggestionSkipRequest(BaseModel):
    """Request to skip a column."""
    reviewed_by: str = Field(..., description="User skipping")
    notes: Optional[str] = Field(None, description="Optional reason for skipping")


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class SuggestionReviewItem(BaseModel):
    """
    A suggestion ready for user review.
    
    Used in the suggestion review UI.
    """
    suggestion_id: int
    semantic_field_id: int
    
    # Target info
    tgt_table_name: str
    tgt_table_physical_name: str
    tgt_column_name: str
    tgt_column_physical_name: str
    tgt_comments: Optional[str] = None
    tgt_physical_datatype: Optional[str] = None
    
    # Pattern info
    pattern_type: Optional[str] = None
    pattern_sql: Optional[str] = None
    
    # Suggestion
    matched_source_fields: List[MatchedSourceField] = []
    suggested_sql: Optional[str] = None
    sql_changes: List[SQLChange] = []
    
    # Confidence
    confidence_score: Optional[float] = None
    confidence_level: ConfidenceLevel = ConfidenceLevel.VERY_LOW
    ai_reasoning: Optional[str] = None
    warnings: List[SuggestionWarning] = []
    has_warnings: bool = False
    
    # Status
    suggestion_status: SuggestionStatus
    
    # Edits (if any)
    edited_sql: Optional[str] = None
    edit_notes: Optional[str] = None
    
    # Audit
    created_ts: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_ts: Optional[datetime] = None


class SuggestionSummary(BaseModel):
    """Summary counts for suggestions in a table."""
    total: int = 0
    pending: int = 0
    approved: int = 0
    edited: int = 0
    rejected: int = 0
    skipped: int = 0
    auto_mapped: int = 0  # Auto-generated columns (no SQL needed)
    no_pattern: int = 0
    no_match: int = 0
    processing: int = 0
    error: int = 0
    avg_confidence: Optional[float] = None

