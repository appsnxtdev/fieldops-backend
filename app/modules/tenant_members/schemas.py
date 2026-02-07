from pydantic import BaseModel, EmailStr


class TenantMemberCreate(BaseModel):
    email: EmailStr
    role: str  # org_admin | member


class TenantMemberUpdate(BaseModel):
    role: str  # org_admin | member


class TenantMemberResponse(BaseModel):
    tenant_id: str
    user_id: str
    role: str
    created_at: str | None = None
