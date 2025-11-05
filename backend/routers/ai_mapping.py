"""
AI Mapping API endpoints.
"""
from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel
from backend.services.ai_mapping_service import ai_mapping_service


router = APIRouter(prefix="/api/ai-mapping", tags=["ai-mapping"])


class GenerateAISuggestionsRequest(BaseModel):
    """Request body for generating AI suggestions."""
    src_table_name: str
    src_column_name: str
    src_datatype: str
    src_nullable: str
    src_comments: str
    num_vector_results: Optional[int] = 25
    num_ai_results: Optional[int] = 10
    user_feedback: Optional[str] = ""


class AISuggestion(BaseModel):
    """AI mapping suggestion with confidence score."""
    rank: int
    target_table: str
    target_column: str
    target_table_physical: str
    target_column_physical: str
    semantic_field: str
    confidence_score: float
    reasoning: str


@router.post("/generate-suggestions", response_model=List[AISuggestion])
async def generate_ai_suggestions(request_body: GenerateAISuggestionsRequest):
    """
    Generate AI-powered mapping suggestions using vector search.
    Returns suggestions with confidence scores from vector similarity.
    """
    try:
        print("[AI Mapping Router] POST /generate-suggestions called")
        print(f"[AI Mapping Router] Source field: {request_body.src_table_name}.{request_body.src_column_name}")
        
        suggestions = await ai_mapping_service.generate_ai_suggestions(
            src_table_name=request_body.src_table_name,
            src_column_name=request_body.src_column_name,
            src_datatype=request_body.src_datatype,
            src_nullable=request_body.src_nullable,
            src_comments=request_body.src_comments,
            num_vector_results=request_body.num_vector_results,
            num_ai_results=request_body.num_ai_results,
            user_feedback=request_body.user_feedback
        )
        
        print(f"[AI Mapping Router] Returning {len(suggestions)} suggestions")
        return suggestions
        
    except Exception as e:
        print(f"[AI Mapping Router] ERROR generating suggestions: {str(e)}")
        import traceback
        print(f"[AI Mapping Router] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

