"""
Shared Pydantic models used across V3 services.

These models are shared between multiple services and don't belong
to a specific version. They include:
- UnmappedField: Source fields awaiting mapping
- Transformation: Reusable transformation templates
- MappingFeedback: User feedback on AI suggestions
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UnmappedField(BaseModel):
    """
    A source field awaiting mapping to a target field.
    
    Attributes:
        id: Auto-generated unique identifier
        src_table_name: Logical name of the source table
        src_table_physical_name: Physical name of the source table
        src_column_name: Logical name of the source column
        src_column_physical_name: Physical name of the source column
        src_nullable: Whether column is nullable ("YES" or "NO")
        src_physical_datatype: Physical data type of the column
        src_comments: Description or comments about the column
        domain: Domain category
        uploaded_at: Timestamp when field was added
        uploaded_by: User who uploaded this field
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    id: Optional[int] = Field(None, description="Unique identifier (auto-generated)")
    src_table_name: str = Field(..., description="Source table logical name")
    src_table_physical_name: str = Field(..., description="Source table physical name")
    src_column_name: str = Field(..., description="Source column logical name")
    src_column_physical_name: str = Field(..., description="Source column physical name")
    src_nullable: str = Field(..., description="Whether column is nullable (YES/NO)")
    src_physical_datatype: str = Field(..., description="Physical data type")
    src_comments: Optional[str] = Field(None, description="Column description")
    domain: Optional[str] = Field(None, description="Domain category")
    uploaded_at: Optional[datetime] = Field(None, description="Upload timestamp")
    uploaded_by: Optional[str] = Field(None, description="User who uploaded")


class UnmappedFieldCreate(BaseModel):
    """Create request for unmapped field."""
    src_table_name: str
    src_table_physical_name: str
    src_column_name: str
    src_column_physical_name: str
    src_nullable: str
    src_physical_datatype: str
    src_comments: Optional[str] = None
    domain: Optional[str] = None
    uploaded_by: Optional[str] = None


class Transformation(BaseModel):
    """
    Reusable transformation template.
    
    Predefined SQL transformations that can be applied to source fields.
    
    Attributes:
        transformation_id: Unique identifier
        transformation_name: Display name
        transformation_code: Short code
        transformation_expression: SQL expression template
        transformation_description: Human-readable explanation
        category: Grouping category
        is_system: Whether system-provided
        created_ts: Creation timestamp
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    transformation_id: Optional[int] = Field(None, description="Unique identifier")
    transformation_name: str = Field(..., description="Display name")
    transformation_code: str = Field(..., description="Short code")
    transformation_expression: str = Field(..., description="SQL expression template")
    transformation_description: Optional[str] = Field(None, description="Description")
    category: Optional[str] = Field(None, description="Category")
    is_system: Optional[bool] = Field(False, description="System-provided")
    created_ts: Optional[datetime] = Field(None, description="Creation timestamp")


class TransformationCreate(BaseModel):
    """Create request for transformation."""
    transformation_name: str
    transformation_code: str
    transformation_expression: str
    transformation_description: Optional[str] = None
    category: Optional[str] = None
    is_system: Optional[bool] = False


class MappingFeedback(BaseModel):
    """
    User feedback on AI-suggested mappings.
    
    Tracks user acceptance/rejection of AI suggestions for pattern learning.
    
    Attributes:
        feedback_id: Unique identifier
        suggested_src_table: Source table in AI suggestion
        suggested_src_column: Source column in AI suggestion
        suggested_tgt_table: Target table in AI suggestion
        suggested_tgt_column: Target column in AI suggestion
        feedback_action: User response (ACCEPTED, REJECTED, MODIFIED)
        user_comments: Optional user explanation
        ai_confidence_score: AI confidence score
        ai_reasoning: AI explanation
        vector_search_score: Raw vector search score
        suggestion_rank: Rank of this suggestion
        feedback_ts: Timestamp when feedback was provided
        feedback_by: User who provided feedback
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    feedback_id: Optional[int] = Field(None, description="Unique identifier")
    suggested_src_table: str = Field(..., description="Source table in suggestion")
    suggested_src_column: str = Field(..., description="Source column in suggestion")
    suggested_tgt_table: str = Field(..., description="Target table in suggestion")
    suggested_tgt_column: str = Field(..., description="Target column in suggestion")
    feedback_action: str = Field(default="PENDING", description="User response")
    user_comments: Optional[str] = Field(None, description="User explanation")
    ai_confidence_score: Optional[float] = Field(None, description="AI confidence")
    ai_reasoning: Optional[str] = Field(None, description="AI explanation")
    vector_search_score: Optional[float] = Field(None, description="Vector search score")
    suggestion_rank: Optional[int] = Field(None, description="Suggestion rank")
    feedback_ts: Optional[datetime] = Field(None, description="Feedback timestamp")
    feedback_by: Optional[str] = Field(None, description="User who provided feedback")


class MappingFeedbackCreate(BaseModel):
    """Create request for mapping feedback."""
    suggested_src_table: str
    suggested_src_column: str
    suggested_tgt_table: str
    suggested_tgt_column: str
    feedback_action: str = "PENDING"
    user_comments: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    ai_reasoning: Optional[str] = None
    vector_search_score: Optional[float] = None
    suggestion_rank: Optional[int] = None
    feedback_by: Optional[str] = None


# Aliases for backward compatibility
UnmappedFieldV2 = UnmappedField
UnmappedFieldCreateV2 = UnmappedFieldCreate
TransformationV2 = Transformation
TransformationCreateV2 = TransformationCreate
MappingFeedbackV2 = MappingFeedback
MappingFeedbackCreateV2 = MappingFeedbackCreate

