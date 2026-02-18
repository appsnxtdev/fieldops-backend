from pydantic import BaseModel


class DailyReportResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    report_date: str
    created_at: str | None = None


class DailyReportListResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    report_date: str
    created_at: str | None = None


class DailyReportEntryCreate(BaseModel):
    report_date: str  # YYYY-MM-DD
    type: str  # photo | note
    content: str  # note text or storage path for photo
    sort_order: int = 0


class DailyReportEntryResponse(BaseModel):
    id: str
    daily_report_id: str
    type: str
    content: str
    sort_order: int
    created_at: str | None = None


class DailyReportEntryWithUser(BaseModel):
    id: str
    daily_report_id: str
    type: str
    content: str
    sort_order: int
    created_at: str | None = None
    user_id: str


class DailyReportDayAggregate(BaseModel):
    photos: list[DailyReportEntryWithUser]
    notes: list[DailyReportEntryWithUser]


class DailyReportsByDateRangeResponse(BaseModel):
    by_date: dict[str, DailyReportDayAggregate]
