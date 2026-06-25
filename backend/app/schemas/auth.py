from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.validation import strip_required_str
from app.models.user import Role


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return strip_required_str(v, field_name="用户名", max_len=64)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    username: str
    role: Role


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str | None = Field(None, max_length=128)
    role: Role = Role.VIEWER

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return strip_required_str(v, field_name="用户名", min_len=3, max_len=64)


class UserOut(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str | None
    role: Role
    is_active: bool

    model_config = {"from_attributes": True}
