from supabase import Client

from app.core.constants import DB_SCHEMA
from app.modules.tenant_members.schemas import TenantMemberCreate, TenantMemberResponse


def _get_user_id_by_email(supabase: Client, email: str) -> str | None:
    """Look up auth user by email and return their id (supabase auth id)."""
    email = email.strip().lower()
    try:
        admin = getattr(supabase, "auth", None) and getattr(supabase.auth, "admin", None)
        if not admin:
            return None
        page = 1
        per_page = 500
        while True:
            users = admin.list_users(page=page, per_page=per_page)
            if not users:
                return None
            for u in users:
                u_email = getattr(u, "email", None)
                if u_email and (u_email.strip().lower() if isinstance(u_email, str) else "") == email:
                    return str(getattr(u, "id", None))
            if len(users) < per_page:
                return None
            page += 1
    except Exception:
        return None


def list_members(supabase: Client, tenant_id: str) -> list[TenantMemberResponse]:
    r = supabase.schema(DB_SCHEMA).table("tenant_members").select("tenant_id, user_id, role, created_at").eq("tenant_id", tenant_id).order("created_at").execute()
    return [TenantMemberResponse(**row) for row in (r.data or [])]


def add_member(supabase: Client, tenant_id: str, payload: TenantMemberCreate) -> TenantMemberResponse:
    user_id = _get_user_id_by_email(supabase, payload.email)
    if not user_id:
        raise ValueError("user_not_found")
    row = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "role": payload.role,
    }
    r = supabase.schema(DB_SCHEMA).table("tenant_members").insert(row).execute()
    data = (r.data or [None])[0]
    if not data:
        raise ValueError("Insert did not return row")
    return TenantMemberResponse(**data)


def update_member(supabase: Client, tenant_id: str, user_id: str, role: str) -> TenantMemberResponse:
    r = supabase.schema(DB_SCHEMA).table("tenant_members").update({"role": role}).eq("tenant_id", tenant_id).eq("user_id", user_id).execute()
    data = (r.data or [None])[0]
    if not data:
        raise ValueError("tenant_member_not_found")
    return TenantMemberResponse(**data)


def remove_member(supabase: Client, tenant_id: str, user_id: str) -> None:
    supabase.schema(DB_SCHEMA).table("tenant_members").delete().eq("tenant_id", tenant_id).eq("user_id", user_id).execute()
