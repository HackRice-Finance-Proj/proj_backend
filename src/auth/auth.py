from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_auth0 import Auth0, Auth0User
import os
from dotenv import load_dotenv

load_dotenv()

# Auth0 Configuration
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

security = HTTPBearer()

# Express-like middleware function
async def authenticate(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Auth0User:
    """
    Express-like authentication middleware.
    Use this as a dependency in any router to make all routes in that router authenticated.
    """
    try:
        token = credentials.credentials
        user = await auth.get_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

# Helper to get current user in route handlers
def get_current_user(request: Request) -> Auth0User:
    """Get authenticated user from request state (when using router dependencies)"""
    return request.state.user