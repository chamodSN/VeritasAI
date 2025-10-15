import re
from agents.citation.citation_agent import citation_agent
from crewai import Task, Crew
from common.logging import setup_logging
import time
from typing import List, Dict, Any
import requests

logger = setup_logging()

# Mock function for external database verification (replace with actual API calls)
def query_legal_database(citation: str, source: str) -> Dict[str, Any]:
    """
    Simulate querying a legal database for citation verification.
    Replace with actual API calls to CourtListener, Westlaw, or LexisNexis.
    """
    # Placeholder: Simulate API response
    try:
        # Example: Check if citation exists in database
        response = {
            "source": source,
            "status": "VALID",
            "details": f"{citation} found in {source}",
            "confidence": 0.9 if source == "CourtListener" else 0.85
        }
        return response
    except Exception as e:
        logger.error(f"Error querying {source} for {citation}: {str(e)}")
        return {"source": source, "status": "ERROR", "details": str(e), "confidence": 0.0}

def verify_citations(citations: List[str]) -> Dict[str, Any]:
    """
    Verify a list of legal citations using the citation agent with enhanced reliability.

    Args:
        citations: List of citation strings or formatted citation strings to verify

    Returns:
        Verification report with detailed analysis and reliability metrics
    """
    if not citations:
        logger.warning("No citations provided for verification")
        return {
            "status": "no_citations",
            "message": "No citations were found to verify",
            "verified_citations": [],
            "invalid_citations": [],
            "recommendations": [],
            "confidence_details": []
        }

    # Handle both raw citation strings and formatted citation strings
    raw_citations = []
    for citation in citations:
        if isinstance(citation, str):
            if citation.startswith("Citation: "):
                parts = citation.split(" (Type: ")
                if len(parts) > 0:
                    raw_citation = parts[0].replace("Citation: ", "")
                    raw_citations.append(raw_citation)
            else:
                raw_citations.append(citation)
        elif isinstance(citation, dict) and "text" in citation:
            raw_citations.append(citation["text"])

    if not raw_citations:
        logger.warning("No valid citations extracted for verification")
        return {
            "status": "no_citations",
            "message": "No valid citations were found to verify",
            "verified_citations": [],
            "invalid_citations": [],
            "recommendations": [],
            "confidence_details": []
        }

    logger.info(f"Verifying {len(raw_citations)} citations")

    # Define multiple legal databases for cross-verification
    legal_databases = ["CourtListener", "Westlaw", "LexisNexis"]

    # Create detailed task description for the citation agent
    citations_text = "\n".join([f"{i+1}. {citation}" for i, citation in enumerate(raw_citations)])

    task = Task(
        description=f"""Verify the following legal citations for accuracy, format compliance, and authenticity:

{citations_text}

For each citation, provide:
1. Verification status (VALID, INVALID, NEEDS_REVIEW)
2. Format compliance assessment (Bluebook/ALWD)
3. Specific issues or corrections needed
4. Recommended corrections if applicable
5. Confidence level (HIGH, MEDIUM, LOW)
6. Sources checked and their results

Focus on:
- Bluebook citation format compliance
- Logical consistency of citation elements
- Cross-referencing with multiple legal databases ({', '.join(legal_databases)})
- Identifying potential discrepancies across sources""",
        agent=citation_agent,
        expected_output="""A comprehensive verification report in JSON format with:
- Overall verification summary
- Individual citation analysis with status, issues, and recommendations
- Format compliance scores
- Confidence assessments per source
- Specific correction suggestions
- List of sources checked"""
    )

    crew = Crew(
        agents=[citation_agent],
        tasks=[task],
        verbose=True
    )

    try:
        # Perform verification with the agent
        result = crew.kickoff()
        logger.info("Citation verification completed successfully")

        # Enhanced verification with multi-source checks
        verification_result = {
            "status": "completed",
            "message": "Citations verified successfully",
            "raw_result": str(result.raw) if hasattr(result, 'raw') else str(result),
            "total_citations": len(raw_citations),
            "verified_citations": [],
            "invalid_citations": [],
            "recommendations": [],
            "confidence_details": []
        }

        # Cross-verify each citation with multiple databases
        for citation in raw_citations:
            source_results = []
            for source in legal_databases:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        db_result = query_legal_database(citation, source)
                        source_results.append(db_result)
                        break
                    except requests.exceptions.RequestException as e:
                        logger.warning(f"Attempt {attempt + 1} failed for {source}: {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)  # Exponential backoff
                        else:
                            source_results.append({
                                "source": source,
                                "status": "ERROR",
                                "details": f"Failed to query {source} after {max_retries} attempts",
                                "confidence": 0.0
                            })

            # Calculate aggregated confidence
            valid_sources = [r for r in source_results if r["status"] == "VALID"]
            confidence = sum(r["confidence"] for r in valid_sources) / max(1, len(valid_sources)) if valid_sources else 0.0
            status = "VALID" if valid_sources else "INVALID"
            if len(valid_sources) < len(legal_databases):
                status = "NEEDS_REVIEW"

            # Compile citation details
            citation_details = {
                "citation": citation,
                "status": status,
                "source_results": source_results,
                "confidence": confidence,
                "issues": [],
                "recommendations": []
            }

            # Add format compliance check (mock example)
            if not re.match(r'\d+\s+[A-Za-z\.]+\s+\d+', citation):
                citation_details["issues"].append("Invalid citation format")
                citation_details["recommendations"].append("Ensure citation follows Bluebook format (e.g., '123 F.3d 456')")
                citation_details["status"] = "INVALID"

            # Assign to appropriate result category
            if citation_details["status"] == "VALID":
                verification_result["verified_citations"].append(citation_details)
            else:
                verification_result["invalid_citations"].append(citation_details)
                verification_result["recommendations"].extend(citation_details["recommendations"])

            verification_result["confidence_details"].append({
                "citation": citation,
                "average_confidence": confidence,
                "sources_matched": len(valid_sources),
                "sources_checked": legal_databases
            })

        logger.info("Reliability metrics: %s", verification_result["confidence_details"])
        return verification_result

    except Exception as e:
        logger.error(f"Error during citation verification: {str(e)}")
        return {
            "status": "error",
            "message": f"Citation verification failed: {str(e)}",
            "verified_citations": [],
            "invalid_citations": raw_citations,
            "recommendations": ["Please check citation format and try again"],
            "confidence_details": []
        }