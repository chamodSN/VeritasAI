# agents/citation/validators.py

import httpx

def validate_url(url: str) -> tuple[bool, str]:
    if not url:
        return False, ""
    try:
        r = httpx.head(url, timeout=3)
        return r.status_code == 200, url
    except Exception:
        return False, url