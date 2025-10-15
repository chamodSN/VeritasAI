from crewai import Crew, Task
from agents.argument.argument_agent import argument_agent
from agents.analytics.analytics_agent import analytics_agent
from agents.summary.summarization_agent import summarization_agent
from agents.issue.issue_agent import issue_agent
from model.case_indexer import retrieve_documents
from model.issue_extractor import extract_issues
from model.citation_verifier import verify_citations
from model.citation_extractor import extract_citations_from_documents, format_citations_for_verification
from common.logging import setup_logging
from model.courtlistener_client import courtlistener_client
from typing import Dict, Any, List

logger = setup_logging()


def orchestrate_query(query: str, user_id: str) -> Dict[str, Any]:
    """
    Orchestrate a legal research query using CourtListener API
    """
    logger.info("=" * 60)
    logger.info("STARTING ORCHESTRATION")
    logger.info("Query: %s", query)
    logger.info("User ID: %s", user_id)
    logger.info("=" * 60)

    try:
        # Step 1: Retrieve cases from CourtListener API
        logger.info("STEP 1: Retrieving documents from CourtListener API")
        docs = retrieve_documents(query, k=10)
        logger.info("Retrieved %d documents", len(docs) if docs else 0)

        if not docs:
            logger.warning("No documents retrieved from CourtListener API")
            return {
                "error": "No relevant cases found for the given query",
                "summary": "No cases found",
                "issues": [],
                "arguments": "Unable to generate arguments without case data",
                "citations": [],
                "analytics": "No data available for analysis",
                "confidence": 0.0
            }

        # Log document details
        for i, doc in enumerate(docs):
            logger.info("Document %d: %d characters, metadata: %s",
                        i+1, len(doc.page_content), doc.metadata)

        # Step 2: Extract and process text content
        logger.info("STEP 2: Extracting and processing text content")
        doc_texts = [doc.page_content for doc in docs]
        logger.info("Extracted text from %d documents", len(doc_texts))

        # Limit document text to prevent token overflow
        max_chars_per_doc = 3000  # Increased limit for CourtListener data
        limited_doc_texts = []
        for i, text in enumerate(doc_texts):
            original_length = len(text)
            if len(text) > max_chars_per_doc:
                limited_text = text[:max_chars_per_doc] + "..."
                limited_doc_texts.append(limited_text)
                logger.info("Document %d: Truncated from %d to %d characters",
                            i+1, original_length, len(limited_text))
            else:
                limited_doc_texts.append(text)
                logger.info("Document %d: %d characters (no truncation needed)",
                            i+1, original_length)

        # Combine texts but limit total size
        combined_text = '\n'.join(limited_doc_texts)
        max_total_chars = 8000  # Increased limit for CourtListener data
        original_combined_length = len(combined_text)
        if len(combined_text) > max_total_chars:
            combined_text = combined_text[:max_total_chars] + "..."
            logger.info("Combined text truncated from %d to %d characters",
                        original_combined_length, len(combined_text))
        else:
            logger.info("Combined text: %d characters (no truncation needed)",
                        len(combined_text))

        logger.info("Processing %d cases with %d characters of text",
                    len(docs), len(combined_text))

        # Step 3: Extract issues from documents
        logger.info("STEP 3: Extracting legal issues")
        try:
            issues = extract_issues(combined_text)
            logger.info("Successfully extracted %d issues: %s",
                        len(issues), issues)
        except Exception as e:
            logger.error("Error extracting issues: %s", e)
            issues = []

        # Step 4: Generate summaries
        logger.info("STEP 4: Generating case summaries")
        try:
            summary_task = Task(
                description=f"Summarize the following legal cases from CourtListener API (focus on key legal points, rulings, and precedents): {combined_text}",
                agent=summarization_agent,
                expected_output="A comprehensive summary of the legal cases highlighting key points, rulings, precedents, and legal principles"
            )

            summary_crew = Crew(
                agents=[summarization_agent],
                tasks=[summary_task],
                verbose=True
            )
            summaries = summary_crew.kickoff()
            logger.info("Successfully generated summaries")
        except Exception as e:
            logger.error("Error generating summaries: %s", e)
            summaries = "Error occurred during summarization"

        # Step 5: Extract and verify citations
        logger.info("STEP 5: Extracting and verifying citations")
        try:
            # Extract citations from FULL documents (not truncated) to capture citations at the end
            raw_citations = extract_citations_from_documents(doc_texts)
            logger.info("Extracted %d raw citations from full documents", len(raw_citations))
            citations_for_verification = format_citations_for_verification(
                raw_citations)
            logger.info("Formatted %d citations for verification",
                        len(citations_for_verification))

            # Verify citations using CourtListener API
            verified_citations = verify_citations(citations_for_verification)
            logger.info("Verified %d citations", len(verified_citations))
        except Exception as e:
            logger.error("Error processing citations: %s", e)
            raw_citations = []
            verified_citations = []

        try:
            arg_task = Task(
                description=f"Generate comprehensive legal arguments for query '{query}' using identified issues: {issues} and case summaries: {summaries}. Focus on precedential value and legal reasoning.",
                agent=argument_agent,
                expected_output="Well-structured legal arguments and counterarguments based on the identified issues, case summaries, and precedential analysis"
            )

            arg_crew = Crew(
                agents=[argument_agent],
                tasks=[arg_task],
                verbose=True
            )
            arguments = arg_crew.kickoff()
            logger.info("Successfully generated arguments")
        except Exception as e:
            logger.error("Error generating arguments: %s", e)
            arguments = "Error occurred during argument generation"

        # Step 7: Generate analytics
        logger.info("STEP 7: Generating analytics and patterns")
        try:
            analytics_task = Task(
                description=f"Analyze legal patterns, trends, and insights for query: {query}. Consider case precedents, court jurisdictions, and legal evolution.",
                agent=analytics_agent,
                expected_output="Comprehensive analysis of legal patterns, trends, jurisdictional differences, and insights relevant to the query"
            )

            analytics_crew = Crew(
                agents=[analytics_agent],
                tasks=[analytics_task],
                verbose=True
            )
            analytics = analytics_crew.kickoff()
            logger.info("Successfully generated analytics")
        except Exception as e:
            logger.error("Error generating analytics: %s", e)
            analytics = "Error occurred during analytics generation"

        # Step 8: Calculate confidence and compile results
        logger.info("STEP 8: Calculating confidence and compiling results")
        try:
            confidence = calculate_confidence(docs, verified_citations)
            logger.info("Calculated confidence: %f", confidence)

            # Collate results
            result = {
                "summary": summaries,
                "issues": issues,
                "arguments": arguments,
                "citations": verified_citations,
                "raw_citations": raw_citations,
                "analytics": analytics,
                "confidence": confidence,
                "case_count": len(docs),
                "source": "CourtListener API"
            }

            # Store results
            from model.user_model import store_result
            store_result(user_id, result)
            logger.info("Stored results for user: %s", user_id)

            # Return serialized results for API response
            serialized_result = serialize_results(result)
            logger.info("Serialized results successfully")

            logger.info("=" * 60)
            logger.info("ORCHESTRATION COMPLETED SUCCESSFULLY")
            logger.info("Confidence: %f", confidence)
            logger.info("Case Count: %d", len(docs))
            logger.info("=" * 60)
            return serialized_result

        except Exception as e:
            logger.error("Error in final result compilation: %s", e)
            return {
                "error": f"Error in final processing: {str(e)}",
                "summary": "Error occurred during processing",
                "issues": [],
                "arguments": "Unable to generate arguments due to processing error",
                "citations": [],
                "analytics": "No analysis available due to error",
                "confidence": 0.0
            }

    except Exception as e:
        logger.error("Error in orchestration: %s", e)
        return {
            "error": f"Error processing query: {str(e)}",
            "summary": "Error occurred during processing",
            "issues": [],
            "arguments": "Unable to generate arguments due to processing error",
            "citations": [],
            "analytics": "No analysis available due to error",
            "confidence": 0.0
        }


def calculate_confidence(docs: List, verified_citations: List) -> float:
    """Calculate confidence score based on case quality and quantity"""
    if not docs:
        return 0.0

    base_confidence = 0.5

    # Factor in number of cases
    # Up to 0.3 for having many cases
    case_count_factor = min(len(docs) / 10, 0.3)

    # Factor in citation verification
    # Up to 0.2 for verified citations
    citation_factor = min(len(verified_citations) / 5, 0.2)

    # Factor in case precedential value
    precedential_factor = 0.0
    for doc in docs:
        if doc.metadata.get('precedential'):
            precedential_factor += 0.1

    precedential_factor = min(precedential_factor, 0.2)  # Cap at 0.2

    confidence = base_confidence + case_count_factor + \
        citation_factor + precedential_factor
    return min(confidence, 1.0)  # Cap at 1.0


def serialize_results(result: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize results for API response"""
    serialized_result = {}
    for key, value in result.items():
        if hasattr(value, 'raw'):  # CrewOutput object
            serialized_result[key] = str(value.raw)
        else:
            serialized_result[key] = value

    return serialized_result


def get_case_alerts(query: str, _user_id: str) -> Dict[str, Any]:
    """Create alerts for new cases matching the query"""
    try:
        alert_name = f"Alert for {query[:50]}..."
        alert_uri = courtlistener_client.create_alert(query, alert_name)

        if alert_uri:
            return {
                "success": True,
                "alert_uri": alert_uri,
                "message": f"Alert created successfully for query: {query}"
            }
        else:
            return {
                "success": False,
                "message": "Failed to create alert"
            }
    except Exception as e:
        logger.error("Error creating alert: %s", e)
        return {
            "success": False,
            "message": f"Error creating alert: {str(e)}"
        }
