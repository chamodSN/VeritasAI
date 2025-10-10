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

logger = setup_logging()


def orchestrate_query(query: str, user_id: str):
    # Retrieve documents
    docs = retrieve_documents(query)
    doc_texts = [doc.page_content for doc in docs]

    # Limit document text to prevent token overflow
    max_chars_per_doc = 2000  # Limit each document to 2000 characters
    limited_doc_texts = []
    for text in doc_texts:
        if len(text) > max_chars_per_doc:
            limited_doc_texts.append(text[:max_chars_per_doc] + "...")
        else:
            limited_doc_texts.append(text)

    # Combine texts but limit total size
    combined_text = '\n'.join(limited_doc_texts)
    max_total_chars = 5000  # Limit total input to 5000 characters
    if len(combined_text) > max_total_chars:
        combined_text = combined_text[:max_total_chars] + "..."

    # Extract issues from documents
    issues = extract_issues(combined_text)

    # Generate summaries
    summary_task = Task(
        description=f"Summarize the following legal documents (focus on key points): {combined_text}",
        agent=summarization_agent,
        expected_output="A concise summary of the legal documents highlighting key points, rulings, and precedents"
    )

    summary_crew = Crew(
        agents=[summarization_agent],
        tasks=[summary_task],
        verbose=True
    )
    summaries = summary_crew.kickoff()

    # Extract citations from documents
    raw_citations = extract_citations_from_documents(limited_doc_texts)
    citations_for_verification = format_citations_for_verification(
        raw_citations)

    # Verify citations
    verified_citations = verify_citations(citations_for_verification)

    # Generate arguments
    arg_task = Task(
        description=f"Generate legal arguments for query '{query}' using issues: {issues} and summaries: {summaries}",
        agent=argument_agent,
        expected_output="Well-structured legal arguments and counterarguments based on the identified issues and document summaries"
    )

    arg_crew = Crew(
        agents=[argument_agent],
        tasks=[arg_task],
        verbose=True
    )
    arguments = arg_crew.kickoff()

    # Optional analytics
    analytics_task = Task(
        description=f"Analyze patterns and trends for query: {query}",
        agent=analytics_agent,
        expected_output="Analysis of legal patterns, trends, and insights relevant to the query"
    )

    analytics_crew = Crew(
        agents=[analytics_agent],
        tasks=[analytics_task],
        verbose=True
    )
    analytics = analytics_crew.kickoff()

    # Collate results
    result = {
        "summary": summaries,
        "issues": issues,
        "arguments": arguments,
        "citations": verified_citations,
        "raw_citations": raw_citations,  # Include extracted citations for debugging
        "analytics": analytics,
        "confidence": 0.85  # Placeholder
    }

    # Store
    from model.user_model import store_result
    store_result(user_id, result)

    # Return serialized results for API response
    serialized_result = {}
    for key, value in result.items():
        if hasattr(value, 'raw'):  # CrewOutput object
            serialized_result[key] = str(value.raw)
        else:
            serialized_result[key] = value

    return serialized_result
