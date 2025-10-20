from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.docstore.document import Document as LangDocument
from common.config import Config
from common.logging import logger
from model.courtlistener_client import courtlistener_client, CaseData
from typing import List, Dict, Any
import json

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
logger = logger


def case_data_to_document(case: CaseData) -> LangDocument:
    """Convert CaseData to LangChain Document"""
    # Create comprehensive text content from case data
    content_parts = [
        f"Case Name: {case.case_name}",
        f"Court: {case.court}",
        f"Date Filed: {case.date_filed}",
        f"Docket Number: {case.docket_number or 'N/A'}",
        f"Nature of Suit: {case.nature_of_suit or 'N/A'}",
        f"Jurisdiction: {case.jurisdiction or 'N/A'}",
        f"Precedential: {case.precedential}",
        f"Citation Count: {case.citation_count or 0}"
    ]

    # Add casebody content if available
    if case.casebody:
        casebody_text = case.casebody.get('text', '')
        if casebody_text:
            # Limit text length
            content_parts.append(f"Case Text: {casebody_text[:2000]}...")

    content = "\n".join(content_parts)

    # Create metadata
    metadata = {
        "source": case.absolute_url,
        "case_name": case.case_name,
        "court": case.court,
        "date_filed": case.date_filed,
        "docket_number": case.docket_number,
        "nature_of_suit": case.nature_of_suit,
        "jurisdiction": case.jurisdiction,
        "precedential": case.precedential,
        "citation_count": case.citation_count,
        "resource_uri": case.resource_uri
    }

    return LangDocument(page_content=content, metadata=metadata)


def retrieve_cases_from_courtlistener(query: str, k: int = 10) -> List[LangDocument]:
    """Retrieve cases from CourtListener API and convert to LangChain Documents"""
    try:
        # Use comprehensive search to get relevant cases
        cases = courtlistener_client.comprehensive_search(query, max_cases=k*2)

        # Convert to LangChain Documents
        documents = []
        for case in cases[:k]:
            try:
                # Get detailed case information
                case_details = courtlistener_client.get_case_details(
                    case.resource_uri)
                if case_details:
                    # Update case object with detailed information
                    case.casebody = case_details.get('casebody')

                doc = case_data_to_document(case)
                documents.append(doc)

            except Exception as e:
                logger.warning(f"Error processing case {case.case_name}: {e}")
                # Still add the basic case info
                doc = case_data_to_document(case)
                documents.append(doc)

        logger.info(f"Retrieved {len(documents)} cases from CourtListener API")
        return documents

    except Exception as e:
        logger.error(f"Error retrieving cases from CourtListener: {e}")
        return []


def build_vector_index_from_cases(cases: List[CaseData]) -> FAISS:
    """Build FAISS vector index from CourtListener cases"""
    try:
        documents = []
        for case in cases:
            doc = case_data_to_document(case)
            documents.append(doc)

        if documents:
            vectorstore = FAISS.from_documents(documents, embeddings)
            return vectorstore
        else:
            logger.warning("No documents to build index from")
            return None

    except Exception as e:
        logger.error(f"Error building vector index: {e}")
        return None


def retrieve_documents(query: str, k=5):
    """Main function to retrieve documents - now uses CourtListener API"""
    try:
        # Retrieve cases from CourtListener API
        documents = retrieve_cases_from_courtlistener(query, k=k)

        if not documents:
            logger.warning("No documents retrieved from CourtListener API")
            return []

        # Create a temporary vector store for similarity search
        if len(documents) > 1:
            temp_vectorstore = FAISS.from_documents(documents, embeddings)
            # Perform similarity search within the retrieved cases
            results = temp_vectorstore.similarity_search(query, k=k)
            return results
        else:
            return documents

    except Exception as e:
        logger.error(f"Error in retrieve_documents: {e}")
        return []


def get_case_statistics() -> Dict[str, Any]:
    """Get statistics about retrieved cases"""
    # This could be enhanced to track statistics over time
    return {
        "total_cases_searched": 0,
        "successful_retrievals": 0,
        "api_errors": 0,
        "last_search_time": None
    }
