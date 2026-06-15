from datetime import datetime,timezone,timedelta
from typing import Any
import jwt
from fastapi import HTTPException, status

from config import settings
from logging import logger

def create_access_token(user_id:str, email:str) -> str:
    
    now = datetime.now(tz=timezone.utc)

    payload:dict[str,Any] = {
        "sub":user_id,
        "email":email,
        "iat":now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token:str) ->dict[str,Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        if "sub" not in payload:
            raise ValueError("Invalid token: missing subject")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired", 
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError as exc:
        logger.warning("invalid_jwt", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
