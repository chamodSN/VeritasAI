from crewai import Crew, Task
from agents.argument.argument_agent import argument_agent
from agents.analytics.analytics_agent import analytics_agent
from agents.summary.summarization_agent import summarization_agent
from model.issue_extractor import extract_issues
from model.citation_verifier import verify_citations
from common.logging import logger
from model.courtlistener_client import courtlistener_client
from common.responsible_ai import rai_framework
from common.encryption import secure_storage
from typing import Dict, Any, List
from datetime import datetime


def serialize_results(result: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize CrewAI results for storage"""
    serialized = {}
    for key, value in result.items():
        if hasattr(value, 'raw'):  # CrewAI output
            serialized[key] = str(value.raw)
        elif hasattr(value, 'model_dump'):  # Pydantic model
            serialized[key] = value.model_dump()
        else:
            serialized[key] = value
    return serialized


def orchestrate_query_with_text(query: str, user_id: str, document_text: str) -> Dict[str, Any]:
    """
    Enhanced orchestration for PDF document analysis using provided text
    with responsible AI checks and improved case processing
    """
    logger.info("Starting PDF document orchestration for: %s", query)

    try:
        # Step 1: Extract issues from the document text
        issues = extract_issues(document_text)
        logger.info("Extracted %d issues from document", len(issues))

        # Step 2: Extract citations from the document
        citations = []
        try:
            from agents.citation.citation_service import citation_extractor
            citations = citation_extractor.extract_citations_from_text(document_text)
            logger.info("Extracted %d citations from document", len(citations))
        except Exception as e:
            logger.error("Error extracting citations: %s", e)
            citations = []

        # Step 3: Generate comprehensive summary using summarization agent
        try:
            summary_task = Task(
                description=f"Create a comprehensive summary of this legal document. Focus on key legal principles, main arguments, and important findings. Document text: {document_text[:2000]}...",
                agent=summarization_agent,
                expected_output="Well-structured summary including key legal principles, main arguments, court findings, and legal significance"
            )

            summary_crew = Crew(
                agents=[summarization_agent],
                tasks=[summary_task],
                verbose=True
            )
            summary = summary_crew.kickoff()
            logger.info("Generated comprehensive summary")
        except Exception as e:
            logger.error("Error generating summary: %s", e)
            summary = "Error occurred during summary generation"

        # Step 4: Generate comprehensive arguments using argument agent
        try:
            arg_task = Task(
                description=f"Analyze the legal arguments presented in this document. Identify main arguments, supporting evidence, and legal reasoning. Document text: {document_text[:2000]}... Issues identified: {issues[:10]}",
                agent=argument_agent,
                expected_output="Comprehensive analysis of legal arguments including main points, supporting evidence, and legal reasoning"
            )

            arg_crew = Crew(
                agents=[argument_agent],
                tasks=[arg_task],
                verbose=True
            )
            arguments = arg_crew.kickoff()
            logger.info("Generated comprehensive arguments")
        except Exception as e:
            logger.error("Error generating arguments: %s", e)
            arguments = "Error occurred during argument generation"

        # Step 5: Generate enhanced analytics using analytics agent
        try:
            analytics_task = Task(
                description=f"Analyze this legal document for patterns, legal trends, and insights. Consider the legal principles, court reasoning, and precedential value. Document text: {document_text[:2000]}...",
                agent=analytics_agent,
                expected_output="Comprehensive analysis including legal patterns, precedential analysis, and insights about the document's legal significance"
            )

            analytics_crew = Crew(
                agents=[analytics_agent],
                tasks=[analytics_task],
                verbose=True
            )
            analytics = analytics_crew.kickoff()
            logger.info("Generated enhanced analytics")
        except Exception as e:
            logger.error("Error generating analytics: %s", e)
            analytics = "Error occurred during analytics generation"

        # Step 6: Compile results
        result = {
            "summary": str(summary.raw) if hasattr(summary, 'raw') else str(summary),
            "issues": issues,
            "arguments": str(arguments.raw) if hasattr(arguments, 'raw') else str(arguments),
            "citations": citations,
            "analytics": str(analytics.raw) if hasattr(analytics, 'raw') else str(analytics),
            "document_length": len(document_text),
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "query": query
        }

        # Step 7: Run responsible AI checks
        try:
            rai_checks = rai_framework.run_comprehensive_checks(query, result, [])
            # Serialize RAI checks before adding to result
            serialized_rai_checks = [check.model_dump() if hasattr(check, 'model_dump') else check.__dict__ for check in rai_checks]
            result["responsible_ai_checks"] = serialized_rai_checks
            
            # Calculate RAI metrics
            rai_metrics = rai_framework.calculate_overall_score(rai_checks)
            result["rai_metrics"] = {
                "explainability_score": rai_metrics.explainability_score,
                "fairness_score": rai_metrics.fairness_score,
                "robustness_score": rai_metrics.robustness_score,
                "transparency_score": rai_metrics.transparency_score,
                "privacy_score": rai_metrics.privacy_score,
                "overall_score": rai_metrics.overall_score
            }
            logger.info("RAI checks completed successfully")
        except Exception as rai_error:
            logger.error("Error in RAI checks: %s", rai_error)
            result["responsible_ai_checks"] = []
            result["rai_metrics"] = {
                "explainability_score": 0.0,
                "fairness_score": 0.0,
                "robustness_score": 0.0,
                "transparency_score": 0.0,
                "privacy_score": 0.0,
                "overall_score": 0.0
            }

        # Store encrypted results
        from model.user_model import store_result
        serialized_result = serialize_results(result)
        # Add query to the result data for linking
        serialized_result["original_query"] = query
        encrypted_result = secure_storage.store_analysis_result(user_id, serialized_result)
        store_result(user_id, encrypted_result, original_query=query)
        logger.info("Stored encrypted PDF analysis results for user: %s with query: %s", user_id, query)

        return result

    except Exception as e:
        logger.error("Error in PDF orchestration: %s", e)
        return {
            "summary": "Error occurred during PDF analysis",
            "issues": [],
            "arguments": "Error occurred during argument analysis",
            "citations": [],
            "analytics": "Error occurred during analytics generation",
            "error": str(e)
        }


def orchestrate_query(query: str, user_id: str) -> Dict[str, Any]:
    """
    Enhanced orchestration for legal research query using CourtListener API
    with responsible AI checks and improved case processing
    """
    logger.info("Starting orchestration for query: %s", query)

    try:
        # Step 1: Enhanced case retrieval from CourtListener API
        cases = courtlistener_client.comprehensive_search(query, max_cases=30)
        logger.info("Retrieved %d cases from comprehensive search", len(cases))

        if not cases:
            logger.warning("No cases retrieved from CourtListener API")
            return {
                "error": "No relevant cases found for the given query",
                "summary": "No cases found",
                "issues": [],
                "arguments": "Unable to generate arguments without case data",
                "citations": [],
                "analytics": "No data available for analysis",
                "confidence": 0.0,
                "responsible_ai_checks": [],
                "case_count": 0,
                "source": "CourtListener API"
            }

        # Step 2: Get case texts and clean data
        case_ids = [case.cluster_id for case in cases if case.cluster_id]
        case_texts = courtlistener_client.get_multiple_cases_text(case_ids)
        
        # Filter cases with sufficient text
        valid_cases = []
        for case in cases:
            case_id = case.cluster_id if case.cluster_id else None
            if case_id and case_id in case_texts and len(case_texts[case_id]) > 500:
                valid_cases.append(case)
        
        logger.info("Found %d cases with sufficient text content", len(valid_cases))
        
        if not valid_cases:
            logger.warning("No cases with sufficient text content")
            return {
                "error": "No cases with sufficient text content found",
                "summary": "No analyzable cases found",
                "issues": [],
                "arguments": "Unable to generate arguments without sufficient case data",
                "citations": [],
                "analytics": "No data available for analysis",
                "confidence": 0.0,
                "responsible_ai_checks": [],
                "case_count": 0,
                "source": "CourtListener API"
            }

        # Step 3: Extract and process text content
        case_data = []
        combined_text = ""
        
        for case in valid_cases[:10]:  # Limit to top 10 cases for processing
            case_id = case.cluster_id if case.cluster_id else None
            if case_id and case_id in case_texts:
                text = case_texts[case_id]
                case_info = {
                    'case_name': case.case_name,
                    'court': case.court,
                    'date_filed': case.date_filed,
                    'precedential': case.precedential,
                    'case_text': text,
                    'resource_uri': case.resource_uri
                }
                case_data.append(case_info)
                combined_text += f"\n\n{text[:2000]}"  # Limit each case text

        # Step 4: Extract legal issues using enhanced method
        try:
            issues = extract_issues(combined_text)
            logger.info("Extracted %d legal issues", len(issues))
        except Exception as e:
            logger.error("Error extracting issues: %s", e)
            issues = []

        # Step 5: Generate summaries using multiple cases
        try:
            summary_task = Task(
                description=f"Summarize the following legal cases from CourtListener API. Focus on key legal points, rulings, precedents, and how they relate to the query: '{query}'. Cases: {combined_text[:4000]}",
                agent=summarization_agent,
                expected_output="A comprehensive summary highlighting key legal principles, rulings, and precedents from the cases, organized by relevance to the query"
            )

            summary_crew = Crew(
                agents=[summarization_agent],
                tasks=[summary_task],
                verbose=True
            )
            summaries = summary_crew.kickoff()
            logger.info("Generated comprehensive summaries")
        except Exception as e:
            logger.error("Error generating summaries: %s", e)
            summaries = "Error occurred during summarization"

        # Step 6: Enhanced citation extraction and verification
        try:
            from agents.citation.citation_service import citation_extractor
            
            # Extract citations from all cases
            all_citations = []
            for case_info in case_data:
                citations = citation_extractor.extract_citations_from_text(case_info['case_text'])
                all_citations.extend(citations)
            
            # Remove duplicates and rank by relevance
            unique_citations = list(set(all_citations))
            ranked_citations = citation_extractor.rank_citations_by_relevance(unique_citations, query)
            
            # Verify citations using CourtListener API
            citations_for_verification = ranked_citations[:20]  # Limit to top 20
            verified_citations = verify_citations(citations_for_verification)
            
            logger.info("Extracted %d unique citations, verified %d", 
                       len(unique_citations), len(verified_citations))
        except Exception as e:
            logger.error("Error processing citations: %s", e)
            ranked_citations = []
            verified_citations = []

        # Step 7: Generate comprehensive arguments
        try:
            arg_task = Task(
                description=f"Generate comprehensive legal arguments for query '{query}' using the identified issues: {issues[:10]} and case summaries: {summaries}. Consider multiple perspectives and precedential value.",
                agent=argument_agent,
                expected_output="Well-structured legal arguments including supporting precedents, counterarguments, and analysis of legal principles"
            )

            arg_crew = Crew(
                agents=[argument_agent],
                tasks=[arg_task],
                verbose=True
            )
            arguments = arg_crew.kickoff()
            logger.info("Generated comprehensive arguments")
        except Exception as e:
            logger.error("Error generating arguments: %s", e)
            arguments = "Error occurred during argument generation"

        # Step 8: Generate enhanced analytics
        try:
            analytics_task = Task(
                description=f"Analyze legal patterns, trends, and insights for query: {query}. Consider case precedents, court jurisdictions, temporal patterns, and legal evolution. Cases: {len(case_data)} cases from various courts.",
                agent=analytics_agent,
                expected_output="Comprehensive analysis including jurisdictional patterns, temporal trends, precedential analysis, and legal insights"
            )

            analytics_crew = Crew(
                agents=[analytics_agent],
                tasks=[analytics_task],
                verbose=True
            )
            analytics = analytics_crew.kickoff()
            logger.info("Generated enhanced analytics")
        except Exception as e:
            logger.error("Error generating analytics: %s", e)
            analytics = "Error occurred during analytics generation"

        # Step 9: Calculate enhanced confidence and compile results
        try:
            confidence = calculate_enhanced_confidence(case_data, verified_citations, issues)
            logger.info("Calculated enhanced confidence: %f", confidence)

            # Compile results
            result = {
                "summary": summaries,
                "issues": issues,
                "arguments": arguments,
                "citations": verified_citations,
                "raw_citations": ranked_citations,
                "analytics": analytics,
                "confidence": confidence,
                "case_count": len(case_data),
                "case_data": case_data,  # Include full case data with text
                "source": "CourtListener API Enhanced",
                "case_details": [{
                    "case_name": case['case_name'],
                    "court": case['court'],
                    "date_filed": case['date_filed'],
                    "precedential": case['precedential']
                } for case in case_data]
            }

            # Step 10: Run responsible AI checks
            try:
                rai_checks = rai_framework.run_comprehensive_checks(query, result, case_data)
                # Serialize RAI checks before adding to result
                serialized_rai_checks = [check.model_dump() if hasattr(check, 'model_dump') else check.__dict__ for check in rai_checks]
                result["responsible_ai_checks"] = serialized_rai_checks
                
                # Calculate RAI metrics
                rai_metrics = rai_framework.calculate_overall_score(rai_checks)
                result["rai_metrics"] = {
                    "explainability_score": rai_metrics.explainability_score,
                    "fairness_score": rai_metrics.fairness_score,
                    "robustness_score": rai_metrics.robustness_score,
                    "transparency_score": rai_metrics.transparency_score,
                    "privacy_score": rai_metrics.privacy_score,
                    "overall_score": rai_metrics.overall_score
                }
                logger.info("RAI checks completed successfully")
            except Exception as rai_error:
                logger.error("Error in RAI checks: %s", rai_error)
                result["responsible_ai_checks"] = []
                result["rai_metrics"] = {
                    "explainability_score": 0.0,
                    "fairness_score": 0.0,
                    "robustness_score": 0.0,
                    "transparency_score": 0.0,
                    "privacy_score": 0.0,
                    "overall_score": 0.0
                }

            # Store encrypted results
            from model.user_model import store_result
            serialized_result = serialize_results(result)
            # Add query to the result data for linking
            serialized_result["original_query"] = query
            encrypted_result = secure_storage.store_analysis_result(user_id, serialized_result)
            store_result(user_id, encrypted_result, original_query=query)
            logger.info("Stored encrypted results for user: %s with query: %s", user_id, query)

            # Return serialized results for API response
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
                "confidence": 0.0,
                "responsible_ai_checks": [],
                "case_count": 0,
                "source": "CourtListener API"
            }

    except Exception as e:
        logger.error("Error in enhanced orchestration: %s", e)
        return {
            "error": f"Error processing query: {str(e)}",
            "summary": "Error occurred during processing",
            "issues": [],
            "arguments": "Unable to generate arguments due to processing error",
            "citations": [],
            "analytics": "No analysis available due to error",
            "confidence": 0.0,
            "responsible_ai_checks": [],
            "case_count": 0,
            "source": "CourtListener API"
        }


def calculate_enhanced_confidence(case_data: List[Dict[str, Any]], verified_citations: List, issues: List) -> float:
    """Calculate enhanced confidence score based on multiple factors"""
    if not case_data:
        return 0.0

    base_confidence = 0.4

    # Factor in number of cases (up to 0.2)
    case_count_factor = min(len(case_data) / 15, 0.2)

    # Factor in citation verification (up to 0.2)
    citation_factor = min(len(verified_citations) / 10, 0.2)

    # Factor in precedential value (up to 0.15)
    precedential_cases = [case for case in case_data if case.get('precedential')]
    precedential_factor = min(len(precedential_cases) / len(case_data) * 0.15, 0.15)

    # Factor in case text quality (up to 0.1)
    text_quality_factor = 0.0
    for case in case_data:
        text_length = len(case.get('case_text', ''))
        if text_length > 2000:
            text_quality_factor += 0.02
        elif text_length > 1000:
            text_quality_factor += 0.01
    text_quality_factor = min(text_quality_factor, 0.1)

    # Factor in issues extracted (up to 0.1)
    issues_factor = min(len(issues) / 10, 0.1)

    # Factor in court diversity (up to 0.05)
    courts = set(case.get('court', '') for case in case_data if case.get('court'))
    court_diversity_factor = min(len(courts) / 5, 0.05)

    confidence = (base_confidence + case_count_factor + citation_factor + 
                 precedential_factor + text_quality_factor + issues_factor + 
                 court_diversity_factor)
    
    return min(confidence, 1.0)  # Cap at 1.0

def calculate_confidence(docs: List, verified_citations: List) -> float:
    """Legacy confidence calculation for backward compatibility"""
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
