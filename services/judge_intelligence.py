from __future__ import annotations

from dataclasses import dataclass, field

from core.logging import logger
from services.courtlistener import courtlistener_client, CaseResult

CL_PEOPLE_URL = "https://www.courtlistener.com/api/rest/v4/people/"


@dataclass
class JudgeProfile:
    name: str
    court: str
    appointing_president: str | None = None
    political_affiliation: str | None = None
    law_school: str | None = None
    date_appointed: str | None = None
    total_opinions: int = 0
    practice_areas: list[str] = field(default_factory=list)
    recent_opinions: list[dict] = field(default_factory=list)


async def _lookup_judge(client, name: str, court: str) -> JudgeProfile | None:
    try:
        data = await client._get_with_retry(CL_PEOPLE_URL, params={"name_last": name.split()[-1]})
    except Exception as exc:
        logger.warning("judge_lookup_failed", name=name, error=str(exc))
        return None

    results = data.get("results", [])
    if not results:
        return None

    person = results[0]
    positions = person.get("positions", []) or []
    appointing_president = None
    date_appointed = None
    if positions:
        pos = positions[0]
        appointing_president = pos.get("appointer")
        date_appointed = pos.get("date_start")

    educations = person.get("educations", []) or []
    law_school = educations[0].get("school") if educations else None

    return JudgeProfile(
        name=person.get("name_full", name),
        court=court,
        appointing_president=appointing_president,
        political_affiliation=person.get("political_affiliation"),
        law_school=law_school,
        date_appointed=date_appointed,
        total_opinions=len(person.get("opinions", []) or []),
    )


async def fetch_judge_profiles(cases: list[CaseResult]) -> list[JudgeProfile]:
    """Look up unique judges referenced in the retrieved cases. Best-effort —
    CourtListener's People API match rate is imperfect, so failures are silent."""
    judges_seen: dict[str, str] = {}
    for case in cases:
        if case.judge and case.judge not in judges_seen:
            judges_seen[case.judge] = case.court

    if not judges_seen:
        return []

    profiles: list[JudgeProfile] = []
    async with courtlistener_client as client:
        for name, court in list(judges_seen.items())[:3]:  # cap lookups
            profile = await _lookup_judge(client, name, court)
            if profile:
                profiles.append(profile)

    logger.info("judge_profiles_fetched", count=len(profiles))
    return profiles
