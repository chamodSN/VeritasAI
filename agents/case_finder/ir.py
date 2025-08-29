from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from common.security import verify_token
from common.logging import logger
from common.config import Config
from common.models import SearchRequest

router = APIRouter()

model = SentenceTransformer('all-MiniLM-L6-v2')
index = faiss.IndexFlatL2(384)  # Dimension for MiniLM embeddings


class SearchResponse(BaseModel):
    case_ids: list[str]


@router.post("/search", response_model=SearchResponse)
async def search_cases(request: SearchRequest, token: str = Depends(verify_token)):
    try:
        query = f"{request.case_type} {request.topic}"
        query_embedding = model.encode([query])[0]
        query_embedding = np.array([query_embedding]).astype('float32')

        async with httpx.AsyncClient() as client:
            # Start with mandatory parameters
            params = {
                "q": query,
                "type": "o"
            }

            # Add optional parameters only if they are not None
            if request.date_from:
                params["date_filed_after"] = request.date_from
            if request.date_to:
                params["date_filed_before"] = request.date_to

            response = await client.get(
                f"{Config.COURTLISTENER_BASE_URL}search/",
                params=params,
                headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
            )
            response.raise_for_status()
            cases = response.json().get("results", [])

        case_ids = [str(case["id"]) for case in cases]
        logger.info(f"Processed case IDs: {case_ids}")
        return SearchResponse(case_ids=case_ids)
    except Exception as e:
        logger.error(f"Error retrieving cases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
