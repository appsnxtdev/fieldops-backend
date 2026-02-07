from decimal import Decimal
from pydantic import BaseModel


class MaterialCreate(BaseModel):
    master_material_id: str | None = None  # use catalog entry; name/unit copied
    name: str | None = None  # required if master_material_id not set
    unit: str | None = None  # required if master_material_id not set


class MaterialUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None


class MaterialResponse(BaseModel):
    id: str
    project_id: str
    name: str
    unit: str
    master_material_id: str | None = None
    created_at: str | None = None


class LedgerEntryCreate(BaseModel):
    type: str  # in | out
    quantity: float
    notes: str | None = None


class LedgerEntryResponse(BaseModel):
    id: str
    material_id: str
    type: str
    quantity: float
    notes: str | None = None
    receipt_path: str | None = None
    created_at: str | None = None
    created_by: str | None = None


class MaterialWithBalanceResponse(BaseModel):
    id: str
    project_id: str
    name: str
    unit: str
    balance: float
    master_material_id: str | None = None
    created_at: str | None = None


class ProjectMaterialsSummary(BaseModel):
    project_id: str
    project_name: str
    materials: list[MaterialWithBalanceResponse]
