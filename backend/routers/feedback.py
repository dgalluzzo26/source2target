"""
Feedback API endpoints for AI suggestion tracking.

Allows users to accept/reject AI suggestions for pattern learning.
"""
from fastapi import APIRouter, HTTPException, Body
from backend.models.mapping_v2 import MappingFeedbackV2, MappingFeedbackCreateV2
from backend.services.feedback_service import FeedbackService

router = APIRouter(prefix="/api/v2/feedback", tags=["Feedback V2"])

feedback_service = FeedbackService()


@router.post("/", response_model=MappingFeedbackV2)
async def create_feedback(feedback_data: MappingFeedbackCreateV2 = Body(...)):
    """
    Submit feedback on an AI mapping suggestion.
    
    Captures user acceptance or rejection of AI suggestions to improve
    future recommendations through pattern learning.
    
    **Feedback Status Values:**
    - `ACCEPTED`: User accepted the AI suggestion
    - `REJECTED`: User rejected the AI suggestion
    - `PENDING`: Suggestion not yet reviewed
    
    **Example Request:**
    ```json
    {
      "src_table_name": "T_MEMBER",
      "src_table_physical_name": "t_member",
      "src_column_name": "FIRST_NAME",
      "src_column_physical_name": "first_name",
      "suggested_tgt_table_name": "slv_member",
      "suggested_tgt_column_name": "full_name",
      "feedback_status": "ACCEPTED",
      "user_comment": "Good match, used it",
      "ai_confidence_score": 0.95,
      "ai_reasoning": "Strong semantic match",
      "feedback_by": "john.doe@example.com"
    }
    ```
    
    Args:
        feedback_data: MappingFeedbackCreateV2 with feedback details
    
    Returns:
        MappingFeedbackV2 model with created feedback
    
    Raises:
        HTTPException 400: If validation fails
        HTTPException 500: If database operation fails
    """
    try:
        result = await feedback_service.create_feedback(feedback_data)
        print(f"[Feedback API] Created feedback: {feedback_data.feedback_status}")
        return result
        
    except ValueError as e:
        print(f"[Feedback API] Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[Feedback API] Error creating feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

