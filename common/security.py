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
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
fernet = Fernet(ENCRYPTION_KEY.encode())
limiter = Limiter(key_func=get_remote_address)
api_key_header = APIKeyHeader(name="Authorization")

def verify_token(token: str):
    try:
        payload = jwt.decode(token.replace("Bearer ", ""), JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def encrypt_data(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    return fernet.decrypt(encrypted_data.encode()).decode()