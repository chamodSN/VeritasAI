# precedent/main.py
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import httpx
import faiss
import numpy as np
from typing import List, Dict, Any
from common.security import verify_token
from common.logging import logger
from common.models import PrecedentRequest, PrecedentResponse
from common.config import Config
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Precedent Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    dimension = 384
    index = faiss.IndexFlatL2(dimension)
    logger.info("SentenceTransformer and FAISS index initialized successfully")
except Exception as e:
    logger.error(
        f"Failed to initialize SentenceTransformer or FAISS: {str(e)}")
    raise Exception("Precedent agent initialization failed")


async def fetch_case_text(case_id: str, client: httpx.AsyncClient) -> str:
    try:
        response = await client.get(
            f"{Config.COURTLISTENER_BASE_URL}opinions/?cluster={case_id}&fields=plain_text",
            headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
        )
        response.raise_for_status()
        opinions = response.json().get("results", [])
        text = opinions[0].get("plain_text", "") if opinions else ""
        if not text:
            logger.warning(f"No plain_text for case_id {case_id}")
        return text
    except httpx.HTTPStatusError as e:
        logger.error(
            f"CourtListener API error for case_id {case_id}: {str(e)}")
        return ""
    except Exception as e:
        logger.error(
            f"Error fetching case text for case_id {case_id}: {str(e)}")
        return ""


async def fetch_cited_cases(citation: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    try:
        response = await client.get(
            f"{Config.COURTLISTENER_BASE_URL}clusters/?q=cited_by:{citation}&court=scotus&date_filed_min=2010-01-01&date_filed_max=2025-12-31",
            headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        return [
            {
                "case_id": str(result.get("id")),
                "case_name": result.get("case_name", "Unknown"),
                "court": result.get("court_name", "United States Supreme Court"),
                "date_filed": result.get("date_filed", "Unknown")
            }
            for result in results[:3]
            if result.get("date_filed", "") <= "2025-12-31"
        ]
    except httpx.HTTPStatusError as e:
        logger.error(
            f"CourtListener API error for citation {citation}: {str(e)}")
        return []
    except Exception as e:
        logger.error(
            f"Error fetching cited cases for citation {citation}: {str(e)}")
        return []


async def fetch_similar_cases(case_text: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    try:
        if not case_text:
            return []

        embedding = model.encode([case_text])[0]
        embedding = np.array([embedding]).astype('float32')
        embedding /= np.linalg.norm(embedding, axis=1, keepdims=True)

        response = await client.get(
            f"{Config.COURTLISTENER_BASE_URL}clusters/?court=scotus&date_filed_min=2010-01-01&date_filed_max=2025-12-31",
            headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
        )
        response.raise_for_status()
        results = response.json().get("results", [])

        texts = []
        case_ids = []
        case_details = []
        for result in results[:50]:
            case_id = str(result.get("id"))
            opinion_response = await client.get(
                f"{Config.COURTLISTENER_BASE_URL}opinions/?cluster={case_id}&fields=plain_text",
                headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
            )
            if opinion_response.status_code == 200:
                opinions = opinion_response.json().get("results", [])
                text = opinions[0].get("plain_text", "") if opinions else ""
                if text:
                    texts.append(text)
                    case_ids.append(case_id)
                    case_details.append({
                        "case_id": case_id,
                        "case_name": result.get("case_name", "Unknown"),
                        "court": result.get("court_name", "United States Supreme Court"),
                        "date_filed": result.get("date_filed", "Unknown")
                    })

        if not texts:
            return []

        embeddings = model.encode(texts)
        embeddings = np.array(embeddings).astype('float32')
        embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)
        temp_index = faiss.IndexFlatL2(dimension)
        temp_index.add(embeddings)

        _, indices = temp_index.search(embedding, 3)
        return [case_details[i] for i in indices[0] if i < len(case_details)]

    except httpx.HTTPStatusError as e:
        logger.error(f"CourtListener API error in similarity search: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error in similarity search: {str(e)}")
        return []


@app.post("/find_precedents", response_model=PrecedentResponse)
async def find_precedents(request: PrecedentRequest, token: dict = Depends(verify_token)):
    try:
        case_id = request.case_id
        citations = request.citations
        logger.debug(
            f"Processing precedents for case_id {case_id}, citations: {citations}")

        if not case_id or not case_id.isdigit():
            logger.error(f"Invalid case_id: {case_id}")
            raise HTTPException(
                status_code=400, detail="Valid case_id required")

        related_cases = []
        async with httpx.AsyncClient(timeout=30) as client:
            case_text = await fetch_case_text(case_id, client)

            for citation in citations[:5]:
                cited_cases = await fetch_cited_cases(citation, client)
                related_cases.extend(cited_cases)

            if not related_cases and case_text:
                logger.debug(
                    f"No citation-based precedents for case_id {case_id}, trying similarity search")
                similar_cases = await fetch_similar_cases(case_text, client)
                related_cases.extend(similar_cases)

        seen = set()
        unique_cases = [case for case in related_cases if not (
            case["case_id"] in seen or seen.add(case["case_id"]))]

        logger.info(
            f"Found {len(unique_cases)} related cases for case_id {case_id}")
        return PrecedentResponse(related_cases=unique_cases)

    except httpx.HTTPStatusError as e:
        logger.error(
            f"CourtListener API error for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error finding precedents for case_id {case_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Precedent error: {str(e)}")