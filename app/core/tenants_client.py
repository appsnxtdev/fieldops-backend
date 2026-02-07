"""HTTP client for core service (tenants, users)."""

import httpx

from app.core.config import Settings, get_settings


def get_tenant(tenant_id: str, settings: Settings | None = None) -> dict | None:
    if settings is None:
        settings = get_settings()
    if not settings.CORE_SERVICE_URL:
        return None
    url = f"{settings.CORE_SERVICE_URL.rstrip('/')}/tenants/{tenant_id}"
    headers = {}
    if settings.CORE_SERVICE_API_KEY:
        headers["Authorization"] = f"Bearer {settings.CORE_SERVICE_API_KEY}"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url, headers=headers or None)
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


def get_core_user_me(token: str, settings: Settings | None = None) -> dict | None:
    """GET core_service/users/me with Bearer token; returns full user details or None."""
    if settings is None:
        settings = get_settings()
    if not settings.CORE_SERVICE_URL or not token:
        return None
    url = f"{settings.CORE_SERVICE_URL.rstrip('/')}/users/me"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url, headers=headers)
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None
