from authlib.integrations.starlette_client import OAuth
from common.config import Config
import jwt
import secrets
from datetime import datetime, timedelta

oauth = OAuth()
oauth.register(
    name='google',
    client_id=Config.GOOGLE_CLIENT_ID,
    client_secret=Config.GOOGLE_CLIENT_SECRET,
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    access_token_url='https://oauth2.googleapis.com/token',
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
    client_kwargs={'scope': 'openid email profile'},
)

# JWT Configuration
JWT_SECRET = Config.JWT_SECRET if hasattr(
    Config, 'JWT_SECRET') else secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


def create_access_token(user_id: str, email: str) -> str:
    """Create JWT access token for authenticated user."""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> dict:
    """Verify JWT access token and return user info."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"user_id": payload["user_id"], "email": payload["email"]}
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


async def get_user_info(access_token: str):
    userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
    headers = {'Authorization': f'Bearer {access_token}'}
    # Use requests or httpx to get user info
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(userinfo_url, headers=headers)
    return response.json()
