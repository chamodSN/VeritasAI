from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from controller.orchestrator import orchestrate_query, get_case_alerts
from controller.auth_controller import verify_access_token
from model.user_model import store_query, get_user_queries, get_user_results
from model.courtlistener_advanced import courtlistener_advanced
from agents.pdf.pdf_service import pdf_processor
from common.responsible_ai import rai_framework
from common.encryption import secure_storage
from common.models import PDFUploadRequest
from datetime import datetime
from typing import List, Dict, Any, Optional
import base64

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

        # Store encrypted query in MongoDB (result is already stored encrypted by orchestrator)
        store_query(user_id, {"query": payload.query,
                    "timestamp": datetime.utcnow()})

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
    from common.encryption import secure_storage
    
    user_id = current_user["user_id"]
    encrypted_queries = get_user_queries(user_id)
    
    # Decrypt queries for display
    decrypted_queries = []
    for query in encrypted_queries:
        try:
            if "encrypted_data" in query and "encryption_version" in query:
                decrypted_data = secure_storage.retrieve_user_query({
                    "encrypted_data": query["encrypted_data"],
                    "encryption_version": query["encryption_version"]
                })
                decrypted_queries.append({
                    "_id": str(query["_id"]),
                    "user_id": query["user_id"],
                    "query": decrypted_data.get("query", ""),
                    "timestamp": query.get("timestamp", ""),
                    "type": decrypted_data.get("type", "user_query")
                })
        except Exception as e:
            # Skip corrupted queries
            continue
    
    return {"queries": decrypted_queries}


@router.get("/user/results")
async def get_user_results_history(current_user: dict = Depends(get_current_user)):
    """Get user's analysis results history."""
    from common.encryption import secure_storage
    
    user_id = current_user["user_id"]
    encrypted_results = get_user_results(user_id)
    
    # Decrypt results for display
    decrypted_results = []
    for result in encrypted_results:
        try:
            if "encrypted_data" in result and "encryption_version" in result:
                decrypted_data = secure_storage.retrieve_analysis_result({
                    "encrypted_data": result["encrypted_data"],
                    "encryption_version": result["encryption_version"]
                })
                decrypted_results.append({
                    "_id": str(result["_id"]),
                    "user_id": result["user_id"],
                    "timestamp": decrypted_data.get("timestamp"),
                    "result": decrypted_data.get("result", {})
                })
        except Exception as e:
            # Skip corrupted results
            continue
    
    return {"results": decrypted_results}


@router.get("/user/history")
async def get_user_history(current_user: dict = Depends(get_current_user)):
    """Get user's complete history including queries and results."""
    user_id = current_user["user_id"]
    
    # Get encrypted queries
    encrypted_queries = get_user_queries(user_id)
    queries_data = []
    for query in encrypted_queries:
        try:
            if "encrypted_data" in query and "encryption_version" in query:
                decrypted_data = secure_storage.retrieve_user_query({
                    "encrypted_data": query["encrypted_data"],
                    "encryption_version": query["encryption_version"]
                })
                queries_data.append({
                    "_id": str(query["_id"]),
                    "query": decrypted_data.get("query", ""),
                    "timestamp": query.get("timestamp", ""),
                    "user_id": query.get("user_id", ""),
                    "type": decrypted_data.get("type", "user_query")
                })
        except Exception as e:
            # Skip corrupted queries
            continue
    
    # Get encrypted results
    encrypted_results = get_user_results(user_id)
    results_data = []
    for result in encrypted_results:
        try:
            if "encrypted_data" in result and "encryption_version" in result:
                decrypted_data = secure_storage.retrieve_analysis_result({
                    "encrypted_data": result["encrypted_data"],
                    "encryption_version": result["encryption_version"]
                })
                results_data.append({
                    "_id": str(result["_id"]),
                    "user_id": result["user_id"],
                    "timestamp": decrypted_data.get("timestamp"),
                    "summary": decrypted_data.get("result", {}).get("summary", ""),
                    "confidence": decrypted_data.get("result", {}).get("confidence", 0),
                    "case_count": decrypted_data.get("result", {}).get("case_count", 0),
                    "issues_count": len(decrypted_data.get("result", {}).get("issues", [])),
                    "citations_count": len(decrypted_data.get("result", {}).get("citations", [])),
                    "result": decrypted_data.get("result", {})
                })
        except Exception as e:
            # Skip corrupted results
            continue
    
    return {
        "queries": queries_data,
        "results": results_data,
        "total_queries": len(queries_data),
        "total_results": len(results_data)
    }


@router.post("/pdf/upload")
async def upload_pdf(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Upload and analyze a PDF legal document"""
    try:
        user_id = current_user["user_id"]
        
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        content = await file.read()
        
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
        
        # Process PDF
        analysis_result = pdf_processor.analyze_legal_document(
            pdf_processor.extract_text_from_pdf(content)
        )
        
        if analysis_result["success"]:
            # Store encrypted PDF data
            encrypted_pdf = secure_storage.store_pdf_data(user_id, content, file.filename)
            
            # Run responsible AI checks on PDF analysis
            rai_checks = rai_framework.run_comprehensive_checks(
                f"PDF Analysis: {file.filename}", 
                analysis_result, 
                []
            )
            
            analysis_result["responsible_ai_checks"] = rai_checks
            analysis_result["encrypted_pdf_id"] = encrypted_pdf["encrypted_data"][:50] + "..."  # Truncated for response
            
            return analysis_result
        else:
            raise HTTPException(status_code=400, detail=analysis_result.get("error", "PDF analysis failed"))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pdf/analyze")
async def analyze_pdf_text(request: PDFUploadRequest, current_user: dict = Depends(get_current_user)):
    """Analyze PDF text content (base64 encoded)"""
    try:
        user_id = current_user["user_id"]
        
        # Decode base64 content
        pdf_content = base64.b64decode(request.content)
        
        # Process PDF
        analysis_result = pdf_processor.analyze_legal_document(
            pdf_processor.extract_text_from_pdf(pdf_content)
        )
        
        if analysis_result["success"]:
            # Store encrypted PDF data
            encrypted_pdf = secure_storage.store_pdf_data(user_id, pdf_content, request.filename)
            
            # Run responsible AI checks
            rai_checks = rai_framework.run_comprehensive_checks(
                f"PDF Analysis: {request.filename}", 
                analysis_result, 
                []
            )
            
            analysis_result["responsible_ai_checks"] = rai_checks
            analysis_result["encrypted_pdf_id"] = encrypted_pdf["encrypted_data"][:50] + "..."
            
            return analysis_result
        else:
            raise HTTPException(status_code=400, detail=analysis_result.get("error", "PDF analysis failed"))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rai/checks")
async def get_responsible_ai_info(current_user: dict = Depends(get_current_user)):
    """Get information about responsible AI framework"""
    return {
        "framework": "IBM Responsible AI Framework",
        "pillars": [
            {
                "name": "Explainability",
                "description": "Can users understand how AI derives conclusions?",
                "checks": ["Summary clarity", "Citation quality", "Confidence transparency"]
            },
            {
                "name": "Fairness", 
                "description": "Are results unbiased and representative?",
                "checks": ["Court diversity", "Temporal diversity", "Precedential balance", "Bias detection"]
            },
            {
                "name": "Robustness",
                "description": "Does the system handle edge cases gracefully?",
                "checks": ["Error handling", "Data quality", "Case count adequacy"]
            },
            {
                "name": "Transparency",
                "description": "Are processes and sources clear?",
                "checks": ["Data source identification", "Methodology transparency", "Timestamp tracking"]
            },
            {
                "name": "Privacy",
                "description": "Is user data protected appropriately?",
                "checks": ["PII detection", "Data encryption", "Retention policies"]
            }
        ],
        "implementation": "Custom implementation for legal research with legal-specific adaptations"
    }
