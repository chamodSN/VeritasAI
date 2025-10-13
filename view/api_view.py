from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from controller.orchestrator import orchestrate_query, get_case_alerts
from controller.auth_controller import verify_access_token
from model.user_model import store_query, store_result
from model.courtlistener_advanced import courtlistener_advanced
from datetime import datetime
from typing import List, Dict, Any, Optional

router = APIRouter()
security = HTTPBearer()


class QueryPayload(BaseModel):
    query: str


class AlertPayload(BaseModel):
    query: str
    name: str
    rate: str = "dly"


class CaseAnalysisPayload(BaseModel):
    case_ids: List[str]


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user."""
    try:
        user_info = verify_access_token(credentials.credentials)
        return user_info
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        ) from e


@router.post("/query")
async def handle_query(payload: QueryPayload, current_user: dict = Depends(get_current_user)):
    """Handle legal queries with authentication using CourtListener API."""
    try:
        user_id = current_user["user_id"]
        result = orchestrate_query(payload.query, user_id)

        # Store query and result in MongoDB
        store_query(user_id, {"query": payload.query,
                    "timestamp": datetime.utcnow()})
        store_result(user_id, result)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/alerts/create")
async def create_alert(payload: AlertPayload, current_user: dict = Depends(get_current_user)):
    """Create a CourtListener alert for new cases."""
    try:
        user_id = current_user["user_id"]
        result = get_case_alerts(payload.query, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/alerts")
async def get_alerts(current_user: dict = Depends(get_current_user)):
    """Get all alerts for the authenticated user."""
    try:
        alerts = courtlistener_advanced.get_user_alerts()
        return {"alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/alerts/{alert_uri:path}")
async def delete_alert(alert_uri: str, current_user: dict = Depends(get_current_user)):
    """Delete a specific alert."""
    try:
        success = courtlistener_advanced.delete_alert(alert_uri)
        if success:
            return {"message": "Alert deleted successfully"}
        else:
            raise HTTPException(
                status_code=400, detail="Failed to delete alert")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courts/statistics")
async def get_court_statistics(current_user: dict = Depends(get_current_user)):
    """Get court statistics and information."""
    try:
        stats = courtlistener_advanced.get_court_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{case_id}/opinions")
async def get_case_opinions(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get opinions for a specific case."""
    try:
        opinions = courtlistener_advanced.get_case_opinions(case_id)
        return {"opinions": opinions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{case_id}/citations")
async def get_case_citations(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get citations for a specific case."""
    try:
        citations = courtlistener_advanced.get_case_citations(case_id)
        return citations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{case_id}/docket")
async def get_case_docket(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get docket entries for a specific case."""
    try:
        docket_entries = courtlistener_advanced.get_docket_entries(case_id)
        return {"docket_entries": docket_entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{case_id}/track")
async def track_case_updates(case_id: str, current_user: dict = Depends(get_current_user)):
    """Track updates for a specific case."""
    try:
        updates = courtlistener_advanced.track_case_updates(case_id)
        return updates
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cases/bulk-analysis")
async def bulk_case_analysis(payload: CaseAnalysisPayload, current_user: dict = Depends(get_current_user)):
    """Perform bulk analysis on multiple cases."""
    try:
        analysis = courtlistener_advanced.bulk_case_analysis(payload.case_ids)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Get API status."""
    return {
        "status": "running",
        "service": "VeritasAI API",
        "data_source": "CourtListener API v4",
        "features": [
            "Case Search",
            "Alert Creation",
            "Opinion Retrieval",
            "Citation Analysis",
            "Docket Tracking",
            "Bulk Case Analysis"
        ]
    }


@router.get("/user/queries")
async def get_user_query_history(current_user: dict = Depends(get_current_user)):
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
