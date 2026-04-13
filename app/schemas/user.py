"""
Pydantic schemas for User-related request/response payloads.
"""

from pydantic import BaseModel, Field

from app.models.user import UserRole


# ── Request Schemas ───────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.support_agent


class UserLogin(BaseModel):
    username: str
    password: str


# ── Response Schemas ──────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    username: str
    role: UserRole

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
