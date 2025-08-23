"""signing and verifying messages securely using HMAC with SHA-256 hashing.
for communication between agents or the main application."""
import hmac
import hashlib
import os

SECRET_KEY = os.getenv("AGENT_SECRET", "default_secret_key")


def sign_message(message: str) -> str:
    """"Signing the Message"""
    return hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()


def verify_message(message: str, signature: str) -> bool:
    """Verifying the Message"""
    expected_signature = sign_message(message)
    return hmac.compare_digest(expected_signature, signature)
