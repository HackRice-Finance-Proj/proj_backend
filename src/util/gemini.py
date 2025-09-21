import os
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

class GeminiClient:
    """Gemini AI client configuration and management"""
    
    def __init__(self):
        self.model = None
        self.is_configured = False
    
    def initialize(self) -> None:
        """Initialize Google Gemini API"""
        try:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                raise ValueError("GEMINI_API_KEY not found in .env file")
            
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.is_configured = True
            print("✅ Gemini API configured successfully")
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to configure Gemini API: {e}")
    
    def get_model(self):
        """Get the Gemini model instance"""
        if not self.is_configured or not self.model:
            raise HTTPException(status_code=500, detail="Gemini API not initialized")
        return self.model