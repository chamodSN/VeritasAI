from agents.issue_agent import issue_agent
from crewai import Task, Crew
import re


def extract_issues(text: str):
    """Extract legal issues from text using the issue agent"""
    try:
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
        
        # Convert result to string if it's a CrewOutput object
        if hasattr(result, 'raw'):
            result_str = str(result.raw)
        else:
            result_str = str(result)
        
        # Parse the result to extract issues
        if isinstance(result_str, str):
            # Try to extract numbered issues from the text
            issues = []
            
            # Look for numbered lists with bold text (1. **Issue Name**:)
            numbered_pattern = r'(\d+)\.\s*\*\*([^*]+)\*\*:'
            matches = re.findall(numbered_pattern, result_str)
            
            for match in matches:
                issue_text = match[1].strip()
                if issue_text:
                    issues.append(issue_text)
            
            # If no numbered issues found, try alternative patterns
            if not issues:
                # Look for bold text patterns (with colons)
                bold_pattern = r'\*\*([^*]+)\*\*:'
                bold_matches = re.findall(bold_pattern, result_str)
                for match in bold_matches:
                    issue_text = match.strip()
                    if issue_text and len(issue_text) > 5:
                        issues.append(issue_text)
            
            # If still no issues, try to split by common patterns
            if not issues:
                # Split by bullet points or dashes
                lines = result_str.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and ('**' in line or '•' in line or '- ' in line):
                        # Clean up the line
                        clean_line = re.sub(r'^\d+\.\s*', '', line)  # Remove leading numbers
                        clean_line = re.sub(r'^\*\*|\*\*$', '', clean_line)  # Remove bold markers
                        clean_line = re.sub(r'^[•\-]\s*', '', clean_line)  # Remove bullet points
                        clean_line = re.sub(r':\s*$', '', clean_line)  # Remove trailing colons
                        if clean_line and len(clean_line) > 10:  # Only add substantial issues
                            issues.append(clean_line)
            
            return issues[:10]  # Limit to 10 issues
        
        return []
        
    except Exception as e:
        logger.error("Error extracting issues: %s", e)
        return []