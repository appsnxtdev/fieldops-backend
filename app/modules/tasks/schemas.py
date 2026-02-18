from pydantic import BaseModel


class TaskStatusCreate(BaseModel):
    name: str
    sort_order: int = 0


class TaskStatusUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None


class TaskStatusResponse(BaseModel):
    id: str
    project_id: str
    name: str
    sort_order: int
    created_at: str | None = None


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    status_id: str | None = None
    assignee_id: str | None = None
    due_at: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status_id: str | None = None
    assignee_id: str | None = None
    due_at: str | None = None


class TaskResponse(BaseModel):
    id: str
    project_id: str
    title: str
    description: str | None = None
    status_id: str | None = None
    assignee_id: str | None = None
    assignee_name: str | None = None
    created_by: str | None = None
    due_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class TaskUpdateNoteCreate(BaseModel):
    note: str


class TaskUpdateNoteResponse(BaseModel):
    id: str
    task_id: str
    project_id: str
    author_id: str
    note: str
    created_at: str | None = None
