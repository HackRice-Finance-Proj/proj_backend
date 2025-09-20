from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
import google.generativeai as genai
import json
import os

# --- Configuration & Setup ---
load_dotenv()
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
    users = db.get_collection("user_answers")
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to connect to MongoDB: {e}")

# Load credit card data from the JSON file
try:
    with open('credit_cards.json', 'r') as file:
        cards_data = json.load(file)
except FileNotFoundError:
    raise HTTPException(status_code=500, detail="credit_cards.json file not found.")

# --- Pydantic Model for Data Validation ---
class UserAnswers(BaseModel):
    user_id: str
    answers: dict

# --- API Endpoints ---
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
    # 1. Retrieve user data from MongoDB
    user_doc = users.find_one({"user_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found.")

    # 2. Prepare the prompt for Gemini
    prompt_content = f"""
    You are a credit card expert. Your task is to recommend the single best credit card
    from a list based on a user's survey answers.

    Instructions:
    - Analyze the user's answers and find the best match from the card list.
    - Your response must be the full JSON object of the single recommended card and nothing else.

    User Answers: {json.dumps(user_doc['answers'])}

    Credit Cards: {json.dumps(cards_data)}
    """

    # 3. Call the Gemini API
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt_content)
        # Assuming the response is a valid JSON string
        recommended_card = json.loads(response.text.strip())
        return recommended_card
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API call failed: {e}")