from pydantic import BaseModel


class TenantResponse(BaseModel):
    id: str
    name: str | None = None
