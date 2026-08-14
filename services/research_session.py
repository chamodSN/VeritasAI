from __future__ import annotations

from db.user_repository import UserRepository

SIMILARITY_MIN_SHARED_WORDS = 2


def _keywords(text: str) -> set[str]:
    stop = {"the", "a", "an", "of", "in", "on",
            "for", "and", "or", "to", "is", "are"}
    return {w.lower() for w in text.split() if len(w) > 3 and w.lower() not in stop}


async def get_prior_context(repo: UserRepository, user_id: str, query: str) -> str | None:
    """Looks at the user's recent research history and, if a prior query shares
    meaningful overlap with the current one, surfaces its summary as context so
    the pipeline can build on earlier findings instead of starting from scratch."""
    recent = await repo.get_user_results(user_id, limit=10)
    if not recent:
        return None

    current_keywords = _keywords(query)
    if not current_keywords:
        return None

    best_match = None
    best_overlap = 0

    for item in recent:
        prior_query = item.get("query", "")
        overlap = len(current_keywords & _keywords(prior_query))
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = item

    if best_match and best_overlap >= SIMILARITY_MIN_SHARED_WORDS:
        prior_summary = best_match.get("result", {}).get("summary", "")
        if prior_summary:
            return f"Prior research on a related query found:\n{prior_summary[:1500]}"

    return None
