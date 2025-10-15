from crewai import Crew, Task
from agents.argument.argument_agent import argument_agent
from agents.analytics.analytics_agent import analytics_agent
from agents.summary.summarization_agent import summarization_agent
from agents.issue.issue_agent import issue_agent
from model.case_indexer import retrieve_documents
from model.issue_extractor import extract_issues
from model.citation_verifier import verify_citations
from model.citation_extractor import extract_citations_from_documents, format_citations_for_verification
from model.user_model import store_result 
from common.logging import setup_logging
from model.courtlistener_client import courtlistener_client
from typing import Dict, Any, List
from datetime import datetime

logger = setup_logging()

def orchestrate_query(query: str, user_id: str) -> Dict[str, Any]:
    """
    Orchestrate a legal research query using CourtListener API with accountability mechanisms.
    """
    logger.info("=" * 60)
    logger.info("STARTING ORCHESTRATION")
    logger.info("Query: %s", query)
    logger.info("User ID: %s", user_id)
    logger.info("=" * 60)

    # Initialize audit trail
    audit_trail = {
        "query": query,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "steps": [],
        "sources_checked": [],
        "review_status": "PENDING"
    }

    try:
        # Step 1: Refine query for better citation-rich results
        refined_query = f'"{query}" type:opinions precedential:true'  # Focus on precedential opinions
        logger.info("Refined Query: %s", refined_query)
        audit_trail["steps"].append({"step": "query_refinement", "details": refined_query})

        # Step 2: Retrieve cases from CourtListener API
        logger.info("STEP 1: Retrieving documents from CourtListener API")
        docs = retrieve_documents(refined_query, k=10)
        logger.info("Retrieved %d documents", len(docs) if docs else 0)
        audit_trail["steps"].append({"step": "document_retrieval", "count": len(docs) if docs else 0})
        audit_trail["sources_checked"].append("CourtListener API")

        if not docs:
            logger.warning("No documents retrieved from CourtListener API")
            audit_trail["steps"].append({"step": "document_retrieval_failed", "details": "No documents found"})
            result = {
                "error": "No relevant cases found for the given query",
                "summary": "No cases found",
                "issues": [],
                "arguments": "Unable to generate arguments without case data",
                "citations": [],
                "analytics": "No data available for analysis",
                "confidence": 0.0,
                "suggestion": "Try a more specific query or check case names (e.g., 'contract breach damages remedies site:law.cornell.edu').",
                "audit_trail": audit_trail
            }
            store_result(user_id, result, audit_trail=audit_trail, review_status=audit_trail["review_status"])
            return result

        # Log document details
        for i, doc in enumerate(docs):
            logger.info("Document %d: %d characters, metadata: %s",
                        i+1, len(doc.page_content), doc.metadata)

        # Step 3: Extract and process text content
        logger.info("STEP 2: Extracting and processing text content")
        doc_texts = [doc.page_content for doc in docs]
        logger.info("Extracted text from %d documents", len(doc_texts))
        audit_trail["steps"].append({"step": "text_extraction", "document_count": len(doc_texts)})

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
                audit_trail["steps"].append({"step": "text_truncation", "document": i+1, "original_length": original_length, "truncated_length": len(limited_text)})
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
            audit_trail["steps"].append({"step": "combined_text_truncation", "original_length": original_combined_length, "truncated_length": len(combined_text)})
        else:
            logger.info("Combined text: %d characters (no truncation needed)",
                        len(combined_text))

        logger.info("Processing %d cases with %d characters of text",
                    len(docs), len(combined_text))

        # Step 4: Extract issues from documents
        logger.info("STEP 3: Extracting legal issues")
        try:
            issues = extract_issues(combined_text)
            logger.info("Successfully extracted %d issues: %s",
                        len(issues), issues)
            audit_trail["steps"].append({"step": "issue_extraction", "issue_count": len(issues)})
        except Exception as e:
            logger.error("Error extracting issues: %s", e)
            issues = []
            audit_trail["steps"].append({"step": "issue_extraction_failed", "error": str(e)})

        # Step 5: Generate summaries
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
            audit_trail["steps"].append({"step": "summary_generation", "success": True})
        except Exception as e:
            logger.error("Error generating summaries: %s", e)
            summaries = "Error occurred during summarization"
            audit_trail["steps"].append({"step": "summary_generation_failed", "error": str(e)})

        # Step 6: Extract and verify citations
        logger.info("STEP 5: Extracting and verifying citations")
        try:
            raw_citations = extract_citations_from_documents(docs)
            logger.info("Extracted %d raw citations from full documents", len(raw_citations))
            audit_trail["steps"].append({"step": "citation_extraction", "citation_count": len(raw_citations)})

            if not raw_citations:
                logger.warning("No raw citations extracted; attempting metadata enrichment fallback")
                raw_citations = enrich_citations_from_metadata(docs)
                audit_trail["steps"].append({"step": "citation_enrichment", "citation_count": len(raw_citations)})

            citations_for_verification = format_citations_for_verification(raw_citations)
            logger.info("Formatted %d citations for verification", len(citations_for_verification))
            audit_trail["steps"].append({"step": "citation_formatting", "formatted_count": len(citations_for_verification)})

            verified_citations = verify_citations(citations_for_verification)
            logger.info("Verified %d citations", len(verified_citations))
            audit_trail["steps"].append({"step": "citation_verification", "verified_count": len(verified_citations)})

            # Check for NEEDS_REVIEW citations
            needs_review = [c for c in verified_citations.get("verified_citations", []) if c.get("status") == "NEEDS_REVIEW"]
            if needs_review:
                audit_trail["review_status"] = "REQUIRES_HUMAN_REVIEW"
                audit_trail["steps"].append({
                    "step": "citation_review_flag",
                    "details": f"{len(needs_review)} citations marked NEEDS_REVIEW",
                    "citations": [c["citation"] for c in needs_review]
                })
        except Exception as e:
            logger.error("Error processing citations: %s", e)
            raw_citations = []
            verified_citations = []
            audit_trail["steps"].append({"step": "citation_processing_failed", "error": str(e)})

        # Step 7: Generate arguments
        logger.info("STEP 6: Generating arguments")
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
            audit_trail["steps"].append({"step": "argument_generation", "success": True})
        except Exception as e:
            logger.error("Error generating arguments: %s", e)
            arguments = "Error occurred during argument generation"
            audit_trail["steps"].append({"step": "argument_generation_failed", "error": str(e)})

        # Step 8: Generate analytics
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
            audit_trail["steps"].append({"step": "analytics_generation", "success": True})
        except Exception as e:
            logger.error("Error generating analytics: %s", e)
            analytics = "Error occurred during analytics generation"
            audit_trail["steps"].append({"step": "analytics_generation_failed", "error": str(e)})

        # Step 9: Calculate confidence and compile results
        logger.info("STEP 8: Calculating confidence and compiling results")
        try:
            confidence = calculate_confidence(docs, verified_citations)
            logger.info("Calculated confidence: %f", confidence)
            audit_trail["steps"].append({"step": "confidence_calculation", "confidence": confidence})

            # Flag non-precedential cases for governance review
            non_precedential = [doc for doc in docs if not doc.metadata.get('precedential')]
            if non_precedential:
                audit_trail["steps"].append({
                    "step": "governance_check",
                    "details": f"{len(non_precedential)} non-precedential cases detected, recommend human review",
                    "case_ids": [doc.metadata.get('caseName', 'Unknown') for doc in non_precedential]
                })
                audit_trail["review_status"] = "REQUIRES_HUMAN_REVIEW"

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
                "source": "CourtListener API",
                "accountability_note": ("Citations or cases marked NEEDS_REVIEW or non-precedential require human validation before use in legal arguments." 
                                       if audit_trail["review_status"] == "REQUIRES_HUMAN_REVIEW" else "All outputs verified, but human review recommended for critical use."),
                "audit_trail": audit_trail
            }

            # Store results with accountability metadata
            store_result(user_id, result, audit_trail=audit_trail, review_status=audit_trail["review_status"])
            logger.info("Stored results for user: %s with review status: %s", user_id, audit_trail["review_status"])

            # Return serialized results for API response
            serialized_result = serialize_results(result)
            logger.info("Serialized results successfully")

            logger.info("=" * 60)
            logger.info("ORCHESTRATION COMPLETED SUCCESSFULLY")
            logger.info("Confidence: %f", confidence)
            logger.info("Case Count: %d", len(docs))
            logger.info("Review Status: %s", audit_trail["review_status"])
            logger.info("=" * 60)
            return serialized_result

        except Exception as e:
            logger.error("Error in final result compilation: %s", e)
            audit_trail["steps"].append({"step": "result_compilation_failed", "error": str(e)})
            result = {
                "error": f"Error in final processing: {str(e)}",
                "summary": "Error occurred during processing",
                "issues": [],
                "arguments": "Unable to generate arguments due to processing error",
                "citations": [],
                "analytics": "No analysis available due to error",
                "confidence": 0.0,
                "audit_trail": audit_trail
            }
            store_result(user_id, result, audit_trail=audit_trail, review_status="ERROR")
            return result

    except Exception as e:
        logger.error("Error in orchestration: %s", e)
        audit_trail["steps"].append({"step": "orchestration_failed", "error": str(e)})
        result = {
            "error": f"Error processing query: {str(e)}",
            "summary": "Error occurred during processing",
            "issues": [],
            "arguments": "Unable to generate arguments due to processing error",
            "citations": [],
            "analytics": "No analysis available due to error",
            "confidence": 0.0,
            "audit_trail": audit_trail
        }
        store_result(user_id, result, audit_trail=audit_trail, review_status="ERROR")
        return result

def calculate_confidence(docs: List, verified_citations: List) -> float:
    """Calculate confidence score based on case quality and quantity"""
    if not docs:
        return 0.0

    base_confidence = 0.5

    # Factor in number of cases
    case_count_factor = min(len(docs) / 10, 0.3)

    # Factor in citation verification
    citation_factor = min(len(verified_citations.get("verified_citations", [])) / 5, 0.2)

    # Factor in case precedential value
    precedential_factor = 0.0
    for doc in docs:
        if doc.metadata.get('precedential'):
            precedential_factor += 0.1

    precedential_factor = min(precedential_factor, 0.2)  # Cap at 0.2

    confidence = base_confidence + case_count_factor + citation_factor + precedential_factor
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

def get_case_alerts(query: str, user_id: str) -> Dict[str, Any]:
    """Create alerts for new cases matching the query"""
    audit_trail = {
        "query": query,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "steps": []
    }
    try:
        alert_name = f"Alert for {query[:50]}..."
        alert_uri = courtlistener_client.create_alert(query, alert_name)
        audit_trail["steps"].append({"step": "alert_creation", "alert_name": alert_name})

        if alert_uri:
            audit_trail["steps"].append({"step": "alert_creation_success", "alert_uri": alert_uri})
            result = {
                "success": True,
                "alert_uri": alert_uri,
                "message": f"Alert created successfully for query: {query}",
                "audit_trail": audit_trail
            }
            store_result(user_id, result, audit_trail=audit_trail, review_status="COMPLETED")
            return result
        else:
            audit_trail["steps"].append({"step": "alert_creation_failed", "details": "Failed to create alert"})
            result = {
                "success": False,
                "message": "Failed to create alert",
                "audit_trail": audit_trail
            }
            store_result(user_id, result, audit_trail=audit_trail, review_status="ERROR")
            return result
    except Exception as e:
        logger.error("Error creating alert: %s", e)
        audit_trail["steps"].append({"step": "alert_creation_error", "error": str(e)})
        result = {
            "success": False,
            "message": f"Error creating alert: {str(e)}",
            "audit_trail": audit_trail
        }
        store_result(user_id, result, audit_trail=audit_trail, review_status="ERROR")
        return result

def enrich_citations_from_metadata(docs: List[Dict]) -> List[Dict[str, Any]]:
    """
    Fallback to enrich citations using document metadata when text extraction fails.
    """
    enriched_citations = []
    for i, doc in enumerate(docs):
        if 'caseName' in doc.metadata and 'cite' in doc.metadata:
            citation_text = f"{doc.metadata['caseName']} {doc.metadata['cite']} ({doc.metadata.get('court', 'Unknown')} {doc.metadata.get('date_filed', 'Unknown')[:4]})"
            citation = {
                "text": citation_text,
                "type": "case_citation",
                "context": doc.page_content[max(0, len(doc.page_content)-50):] if doc.page_content else "No context",
                "position": 0,
                "groups": (doc.metadata['caseName'], doc.metadata['cite'].split()[0], doc.metadata['cite'].split()[1], doc.metadata.get('court'), doc.metadata.get('date_filed', 'Unknown')[:4]),
                "document_index": i,
                "document_length": len(doc.page_content)
            }
            enriched_citations.append(citation)
    logger.info(f"Enriched {len(enriched_citations)} citations from metadata")
    return enriched_citations

def log_user_feedback(user_id: str, feedback: Dict[str, Any]) -> None:
    """Log user feedback for accountability and system improvement"""
    logger.info("Recording user feedback for user: %s, feedback: %s", user_id, feedback)
    # Placeholder: Implement storage logic for feedback
    audit_trail = {
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "feedback": feedback
    }
    # Store feedback with audit trail
    store_result(user_id, {"feedback": feedback}, audit_trail=audit_trail, review_status="FEEDBACK")