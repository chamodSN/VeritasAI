from agents.citation.citation_agent import citation_agent
from crewai import Task, Crew
from common.logging import logger


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
            "recommendations": [],
            "total_citations": 0
        }

    # Create detailed task description
    citations_text = "\n".join(
        [f"{i+1}. {citation}" for i, citation in enumerate(citations)])

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
- Cross-referencing possibilities

IMPORTANT: Return your response in valid JSON format with the following structure:
{{
  "overall_verification_summary": {{
    "valid": number,
    "invalid": number,
    "needs_review": number,
    "format_compliance_score": percentage
  }},
  "individual_citation_analysis": [
    {{
      "citation": "citation text",
      "status": "VALID|INVALID|NEEDS_REVIEW",
      "confidence_level": "HIGH|MEDIUM|LOW",
      "issues": "description of issues or 'None'",
      "recommendations": "recommended corrections or 'None needed.'"
    }}
  ]
}}""",
        agent=citation_agent,
        expected_output="""A comprehensive verification report in valid JSON format with:
- Overall verification summary with counts and compliance score
- Individual citation analysis with status, issues, and recommendations
- Format compliance scores
- Confidence assessments
- Specific correction suggestions

The response must be valid JSON that can be parsed directly."""
    )

    crew = Crew(
        agents=[citation_agent],
        tasks=[task],
        verbose=True
    )

    try:
        result = crew.kickoff()
        logger.info("Citation verification completed successfully")

        # Parse the result and extract JSON data
        raw_output = str(result.raw) if hasattr(result, 'raw') else str(result)
        
        # Try to extract JSON from markdown code blocks
        json_data = None
        try:
            import json
            import re
            
            # Look for JSON in markdown code blocks
            json_match = re.search(r'```json\s*\n(.*?)\n```', raw_output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                json_data = json.loads(json_str)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    json_data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as parse_error:
            logger.warning("Could not parse JSON from citation result: %s", str(parse_error))
            # Create a fallback structure
            json_data = {
                "overall_verification_summary": {
                    "valid": 0,
                    "invalid": len(citations),
                    "needs_review": 0,
                    "format_compliance_score": 0
                },
                "individual_citation_analysis": [
                    {
                        "citation": citation,
                        "status": "NEEDS_REVIEW",
                        "confidence_level": "LOW",
                        "issues": "Unable to parse verification result",
                        "recommendations": "Please check citation format"
                    } for citation in citations
                ]
            }

        # Return structured data
        verification_result = {
            "status": "completed",
            "message": "Citations verified successfully",
            "raw_result": raw_output,
            "total_citations": len(citations),
            "verification_details": raw_output,
            "parsed_data": json_data
        }

        return verification_result

    except (ValueError, TypeError, AttributeError) as e:
        logger.error("Error during citation verification: %s", str(e))
        return {
            "status": "error",
            "message": f"Citation verification failed: {str(e)}",
            "verified_citations": [],
            "invalid_citations": citations,
            "recommendations": ["Please check citation format and try again"]
        }