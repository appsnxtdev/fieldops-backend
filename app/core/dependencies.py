from fastapi import Depends, Header, HTTPException
from supabase import Client, create_client
import logging


from app.core.config import Settings, get_settings
from app.core.constants import DB_SCHEMA
from app.core.permissions import has_permission


def get_supabase_client(settings: Settings = Depends(get_settings)) -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_bearer_token(authorization: str | None = Header(None, alias="Authorization")) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    return token


def get_current_user(
    token: str = Depends(get_bearer_token),
    supabase: Client = Depends(get_supabase_client),
) -> dict:
    try:
        response = supabase.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        u = response.user
        return {
            "id": u.id,
            "email": getattr(u, "email", None),
            "raw_user_metadata": getattr(u, "user_metadata") or {},
            "app_metadata": getattr(u, "app_metadata") or {},
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_tenant_id(current_user: dict = Depends(get_current_user)) -> str:
    tenant_id = (current_user.get("app_metadata") or {}).get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Missing tenant_id in token")
    return str(tenant_id)


def _ensure_first_tenant_admin(
    tenant_id: str, user_id: str, supabase: Client
) -> None:
    """If tenant has no members, insert this user as org_admin (bootstrap / secret zero)."""
    existing = (
        supabase.schema(DB_SCHEMA).table("tenant_members")
        .select("user_id")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not existing.data or len(existing.data) == 0:
        try:
            supabase.schema(DB_SCHEMA).table("tenant_members").insert(
                {"tenant_id": tenant_id, "user_id": user_id, "role": "org_admin"}
            ).execute()
        except Exception:
            pass  # race: another request inserted; re-query will return role


def get_tenant_membership(
    tenant_id: str,
    user_id: str,
    supabase: Client = Depends(get_supabase_client),
) -> str | None:
    r = (
        supabase.schema(DB_SCHEMA).table("tenant_members")
        .select("role")
        .eq("tenant_id", tenant_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if r and r.data:
        row = r.data[0] if isinstance(r.data, list) and r.data else r.data
        return row.get("role") if isinstance(row, dict) else None
    _ensure_first_tenant_admin(tenant_id, user_id, supabase)
    r2 = (
        supabase.schema(DB_SCHEMA).table("tenant_members")
        .select("role")
        .eq("tenant_id", tenant_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if r2 and r2.data:
        row = r2.data[0] if isinstance(r2.data, list) and r2.data else r2.data
        return row.get("role") if isinstance(row, dict) else None
    return None


def require_tenant_org_admin(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> str:
    logging.info(f"Checking tenant org_admin for user {current_user['id']} in tenant {tenant_id}")
    role = get_tenant_membership(tenant_id, current_user["id"], supabase)
    if role != "org_admin":
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


def get_project_access(required_permission: str):
    """Dependency factory: ensure user has access to project and required permission. Org admins have access to all projects in their tenant."""

    def _get_project_access(
        project_id: str,
        tenant_id: str = Depends(get_tenant_id),
        current_user: dict = Depends(get_current_user),
        supabase: Client = Depends(get_supabase_client),
    ) -> dict:
        proj_result = (
            supabase.schema(DB_SCHEMA).table("projects")
            .select("id, tenant_id")
            .eq("id", project_id)
            .maybe_single()
            .execute()
        )
        proj = _first_row(proj_result)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        if str(proj.get("tenant_id")) != str(tenant_id):
            raise HTTPException(status_code=403, detail="Project not in your tenant")
        tenant_role = get_tenant_membership(tenant_id, current_user["id"], supabase)
        if tenant_role == "org_admin":
            return {"project_id": project_id, "tenant_id": tenant_id, "role": "admin"}
        mem_result = (
            supabase.schema(DB_SCHEMA).table("project_members")
            .select("role")
            .eq("project_id", project_id)
            .eq("user_id", current_user["id"])
            .maybe_single()
            .execute()
        )
        mem = _first_row(mem_result)
        if not mem:
            raise HTTPException(status_code=403, detail="Not a project member")
        role = mem.get("role") or "viewer"
        if not has_permission(role, required_permission):
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return {"project_id": project_id, "tenant_id": tenant_id, "role": role}

    return _get_project_access
