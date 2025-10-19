from agents.issue.issue_agent import issue_agent
from crewai import Task


def extract_issues(text: str):
    from crewai import Crew

    task = Task(
        description=f"Identify legal issues in: {text}",
        agent=issue_agent,
        expected_output="A structured list of legal issues, doctrines, and precedents found in the text"
    )

    crew = Crew(
        agents=[issue_agent],
        tasks=[task],
        verbose=True
    )

    result = crew.kickoff()
    return result
