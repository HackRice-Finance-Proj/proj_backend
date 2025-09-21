import os
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.auth.supabase import authenticate, SupabaseUser
from typing import List, Union, Optional
from fastapi import Body

from src.models.db import DatabaseConfig
from src.util.gemini import GeminiClient

# Request models
class UserAnswers(BaseModel):
    answers: Union[List[str], dict]
    metadata: dict = {}

class SaveCardRequest(BaseModel):
    card_id: Optional[str] = None
    name: Optional[str] = None

class ChatRequest(BaseModel):
    message: str

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

    @router.get("/saved-cards")
    async def get_saved_cards(
        card_id: Optional[str] = None,
        include_plans: bool = False,
        auth_user: SupabaseUser = Depends(authenticate),
    ):
        users = db_config.get_users_collection()
        user_doc = users.find_one(
            {"supabase_user_id": auth_user.id},
            {"saved_card_plans": 1, "_id": 0},
        ) or {}

        saved_card_plans = user_doc.get("saved_card_plans", {}) or {}

        # Optionally filter by card_id
        items = (
            {card_id_key: value} for card_id_key, value in saved_card_plans.items()
            if (not card_id or card_id_key == card_id)
        )

        # Build response using only saved_card_plans as source of truth.
        cards_out = []
        # Access to cards catalog for legacy entries that might not include 'card'
        cards_catalog = None
        for item in items:
            # item is a dict like {"<cid>": value}
            [(cid, value)] = item.items()
            if isinstance(value, dict) and "card" in value:
                card_snapshot = value.get("card") or {}
                plan_obj = value.get("plan") if include_plans else None
                out = dict(card_snapshot)
                if include_plans:
                    out["plan"] = plan_obj
                cards_out.append(out)
            else:
                # Legacy: value might be just the plan. Try to reconstruct snapshot from catalog.
                if cards_catalog is None:
                    try:
                        cards_catalog = load_cards()
                    except Exception:
                        cards_catalog = []
                snap = next((c for c in (cards_catalog or []) if c.get("id") == cid), None) or {"id": cid}
                snap_min = {
                    "id": snap.get("id"),
                    "name": snap.get("name"),
                    "issuer": snap.get("issuer"),
                    "card_type": snap.get("card_type"),
                    "annual_fee": snap.get("annual_fee"),
                    "apr_range": snap.get("apr_range"),
                    "image_url": snap.get("image_url"),
                }
                out = dict(snap_min)
                if include_plans:
                    out["plan"] = value
                cards_out.append(out)

        return {"saved_cards": cards_out}

    @router.post("/save-card")
    async def save_card(
        payload: SaveCardRequest = Body(...),
        auth_user: SupabaseUser = Depends(authenticate),
    ):
        users = db_config.get_users_collection()
        # 1) Lookup selected card
        cards = load_cards()
        card: Optional[dict] = None
        if payload.card_id:
            card = next((c for c in cards if c.get("id") == payload.card_id), None)
        if not card and payload.name:
            lname = payload.name.strip().lower()
            card = next((c for c in cards if str(c.get("name", "")).strip().lower() == lname), None)
        if not card:
            raise HTTPException(status_code=404, detail="Selected card not found (provide valid card_id or name)")

        # 2) Save minimal card snapshot to user's saved_cards (no duplicates)
        saved_snapshot = {
            "id": card.get("id"),
            "name": card.get("name"),
            "issuer": card.get("issuer"),
            "card_type": card.get("card_type"),
            "annual_fee": card.get("annual_fee"),
            "apr_range": card.get("apr_range"),
            "image_url": card.get("image_url"),
        }
        # No longer store a separate saved_cards array; plans object will hold card info

        # 3) Build a tailored guidance plan via Gemini using user's answers
        user_doc = users.find_one({"supabase_user_id": auth_user.id}) or {}
        answers = user_doc.get("answers", {})

        prompt = (
            "You are a credit card guidance assistant.\n"
            "Given the user's answers and the selected credit card details, return a single JSON object with: \n"
            "- name: string (card name)\n"
            "- issuer: string\n"
            "- category: string (use card_type)\n"
            "- annualFee: number (use annual_fee)\n"
            "- rewardRate: string (succinct summary from rewards_structure, e.g. '4% dining; 1% other')\n"
            "- keyFeatures: array of exactly 5 short bullet strings (10-20 words each)\n"
            "- spendingTip: one-sentence tip tailored to user answers\n"
            "- upgradePathTip: one-sentence tip about potential upgrade options\n"
            "- monthlyOptimizationTip: one-sentence tip to optimize monthly use\n"
            "- extraTips: array of exactly 3 short, specific tips (10-20 words)\n\n"
            "User Answers JSON: \n" + json.dumps(answers) + "\n\n"
            "Selected Card JSON: \n" + json.dumps(card) + "\n\n"
            "Only return JSON, no explanation or prose."
        )

        try:
            model = gemini.get_model()
            response = await model.generate_content_async(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            text = response.text.strip()
            plan = json.loads(text)

            # Validate shape
            required_keys = [
                "name", "issuer", "category", "annualFee", "rewardRate",
                "keyFeatures", "spendingTip", "upgradePathTip", "monthlyOptimizationTip", "extraTips"
            ]
            for k in required_keys:
                if k not in plan:
                    raise ValueError(f"Missing key: {k}")
            if not isinstance(plan.get("keyFeatures"), list) or len(plan["keyFeatures"]) != 5:
                raise ValueError("keyFeatures must have exactly 5 items")
            if not isinstance(plan.get("extraTips"), list) or len(plan["extraTips"]) != 3:
                raise ValueError("extraTips must have exactly 3 items")

            # 4) Persist under a single source of truth keyed by card id
            try:
                card_id = card.get("id") or saved_snapshot.get("id")
                if card_id:
                    users.update_one(
                        {"supabase_user_id": auth_user.id},
                        {"$set": {f"saved_card_plans.{card_id}": {"card": saved_snapshot, "plan": plan}}},
                        upsert=True,
                    )
            except Exception:
                # Non-fatal: still return the plan even if persistence fails
                pass

            return {
                "message": "Card saved and guidance generated",
                "saved_card": saved_snapshot,
                "plan": plan,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate plan: {e}")

    @router.post("/chat")
    async def chat(
        payload: ChatRequest = Body(...),
        auth_user: SupabaseUser = Depends(authenticate),
    ):
        users = db_config.get_users_collection()
        user_doc = users.find_one({"supabase_user_id": auth_user.id}) or {}

        profile = {
            "email": user_doc.get("email"),
            "firstName": user_doc.get("firstName"),
            "lastName": user_doc.get("lastName"),
        }
        answers = user_doc.get("answers", {}) or {}
        previous_recs = user_doc.get("gemini_recommendations", []) or []
        saved_card_plans = user_doc.get("saved_card_plans", {}) or {}

        # For completeness, include the catalog for any card-specific facts
        try:
            cards_catalog = load_cards()
        except Exception:
            cards_catalog = []

        prompt = (
            "You are a friendly, practical credit card advisor.\n"
            "Use ONLY the provided user context and the card catalog.\n"
            "Be specific, avoid generic fluff. If some detail is unknown, say so briefly.\n"
            "Prefer recommending from saved cards and prior recommendations when relevant.\n"
            "When listing tips, use concise bullets.\n\n"
            "User Profile JSON:\n" + json.dumps(profile) + "\n\n"
            "User Answers JSON:\n" + json.dumps(answers) + "\n\n"
            "Saved Card Plans JSON (per card_id => {card, plan}):\n" + json.dumps(saved_card_plans) + "\n\n"
            "Previous Recommendations JSON (array):\n" + json.dumps(previous_recs) + "\n\n"
            "Available Credit Cards Catalog JSON:\n" + json.dumps(cards_catalog) + "\n\n"
            "User Message:\n" + payload.message + "\n\n"
            "Now provide your best, tailored advice in plain text."
        )

        try:
            model = gemini.get_model()
            response = await model.generate_content_async(prompt)
            reply = (response.text or "").strip()
            if not reply:
                raise ValueError("Empty response from model")
            return {"reply": reply}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate advice: {e}")

    return router