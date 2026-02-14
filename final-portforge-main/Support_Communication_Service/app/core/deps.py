from fastapi import Header, HTTPException, status
from typing import Optional, Dict, Any


async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    Placeholder auth dependency.
    - If Authorization header is missing, returns a dummy user (temporarily bypass auth).
    - Otherwise, returns a dummy user payload (replace with real verification later).
    """
    # TODO: Replace with real token verification.
    return {
        "id": 1,
        "email": "demo@example.com",
        "name": "Demo User",
        "nickname": "demo",
    }


async def get_optional_user(
    authorization: Optional[str] = Header(None),
) -> Optional[Dict[str, Any]]:
    """Allows unauthenticated access but still returns a dummy user if a header is present."""
    if not authorization:
        return None
    return {
        "id": 1,
        "email": "demo@example.com",
        "name": "Demo User",
        "nickname": "demo",
    }


