"""
Pydantic models for source-to-target field mappings.

These models define the data structures for:
- MappedField: A source field that has been mapped to a target field
- UnmappedField: A source field that has not yet been mapped
"""
from pydantic import BaseModel, Field
from typing import Optional


class MappedField(BaseModel):
    """
    A mapped field record showing source to target mapping.
    
    Represents a source database field that has been successfully mapped
    to a target field in the semantic table. Used for displaying and
    managing existing mappings in the UI.
    
    Attributes:
        src_table_name: Logical name of the source table
        src_column_name: Logical name of the source column
        tgt_mapping: Target column logical name (display name)
        tgt_table_name: Target table logical name
        tgt_column_physical: Physical name of target column in database
        tgt_table_physical: Physical name of target table in database
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    src_table_name: str = Field(..., description="Source table logical name")
    src_column_name: str = Field(..., description="Source column logical name")
    tgt_mapping: Optional[str] = Field(None, description="Target column name (mapped value)")
    tgt_table_name: Optional[str] = Field(None, description="Target table logical name")
    tgt_column_physical: Optional[str] = Field(None, description="Target column physical name")
    tgt_table_physical: Optional[str] = Field(None, description="Target table physical name")


class UnmappedField(BaseModel):
    """
    An unmapped field record from source database.
    
    Represents a source database field that has not yet been mapped to
    a target field. Contains metadata needed for AI suggestions and
    manual mapping search.
    
    Attributes:
        src_table_name: Logical name of the source table
        src_column_name: Logical name of the source column
        src_column_physical_name: Physical name of source column in database
        src_nullable: Whether column is nullable ("YES" or "NO")
        src_physical_datatype: Physical data type of the column
        src_comments: Description or comments about the column
    """
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    src_table_name: str = Field(..., description="Source table logical name")
    src_column_name: str = Field(..., description="Source column logical name")
    src_column_physical_name: str = Field(..., description="Source column physical name")
    src_nullable: str = Field(..., description="Whether column is nullable (YES/NO)")
    src_physical_datatype: str = Field(..., description="Physical data type (e.g., STRING, INT)")
    src_comments: Optional[str] = Field(None, description="Column description or comments")

