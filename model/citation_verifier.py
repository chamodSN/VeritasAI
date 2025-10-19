from agents.citation.citation_agent import citation_agent
from crewai import Task, Crew
from common.logging import setup_logging

logger = setup_logging()


def verify_citations(citations: list):
    """
    Verify a list of legal citations using the citation agent.
    
    Args:
        citations: List of citation strings or formatted citation strings to verify
        
    Returns:
        Verification report with detailed analysis
    """
    if not citations:
        logger.warning("No citations provided for verification")
        return {
            "status": "no_citations",
            "message": "No citations were found to verify",
            "verified_citations": [],
            "invalid_citations": [],
            "recommendations": []
        }
    
    # Handle both raw citation strings and formatted citation strings
    raw_citations = []
    for citation in citations:
        if isinstance(citation, str):
            # If it's a formatted citation string, extract the raw citation
            if citation.startswith("Citation: "):
                # Extract citation from "Citation: [citation] (Type: [type])"
                parts = citation.split(" (Type: ")
                if len(parts) > 0:
                    raw_citation = parts[0].replace("Citation: ", "")
                    raw_citations.append(raw_citation)
            else:
                # It's already a raw citation
                raw_citations.append(citation)
        else:
            # If it's a dictionary, extract the text field
            if isinstance(citation, dict) and "text" in citation:
                raw_citations.append(citation["text"])
    
    if not raw_citations:
        logger.warning("No valid citations extracted for verification")
        return {
            "status": "no_citations",
            "message": "No valid citations were found to verify",
            "verified_citations": [],
            "invalid_citations": [],
            "recommendations": []
        }
    
    logger.info(f"Verifying {len(raw_citations)} citations")
    
    # Create detailed task description
    citations_text = "\n".join([f"{i+1}. {citation}" for i, citation in enumerate(raw_citations)])
    
    task = Task(
        description=f"""Verify the following legal citations for accuracy, format compliance, and authenticity:

{citations_text}

For each citation, provide:
1. Verification status (VALID, INVALID, NEEDS_REVIEW)
2. Format compliance assessment
3. Specific issues or corrections needed
4. Recommended corrections if applicable
5. Confidence level (HIGH, MEDIUM, LOW)

Focus on:
- Bluebook citation format compliance
- Logical consistency of citation elements
- Known legal databases and sources
- Cross-referencing possibilities""",
        agent=citation_agent,
        expected_output="""A comprehensive verification report in JSON format with:
- Overall verification summary
- Individual citation analysis with status, issues, and recommendations
- Format compliance scores
- Confidence assessments
- Specific correction suggestions"""
    )
    
    crew = Crew(
        agents=[citation_agent],
        tasks=[task],
        verbose=True
    )
    
    try:
        result = crew.kickoff()
        logger.info("Citation verification completed successfully")
        
        # Parse the result and return structured data
        verification_result = {
            "status": "completed",
            "message": "Citations verified successfully",
            "raw_result": str(result.raw) if hasattr(result, 'raw') else str(result),
            "total_citations": len(raw_citations),
            "verification_details": str(result.raw) if hasattr(result, 'raw') else str(result)
        }
        
        return verification_result
        
    except Exception as e:
        logger.error(f"Error during citation verification: {str(e)}")
        return {
            "status": "error",
            "message": f"Citation verification failed: {str(e)}",
            "verified_citations": [],
            "invalid_citations": raw_citations,
            "recommendations": ["Please check citation format and try again"]
        }