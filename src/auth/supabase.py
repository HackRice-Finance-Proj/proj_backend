from typing import Any, Dict, Optional
import json
import base64
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

security = HTTPBearer(auto_error=False)

class SupabaseUser(BaseModel):
    id: str
    email: Optional[str] = None
    role: Optional[str] = None
    raw_claims: Dict[str, Any]

def decode_jwt_payload(token: str) -> Dict[str, Any]:
    """
    Decode JWT payload without verification (FAST setup for development).
    WARNING: This does not verify the token signature! Only use for rapid prototyping.
    """
    try:
        # Split JWT (header.payload.signature)
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        
        # Decode payload (second part)
        payload = parts[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)
        decoded_bytes = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded_bytes.decode('utf-8'))
        
        return claims
    except Exception as e:
        raise ValueError(f"Failed to decode JWT: {e}")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> SupabaseUser:
    """
    Extract user info from Supabase JWT token (no verification for speed).
    Use this dependency to protect routes that need authentication.
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Missing Bearer token"
        )

    token = credentials.credentials
    try:
        claims = decode_jwt_payload(token)
        
        # Extract user info from Supabase JWT structure
        sub = claims.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token (no sub)"
            )

        return SupabaseUser(
            id=sub,
            email=claims.get("email"),
            role=claims.get("role"),
            raw_claims=claims,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Invalid token: {e}"
        )

# For compatibility with existing code
async def authenticate(credentials: HTTPAuthorizationCredentials = Depends(security)) -> SupabaseUser:
    """Alias for get_current_user to maintain compatibility with existing routes"""
    return await get_current_user(credentials)