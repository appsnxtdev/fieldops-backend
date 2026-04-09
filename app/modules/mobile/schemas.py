from pydantic import BaseModel, Field
from typing import Optional, List


# Bulk Sync Schemas
class Location(BaseModel):
    lat: float
    lng: float


class AttendanceToday(BaseModel):
    id: str
    project_id: str
    date: str
    user_id: str
    check_in_at: Optional[str] = None
    check_out_at: Optional[str] = None
    check_in_lat: Optional[float] = None
    check_in_lng: Optional[float] = None
    check_out_lat: Optional[float] = None
    check_out_lng: Optional[float] = None
    check_in_selfie_path: Optional[str] = None
    check_out_selfie_path: Optional[str] = None


class TaskStatus(BaseModel):
    id: str
    name: str
    color: Optional[str] = None


class MyTask(BaseModel):
    id: str
    project_id: str
    title: str
    description: Optional[str] = None
    status_id: str
    status: TaskStatus
    assigned_to: str
    due_date: Optional[str] = None


class Material(BaseModel):
    id: str
    name: str
    current_stock: float = Field(..., serialization_alias='current_stock')
    unit: str

    model_config = {"populate_by_name": True}


class LabourEntry(BaseModel):
    id: str
    labour_type_id: str
    labour_type_name: str
    quantity: float
    unit: str


class LabourToday(BaseModel):
    id: str
    date: str
    labour_entries: List[LabourEntry]


class WalletTransaction(BaseModel):
    id: str
    amount: float
    type: str
    description: Optional[str] = None
    date: str


class Wallet(BaseModel):
    balance: float
    currency: str
    recent_transactions: List[WalletTransaction]


class DailyReportToday(BaseModel):
    id: str
    date: str
    status: str
    submitted_at: Optional[str] = None


class ProjectData(BaseModel):
    id: str
    name: str
    location: Optional[Location] = None
    attendance_today: Optional[AttendanceToday] = Field(None, serialization_alias='attendance_today')
    my_tasks: List[MyTask] = Field(default_factory=list, serialization_alias='my_tasks')
    task_statuses: List[TaskStatus] = Field(default_factory=list)
    materials: List[Material] = Field(default_factory=list)
    labour_today: Optional[LabourToday] = Field(None, serialization_alias='labour_today')
    wallet: Optional[Wallet] = None
    daily_report_today: Optional[DailyReportToday] = Field(None, serialization_alias='daily_report_today')

    model_config = {"populate_by_name": True}


class BulkSyncResponse(BaseModel):
    projects: List[ProjectData]
    last_sync: str


# Master Data Schemas
class LabourType(BaseModel):
    id: str
    name: str
    rate_per_day: float


class MasterMaterial(BaseModel):
    id: str
    name: str
    unit: str


class MasterDataResponse(BaseModel):
    labour_types: List[LabourType]
    master_materials: List[MasterMaterial]
    last_updated: str


# Sync Queue Schemas
class SyncChange(BaseModel):
    id: str  # local UUID
    entity_type: str  # 'attendance', 'task_update', etc.
    operation: str  # 'create', 'update', 'check_in', etc.
    project_id: Optional[str] = None
    payload: dict


class SyncQueueRequest(BaseModel):
    changes: List[SyncChange]


class SyncResult(BaseModel):
    local_id: str
    success: bool
    server_id: Optional[str] = None
    synced_at: Optional[str] = None
    error: Optional[str] = None


class SyncQueueResponse(BaseModel):
    results: List[SyncResult]
