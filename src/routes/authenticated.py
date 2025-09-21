from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.auth.supabase import authenticate, SupabaseUser
from typing import List, Union, Any
from fastapi import Body

from src.models.db import DatabaseConfig

# Request models
class UserAnswers(BaseModel):
    answers: Union[List[str], dict]
    metadata: dict = {}

# Controller functions
class AuthenticatedController:
    @staticmethod
    async def save_answers(db_config: DatabaseConfig, user: SupabaseUser, payload: UserAnswers) -> dict:
        users = db_config.get_users_collection()
        update = {
            "$set": {
                "answers": payload.answers,
                "answers_metadata": payload.metadata
            }
        }
        result = users.update_one({"supabase_user_id": user.id}, update, upsert=True)
        return {
            "message": "Answers saved successfully",
            "user_id": user.id,
            "upserted": bool(result.upserted_id)
        }


def create_authenticated_router(db_config: DatabaseConfig) -> APIRouter:
    router = APIRouter(
        prefix="/api/protected",
        tags=["protected"],
        dependencies=[Depends(authenticate)]
    )

    # JSON body submission
    @router.post("/submit-answers")
    async def submit_answers(
        payload: UserAnswers = Body(...),
        auth_user: SupabaseUser = Depends(authenticate),
    ):
        return await AuthenticatedController.save_answers(db_config, auth_user, payload)

    # profile sample
    @router.get("/profile")
    async def get_profile(auth_user: SupabaseUser = Depends(authenticate)):
        return {
            "user_id": auth_user.id,
            "email": auth_user.email,
            "profile": "User profile data"
        }

    return router