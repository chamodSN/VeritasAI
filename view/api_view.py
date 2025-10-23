from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from controller.orchestrator import orchestrate_query, orchestrate_query_with_text, get_case_alerts
from controller.auth_controller import verify_access_token
from model.user_model import store_query, get_user_queries, get_user_results, results_collection
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


@router.get("/user/results/by-query")
async def get_results_by_query(query: str, timestamp: str = None, current_user: dict = Depends(get_current_user)):
    """Get analysis results for a specific query using direct MongoDB query."""
    from common.logging import logger
    
    user_id = current_user["user_id"]
    
    logger.info("Searching for query: '%s'", query)
    logger.info("Query timestamp: %s", timestamp)
    
    # First try direct MongoDB query using unencrypted original_query field
    try:
        # Normalize query for comparison
        query_normalized = query.strip().lower()
        
        # Find results with matching original_query
        matching_results = list(results_collection.find({
            "user_id": user_id,
            "original_query": {"$regex": f".*{query_normalized}.*", "$options": "i"}
        }).sort("timestamp", -1))  # Sort by timestamp descending (most recent first)
        
        logger.info("Found %d results with regex match", len(matching_results))
        
        # If no regex matches, try exact match
        if not matching_results:
            exact_match = results_collection.find_one({
                "user_id": user_id,
                "original_query": query.strip()
            })
            if exact_match:
                matching_results = [exact_match]
                logger.info("Found exact match")
        
        # If still no matches and timestamp provided, try timestamp-based search
        if not matching_results and timestamp:
            logger.info("No query matches found, trying timestamp-based search")
            from datetime import datetime, timedelta
            
            try:
                query_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_window = timedelta(minutes=5)
                
                # Find results within time window
                timestamp_results = list(results_collection.find({
                    "user_id": user_id,
                    "timestamp": {
                        "$gte": query_timestamp - time_window,
                        "$lte": query_timestamp + time_window
                    }
                }).sort("timestamp", -1))
                
                if timestamp_results:
                    matching_results = timestamp_results
                    logger.info("Found %d timestamp-based matches", len(matching_results))
                    
            except Exception as e:
                logger.error("Error in timestamp search: %s", str(e))
        
        # Process matching results
        if matching_results:
            # Decrypt the most recent result
            result = matching_results[0]
            
            try:
                if "encrypted_data" in result and "encryption_version" in result:
                    from common.encryption import secure_storage
                    decrypted_data = secure_storage.retrieve_analysis_result({
                        "encrypted_data": result["encrypted_data"],
                        "encryption_version": result["encryption_version"]
                    })
                    
                    logger.info("Successfully decrypted result for query: %s", result.get("original_query", ""))
                    
                    return {
                        "_id": str(result["_id"]),
                        "user_id": result["user_id"],
                        "timestamp": result.get("timestamp"),
                        "result": decrypted_data.get("result", {}),
                        "original_query": result.get("original_query", ""),
                        "match_type": "direct_query"
                    }
                else:
                    logger.warning("Result missing encryption data")
                    return {"error": "Result data is corrupted"}
                    
            except Exception as e:
                logger.error("Error decrypting result: %s", str(e))
                return {"error": "Failed to decrypt result data"}
        else:
            logger.warning("No matching results found for query: %s", query)
            return {"error": "No results found for this query"}
            
    except Exception as e:
        logger.error("Error in get_results_by_query: %s", str(e))
        return {"error": "Database query failed"}


@router.get("/user/history")
async def get_user_history(current_user: dict = Depends(get_current_user)):
    """Get user's complete history including queries and results."""
    user_id = current_user["user_id"]
    print(f"Fetching history for user_id: {user_id}")
    
    # Get encrypted queries
    encrypted_queries = get_user_queries(user_id)
    print(f"Found {len(encrypted_queries)} encrypted queries for user_id: {user_id}")
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
    """Upload and analyze a PDF legal document using full agent orchestration"""
    try:
        user_id = current_user["user_id"]
        
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        content = await file.read()
        
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
        
        # Extract text from PDF
        text = pdf_processor.extract_text_from_pdf(content)
        
        if not text or len(text.strip()) < 100:
            raise HTTPException(status_code=400, detail="Could not extract sufficient text from PDF")
        
        # Use the full orchestrator for comprehensive analysis
        pdf_query = f"Analyze this legal document: {file.filename}"
        
        # Run full orchestration with PDF text
        result = orchestrate_query_with_text(pdf_query, user_id, text)
        
        # Store encrypted PDF data
        encrypted_pdf = secure_storage.store_pdf_data(user_id, content, file.filename)
        result["encrypted_pdf_id"] = encrypted_pdf["encrypted_data"][:50] + "..."
        result["pdf_filename"] = file.filename
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pdf/analyze")
async def analyze_pdf_text(request: PDFUploadRequest, current_user: dict = Depends(get_current_user)):
    """Analyze PDF text content (base64 encoded) using full agent orchestration"""
    try:
        user_id = current_user["user_id"]
        
        # Decode base64 content
        pdf_content = base64.b64decode(request.content)
        
        # Extract text from PDF
        text = pdf_processor.extract_text_from_pdf(pdf_content)
        
        if not text or len(text.strip()) < 100:
            raise HTTPException(status_code=400, detail="Could not extract sufficient text from PDF")
        
        # Use the full orchestrator for comprehensive analysis
        # Create a query-like analysis using the PDF text
        pdf_query = f"Analyze this legal document: {request.filename}"
        
        # Run full orchestration with PDF text as the "query"
        result = orchestrate_query_with_text(pdf_query, user_id, text)
        
        # Store encrypted PDF data
        encrypted_pdf = secure_storage.store_pdf_data(user_id, pdf_content, request.filename)
        result["encrypted_pdf_id"] = encrypted_pdf["encrypted_data"][:50] + "..."
        result["pdf_filename"] = request.filename
        
        return result
    
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
