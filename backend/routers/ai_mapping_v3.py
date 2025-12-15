"""
AI Mapping Router V3 - Hybrid approach with SQL generation.

Endpoints:
- POST /api/v3/ai/suggestions - Get AI suggestions using dual vector search
- POST /api/v3/ai/generate-sql - Generate SQL expression from natural language
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from backend.services.ai_mapping_service_v3 import AIMappingServiceV3

router = APIRouter(prefix="/api/v3/ai", tags=["AI Mapping V3"])

# Initialize service
ai_service = AIMappingServiceV3()


# ============================================================================
# Request/Response Models
# ============================================================================

class SourceField(BaseModel):
    """Source field for mapping."""
    src_table_name: str
    src_table_physical_name: str
    src_column_name: str
    src_column_physical_name: str
    src_physical_datatype: Optional[str] = "STRING"
    src_comments: Optional[str] = ""


class TargetField(BaseModel):
    """Target field for mapping."""
    tgt_table_name: str
    tgt_column_name: str
    tgt_physical_datatype: Optional[str] = "STRING"


class SuggestionsRequest(BaseModel):
    """Request for AI suggestions."""
    source_fields: List[SourceField]
    num_results: Optional[int] = 10


class GenerateSQLRequest(BaseModel):
    """Request for SQL generation."""
    source_fields: List[SourceField]
    target_field: TargetField
    user_description: str


class HistoricalPattern(BaseModel):
    """Historical mapping pattern."""
    mapped_field_id: Optional[int] = None
    tgt_table_name: str
    tgt_column_name: str
    source_expression: Optional[str] = None
    source_columns: Optional[str] = None
    source_relationship_type: Optional[str] = "SINGLE"
    transformations_applied: Optional[str] = None
    search_score: Optional[float] = 0.0


class TargetCandidate(BaseModel):
    """Target field candidate from vector search."""
    semantic_field_id: Optional[int] = None
    tgt_table_name: str
    tgt_column_name: str
    tgt_table_physical_name: Optional[str] = None
    tgt_column_physical_name: Optional[str] = None
    tgt_comments: Optional[str] = ""
    tgt_physical_datatype: Optional[str] = None
    domain: Optional[str] = None
    search_score: Optional[float] = 0.0


class BestTarget(BaseModel):
    """LLM's best target recommendation."""
    tgt_table_name: Optional[str] = None
    tgt_column_name: Optional[str] = None
    confidence: Optional[float] = 0.0
    reasoning: Optional[str] = ""


class SuggestionsResponse(BaseModel):
    """Response with AI suggestions."""
    target_candidates: List[Dict[str, Any]]
    historical_patterns: List[Dict[str, Any]]
    rejections_to_avoid: List[Dict[str, Any]]
    recommended_expression: str
    recommended_transformations: List[str]
    detected_pattern: str
    best_target: Dict[str, Any]


class GenerateSQLResponse(BaseModel):
    """Response with generated SQL."""
    sql_expression: str
    transformations_used: List[str]
    explanation: str
    error: Optional[str] = None


class SearchUnmappedRequest(BaseModel):
    """Request for searching unmapped fields via vector search."""
    description: str
    datatype: Optional[str] = "STRING"
    domain: Optional[str] = ""
    table_filter: Optional[List[str]] = None
    user_email: Optional[str] = None
    num_results: Optional[int] = 10


class UnmappedFieldResult(BaseModel):
    """Result from unmapped fields vector search."""
    unmapped_field_id: int
    src_table_name: str
    src_table_physical_name: str
    src_column_name: str
    src_column_physical_name: str
    src_physical_datatype: Optional[str] = None
    src_comments: Optional[str] = None
    domain: Optional[str] = None
    mapping_status: Optional[str] = None
    match_score: float


class SearchUnmappedResponse(BaseModel):
    """Response with matching unmapped fields."""
    results: List[Dict[str, Any]]
    count: int


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/suggestions", response_model=SuggestionsResponse)
async def get_ai_suggestions(request: SuggestionsRequest):
    """
    Get AI-powered mapping suggestions using the Hybrid approach.
    
    This endpoint performs:
    1. Parallel vector search on semantic_fields (targets) and mapped_fields (patterns)
    2. Exact lookup of rejections for top candidates
    3. LLM analysis to rank and recommend
    
    Returns target candidates, historical patterns, and recommended SQL expression.
    """
    try:
        # Convert to dict for service
        source_fields = [field.model_dump() for field in request.source_fields]
        
        # Call service - returns all results, frontend filters via UI sliders
        result = await ai_service.generate_suggestions(
            source_fields=source_fields,
            num_results=request.num_results
        )
        
        return SuggestionsResponse(
            target_candidates=result.get("target_candidates", []),
            historical_patterns=result.get("historical_patterns", []),
            rejections_to_avoid=result.get("rejections_to_avoid", []),
            recommended_expression=result.get("recommended_expression", ""),
            recommended_transformations=result.get("recommended_transformations", []),
            detected_pattern=result.get("detected_pattern", "SINGLE"),
            best_target=result.get("best_target", {})
        )
        
    except Exception as e:
        print(f"[AI Mapping V3 Router] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-sql", response_model=GenerateSQLResponse)
async def generate_sql_expression(request: GenerateSQLRequest):
    """
    Generate a Databricks SQL expression from natural language.
    
    Examples of user_description:
    - "uppercase and trim"
    - "combine first and last name with space"
    - "convert to date format yyyy-MM-dd"
    - "handle nulls with default 'Unknown'"
    
    Returns the generated SQL expression with explanation.
    """
    try:
        # Convert to dict for service
        source_fields = [field.model_dump() for field in request.source_fields]
        target_field = request.target_field.model_dump()
        
        # Call service
        result = await ai_service.generate_sql_expression(
            source_fields=source_fields,
            target_field=target_field,
            user_description=request.user_description
        )
        
        return GenerateSQLResponse(
            sql_expression=result.get("sql_expression", ""),
            transformations_used=result.get("transformations_used", []),
            explanation=result.get("explanation", ""),
            error=result.get("error")
        )
        
    except Exception as e:
        print(f"[AI Mapping V3 Router] SQL generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-unmapped-fields", response_model=SearchUnmappedResponse)
async def search_unmapped_fields(request: SearchUnmappedRequest):
    """
    Search unmapped fields using vector search.
    
    Used for:
    - Template slot field suggestions (finding fields that match a pattern column description)
    - Join key suggestions (finding potential join columns in selected tables)
    
    The search uses the source_semantic_field column which contains:
    DESCRIPTION + TYPE + DOMAIN
    
    Args:
        description: The description or column name to search for
        datatype: Expected data type (helps narrow results)
        domain: Domain for relevance boosting
        table_filter: Optional list of tables to restrict search to
        user_email: Filter by uploaded_by user
        num_results: Max results (default 10)
        
    Returns:
        List of matching unmapped fields with match_score
    """
    try:
        results = await ai_service.search_unmapped_fields(
            description=request.description,
            datatype=request.datatype or "STRING",
            domain=request.domain or "",
            table_filter=request.table_filter,
            user_email=request.user_email,
            num_results=request.num_results or 10
        )
        
        return SearchUnmappedResponse(
            results=results,
            count=len(results)
        )
        
    except Exception as e:
        print(f"[AI Mapping V3 Router] Unmapped search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check for AI Mapping V3 service."""
    return {"status": "ok", "version": "v3", "features": ["dual_vector_search", "sql_generation", "unmapped_search"]}

