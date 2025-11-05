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

