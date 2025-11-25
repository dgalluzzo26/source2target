"""
AI Mapping V2 API endpoints for multi-field mapping suggestions.

Provides intelligent suggestions for mapping multiple source fields to a single target field.
"""
from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.services.ai_mapping_service_v2 import AIMappingServiceV2

router = APIRouter(prefix="/api/v2/ai-mapping", tags=["AI Mapping V2"])

ai_mapping_service = AIMappingServiceV2()


class SourceFieldInput(BaseModel):
    """
    Source field input for multi-field AI suggestions.
    
    Attributes:
        src_table_name: Logical name of the source table
        src_table_physical_name: Physical name of the source table
        src_column_name: Logical name of the source column
        src_column_physical_name: Physical name of the source column
        src_physical_datatype: Physical data type
        src_comments: Description or comments
    """
    src_table_name: str
    src_table_physical_name: str
    src_column_name: str
    src_column_physical_name: str
    src_physical_datatype: str
    src_comments: str = ""


class MultiFieldSuggestionsRequest(BaseModel):
    """
    Request body for multi-field AI suggestions.
    
    Attributes:
        source_fields: List of 1 or more source fields to map
        num_results: Maximum number of suggestions to return (default: 10)
    """
    source_fields: List[SourceFieldInput] = Field(
        ...,
        description="List of source fields to combine and map (1 or more)",
        min_length=1
    )
    num_results: int = Field(
        default=10,
        description="Maximum number of suggestions to return",
        ge=1,
        le=50
    )


class MappingSuggestion(BaseModel):
    """
    AI-powered mapping suggestion response.
    
    Attributes:
        semantic_field_id: Primary key of the semantic field (required for mapping creation)
        tgt_table_name: Target table logical name
        tgt_column_name: Target column logical name
        tgt_table_physical_name: Target table physical name
        tgt_column_physical_name: Target column physical name
        tgt_comments: Description/comments for the target field
        search_score: Vector search confidence score (0.0-1.0)
        match_quality: Human-readable quality rating (Excellent, Strong, Good, Weak)
        ai_reasoning: LLM explanation for this suggestion
    """
    semantic_field_id: int
    tgt_table_name: str
    tgt_column_name: str
    tgt_table_physical_name: str = ""
    tgt_column_physical_name: str = ""
    tgt_comments: Optional[str] = ""
    search_score: float
    match_quality: str
    ai_reasoning: str


@router.post("/suggestions", response_model=List[MappingSuggestion])
async def generate_multi_field_suggestions(
    request: MultiFieldSuggestionsRequest = Body(...)
):
    """
    Generate AI-powered mapping suggestions for one or more source fields.
    
    **V2 Multi-Field Mapping:**
    - Supports 1 to N source fields
    - For single field: Standard semantic similarity search
    - For multiple fields: Intelligent combination analysis with pattern learning
    
    **How It Works:**
    1. Combines source field descriptions into a single query
    2. Looks for historical patterns in mapped_fields table
    3. Performs vector similarity search on semantic_fields
    4. Calls LLM (Databricks Foundation Model) to generate reasoning
    5. Returns ranked suggestions with match quality and explanation
    
    **Example Use Cases:**
    - Single field: `FIRST_NAME` → suggests `full_name`, `first_name`, etc.
    - Multi-field: `FIRST_NAME + LAST_NAME` → suggests `full_name`, `member_name`, etc.
    - Multi-field: `ADDRESS_LINE1 + CITY + STATE` → suggests `full_address`, etc.
    
    Args:
        request: MultiFieldSuggestionsRequest with source_fields and num_results
    
    Returns:
        List of MappingSuggestion with ranked target field suggestions
    
    Raises:
        HTTPException 400: If request validation fails
        HTTPException 500: If AI suggestion generation fails
    """
    try:
        # Convert Pydantic models to dictionaries
        source_fields = [field.model_dump() for field in request.source_fields]
        
        print(f"[AI Mapping V2 API] Generating suggestions for {len(source_fields)} source fields")
        
        # Generate suggestions
        suggestions = await ai_mapping_service.generate_multi_field_suggestions(
            source_fields=source_fields,
            num_results=request.num_results
        )
        
        print(f"[AI Mapping V2 API] Generated {len(suggestions)} suggestions")
        
        return suggestions
        
    except ValueError as e:
        print(f"[AI Mapping V2 API] Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[AI Mapping V2 API] Error generating suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check for AI Mapping V2 service.
    
    Returns:
        dict: Status and version information
    """
    return {
        "status": "healthy",
        "service": "AI Mapping V2",
        "features": [
            "Multi-field source selection",
            "Historical pattern learning",
            "LLM-powered reasoning",
            "Vector similarity search"
        ]
    }

