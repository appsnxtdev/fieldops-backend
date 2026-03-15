from typing import Literal

from pydantic import BaseModel, EmailStr

TenantRole = Literal["org_admin", "member", "viewer", "demo"]


class TenantMemberCreate(BaseModel):
    email: EmailStr
    role: TenantRole


class TenantMemberUpdate(BaseModel):
    role: TenantRole


class TenantMemberResponse(BaseModel):
    tenant_id: str
    user_id: str
    role: str
    created_at: str | None = None
