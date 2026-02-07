from typing import Any

from fastapi import HTTPException


def require_metadata_key(current_user: dict, key: str, expected: Any = None) -> None:
    """Raise 403 if user app_metadata or user_metadata does not have key (or expected value)."""
    metadata = current_user.get("raw_user_metadata") or current_user.get("app_metadata") or {}
    value = metadata.get(key)
    if value is None:
        raise HTTPException(status_code=403, detail=f"Missing required metadata: {key}")
    if expected is not None and value != expected:
        raise HTTPException(status_code=403, detail=f"Forbidden: {key}")
