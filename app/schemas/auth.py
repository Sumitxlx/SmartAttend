from pydantic import BaseModel, ConfigDict, Field

from app.models import UserRole


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    """What the API is allowed to reveal about a user. No password hash, ever."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole

    