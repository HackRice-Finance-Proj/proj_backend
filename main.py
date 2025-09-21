from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.models.db import DatabaseConfig
from src.util.gemini import GeminiClient
from src.routes.public import create_public_router
from src.routes.authenticated import create_authenticated_router

load_dotenv()

db_config = DatabaseConfig()
gemini_client = GeminiClient()

db_config.initialize_mongodb()
gemini_client.initialize()

app = FastAPI()

# Fix CORS middleware - more permissive for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Pass dependencies when creating router
# api/public
public_router = create_public_router(db_config)
app.include_router(public_router)

# api/protected
protected_router = create_authenticated_router(db_config, gemini_client)
app.include_router(protected_router)



# # --- Other Configurations & Setup ---
# app = FastAPI()

# # Load API keys from .env
# gemini_api_key = os.getenv("GEMINI_API_KEY")
# if not gemini_api_key:
#     raise ValueError("GEMINI_API_KEY not found in .env file")
# genai.configure(api_key=gemini_api_key)

# # Connect to MongoDB
# try:
#     mongo_uri = os.getenv("MONGODB_URI")
#     client = MongoClient(mongo_uri)
#     db = client.get_database("credit_card_db")
#     users = db.get_collection("users")
# except Exception as e:
#     raise HTTPException(status_code=500, detail=f"Failed to connect to MongoDB: {e}")

# # Load credit card data from the JSON file
# try:
#     with open('credit_cards.json', 'r') as file:
#         cards_data = json.load(file)
# except FileNotFoundError:
#     raise HTTPException(status_code=500, detail="credit_cards.json file not found.")

# # --- Pydantic Models for Data Validation ---
# class SavedCard(BaseModel):
#     name: str
#     photo_url: str
#     description: str
#     acquisition_steps: str

# --- API Endpoints ---
# @app.post("/api/submit-answers")
# async def submit_answers(answers: dict, auth_user: Auth0User = Depends(auth.get_user)):
#     """
#     Receives and stores user answers in MongoDB, or updates existing ones.
#     """
#     user_id = auth_user.id
#     try:
#         users.update_one(
#             {"user_id": user_id},
#             {"$set": {"answers": answers}},
#             upsert=True
#         )
#         return {"message": "Answers saved successfully"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to save data: {e}")

# @app.get("/api/recommendations/generate")
# async def get_recommendation(auth_user: Auth0User = Depends(auth.get_user)):
#     """
#     Retrieves user answers, gets a Gemini recommendation, and returns the result.
#     """
#     user_id = auth_user.id
#     user_doc = users.find_one({"user_id": user_id})
#     if not user_doc or "answers" not in user_doc:
#         raise HTTPException(status_code=404, detail="User answers not found.")

#     prompt_content = f"""
#     The user's answers are: {json.dumps(user_doc['answers'])}
#     The list of available credit cards is: {json.dumps(cards_data)}
#     Based on the user's answers, find the three single best credit cards and return a JSON array of three objects. Each object should have the following keys:
#     - "rank": An integer from 1 to 3, where 1 is the best recommendation.
#     - "name": The name of the credit card.
#     - "photo_url": The URL for the credit card's photo.
#     - "description": A detailed, 2-3 sentence explanation of why this card is the best recommendation for the user, referencing their answers.
#     - "acquisition_steps": A clear, numbered list of steps for how the user can apply for and acquire the credit card. **Format this as a single string.**

#     Ensure the response is a valid JSON object.
#     """

#     try:
#         model = genai.GenerativeModel('gemini-1.5-flash')
#         response = await model.generate_content_async(
#             prompt_content,
#             generation_config={"response_mime_type": "application/json"}
#         )

#         recommended_card = json.loads(response.text.strip())
#         # --- Add recommended cards to MongoDB ---
#         users.update_one(
#             {"user_id": user_id},
#             {"$set": {"gemini_recommendations": recommended_card}}
#         )
#         return recommended_card
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Gemini API call failed: {e}")

# @app.post("/api/onboard-user")
# async def onboard_user(auth_user: Auth0User = Depends(auth.get_user)):
#     """
#     Creates a new user document in MongoDB on the first login.
#     """
#     user_id = auth_user.id
#     email = auth_user.email
    
#     # Check if the user document already exists
#     existing_user = users.find_one({"user_id": user_id})

#     if existing_user:
#         return {"message": "User already exists."}
    
#     # Create a new document for the user
#     new_user_data = {
#         "user_id": user_id,
#         "email": email,
#         "answers": {},
#         "gemini_recommendations": [],
#         "saved_cards": []
#     }
    
#     try:
#         users.insert_one(new_user_data)
#         return {"message": "User onboarded successfully!"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to onboard user: {e}")

# # --- Save Card ---
# @app.post("/api/save-card")
# async def save_card(card_info: SavedCard, auth_user: Auth0User = Depends(auth.get_user)):
#     """
#     Adds a selected credit card (from the Gemini response) to the user's saved_cards list in MongoDB.
#     """
#     user_id = auth_user.id

#     try:
#         # Check if the user document exists
#         result = users.update_one(
#             {"user_id": user_id},
#             {"$addToSet": {"saved_cards": card_info.dict()}}
#         )
#         if result.matched_count == 0:
#             raise HTTPException(status_code=404, detail="User not found. Please onboard the user first.")
        
#         return {"message": "Card added to saved list successfully."}
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to save card: {e}")

# # --- Retrieve Saved Cards ---
# @app.get("/api/saved-cards")
# async def get_saved_cards(auth_user: Auth0User = Depends(auth.get_user)):
#     """
#     Retrieves the list of saved credit cards for the authenticated user.
#     """
#     user_id = auth_user.id
#     user_doc = users.find_one({"user_id": user_id})

#     if not user_doc:
#         raise HTTPException(status_code=404, detail="User not found.")

#     return user_doc.get("saved_cards", [])

# # --- Retrieve Gemini Recommendations ---
# @app.get("/api/recommendations")
# async def get_recommendations(auth_user: Auth0User = Depends(auth.get_user)):
#     """
#     Retrieves the Gemini recommendations for the authenticated user.
#     """
#     user_id = auth_user.id
#     user_doc = users.find_one({"user_id": user_id})

#     if not user_doc:
#         raise HTTPException(status_code=404, detail="User not found.")

#     return user_doc.get("gemini_recommendations", [])

# # --- Auth0 Endpoints ---
# @app.get("/api/public")
# async def public_endpoint():
#     """
#     This endpoint does not require authentication.
#     """
#     return {"message": "Hello from a public endpoint!"}

# @app.get("/api/private")
# async def private_endpoint(auth_user: Auth0User = Depends(auth.get_user)):
#     """
#     This endpoint requires a valid JWT token.
#     auth_user will contain the decoded user info from the token.
#     """
#     return {
#         "message": f"Hello from a private endpoint! You are authenticated as {auth_user.email}.",
#         "user_info": auth_user.dict()
#     }