"""Common HTTP utilities for signing and verifying requests."""
import time
import json

from typing import Dict, Any

from .security import sign_message, verify_message

ALLOWED_SKEW = 300  # 5 minutes


def sign_request(method: str, path: str, body: Dict[str, Any]) -> Dict[str, str]:
    """Generate signed headers for an outgoing request."""
    timestamp = str(int(time.time()))
    body_str = json.dumps(body, separators=(',', ':')) if body else ''
    msg = f"{timestamp}{method.upper()}{path}{body_str}"
    signature = sign_message(msg)

    return {
        "X-A2A-Key": "agent1",  # static for now, rotate later
        "X-A2A-Timestamp": timestamp,
        "X-A2A-Signature": signature,
        "Content-Type": "application/json"
    }


def verify_request(method: str, path: str, body: str, headers: Dict[str, str]) -> bool:
    """Verify the incoming request."""
    try:
        timestamp = int(headers.get("X-A2A-Timestamp", "0"))
        if abs(time.time() - timestamp) > ALLOWED_SKEW:
            return False

        signature = headers.get("X-A2A-Signature", "")
        msg = f"{timestamp}{method.upper()}{path}{body or ''}"
        return verify_message(msg, signature)
    except KeyError:
        return False


def error_response(code: str, message: str) -> Dict[str, Any]:
    """Generate a standardized error response as JSON."""
    return {"error": {"code": code, "message": message}}
