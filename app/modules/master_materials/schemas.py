from pydantic import BaseModel


class MasterMaterialCreate(BaseModel):
    name: str
    unit: str


class MasterMaterialUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None


class MasterMaterialResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    unit: str
    created_at: str | None = None
