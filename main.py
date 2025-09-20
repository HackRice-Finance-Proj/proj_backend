from fastapi import FastAPI, HTTPException, Depends # type: ignore
from pydantic import BaseModel # type: ignore
from pymongo import MongoClient # type: ignore
from dotenv import load_dotenv # type: ignore
import google.generativeai as genai # type: ignore
import json
import os

# --- Auth0 Libraries & Configuration ---
from fastapi_auth0 import Auth0, Auth0User #type: ignore

load_dotenv()

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE")

if not AUTH0_DOMAIN or not AUTH0_API_AUDIENCE:
    raise ValueError("Auth0 environment variables not set.")

auth = Auth0(
    domain=AUTH0_DOMAIN,
    api_audience=AUTH0_API_AUDIENCE,
    scopes={
        "openid": "OpenID Connect", 
        "profile": "User profile information", 
        "email": "User email address"
    }
)

# --- Other Configurations & Setup ---
app = FastAPI()

# Load API keys from .env
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")
genai.configure(api_key=gemini_api_key)

# Connect to MongoDB
try:
    mongo_uri = os.getenv("MONGODB_URI")
    client = MongoClient(mongo_uri)
    db = client.get_database("credit_card_db")
    users = db.get_collection("users")
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to connect to MongoDB: {e}")

# Load credit card data from the JSON file
try:
    with open('credit_cards.json', 'r') as file:
        cards_data = json.load(file)
except FileNotFoundError:
    raise HTTPException(status_code=500, detail="credit_cards.json file not found.")

# --- Pydantic Models for Data Validation ---
class UserAnswers(BaseModel):
    user_id: str
    answers: dict

# --- Existing API Endpoints ---
@app.post("/submit-answers")
async def submit_answers(user_data: UserAnswers):
    """
    Receives and stores user answers in MongoDB.
    """
    try:
        users.insert_one(user_data.dict())
        return {"message": "Answers saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save data: {e}")

@app.get("/recommendation/{user_id}")
async def get_recommendation(user_id: str):
    """
    Retrieves user answers, gets a Gemini recommendation, and returns the result.
    """
    user_doc = users.find_one({"user_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found.")

    prompt_content = f"""
    The user's answers are: {json.dumps(user_doc['answers'])}
    The list of available credit cards is: {json.dumps(cards_data)}
    Based on the user's answers, find the three single best credit cards and return a JSON array of three objects. Each object should have the following keys:
    - "rank": An integer from 1 to 3, where 1 is the best recommendation.
    - "name": The name of the credit card.
    - "photo_url": The URL for the credit card's photo.
    - "description": A detailed, 2-3 sentence explanation of why this card is the best recommendation for the user, referencing their answers.
    - "acquisition_steps": A clear, numbered list of steps for how the user can apply for and acquire the credit card.

    Ensure the response is a valid JSON object.
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(
            prompt_content,
            generation_config={"response_mime_type": "application/json"}
        )

        recommended_card = json.loads(response.text.strip())
        # --- Add recommended cards to MongoDB ---
        users.update_one(
            {"user_id": user_id},
            {"$set": {"gemini_recommendations": recommended_card}}
        )
        return recommended_card
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API call failed: {e}")

# --- NEW Auth0 Endpoints ---
@app.get("/api/public")
async def public_endpoint():
    """
    This endpoint does not require authentication.
    """
    return {"message": "Hello from a public endpoint!"}

@app.get("/api/private")
async def private_endpoint(auth_user: Auth0User = Depends(auth.get_user)):
    """
    This endpoint requires a valid JWT token.
    auth_user will contain the decoded user info from the token.
    """
    return {
        "message": f"Hello from a private endpoint! You are authenticated as {auth_user.email}.",
        "user_info": auth_user.dict()
    }