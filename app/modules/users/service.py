from datetime import datetime, timezone
from postgrest.exceptions import APIError
from supabase import Client

from app.core.constants import DB_SCHEMA
from app.modules.users.schemas import UserProfileResponse


def ensure_profile(
    supabase: Client,
    current_user: dict,
    core_user: dict | None = None,
) -> None:
    """Create or sync profile from JWT and/or core service user. Idempotent."""
    meta = current_user.get("raw_user_metadata") or {}
    row = {
        "id": current_user["id"],
        "email": (core_user or {}).get("email") or current_user.get("email"),
        "full_name": (core_user or {}).get("full_name") or meta.get("full_name") or meta.get("name"),
        "avatar_url": (core_user or {}).get("avatar_url") or meta.get("avatar_url"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        supabase.schema(DB_SCHEMA).table("profiles").upsert(row, on_conflict="id").execute()
    except APIError:
        pass


def get_profiles_by_ids(supabase: Client, user_ids: list[str]) -> list[UserProfileResponse]:
    if not user_ids:
        return []
    try:
        r = supabase.schema(DB_SCHEMA).table("profiles").select("id, email, full_name, avatar_url").in_("id", user_ids).execute()
    except APIError:
        return []
    if not r.data:
        return []
    return [
        UserProfileResponse(
            id=row["id"],
            email=row.get("email"),
            full_name=row.get("full_name"),
            avatar_url=row.get("avatar_url"),
        )
        for row in (r.data or [])
    ]


def get_me(supabase: Client, user_id: str) -> UserProfileResponse | None:
    try:
        r = supabase.schema(DB_SCHEMA).table("profiles").select("id, email, full_name, avatar_url").eq("id", user_id).maybe_single().execute()
    except APIError as e:
        if e.code == "204":
            return None
        raise
    if r is None or not r.data:
        return None
    row = r.data[0] if isinstance(r.data, list) else r.data
    if not row:
        return None
    return UserProfileResponse(
        id=row["id"],
        email=row.get("email"),
        full_name=row.get("full_name"),
        avatar_url=row.get("avatar_url"),
    )
