import os
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.auth.supabase import authenticate, SupabaseUser
from typing import List, Union
from fastapi import Body

from src.models.db import DatabaseConfig
from src.util.gemini import GeminiClient

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


def create_authenticated_router(db_config: DatabaseConfig, gemini: GeminiClient) -> APIRouter:
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

    # Utilities for recommendations
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    CARDS_PATH = os.path.join(PROJECT_ROOT, "credit_cards.json")

    def load_cards() -> List[dict]:
        try:
            with open(CARDS_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load cards data: {e}")

    @router.get("/recommendations")
    async def get_recommendations(auth_user: SupabaseUser = Depends(authenticate)):
        users = db_config.get_users_collection()
        user_doc = users.find_one({"supabase_user_id": auth_user.id})
        if not user_doc or "answers" not in user_doc:
            raise HTTPException(status_code=404, detail="User answers not found. Please submit answers first.")

        answers = user_doc.get("answers", {})
        cards = load_cards()

        # Build prompt for Gemini
        prompt = (
            "You are a credit card recommendation assistant. "
            "Given the user's answers and the list of available credit cards, "
            "return exactly 3 recommendations as a JSON array.\n\n"
            f"User Answers JSON: {json.dumps(answers)}\n\n"
            f"Available Credit Cards JSON: {json.dumps(cards)}\n\n"
            "Response format (JSON array of 3 objects). Keys and rules: \n"
            "- name: string (card name)\n"
            "- imageUrl: string (use image_url from data)\n"
            "- interestRate: string (use apr_range from data)\n"
            "- description: string (2-3 concise sentences explaining why the card fits the user's answers)\n"
            "- bullets: array of exactly 4 short bullet strings, each 5-7 words\n\n"
            "Only return the JSON array. No prose."
        )

        try:
            model = gemini.get_model()
            response = await model.generate_content_async(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )

            text = response.text.strip()
            data = json.loads(text)

            # Basic validation
            if not isinstance(data, list) or len(data) != 3:
                raise ValueError("Model did not return exactly 3 items")
            for item in data:
                for key in ["name", "imageUrl", "interestRate", "description", "bullets"]:
                    if key not in item:
                        raise ValueError(f"Missing key: {key}")
                if not isinstance(item["bullets"], list) or len(item["bullets"]) != 4:
                    raise ValueError("bullets must be an array of exactly 4 items")

            # Store recommendations on user document for later retrieval
            users.update_one(
                {"supabase_user_id": auth_user.id},
                {"$set": {"gemini_recommendations": data}}
            )

            print(data)

            return data
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {e}")

    # profile sample
    @router.get("/profile")
    async def get_profile(auth_user: SupabaseUser = Depends(authenticate)):
        return {
            "user_id": auth_user.id,
            "email": auth_user.email,
            "profile": "User profile data"
        }

    return router