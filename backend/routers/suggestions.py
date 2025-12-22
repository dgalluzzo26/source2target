"""
FastAPI router for V4 suggestion endpoints.

V4 Target-First Workflow:
- Get suggestion details
- Approve suggestions (create mappings)
- Edit and approve suggestions
- Reject suggestions (record feedback)
- Skip columns
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel
from backend.services.suggestion_service import SuggestionService
from backend.services.target_table_service import TargetTableService
from backend.services.project_service import ProjectService
from backend.services.pattern_service import PatternService
from backend.models.suggestion import (
    MappingSuggestion,
    SuggestionApproveRequest,
    SuggestionEditRequest,
    SuggestionRejectRequest,
    SuggestionSkipRequest,
    SuggestionStatus
)

router = APIRouter(prefix="/api/v4/suggestions", tags=["V4 Suggestions"])

# Service instances
suggestion_service = SuggestionService()
target_table_service = TargetTableService()
project_service = ProjectService()
pattern_service = PatternService()


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class SuggestionActionResponse(BaseModel):
    """Response for suggestion actions."""
    suggestion_id: int
    status: str
    mapped_field_id: Optional[int] = None
    message: str


# =============================================================================
# GET SUGGESTION
# =============================================================================

@router.get("/{suggestion_id}", response_model=dict)
async def get_suggestion(suggestion_id: int):
    """
    Get a single suggestion with full details.
    
    Includes:
    - Target column info
    - Pattern info (original SQL, pattern type)
    - Matched source fields with scores
    - Suggested SQL
    - SQL changes made
    - Confidence and warnings
    """
    try:
        suggestion = await suggestion_service.get_suggestion_by_id(suggestion_id)
        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        return suggestion
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Suggestions Router] Error getting suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# APPROVE SUGGESTION
# =============================================================================

@router.post("/{suggestion_id}/approve", response_model=SuggestionActionResponse)
async def approve_suggestion(suggestion_id: int, request: SuggestionApproveRequest):
    """
    Approve a suggestion as-is and create a mapping.
    
    This will:
    1. Create a new row in mapped_fields with the suggested SQL
    2. Update suggestion status to APPROVED
    3. Mark matched source fields as MAPPED
    4. Update table and project counters
    
    The new mapping will have is_approved_pattern=false until explicitly approved as a pattern.
    """
    try:
        result = await suggestion_service.approve_suggestion(suggestion_id, request)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Update table counters
        if result.get("target_table_status_id"):
            await target_table_service.recalculate_table_counters(
                result["target_table_status_id"]
            )
            
            # Get project_id from suggestion and update project counters
            suggestion = await suggestion_service.get_suggestion_by_id(suggestion_id)
            if suggestion:
                await project_service.update_project_counters(suggestion["project_id"])
        
        return SuggestionActionResponse(
            suggestion_id=suggestion_id,
            status=result["status"],
            mapped_field_id=result.get("mapped_field_id"),
            message="Suggestion approved and mapping created"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Suggestions Router] Error approving suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# EDIT AND APPROVE SUGGESTION
# =============================================================================

@router.post("/{suggestion_id}/edit", response_model=SuggestionActionResponse)
async def edit_and_approve_suggestion(suggestion_id: int, request: SuggestionEditRequest):
    """
    Edit a suggestion and approve it.
    
    Use this when the AI-generated SQL needs modifications.
    The edited SQL will be used instead of the suggested SQL.
    
    This will:
    1. Create a new row in mapped_fields with the edited SQL
    2. Update suggestion status to EDITED
    3. Store the edited SQL and notes on the suggestion
    4. Mark matched source fields as MAPPED
    5. Update table and project counters
    """
    try:
        result = await suggestion_service.edit_and_approve_suggestion(suggestion_id, request)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Update table counters
        if result.get("target_table_status_id"):
            await target_table_service.recalculate_table_counters(
                result["target_table_status_id"]
            )
            
            # Update project counters
            suggestion = await suggestion_service.get_suggestion_by_id(suggestion_id)
            if suggestion:
                await project_service.update_project_counters(suggestion["project_id"])
        
        return SuggestionActionResponse(
            suggestion_id=suggestion_id,
            status=result["status"],
            mapped_field_id=result.get("mapped_field_id"),
            message="Suggestion edited and mapping created"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Suggestions Router] Error editing suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# REJECT SUGGESTION
# =============================================================================

@router.post("/{suggestion_id}/reject", response_model=SuggestionActionResponse)
async def reject_suggestion(suggestion_id: int, request: SuggestionRejectRequest):
    """
    Reject a suggestion.
    
    This will:
    1. Update suggestion status to REJECTED
    2. Store the rejection reason
    3. Record feedback in mapping_feedback for AI learning
    4. Update table and project counters
    
    Rejection feedback helps the AI avoid similar suggestions in the future.
    """
    try:
        result = await suggestion_service.reject_suggestion(suggestion_id, request)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Update table counters
        if result.get("target_table_status_id"):
            await target_table_service.recalculate_table_counters(
                result["target_table_status_id"]
            )
            
            # Update project counters
            suggestion = await suggestion_service.get_suggestion_by_id(suggestion_id)
            if suggestion:
                await project_service.update_project_counters(suggestion["project_id"])
        
        return SuggestionActionResponse(
            suggestion_id=suggestion_id,
            status=result["status"],
            message="Suggestion rejected and feedback recorded"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Suggestions Router] Error rejecting suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SKIP COLUMN
# =============================================================================

@router.post("/{suggestion_id}/skip", response_model=SuggestionActionResponse)
async def skip_suggestion(suggestion_id: int, request: SuggestionSkipRequest):
    """
    Skip a column (defer mapping to later).
    
    This will:
    1. Update suggestion status to SKIPPED
    2. Update table and project counters
    
    Skipped columns can be revisited later.
    Use this for columns that don't need mapping or need manual handling.
    """
    try:
        result = await suggestion_service.skip_suggestion(suggestion_id, request)
        
        # Update table counters
        if result.get("target_table_status_id"):
            await target_table_service.recalculate_table_counters(
                result["target_table_status_id"]
            )
            
            # Update project counters
            suggestion = await suggestion_service.get_suggestion_by_id(suggestion_id)
            if suggestion:
                await project_service.update_project_counters(suggestion["project_id"])
        
        return SuggestionActionResponse(
            suggestion_id=suggestion_id,
            status=result["status"],
            message="Column skipped"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Suggestions Router] Error skipping suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# BULK ACTIONS
# =============================================================================

class BulkApproveRequest(BaseModel):
    """Request for bulk approve."""
    suggestion_ids: list[int]
    reviewed_by: str
    min_confidence: float = 0.8  # Only approve if confidence >= this


class BulkApproveResponse(BaseModel):
    """Response for bulk approve."""
    approved_count: int
    skipped_count: int
    details: list[dict]


@router.post("/bulk-approve", response_model=BulkApproveResponse)
async def bulk_approve_suggestions(request: BulkApproveRequest):
    """
    Approve multiple suggestions at once.
    
    Only approves suggestions with confidence >= min_confidence.
    Lower confidence suggestions are skipped.
    """
    try:
        approved = []
        skipped = []
        
        for suggestion_id in request.suggestion_ids:
            suggestion = await suggestion_service.get_suggestion_by_id(suggestion_id)
            
            if not suggestion:
                skipped.append({
                    "suggestion_id": suggestion_id,
                    "reason": "not_found"
                })
                continue
            
            confidence = suggestion.get("confidence_score", 0)
            
            if confidence < request.min_confidence:
                skipped.append({
                    "suggestion_id": suggestion_id,
                    "reason": f"confidence {confidence:.2f} < {request.min_confidence}"
                })
                continue
            
            if suggestion.get("suggestion_status") != "PENDING":
                skipped.append({
                    "suggestion_id": suggestion_id,
                    "reason": f"status is {suggestion.get('suggestion_status')}"
                })
                continue
            
            # Approve
            approve_request = SuggestionApproveRequest(reviewed_by=request.reviewed_by)
            result = await suggestion_service.approve_suggestion(suggestion_id, approve_request)
            
            approved.append({
                "suggestion_id": suggestion_id,
                "mapped_field_id": result.get("mapped_field_id"),
                "confidence": confidence
            })
        
        # Update counters for affected tables
        affected_tables = set()
        for item in approved:
            suggestion = await suggestion_service.get_suggestion_by_id(item["suggestion_id"])
            if suggestion:
                affected_tables.add(suggestion.get("target_table_status_id"))
        
        for table_id in affected_tables:
            if table_id:
                await target_table_service.recalculate_table_counters(table_id)
        
        return BulkApproveResponse(
            approved_count=len(approved),
            skipped_count=len(skipped),
            details=approved + skipped
        )
        
    except Exception as e:
        print(f"[Suggestions Router] Error in bulk approve: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PATTERN ALTERNATIVES
# =============================================================================

@router.get("/{suggestion_id}/alternatives", response_model=dict)
async def get_pattern_alternatives(suggestion_id: int):
    """
    Get alternative pattern variants for a suggestion.
    
    Returns a list of different pattern types (by signature) that could be used
    for this target column. Each variant shows:
    - signature: Unique identifier for the pattern type
    - description: Human-readable description (e.g., "JOIN (2 tables) + COALESCE")
    - usage_count: How many times this pattern type has been used
    - latest_mapped_ts: When this pattern type was last used
    - latest_pattern: The most recent pattern of this type
    
    Use the mapped_field_id from latest_pattern to regenerate with a specific pattern.
    """
    try:
        # Get the suggestion to find target table/column
        suggestion = await suggestion_service.get_suggestion_by_id(suggestion_id)
        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        tgt_table = suggestion.get("tgt_table_physical_name")
        tgt_column = suggestion.get("tgt_column_physical_name")
        
        # Get all pattern variants
        variants = pattern_service.get_pattern_variants(tgt_table, tgt_column)
        
        # Mark the currently selected pattern
        current_signature = suggestion.get("pattern_signature")
        for variant in variants:
            variant["is_current"] = variant["signature"] == current_signature
        
        return {
            "suggestion_id": suggestion_id,
            "tgt_table": tgt_table,
            "tgt_column": tgt_column,
            "current_signature": current_signature,
            "variants": variants,
            "total_variants": len(variants)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Suggestions Router] Error getting alternatives: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# REGENERATE SINGLE SUGGESTION
# =============================================================================

@router.post("/{suggestion_id}/regenerate", response_model=SuggestionActionResponse)
async def regenerate_suggestion(
    suggestion_id: int,
    pattern_id: Optional[int] = None
):
    """
    Regenerate AI suggestion for a single column.
    
    Args:
        suggestion_id: The suggestion to regenerate
        pattern_id: Optional specific pattern to use. If provided, uses this pattern
                   instead of auto-selecting the best one. Get pattern IDs from 
                   the /alternatives endpoint.
    
    Use this when:
    - User has added new source fields and wants to re-run discovery
    - Previous discovery had an error
    - User wants to try a different pattern variant (pass pattern_id)
    
    This will:
    1. Look up the pattern (specific or best available)
    2. Re-run vector search to find matching source columns
    3. Re-call the LLM to rewrite the SQL
    4. Update the suggestion with new results
    
    The suggestion status will be reset based on results:
    - PENDING: Pattern found and sources matched
    - NO_MATCH: Pattern found but no matching sources
    - NO_PATTERN: No pattern exists for this target column
    """
    try:
        if pattern_id:
            print(f"[Suggestions Router] Regenerating suggestion {suggestion_id} with pattern {pattern_id}")
        else:
            print(f"[Suggestions Router] Regenerating suggestion: {suggestion_id}")
        
        result = await suggestion_service.regenerate_single_suggestion(
            suggestion_id, 
            pattern_id=pattern_id
        )
        
        if result.get("error"):
            raise HTTPException(status_code=404, detail=result["error"])
        
        return SuggestionActionResponse(
            suggestion_id=suggestion_id,
            status=result.get("status", "unknown"),
            message=result.get("message", "Suggestion regenerated")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Suggestions Router] Error regenerating suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AI SQL ASSISTANT
# =============================================================================

class AIAssistRequest(BaseModel):
    """Request for AI SQL assistance."""
    prompt: str
    current_sql: str
    target_column: Optional[str] = None
    target_table: Optional[str] = None
    available_columns: Optional[list] = None


class AIAssistResponse(BaseModel):
    """Response from AI SQL assistant."""
    sql: str
    explanation: str
    success: bool


@router.post("/ai/assist", response_model=AIAssistResponse)
async def ai_sql_assist(request: AIAssistRequest):
    """
    AI SQL Assistant - helps modify SQL expressions based on natural language prompts.
    
    Example prompts:
    - "Replace CDE_COUNTY with COUNTY_CD"
    - "Add a TRIM around the column name"
    - "Join to the address table on RECIP_ID"
    - "Change the alias from b to rm"
    
    The AI will understand the context and modify the SQL accordingly.
    """
    try:
        print(f"[AI Assist] Processing prompt: {request.prompt[:100]}...")
        
        result = await suggestion_service.ai_sql_assist(
            prompt=request.prompt,
            current_sql=request.current_sql,
            target_column=request.target_column,
            target_table=request.target_table,
            available_columns=request.available_columns
        )
        
        return AIAssistResponse(
            sql=result.get("sql", request.current_sql),
            explanation=result.get("explanation", ""),
            success=result.get("success", False)
        )
        
    except Exception as e:
        print(f"[AI Assist] Error: {e}")
        return AIAssistResponse(
            sql=request.current_sql,
            explanation=f"Error: {str(e)}",
            success=False
        )


# =============================================================================
# DEBUG - GET LAST LLM PROMPT
# =============================================================================

@router.get("/debug/last-prompt")
async def get_last_llm_prompt():
    """
    Get the last LLM prompt used for SQL rewriting.
    
    For debugging - shows the full prompt sent to the LLM including:
    - Target column
    - Pattern SQL
    - Matched source columns
    - Silver tables info
    - Full prompt text
    
    Returns:
        Last prompt data or empty if none
    """
    prompt_data = getattr(suggestion_service, '_last_llm_prompt', None)
    if prompt_data:
        return {
            "status": "ok",
            "prompt": prompt_data
        }
    else:
        return {
            "status": "no_prompt",
            "message": "No LLM prompt captured yet. Run discovery first."
        }
