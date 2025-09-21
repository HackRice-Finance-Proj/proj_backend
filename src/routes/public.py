from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import re
from bson import ObjectId

# Import your database configuration
from src.models.db import DatabaseConfig

# Public router - no authentication required
router = APIRouter(
    prefix="/api/public",
    tags=["public"]
)

# Request/Response models for Supabase integration
class OnboardUserRequest(BaseModel):
    user_id: str  # Supabase user ID
    email: EmailStr
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    
    @validator('firstName', 'lastName', pre=True)
    def validate_names(cls, v):
        if v is None:
            return v
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        if not re.match(r'^[a-zA-Z\s-]+$', v):
            raise ValueError('Name can only contain letters, spaces, and hyphens')
        return v.strip()

class OnboardUserResponse(BaseModel):
    message: str
    user_id: str
    email: str
    is_new_user: bool

class PublicController:
    """Controller for public routes - no authentication required"""
    
    @staticmethod
    async def get_root():
        """Root endpoint handler"""
        return {"message": "Hello World"}
    
    @staticmethod
    async def onboard_user(user: OnboardUserRequest, db_config: DatabaseConfig) -> OnboardUserResponse:
        """
        Onboard a user who has already authenticated with Supabase.
        This creates or updates their profile in our MongoDB database.
        """
        try:
            users_collection = db_config.get_users_collection()
            
            # 1. Check if user already exists in our database
            existing_user = users_collection.find_one({"supabase_user_id": user.user_id})
            
            if existing_user:
                # User exists, optionally update their info
                update_data = {}
                if user.firstName:
                    update_data["firstName"] = user.firstName
                if user.lastName:
                    update_data["lastName"] = user.lastName
                
                if update_data:
                    users_collection.update_one(
                        {"supabase_user_id": user.user_id},
                        {"$set": update_data}
                    )
                
                print(f"✅ Existing user logged in: {user.email}")
                return OnboardUserResponse(
                    message="User profile updated successfully",
                    user_id=user.user_id,
                    email=user.email,
                    is_new_user=False
                )
            
            # 2. Create new user document (no password needed - Supabase handles auth)
            new_user_data = {
                "supabase_user_id": user.user_id,  # Store Supabase ID
                "email": user.email,
                "firstName": user.firstName,
                "lastName": user.lastName,
                "answers": {},
                "gemini_recommendations": [],
                "saved_cards": [],
                "created_at": ObjectId().generation_time,
                "is_active": True
            }
            
            # 3. Save user to database
            result = users_collection.insert_one(new_user_data)
            
            if not result.inserted_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user profile"
                )
            
            print(f"✅ New user onboarded: {user.firstName} {user.lastName} ({user.email})")
            
            # 4. Return user data
            return OnboardUserResponse(
                message="User onboarded successfully",
                user_id=user.user_id,
                email=user.email,
                is_new_user=True
            )
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"❌ User onboarding error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to onboard user"
            )
    
    @staticmethod
    async def health_check():
        """Health check endpoint handler"""
        return {"status": "healthy"}
    
    @staticmethod
    async def app_info():
        """App info endpoint handler"""
        return {"app": "Zentra", "version": "1.0.0"}

# @router.get("/")
# async def root():
#     return await PublicController.get_root()

# @router.post("/signup", status_code=status.HTTP_201_CREATED)
# async def signup(user: SignupRequest, db_config: DatabaseConfig = Depends(get_db_config)):
#     return await PublicController.signup_user(user, db_config)

# @router.get("/health")
# async def health_check():
#     return await PublicController.health_check()

# @router.get("/info")
# async def app_info():
#     return await PublicController.app_info()

def create_public_router(db_config: DatabaseConfig) -> APIRouter:
    """Factory function to create router with dependencies"""
    
    router = APIRouter(prefix="/api/public", tags=["public"])
    
    def get_db_config():
        return db_config  # Closure over the passed db_config
    
    @router.post("/onboard", status_code=status.HTTP_201_CREATED)
    async def onboard_user(user: OnboardUserRequest, db: DatabaseConfig = Depends(get_db_config)):
        """
        Onboard a user who has authenticated with Supabase.
        Call this endpoint after user signs up/logs in on frontend.
        """
        return await PublicController.onboard_user(user, db)
    
    @router.get("/health")
    async def health_check():
        """Health check endpoint"""
        return await PublicController.health_check()
    
    @router.get("/info")
    async def app_info():
        """Application information"""
        return await PublicController.app_info()
    
    return router