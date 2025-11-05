"""
Semantic table models for target field definitions.
"""
from pydantic import BaseModel, Field
from typing import Optional


class SemanticRecord(BaseModel):
    """A single semantic table record representing a target field definition."""
    id: Optional[int] = None
    tgt_table_name: str
    tgt_table_physical_name: str
    tgt_column_name: str
    tgt_column_physical_name: str
    tgt_nullable: str  # "YES" or "NO"
    tgt_physical_datatype: str
    tgt_comments: Optional[str] = None
    semantic_field: Optional[str] = None


class SemanticRecordCreate(BaseModel):
    """Model for creating a new semantic record (excludes id and semantic_field)."""
    tgt_table_name: str
    tgt_table_physical_name: str
    tgt_column_name: str
    tgt_column_physical_name: str
    tgt_nullable: str = "NO"
    tgt_physical_datatype: str
    tgt_comments: Optional[str] = None


class SemanticRecordUpdate(BaseModel):
    """Model for updating an existing semantic record."""
    tgt_table_name: Optional[str] = None
    tgt_table_physical_name: Optional[str] = None
    tgt_column_name: Optional[str] = None
    tgt_column_physical_name: Optional[str] = None
    tgt_nullable: Optional[str] = None
    tgt_physical_datatype: Optional[str] = None
    tgt_comments: Optional[str] = None

