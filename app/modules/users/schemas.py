from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    id: str
    email: str | None
    full_name: str | None = None
    avatar_url: str | None = None
    phone_no: str | None = None
    platform_role: str | None = None
