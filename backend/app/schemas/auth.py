from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.models.user import Role


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    username: str
    role: Role


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None
    role: Role = Role.VIEWER


class UserOut(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str | None
    role: Role
    is_active: bool

    model_config = {"from_attributes": True}
