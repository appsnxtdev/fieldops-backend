from pydantic import BaseModel


class LabourTypeCreate(BaseModel):
    name: str
    rate_per_day: float = 0


class LabourTypeUpdate(BaseModel):
    name: str | None = None
    rate_per_day: float | None = None


class LabourTypeResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    rate_per_day: float
    created_at: str | None = None


class LabourDailyEntryCreate(BaseModel):
    labour_type_id: str
    count: int = 0


class LabourDailyCreate(BaseModel):
    project_id: str
    date: str
    entries: list[LabourDailyEntryCreate]


class LabourDailyCreateBody(BaseModel):
    """Body for POST /daily when project_id is in query."""
    date: str
    entries: list[LabourDailyEntryCreate]


class LabourDailyEntryResponse(BaseModel):
    labour_type_id: str
    labour_type_name: str
    rate_per_day: float
    count: int
    amount: float


class LabourDailyResponse(BaseModel):
    project_id: str
    date: str
    entries: list[LabourDailyEntryResponse]
