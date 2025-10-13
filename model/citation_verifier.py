from agents.citation_agent import citation_agent
from crewai import Task, Crew
from common.logging import setup_logging

logger = setup_logging()


def verify_citations(citations: list):
    """
    Verify a list of legal citations using the citation agent.
    
    Args:
        citations: List of citation strings to verify
        
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
    
    logger.info(f"Verifying {len(citations)} citations")
    
    # Create detailed task description
    citations_text = "\n".join([f"{i+1}. {citation}" for i, citation in enumerate(citations)])
    
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
            "total_citations": len(citations),
            "verification_details": str(result.raw) if hasattr(result, 'raw') else str(result)
        }
        
        return verification_result
        
    except Exception as e:
        logger.error(f"Error during citation verification: {str(e)}")
        return {
            "status": "error",
            "message": f"Citation verification failed: {str(e)}",
            "verified_citations": [],
            "invalid_citations": citations,
            "recommendations": ["Please check citation format and try again"]
        }