from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from controller.orchestrator import orchestrate_query
from controller.auth_controller import verify_access_token
from model.user_model import store_query, store_result
from datetime import datetime

router = APIRouter()
security = HTTPBearer()


class QueryPayload(BaseModel):
    query: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user."""
    try:
        user_info = verify_access_token(credentials.credentials)
        return user_info
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/query")
async def handle_query(payload: QueryPayload, current_user: dict = Depends(get_current_user)):
    """Handle legal queries with authentication."""
    try:
        user_id = current_user["user_id"]
        result = orchestrate_query(payload.query, user_id)

        # Store query and result in MongoDB
        store_query(user_id, {"query": payload.query,
                    "timestamp": datetime.utcnow()})
        store_result(user_id, result)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Get API status."""
    return {"status": "running", "service": "VeritasAI API"}


@router.get("/user/queries")
async def get_user_queries(current_user: dict = Depends(get_current_user)):
    """Get user's query history."""
    from model.user_model import get_user_queries
    user_id = current_user["user_id"]
    queries = get_user_queries(user_id)
    return {"queries": queries}


@router.get("/user/profile")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get user profile information."""
    from model.user_model import get_user_by_id
    user_id = current_user["user_id"]
    user_profile = get_user_by_id(user_id)
    if user_profile:
        # Remove sensitive data
        user_profile.pop('_id', None)
        return user_profile
    else:
        raise HTTPException(status_code=404, detail="User not found")
