# agents/citation/styles.py
def format_citation(data: dict) -> str:
    # Stub: replace with proper Bluebook/OSCOLA formatting
    return f"{data.get('title', 'Unknown')} ({data.get('court', '')}, {data.get('date', '')})"
