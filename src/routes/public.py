from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import re

# Public router - no authentication required
router = APIRouter(
    prefix="/api/public",
    tags=["public"]
)

# Request/Response models
class SignupRequest(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    password: str
    
    @validator('firstName', 'lastName')
    def validate_names(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        if not re.match(r'^[a-zA-Z\s-]+$', v):
            raise ValueError('Name can only contain letters, spaces, and hyphens')
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

class SignupResponse(BaseModel):
    message: str
    user_id: Optional[str] = None
    email: str

class PublicController:
    """Controller for public routes - no authentication required"""
    
    @staticmethod
    async def get_root():
        """Root endpoint handler"""
        return {"message": "Hello World"}
    
    @staticmethod
    async def signup_user(user: SignupRequest) -> SignupResponse:
        """
        Handle user signup logic.
        """
        try:
            # TODO: Add your user creation logic here
            # Example:
            # 1. Check if user already exists in database
            # 2. Hash the password (use bcrypt or similar)
            # 3. Save user to database
            # 4. Send verification email
            # 5. Return user data
            
            print(f"Creating user: {user.firstName} {user.lastName} ({user.email})")
            
            # Placeholder logic - replace with actual implementation
            # Check if user exists
            # existing_user = await user_service.get_user_by_email(user.email)
            # if existing_user:
            #     raise HTTPException(status_code=400, detail="User already exists")
            
            # Hash password
            # hashed_password = hash_password(user.password)
            
            # Save to database
            # new_user = await user_service.create_user({
            #     "first_name": user.firstName,
            #     "last_name": user.lastName,
            #     "email": user.email,
            #     "password": hashed_password
            # })
            
            return SignupResponse(
                message="User registered successfully",
                user_id="temp_user_id_12345",  # Replace with actual user ID
                email=user.email
            )
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user account"
            )
    
    @staticmethod
    async def health_check():
        """Health check endpoint handler"""
        return {"status": "healthy"}
    
    @staticmethod
    async def app_info():
        """App info endpoint handler"""
        return {"app": "Zentra", "version": "1.0.0"}

@router.get("/")
async def root():
    return await PublicController.get_root()

@router.get("/signup")
async def signup(user: SignupRequest):
    return await PublicController.signup_user(user)

@router.get("/health")
async def health_check():
    return await PublicController.health_check()

@router.get("/info")
async def app_info():
    return await PublicController.app_info()