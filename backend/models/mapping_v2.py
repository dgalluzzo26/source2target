"""
Pydantic models for V2 multi-field mapping schema.

V2 Changes:
- Supports many-to-one mapping (multiple source fields → single target field)
- Field ordering and concatenation strategies
- Per-field transformations
- User feedback on AI suggestions
- Separate tables for unmapped, mapped, and mapping details

Models:
- UnmappedFieldV2: Source fields awaiting mapping
- MappedFieldV2: Target fields with completed mappings
- MappingDetailV2: Individual source fields in a mapping
- MappingFeedbackV2: User feedback on AI suggestions
- TransformationV2: Reusable transformation template
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UnmappedFieldV2(BaseModel):
    """
    A source field awaiting mapping to a target field (V2 schema).
    
    In V2, unmapped fields are stored separately from mapped fields.
    Once a field is mapped, it moves to mapped_fields and mapping_details tables.
    
    Attributes:
        id: Auto-generated unique identifier
        src_table_name: Logical name of the source table
        src_table_physical_name: Physical name of the source table in database
        src_column_name: Logical name of the source column
        src_column_physical_name: Physical name of the source column in database
        src_nullable: Whether column is nullable ("YES" or "NO")
        src_physical_datatype: Physical data type of the column
        src_comments: Description or comments about the column
        uploaded_at: Timestamp when field was added (set by database)
        uploaded_by: User who uploaded this field
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    id: Optional[int] = Field(None, description="Unique identifier (auto-generated)")
    src_table_name: str = Field(..., description="Source table logical name")
    src_table_physical_name: str = Field(..., description="Source table physical name")
    src_column_name: str = Field(..., description="Source column logical name")
    src_column_physical_name: str = Field(..., description="Source column physical name")
    src_nullable: str = Field(..., description="Whether column is nullable (YES/NO)")
    src_physical_datatype: str = Field(..., description="Physical data type (e.g., STRING, INT)")
    src_comments: Optional[str] = Field(None, description="Column description or comments")
    domain: Optional[str] = Field(None, description="Domain category (e.g., claims, member, provider)")
    uploaded_at: Optional[datetime] = Field(None, description="Upload timestamp")
    uploaded_by: Optional[str] = Field(None, description="User who uploaded")


class UnmappedFieldCreateV2(BaseModel):
    """Create request for unmapped field (excludes auto-generated fields)."""
    src_table_name: str
    src_table_physical_name: str
    src_column_name: str
    src_column_physical_name: str
    src_nullable: str
    src_physical_datatype: str
    src_comments: Optional[str] = None
    domain: Optional[str] = None
    uploaded_by: Optional[str] = None


class MappedFieldV2(BaseModel):
    """
    A target field with one or more source field mappings (V2 schema).
    
    This represents the "result" side of a mapping. A single record here
    can have multiple source fields (stored in mapping_details table).
    
    Attributes:
        mapping_id: Unique identifier for this mapping
        tgt_table_name: Logical name of the target table
        tgt_table_physical_name: Physical name of the target table in database
        tgt_column_name: Logical name of the target column
        tgt_column_physical_name: Physical name of the target column in database
        concat_strategy: How to combine multiple source fields (SPACE, COMMA, PIPE, CUSTOM, NONE)
        custom_concat_value: Custom concatenation string if strategy is CUSTOM
        final_sql_expression: Complete SQL transformation expression
        mapped_at: Timestamp when mapping was created
        mapped_by: User who created the mapping
        mapping_confidence_score: AI confidence score (0.0-1.0) if AI-suggested
        ai_reasoning: AI explanation for the suggested mapping
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    mapping_id: Optional[int] = Field(None, description="Unique mapping identifier (auto-generated)")
    tgt_table_name: str = Field(..., description="Target table logical name")
    tgt_table_physical_name: str = Field(..., description="Target table physical name")
    tgt_column_name: str = Field(..., description="Target column logical name")
    tgt_column_physical_name: str = Field(..., description="Target column physical name")
    concat_strategy: str = Field(default="SPACE", description="Concatenation strategy (SPACE, COMMA, PIPE, CUSTOM, NONE)")
    custom_concat_value: Optional[str] = Field(None, description="Custom concatenation string")
    final_sql_expression: Optional[str] = Field(None, description="Complete SQL transformation")
    mapped_at: Optional[datetime] = Field(None, description="Mapping timestamp")
    mapped_by: Optional[str] = Field(None, description="User who created mapping")
    mapping_confidence_score: Optional[float] = Field(None, description="AI confidence (0.0-1.0)")
    ai_reasoning: Optional[str] = Field(None, description="AI explanation for mapping")


class MappedFieldCreateV2(BaseModel):
    """Create request for mapped field."""
    tgt_table_name: str
    tgt_table_physical_name: str
    tgt_column_name: str
    tgt_column_physical_name: str
    concat_strategy: str = "SPACE"
    custom_concat_value: Optional[str] = None
    final_sql_expression: Optional[str] = None
    mapped_by: Optional[str] = None
    mapping_confidence_score: Optional[float] = None
    ai_reasoning: Optional[str] = None


class MappingDetailV2(BaseModel):
    """
    An individual source field in a mapping (V2 schema).
    
    This table links source fields to target mappings with ordering
    and transformations. Multiple records can share the same mapping_id
    to represent multi-field mappings.
    
    Attributes:
        detail_id: Unique identifier for this detail record
        mapping_id: Foreign key to mapped_fields table
        src_table_name: Logical name of the source table
        src_table_physical_name: Physical name of the source table
        src_column_name: Logical name of the source column
        src_column_physical_name: Physical name of the source column
        field_order: Order of this field in the concatenation (1, 2, 3...)
        transformation_expr: SQL transformation expression for this field
        added_at: Timestamp when detail was added
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    detail_id: Optional[int] = Field(None, description="Unique detail identifier (auto-generated)")
    mapping_id: int = Field(..., description="Foreign key to mapped_fields")
    src_table_name: str = Field(..., description="Source table logical name")
    src_table_physical_name: str = Field(..., description="Source table physical name")
    src_column_name: str = Field(..., description="Source column logical name")
    src_column_physical_name: str = Field(..., description="Source column physical name")
    field_order: int = Field(..., description="Order in concatenation (1, 2, 3...)")
    transformation_expr: Optional[str] = Field(None, description="SQL transformation expression")
    added_at: Optional[datetime] = Field(None, description="Timestamp when added")


class MappingDetailCreateV2(BaseModel):
    """Create request for mapping detail."""
    mapping_id: Optional[int] = None  # Will be set by backend during creation
    src_table_name: str
    src_table_physical_name: str
    src_column_name: str
    src_column_physical_name: str
    field_order: int
    transformation_expr: Optional[str] = None


class MappingFeedbackV2(BaseModel):
    """
    User feedback on AI-suggested mappings (V2 schema).
    
    Tracks user acceptance/rejection of AI suggestions to improve
    future recommendations. This is key for pattern learning.
    
    Attributes:
        feedback_id: Unique identifier for feedback record
        src_table_name: Source table logical name
        src_table_physical_name: Source table physical name
        src_column_name: Source column logical name
        src_column_physical_name: Source column physical name
        suggested_tgt_table_name: AI-suggested target table logical name
        suggested_tgt_column_name: AI-suggested target column logical name
        feedback_status: User response (ACCEPTED, REJECTED, PENDING)
        user_comment: Optional user explanation for rejection
        ai_confidence_score: AI confidence score for this suggestion
        ai_reasoning: AI explanation for this suggestion
        feedback_at: Timestamp when feedback was provided
        feedback_by: User who provided feedback
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    feedback_id: Optional[int] = Field(None, description="Unique feedback identifier (auto-generated)")
    src_table_name: str = Field(..., description="Source table logical name")
    src_table_physical_name: str = Field(..., description="Source table physical name")
    src_column_name: str = Field(..., description="Source column logical name")
    src_column_physical_name: str = Field(..., description="Source column physical name")
    suggested_tgt_table_name: str = Field(..., description="AI-suggested target table logical name")
    suggested_tgt_column_name: str = Field(..., description="AI-suggested target column logical name")
    feedback_status: str = Field(default="PENDING", description="User response (ACCEPTED, REJECTED, PENDING)")
    user_comment: Optional[str] = Field(None, description="User explanation for rejection")
    ai_confidence_score: Optional[float] = Field(None, description="AI confidence (0.0-1.0)")
    ai_reasoning: Optional[str] = Field(None, description="AI explanation for suggestion")
    feedback_at: Optional[datetime] = Field(None, description="Feedback timestamp")
    feedback_by: Optional[str] = Field(None, description="User who provided feedback")


class MappingFeedbackCreateV2(BaseModel):
    """Create request for mapping feedback."""
    src_table_name: str
    src_table_physical_name: str
    src_column_name: str
    src_column_physical_name: str
    suggested_tgt_table_name: str
    suggested_tgt_column_name: str
    feedback_status: str = "PENDING"
    user_comment: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    ai_reasoning: Optional[str] = None
    feedback_by: Optional[str] = None


class TransformationV2(BaseModel):
    """
    Reusable transformation template (V2 schema).
    
    Predefined SQL transformations that can be applied to source fields.
    Examples: TRIM, UPPER, LOWER, INITCAP, CAST, etc.
    
    Attributes:
        transformation_id: Unique identifier
        transformation_name: Display name (e.g., "Trim Whitespace")
        transformation_code: Short code (e.g., "TRIM")
        transformation_expression: SQL expression template (e.g., "TRIM({field})")
        transformation_description: Human-readable explanation
        category: Grouping (e.g., "STRING", "DATE", "NUMERIC")
        is_system: Whether this is a system-provided transformation
        created_ts: Timestamp when created
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    transformation_id: Optional[int] = Field(None, description="Unique identifier (auto-generated)")
    transformation_name: str = Field(..., description="Display name (e.g., 'Trim Whitespace')")
    transformation_code: str = Field(..., description="Short code (e.g., 'TRIM')")
    transformation_expression: str = Field(..., description="SQL expression template (e.g., 'TRIM({field})')")
    transformation_description: Optional[str] = Field(None, description="Human-readable explanation")
    category: Optional[str] = Field(None, description="Grouping (e.g., 'STRING', 'DATE', 'NUMERIC')")
    is_system: Optional[bool] = Field(False, description="System-provided transformation")
    created_ts: Optional[datetime] = Field(None, description="Creation timestamp")


class TransformationCreateV2(BaseModel):
    """Create request for transformation."""
    transformation_name: str
    transformation_code: str
    transformation_expression: str
    transformation_description: Optional[str] = None
    category: Optional[str] = None
    is_system: Optional[bool] = False

