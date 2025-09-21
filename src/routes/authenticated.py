from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from src.auth.supabase import authenticate, SupabaseUser
from typing import List

# Create router with authentication middleware applied to ALL routes
router = APIRouter(
    prefix="/api/protected",
    tags=["protected"],
    dependencies=[Depends(authenticate)]  # This makes ALL routes in this router authenticated!
)

class UserAnswers(BaseModel):
    answers: List[str]
    metadata: dict = {}

@router.post("/submit-answers")
async def submit_answers(user_data: UserAnswers, auth_user: SupabaseUser = Depends(authenticate)):
    try:
        user_data_dict = user_data.model_dump() # FIXME: Keep an eye on this
        user_data_dict["authenticated_user_id"] = auth_user.id
        
        # Your database logic here
        return {"message": "Answers saved successfully", "user_id": auth_user.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save data: {e}")

@router.get("/recommendation/{user_id}")
async def get_recommendation(user_id: str, auth_user: SupabaseUser = Depends(authenticate)):
    # Ensure user can only access their own data
    if user_id != auth_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {"recommendation": "Your personalized recommendation", "user_id": auth_user.id}

@router.get("/profile")
async def get_profile(auth_user: SupabaseUser = Depends(authenticate)):
    return {
        "user_id": auth_user.id,
        "email": auth_user.email,
        "profile": "User profile data"
    }