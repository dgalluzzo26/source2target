"""
Pydantic models for semantic table (target field definitions).

These models define the data structures for managing the semantic table,
which contains all possible target fields that source fields can be mapped to.

Models:
- SemanticRecord: Complete record with all fields including ID
- SemanticRecordCreate: For creating new records (excludes ID and semantic_field)
- SemanticRecordUpdate: For updating existing records (all fields optional)
"""
from pydantic import BaseModel, Field
from typing import Optional


class SemanticRecord(BaseModel):
    """
    A complete semantic table record representing a target field definition.
    
    The semantic table defines all possible target fields in the destination
    database that source fields can be mapped to. Each record includes both
    logical names (for display) and physical names (for actual database operations).
    
    The semantic_field is automatically generated from the other fields and is
    used for vector search similarity matching.
    
    Attributes:
        id: Unique identifier for the record
        tgt_table_name: Logical name of the target table (display name)
        tgt_table_physical_name: Physical name of target table in database
        tgt_column_name: Logical name of the target column (display name)
        tgt_column_physical_name: Physical name of target column in database
        tgt_nullable: Whether column is nullable ("YES" or "NO")
        tgt_physical_datatype: Physical data type (e.g., STRING, INT, DECIMAL)
        tgt_comments: Description or comments about the target field
        semantic_field: Auto-generated text for vector search (format: "TABLE NAME: ...; COLUMN NAME: ...; ...")
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    id: Optional[int] = Field(None, description="Unique record identifier")
    tgt_table_name: str = Field(..., description="Target table logical name")
    tgt_table_physical_name: str = Field(..., description="Target table physical name")
    tgt_column_name: str = Field(..., description="Target column logical name")
    tgt_column_physical_name: str = Field(..., description="Target column physical name")
    tgt_nullable: str = Field(..., description="Whether column is nullable (YES/NO)")
    tgt_physical_datatype: str = Field(..., description="Physical data type")
    tgt_comments: Optional[str] = Field(None, description="Column description or comments")
    semantic_field: Optional[str] = Field(None, description="Auto-generated semantic field text for vector search")


class SemanticRecordCreate(BaseModel):
    """
    Model for creating a new semantic record.
    
    Used when adding new target fields to the semantic table. The ID will be
    auto-generated and the semantic_field will be automatically created from
    the provided field information.
    
    Attributes:
        tgt_table_name: Logical name of the target table
        tgt_table_physical_name: Physical name of target table in database
        tgt_column_name: Logical name of the target column
        tgt_column_physical_name: Physical name of target column in database
        tgt_nullable: Whether column is nullable ("YES" or "NO", default "NO")
        tgt_physical_datatype: Physical data type
        tgt_comments: Description or comments about the target field
    """
    tgt_table_name: str = Field(..., description="Target table logical name")
    tgt_table_physical_name: str = Field(..., description="Target table physical name")
    tgt_column_name: str = Field(..., description="Target column logical name")
    tgt_column_physical_name: str = Field(..., description="Target column physical name")
    tgt_nullable: str = Field("NO", description="Whether column is nullable (default: NO)")
    tgt_physical_datatype: str = Field(..., description="Physical data type")
    tgt_comments: Optional[str] = Field(None, description="Column description or comments")


class SemanticRecordUpdate(BaseModel):
    """
    Model for updating an existing semantic record.
    
    All fields are optional to allow partial updates. The semantic_field will
    be automatically regenerated based on the updated field values.
    
    Attributes:
        tgt_table_name: Target table logical name (optional)
        tgt_table_physical_name: Target table physical name (optional)
        tgt_column_name: Target column logical name (optional)
        tgt_column_physical_name: Target column physical name (optional)
        tgt_nullable: Whether column is nullable (optional)
        tgt_physical_datatype: Physical data type (optional)
        tgt_comments: Column description or comments (optional)
    """
    tgt_table_name: Optional[str] = Field(None, description="Target table logical name")
    tgt_table_physical_name: Optional[str] = Field(None, description="Target table physical name")
    tgt_column_name: Optional[str] = Field(None, description="Target column logical name")
    tgt_column_physical_name: Optional[str] = Field(None, description="Target column physical name")
    tgt_nullable: Optional[str] = Field(None, description="Whether column is nullable")
    tgt_physical_datatype: Optional[str] = Field(None, description="Physical data type")
    tgt_comments: Optional[str] = Field(None, description="Column description or comments")

