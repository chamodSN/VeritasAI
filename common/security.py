import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from common.config import Config
from common.logging import logger

def verify_token(token: str) -> str:
    """Verify JWT token and return user_id"""
    try:
        if not Config.JWT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT secret not configured"
            )
        
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )

def create_token(user_id: str, expires_delta: timedelta = None) -> str:
    """Create JWT token for user"""
    if not Config.JWT_SECRET:
        raise ValueError("JWT secret not configured")
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    payload = {
        "user_id": user_id,
        "exp": expire
    }
    
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")
