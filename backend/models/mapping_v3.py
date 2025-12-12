"""
Pydantic models for V3 simplified mapping schema.

V3 KEY CHANGES:
- Single row per mapping - no more mapping_details, mapping_joins tables
- SQL expression captures ALL logic (transforms, joins, unions)
- mapped_fields has vector-searchable semantic field for AI learning
- Simplified data model for easier maintenance

Models:
- MappedFieldV3: Complete mapping with SQL expression
- MappedFieldCreateV3: Create request
- MappedFieldUpdateV3: Update request
- MappingFeedbackV3: Rejected suggestions for AI learning
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MappedFieldV3(BaseModel):
    """
    A complete mapping with SQL expression (V3 schema).
    
    One row = one complete mapping. The source_expression field captures
    all transformation, join, and union logic in a single SQL expression.
    
    Attributes:
        mapped_field_id: Unique identifier
        semantic_field_id: FK to semantic_fields table (target definition)
        tgt_table_name: Target table logical name
        tgt_table_physical_name: Target table physical name
        tgt_column_name: Target column logical name  
        tgt_column_physical_name: Target column physical name
        tgt_comments: Target column description
        source_expression: Complete SQL expression for the mapping
        source_tables: Comma-separated source table names
        source_columns: Comma-separated source column names
        source_descriptions: Pipe-separated source column descriptions
        source_datatypes: Comma-separated source data types
        source_relationship_type: SINGLE, JOIN, or UNION
        transformations_applied: Comma-separated list of transformations
        confidence_score: AI confidence score (0.0-1.0)
        mapping_source: How created: AI, MANUAL, BULK_UPLOAD
        ai_reasoning: AI explanation for suggestion
        ai_generated: Whether source_expression was AI-generated
        mapping_status: ACTIVE, INACTIVE, PENDING_REVIEW
        mapped_by: User who created/approved
        mapped_ts: Timestamp when created
        source_semantic_field: Computed field for vector embedding
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    mapped_field_id: Optional[int] = Field(None, description="Unique mapping identifier (auto-generated)")
    semantic_field_id: int = Field(..., description="Foreign key to semantic_fields table")
    
    # Target field info
    tgt_table_name: str = Field(..., description="Target table logical name")
    tgt_table_physical_name: str = Field(..., description="Target table physical name")
    tgt_column_name: str = Field(..., description="Target column logical name")
    tgt_column_physical_name: str = Field(..., description="Target column physical name")
    tgt_comments: Optional[str] = Field(None, description="Target column description")
    
    # Source expression - THE KEY V3 FIELD
    source_expression: str = Field(..., description="Complete SQL expression for the mapping")
    
    # Source metadata for display and AI learning
    source_tables: Optional[str] = Field(None, description="Comma-separated source table names")
    source_tables_physical: Optional[str] = Field(None, description="Comma-separated source table physical names")
    source_columns: Optional[str] = Field(None, description="Comma-separated source column names")
    source_columns_physical: Optional[str] = Field(None, description="Comma-separated source column physical names")
    source_descriptions: Optional[str] = Field(None, description="Pipe-separated source column descriptions")
    source_datatypes: Optional[str] = Field(None, description="Comma-separated source data types")
    source_domain: Optional[str] = Field(None, description="Source domain category")
    target_domain: Optional[str] = Field(None, description="Target domain category")
    source_relationship_type: str = Field(default="SINGLE", description="SINGLE, JOIN, or UNION")
    transformations_applied: Optional[str] = Field(None, description="Comma-separated transformations")
    
    # JOIN metadata for complex patterns
    join_metadata: Optional[str] = Field(None, description="JSON metadata for JOIN/UNION patterns")
    
    # AI/Confidence metadata
    confidence_score: Optional[float] = Field(None, description="AI confidence (0.0-1.0)")
    mapping_source: str = Field(default="MANUAL", description="How created: AI, MANUAL, BULK_UPLOAD")
    ai_reasoning: Optional[str] = Field(None, description="AI explanation for mapping")
    ai_generated: bool = Field(default=False, description="Whether source_expression was AI-generated")
    
    # Status and audit
    mapping_status: str = Field(default="ACTIVE", description="ACTIVE, INACTIVE, PENDING_REVIEW")
    mapped_by: Optional[str] = Field(None, description="User who created/approved mapping")
    mapped_ts: Optional[datetime] = Field(None, description="Mapping timestamp")
    updated_by: Optional[str] = Field(None, description="User who last updated")
    updated_ts: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Vector search field (populated on insert)
    source_semantic_field: Optional[str] = Field(None, description="Concatenated field for vector embedding")


class MappedFieldCreateV3(BaseModel):
    """Create request for V3 mapped field."""
    semantic_field_id: int = Field(..., description="FK to semantic_fields table")
    
    # Target field info
    tgt_table_name: str
    tgt_table_physical_name: str
    tgt_column_name: str
    tgt_column_physical_name: str
    tgt_comments: Optional[str] = None
    
    # Source expression - required
    source_expression: str = Field(..., description="Complete SQL expression")
    
    # Source metadata
    source_tables: Optional[str] = None  # Logical names
    source_tables_physical: Optional[str] = None  # Physical names (for restore)
    source_columns: Optional[str] = None  # Logical names
    source_columns_physical: Optional[str] = None  # Physical names (for restore)
    source_descriptions: Optional[str] = None
    source_datatypes: Optional[str] = None
    source_domain: Optional[str] = None  # Preserve domain for restore on delete
    target_domain: Optional[str] = None  # Target domain category
    source_relationship_type: str = "SINGLE"
    transformations_applied: Optional[str] = None
    
    # JOIN metadata for complex patterns
    join_metadata: Optional[str] = None  # JSON metadata for JOIN/UNION patterns
    
    # AI metadata
    confidence_score: Optional[float] = None
    mapping_source: str = "MANUAL"
    ai_reasoning: Optional[str] = None
    ai_generated: bool = False
    
    # Audit
    mapped_by: Optional[str] = None


class MappedFieldUpdateV3(BaseModel):
    """Update request for V3 mapped field."""
    # Source expression - can be updated
    source_expression: Optional[str] = None
    
    # Source metadata - can be updated
    source_tables: Optional[str] = None  # Logical names
    source_tables_physical: Optional[str] = None  # Physical names
    source_columns: Optional[str] = None  # Logical names
    source_columns_physical: Optional[str] = None  # Physical names
    source_descriptions: Optional[str] = None
    source_datatypes: Optional[str] = None
    source_domain: Optional[str] = None
    target_domain: Optional[str] = None
    source_relationship_type: Optional[str] = None
    transformations_applied: Optional[str] = None
    
    # JOIN metadata for complex patterns
    join_metadata: Optional[str] = None
    
    # AI metadata - can be updated
    ai_reasoning: Optional[str] = None
    ai_generated: Optional[bool] = None
    
    # Status
    mapping_status: Optional[str] = None
    
    # Audit
    updated_by: Optional[str] = None


class MappingFeedbackV3(BaseModel):
    """
    Rejected AI suggestion for learning (V3 schema).
    
    Tracks rejected suggestions so AI learns to avoid them.
    Accepted suggestions become mapped_fields rows.
    
    Attributes:
        feedback_id: Unique identifier
        suggested_src_table: Source table in rejected suggestion
        suggested_src_column: Source column in rejected suggestion  
        suggested_tgt_table: Target table in rejected suggestion
        suggested_tgt_column: Target column in rejected suggestion
        src_comments: Source description at time of rejection
        src_datatype: Source data type at time of rejection
        tgt_comments: Target description at time of rejection
        ai_confidence_score: AI confidence when suggested
        ai_reasoning: AI explanation for suggestion
        vector_search_score: Raw vector similarity score
        suggestion_rank: Rank of this suggestion (1 = top)
        feedback_action: REJECTED or MODIFIED
        user_comments: User explanation for rejection
        modified_src_table: If MODIFIED, actual source table user selected
        modified_src_column: If MODIFIED, actual source column user selected
        modified_expression: If MODIFIED, expression user created instead
        domain: Domain category at time of suggestion
        feedback_by: User who rejected
        feedback_ts: Timestamp of rejection
        source_semantic_field: Computed field for vector embedding
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    feedback_id: Optional[int] = Field(None, description="Unique feedback identifier")
    
    # What was suggested and rejected
    suggested_src_table: str = Field(..., description="Source table in rejected AI suggestion")
    suggested_src_column: str = Field(..., description="Source column in rejected AI suggestion")
    suggested_tgt_table: str = Field(..., description="Target table in rejected AI suggestion")
    suggested_tgt_column: str = Field(..., description="Target column in rejected AI suggestion")
    
    # Context at time of rejection (for vector search)
    src_comments: Optional[str] = Field(None, description="Source column description")
    src_datatype: Optional[str] = Field(None, description="Source column data type")
    tgt_comments: Optional[str] = Field(None, description="Target column description")
    
    # AI suggestion metadata
    ai_confidence_score: Optional[float] = Field(None, description="AI confidence (0.0-1.0)")
    ai_reasoning: Optional[str] = Field(None, description="AI explanation for suggestion")
    vector_search_score: Optional[float] = Field(None, description="Raw vector similarity score")
    suggestion_rank: Optional[int] = Field(None, description="Rank (1 = top suggestion)")
    
    # Feedback details
    feedback_action: str = Field(default="REJECTED", description="REJECTED or MODIFIED")
    user_comments: Optional[str] = Field(None, description="User explanation for rejection")
    
    # If modified
    modified_src_table: Optional[str] = Field(None, description="Actual source table if MODIFIED")
    modified_src_column: Optional[str] = Field(None, description="Actual source column if MODIFIED")
    modified_expression: Optional[str] = Field(None, description="Expression user created if MODIFIED")
    
    # Context
    domain: Optional[str] = Field(None, description="Domain category at time of suggestion")
    
    # Audit
    feedback_by: Optional[str] = Field(None, description="User who rejected")
    feedback_ts: Optional[datetime] = Field(None, description="Rejection timestamp")
    
    # Vector search field (auto-generated in DB)
    source_semantic_field: Optional[str] = Field(None, description="Computed field for vector embedding")


class MappingFeedbackCreateV3(BaseModel):
    """Create request for mapping feedback (rejection)."""
    suggested_src_table: str
    suggested_src_column: str
    suggested_tgt_table: str
    suggested_tgt_column: str
    src_comments: Optional[str] = None
    src_datatype: Optional[str] = None
    tgt_comments: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    ai_reasoning: Optional[str] = None
    vector_search_score: Optional[float] = None
    suggestion_rank: Optional[int] = None
    feedback_action: str = "REJECTED"
    user_comments: Optional[str] = None
    modified_src_table: Optional[str] = None
    modified_src_column: Optional[str] = None
    modified_expression: Optional[str] = None
    domain: Optional[str] = None
    feedback_by: Optional[str] = None

