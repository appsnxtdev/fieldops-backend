import hashlib
import logging
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, Query
from supabase import Client, create_client

from app.core.cache import CacheKeys, cache_delete, cache_get, cache_set, get_redis_client, token_hash
from app.core.config import Settings, get_settings
from app.core.constants import DB_SCHEMA
from app.core.permissions import READ_PERMISSIONS, has_permission
from app.core.tenants_client import get_core_user_role

logger = logging.getLogger(__name__)


@lru_cache()
def _get_supabase_singleton() -> Client | None:
    """
    Return a Supabase Client singleton with connection pooling.
    Decorated with @lru_cache so the same instance is reused across all requests.
    Returns None if SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY are not configured.
    """
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase not configured (missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY)")
        return None
    try:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    except Exception as exc:
        logger.error(f"Failed to create Supabase client: {exc}")
        return None


def get_supabase_client() -> Client:
    """
    FastAPI dependency that returns the singleton Supabase client.
    Raises HTTPException if Supabase is not configured.
    """
    client = _get_supabase_singleton()
    if client is None:
        raise HTTPException(status_code=503, detail="Supabase not configured (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)")
    return client


def get_bearer_token(authorization: str | None = Header(None, alias="Authorization")) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    t = authorization.removeprefix("Bearer ").strip()
    if not t:
        raise HTTPException(status_code=401, detail="Missing token")
    return t


def get_current_user(
    token: str = Depends(get_bearer_token),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
) -> dict:
    key = CacheKeys.auth_user(token_hash(token))
    cached = cache_get(redis, key)
    if cached is not None:
        return cached
    try:
        response = supabase.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        u = response.user
        user_dict = {
            "id": u.id,
            "email": getattr(u, "email", None),
            "raw_user_metadata": getattr(u, "user_metadata") or {},
            "app_metadata": getattr(u, "app_metadata") or {},
        }
        cache_set(redis, key, user_dict, ttl=300)
        return user_dict
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_tenant_id(current_user: dict = Depends(get_current_user)) -> str:
    tenant_id = (current_user.get("app_metadata") or {}).get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Missing tenant_id in token")
    return str(tenant_id)


def _ensure_first_tenant_admin(
    tenant_id: str,
    user_id: str,
    supabase: Client,
    token: str | None = None,
    settings: Settings | None = None,
) -> None:
    """Bootstrap the first org_admin for a new tenant.

    Validates the user's role in core_service before granting org_admin.
    If the tenant already has members this is a no-op.
    Raises 403 if the user is not an admin in core_service.
    """
    existing = (
        supabase.schema(DB_SCHEMA).table("tenant_members")
        .select("user_id")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if existing.data and len(existing.data) > 0:
        return  # tenant already has members — nothing to bootstrap

    # New tenant: validate the user is an admin in core_service before creating org_admin
    core_role = get_core_user_role(token, settings=settings) if token else None
    if core_role != "admin":
        raise HTTPException(
            status_code=403,
            detail=(
                "The organisation is not created yet, ask your admin to login once "
                "and then add you to the projects"
            ),
        )

    try:
        supabase.schema(DB_SCHEMA).table("tenant_members").insert(
            {"tenant_id": tenant_id, "user_id": user_id, "role": "org_admin"}
        ).execute()
    except Exception:
        pass  # race condition: another request inserted first; re-query will return the role


def get_tenant_membership(
    tenant_id: str,
    user_id: str,
    supabase: Client,
    redis=None,
    token: str | None = None,
    settings: Settings | None = None,
) -> str | None:
    """
    Get user's role in a tenant with multi-level caching.
    - Checks Redis cache first
    - Falls back to database query
    - Caches all roles (org_admin/demo: 5min TTL, others: 1min TTL)
    """
    key = CacheKeys.tenant_member(tenant_id, user_id)

    # Check Redis cache first
    cached = cache_get(redis, key)
    if cached is not None:
        logger.debug(f"Cache HIT for tenant_membership {key}: {cached}")
        return cached

    logger.debug(f"Cache MISS for tenant_membership {key}, querying database")

    try:
        r = (
            supabase.schema(DB_SCHEMA).table("tenant_members")
            .select("role")
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if r and r.data and len(r.data) > 0:
            role = r.data[0].get("role") if isinstance(r.data[0], dict) else None
            if role:
                # Cache all roles with appropriate TTL
                # org_admin and demo: longer TTL (5 min) as these rarely change
                # member/worker: shorter TTL (1 min) to reflect permission changes faster
                ttl = 300 if role in ("org_admin", "demo") else 60
                cache_set(redis, key, role, ttl=ttl)
                logger.debug(f"Cached tenant_membership {key}={role} with TTL={ttl}s")
            return role
    except Exception as e:
        logger.warning(f"Error querying tenant_members: {e}")

    # No membership record found — attempt bootstrap for new tenants.
    # _ensure_first_tenant_admin raises 403 if the tenant already exists with members
    # or if the user is not a core_service admin.
    _ensure_first_tenant_admin(tenant_id, user_id, supabase, token=token, settings=settings)

    try:
        r2 = (
            supabase.schema(DB_SCHEMA).table("tenant_members")
            .select("role")
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if r2 and r2.data and len(r2.data) > 0:
            role = r2.data[0].get("role") if isinstance(r2.data[0], dict) else None
            if role:
                # Cache all roles with appropriate TTL
                ttl = 300 if role in ("org_admin", "demo") else 60
                cache_set(redis, key, role, ttl=ttl)
                logger.debug(f"Cached tenant_membership {key}={role} with TTL={ttl}s (after bootstrap)")
            return role
    except Exception as e:
        logger.warning(f"Error querying tenant_members after bootstrap: {e}")

    return None


def require_tenant_org_admin(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
    token: str = Depends(get_bearer_token),
    settings: Settings = Depends(get_settings),
) -> str:
    logging.info(f"Checking tenant org_admin for user {current_user['id']} in tenant {tenant_id}")
    role = get_tenant_membership(tenant_id, current_user["id"], supabase, redis=redis, token=token, settings=settings)
    if role != "org_admin":
        raise HTTPException(status_code=403, detail="Tenant org_admin required")
    return tenant_id


def require_tenant_admin_or_demo(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
    token: str = Depends(get_bearer_token),
    settings: Settings = Depends(get_settings),
) -> str:
    """Allow org_admin OR demo users. Demo users get read-only data visibility."""
    role = get_tenant_membership(tenant_id, current_user["id"], supabase, redis=redis, token=token, settings=settings)
    if role not in ("org_admin", "demo"):
        raise HTTPException(status_code=403, detail="Tenant org_admin required")
    return tenant_id


def _first_row(result) -> dict | None:
    """Normalize Supabase execute result: return first row dict or None."""
    if result is None or not getattr(result, "data", None):
        return None
    data = result.data
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None


def ensure_project_access(
    supabase: Client, tenant_id: str, user_id: str, project_id: str, required_permission: str,
    redis=None, token: str | None = None, settings: Settings | None = None,
) -> dict:
    """Validate user has access to project and required permission. Returns access dict or raises HTTPException."""
    proj_result = (
        supabase.schema(DB_SCHEMA).table("projects")
        .select("id, tenant_id")
        .eq("id", project_id)
        .limit(1)
        .execute()
    )
    proj = _first_row(proj_result)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    if str(proj.get("tenant_id")) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Project not in your tenant")
    tenant_role = get_tenant_membership(tenant_id, user_id, supabase, redis=redis, token=token, settings=settings)
    if tenant_role == "org_admin":
        return {"project_id": project_id, "tenant_id": tenant_id, "role": "admin", "tenant_role": tenant_role}
    if tenant_role == "demo":
        if required_permission not in READ_PERMISSIONS:
            raise HTTPException(status_code=403, detail="demo_mode")
        return {"project_id": project_id, "tenant_id": tenant_id, "role": "viewer", "tenant_role": tenant_role}
    mem_result = (
        supabase.schema(DB_SCHEMA).table("project_members")
        .select("role")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    mem = _first_row(mem_result)
    if not mem:
        raise HTTPException(status_code=403, detail="Not a project member")
    role = mem.get("role") or "viewer"
    if not has_permission(role, required_permission):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    return {"project_id": project_id, "tenant_id": tenant_id, "role": role, "tenant_role": tenant_role}


def get_project_access(required_permission: str):
    """Dependency factory: ensure user has access to project and required permission."""

    def _get_project_access(
        project_id: str,
        tenant_id: str = Depends(get_tenant_id),
        current_user: dict = Depends(get_current_user),
        supabase: Client = Depends(get_supabase_client),
        redis=Depends(get_redis_client),
        token: str = Depends(get_bearer_token),
        settings: Settings = Depends(get_settings),
    ) -> dict:
        return ensure_project_access(
            supabase, tenant_id, current_user["id"], project_id, required_permission,
            redis=redis, token=token, settings=settings,
        )

    return _get_project_access


def get_project_access_query(required_permission: str):
    """Like get_project_access but project_id from query (for list endpoints)."""

    def _get_project_access(
        project_id: str = Query(..., alias="project_id"),
        tenant_id: str = Depends(get_tenant_id),
        current_user: dict = Depends(get_current_user),
        supabase: Client = Depends(get_supabase_client),
        redis=Depends(get_redis_client),
        token: str = Depends(get_bearer_token),
        settings: Settings = Depends(get_settings),
    ) -> dict:
        return ensure_project_access(
            supabase, tenant_id, current_user["id"], project_id, required_permission,
            redis=redis, token=token, settings=settings,
        )

    return _get_project_access
