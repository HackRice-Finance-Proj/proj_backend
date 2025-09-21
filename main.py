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