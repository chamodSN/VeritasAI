from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.responses import RedirectResponse
from controller.auth_controller import oauth, get_user_info, create_access_token, verify_access_token
from model.user_model import store_user, get_user_by_email
import uuid
from datetime import datetime

router = APIRouter()
security = HTTPBearer()


@router.get("/auth/google")
async def google_login(request: Request):
    """Initiate Google OAuth login."""
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback", name="google_callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback and create JWT token."""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = await get_user_info(token['access_token'])

        # Generate unique user ID
        user_id = str(uuid.uuid4())

        # Store user in MongoDB
        user_data = {
            "user_id": user_id,
            "email": user_info.get('email'),
            "name": user_info.get('name'),
            "picture": user_info.get('picture'),
            "google_id": user_info.get('id'),
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow()
        }

        # Check if user already exists
        existing_user = get_user_by_email(user_info.get('email'))
        if existing_user:
            user_id = existing_user['user_id']
            user_data['last_login'] = datetime.utcnow()

        store_user(user_data)

        # Create JWT token
        access_token = create_access_token(user_id, user_info.get('email'))

        # Redirect to frontend with token
        frontend_url = f"http://localhost:3000/auth/callback?token={access_token}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/auth/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user info."""
    try:
        user_info = verify_access_token(credentials.credentials)
        return {"user_id": user_info["user_id"], "email": user_info["email"]}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/auth/logout")
async def logout():
    """Logout user (client-side token removal)."""
    return {"message": "Logged out successfully"}
