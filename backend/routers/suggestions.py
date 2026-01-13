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


@router.get("/debug/last-vector-search")
async def get_last_vector_search():
    """
    Get the last vector search details for debugging.
    
    Shows:
    - Query text sent to vector search
    - Raw results before project_id filtering
    - Filtered results after project_id filtering
    - Scores for each result
    
    Returns:
        Last vector search data or empty if none
    """
    vs_data = getattr(suggestion_service, '_last_vector_search', None)
    if vs_data:
        return {
            "status": "ok",
            "vector_search": vs_data
        }
    else:
        return {
            "status": "no_data",
            "message": "No vector search captured yet. Run discovery first."
        }


# =============================================================================
# VECTOR SEARCH CANDIDATES FOR A SUGGESTION
# =============================================================================

@router.get("/{suggestion_id}/vs-candidates", response_model=dict)
async def get_suggestion_vs_candidates(suggestion_id: int):
    """
    Get vector search candidates for a suggestion.
    
    Returns all the source field alternatives that were found during vector search,
    organized by pattern column. This allows users to see what options the LLM
    had when making its selection.
    
    Each pattern column shows:
    - The candidates found by vector search (up to 10 per column)
    - Similarity scores
    - Source table/column info
    - Descriptions
    
    Use this to:
    - Understand why the AI chose certain matches
    - See alternative source fields that could be used
    - Verify the AI made the right choice or identify better alternatives
    """
    try:
        suggestion = await suggestion_service.get_suggestion_by_id(suggestion_id)
        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        import json
        
        # Parse the vector_search_candidates JSON
        vs_candidates_raw = suggestion.get("vector_search_candidates")
        vs_candidates = {}
        
        if vs_candidates_raw:
            try:
                vs_candidates = json.loads(vs_candidates_raw)
            except:
                pass
        
        # Parse sql_changes to determine what was ACTUALLY selected
        # sql_changes has: {type: "column_replace", original: "PATTERN_COL", new: "SOURCE_COL"}
        sql_changes_raw = suggestion.get("sql_changes")
        sql_changes = []
        
        if sql_changes_raw:
            try:
                sql_changes = json.loads(sql_changes_raw)
            except:
                pass
        
        # Build structured data:
        # 1. changes_by_table: {alias: {table_name, changes: [{orig_col, new_col, new_table}]}}
        # 2. table_mappings: [{alias, pattern_table, source_table}]
        # 3. column_usage: {column_name: [{alias, pattern_table, new_col, new_table}]}
        # 4. alias_to_pattern_table: {alias: pattern_table_name} from join_metadata
        
        changes_by_table = {}  # alias -> {pattern_table, source_table, changes}
        table_mappings = []    # [{alias, pattern_table, source_table}]
        column_usage = {}      # pattern_col -> list of usages
        alias_to_pattern_table = {}  # alias -> pattern table physical name (from join_metadata)
        
        # Extract alias-to-table mapping from join_metadata (the source of truth)
        pattern_sql_raw = suggestion.get("pattern_sql", "")
        join_metadata_raw = None
        
        # Try to get join_metadata from pattern using pattern_mapped_field_id
        # The pattern contains join_metadata with unionBranches and bronzeTable alias mappings
        try:
            from backend.services.pattern_service import PatternService
            pattern_service = PatternService()
            
            pattern_id = suggestion.get("pattern_mapped_field_id")
            
            if pattern_id:
                pattern = pattern_service.get_pattern_by_id(pattern_id)
                if pattern and pattern.get("join_metadata"):
                    jm_str = pattern.get("join_metadata")
                    jm = json.loads(jm_str) if isinstance(jm_str, str) else jm_str
                    
                    # Extract from unionBranches (UNION_JOIN patterns)
                    for branch in jm.get("unionBranches", []):
                        bronze_table = branch.get("bronzeTable", {})
                        alias = bronze_table.get("alias", "").lower()
                        physical_name = bronze_table.get("physicalName", "")
                        if alias and physical_name:
                            # Extract just the table name from full path
                            table_name = physical_name.split(".")[-1]
                            alias_to_pattern_table[alias] = table_name
                    
                    # Also check for simple join patterns with main table
                    if "mainTable" in jm:
                        main_table = jm.get("mainTable", {})
                        alias = main_table.get("alias", "").lower()
                        physical_name = main_table.get("physicalName", "")
                        if alias and physical_name:
                            table_name = physical_name.split(".")[-1]
                            alias_to_pattern_table[alias] = table_name
                    
                    print(f"[VS Candidates] Extracted alias mapping from join_metadata: {alias_to_pattern_table}")
        except Exception as e:
            print(f"[VS Candidates] Could not extract alias mapping from join_metadata: {e}")
        
        # Also extract table aliases directly from pattern_sql using regex
        # This catches actual SQL aliases like "FROM MEMBER m" or "JOIN ENTITY e ON"
        # Always try this - join_metadata may have CTE names, but we need actual table aliases
        pattern_sql = suggestion.get("pattern_sql", "")
        if pattern_sql:
            try:
                import re
                # Match patterns like: FROM schema.table alias, JOIN schema.table alias ON
                # Pattern: (FROM|JOIN)\s+(\S+)\s+(\w+)\s+(ON|WHERE|JOIN|LEFT|RIGHT|INNER|,|$)
                table_alias_pattern = r'(?:FROM|JOIN)\s+([\w.]+)\s+(\w{1,3})\s*(?:ON|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|,|\)|$)'
                matches = re.findall(table_alias_pattern, pattern_sql, re.IGNORECASE)
                for full_table, alias in matches:
                    if alias.lower() not in ('on', 'where', 'and', 'or', 'as', 'join', 'left', 'right', 'inner'):
                        table_name = full_table.split(".")[-1].upper()
                        alias_to_pattern_table[alias.lower()] = table_name
                        print(f"[VS Candidates] Extracted from SQL: alias '{alias}' -> table '{table_name}'")
            except Exception as e:
                print(f"[VS Candidates] Error parsing pattern_sql for aliases: {e}")
        
        # First pass: extract table replacements from sql_changes
        for change in sql_changes:
            change_type = change.get("type", "")
            orig = str(change.get("original", ""))
            new = str(change.get("new", ""))
            
            if change_type == "table_replace" and orig and new:
                # Extract table name from full path (e.g., "oz_dev.bronze_dmes_de.t_re_base" -> "t_re_base")
                pattern_table = orig.split(".")[-1].upper()
                source_table = new.split(".")[-1].upper()
                table_mappings.append({
                    "pattern_table": orig,
                    "source_table": new
                })
        
        # Second pass: extract column replacements with table context
        for change in sql_changes:
            change_type = change.get("type", "")
            orig = str(change.get("original", ""))
            new = str(change.get("new", ""))
            
            if change_type in ("column_replace", "replaced") and orig and new:
                # Parse original: "b.ADR_STREET_1" -> alias=b, col=ADR_STREET_1
                if "." in orig:
                    orig_parts = orig.split(".")
                    alias = orig_parts[0].lower()
                    orig_col = orig_parts[-1].upper()
                else:
                    alias = "?"
                    orig_col = orig.upper()
                
                # Parse new: "RECIP_BASE.STREET_ADDR_1" or "r.STREET_ADDR_1"
                if "." in new:
                    new_parts = new.split(".")
                    new_table = new_parts[0].upper()
                    new_col = new_parts[-1].upper()
                else:
                    new_table = "?"
                    new_col = new.upper()
                
                # Initialize table group if needed
                if alias not in changes_by_table:
                    # Use alias_to_pattern_table if available (from join_metadata)
                    pattern_table_name = alias_to_pattern_table.get(alias, "")
                    changes_by_table[alias] = {
                        "alias": alias,
                        "pattern_table": pattern_table_name,  # From join_metadata
                        "source_table": new_table,
                        "changes": []
                    }
                
                # Add to changes for this table
                changes_by_table[alias]["changes"].append({
                    "original": orig,
                    "original_column": orig_col,
                    "new": new,
                    "new_column": new_col,
                    "new_table": new_table
                })
                
                # Track column usage (same column may appear in multiple tables)
                if orig_col not in column_usage:
                    column_usage[orig_col] = []
                column_usage[orig_col].append({
                    "alias": alias,
                    "original": orig,
                    "new": new,
                    "new_column": new_col,
                    "new_table": new_table
                })
        
        # Try to match aliases to table names from table_replace entries
        for tm in table_mappings:
            pattern_short = tm["pattern_table"].split(".")[-1].upper()
            source_short = tm["source_table"].split(".")[-1].upper()
            # Look for matching source table in changes_by_table
            for alias, group in changes_by_table.items():
                if group["source_table"].upper() == source_short:
                    group["pattern_table"] = tm["pattern_table"]
        
        # Mark which candidates were selected, now with table context
        # For each pattern column in VS candidates, check all usages
        for pattern_column, candidates in vs_candidates.items():
            pattern_col_upper = pattern_column.split(".")[-1].upper()
            
            # Get all usages of this column
            usages = column_usage.get(pattern_col_upper, [])
            
            for candidate in candidates:
                candidate_col = str(candidate.get("src_column_physical_name", "")).upper()
                candidate_table = str(candidate.get("src_table_physical_name", "")).upper()
                
                # Check if this candidate matches ANY usage
                candidate["was_selected"] = False
                candidate["selected_for_tables"] = []
                
                for usage in usages:
                    if usage["new_column"] == candidate_col:
                        candidate["was_selected"] = True
                        candidate["selected_for_tables"].append(usage["alias"])
        
        return {
            "suggestion_id": suggestion_id,
            "tgt_column": suggestion.get("tgt_column_physical_name"),
            "tgt_table": suggestion.get("tgt_table_physical_name"),
            "candidates_by_column": vs_candidates,
            "changes_by_table": changes_by_table,  # Grouped by table alias
            "table_mappings": table_mappings,      # Table-level replacements
            "column_usage": column_usage,          # Which tables use each column
            "alias_to_pattern_table": alias_to_pattern_table,  # Alias -> original pattern table name
            "has_candidates": bool(vs_candidates)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Suggestions Router] Error getting VS candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{suggestion_id}/llm-debug", response_model=dict)
async def get_suggestion_llm_debug(suggestion_id: int):
    """
    Get LLM debug info for a suggestion.
    
    Returns the full prompt sent to the LLM and its raw response.
    This is for admins/power users to debug AI decisions.
    
    Includes:
    - prompt_sent: The full prompt text
    - raw_response: The LLM's raw response
    - model_endpoint: Which model was used
    - latency_ms: How long the LLM call took
    - timestamp: When the call was made
    
    Use this to:
    - Debug why the AI generated certain SQL
    - Understand the AI's reasoning
    - Identify issues with prompts or responses
    """
    try:
        suggestion = await suggestion_service.get_suggestion_by_id(suggestion_id)
        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        # Parse the llm_debug_info JSON
        # Try both lowercase and uppercase column names (Databricks may return either)
        debug_info_raw = suggestion.get("llm_debug_info") or suggestion.get("LLM_DEBUG_INFO")
        debug_info = None
        
        # Debug: log what we found
        print(f"[LLM Debug] Suggestion keys: {list(suggestion.keys())}")
        print(f"[LLM Debug] debug_info_raw type: {type(debug_info_raw)}, length: {len(str(debug_info_raw)) if debug_info_raw else 0}")
        
        if debug_info_raw:
            import json
            try:
                debug_info = json.loads(debug_info_raw)
                print(f"[LLM Debug] Parsed successfully, keys: {list(debug_info.keys()) if isinstance(debug_info, dict) else 'not a dict'}")
            except Exception as parse_error:
                print(f"[LLM Debug] JSON parse error: {parse_error}")
                print(f"[LLM Debug] Raw value preview: {str(debug_info_raw)[:200]}")
        
        if not debug_info:
            return {
                "suggestion_id": suggestion_id,
                "has_debug_info": False,
                "message": "No LLM debug info available for this suggestion. This may be an older suggestion or a special case (auto-generated, hardcoded, etc.)"
            }
        
        return {
            "suggestion_id": suggestion_id,
            "has_debug_info": True,
            "tgt_column": suggestion.get("tgt_column_physical_name"),
            "tgt_table": suggestion.get("tgt_table_physical_name"),
            "debug_info": debug_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Suggestions Router] Error getting LLM debug info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
