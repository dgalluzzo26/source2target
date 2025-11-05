"""
Mapping models for source-to-target field mappings.
"""
from pydantic import BaseModel
from typing import Optional


class MappedField(BaseModel):
    """A mapped field record showing source to target mapping."""
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    src_table_name: str
    src_column_name: str
    tgt_mapping: Optional[str] = None  # target column name
    tgt_table_name: Optional[str] = None
    tgt_column_physical: Optional[str] = None
    tgt_table_physical: Optional[str] = None


class UnmappedField(BaseModel):
    """An unmapped field record from source database."""
    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
    
    src_table_name: str
    src_column_name: str
    src_column_physical_name: str
    src_nullable: str
    src_physical_datatype: str
    src_comments: Optional[str] = None

