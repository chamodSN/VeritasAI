# common/security.py
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv
import os
from cryptography.fernet import Fernet
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET is not set in environment variables")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
fernet = Fernet(ENCRYPTION_KEY.encode())
limiter = Limiter(key_func=get_remote_address)
api_key_header = APIKeyHeader(name="Authorization")


def verify_token(token: str = Depends(api_key_header)) -> dict:
    if not token.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Invalid token format: Missing 'Bearer' prefix")
    raw_jwt = token.split(" ")[1]
    try:
        claims = jwt.decode(raw_jwt, JWT_SECRET, algorithms=["HS256"])
        claims['raw_jwt'] = raw_jwt  # Store raw token for downstream use
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def encrypt_data(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    return fernet.decrypt(encrypted_data.encode()).decode()
