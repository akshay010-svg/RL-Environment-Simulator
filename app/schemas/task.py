"""
Pydantic schemas for Task request/response payloads.
"""

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    ticket_id: int
    description: str = Field(..., min_length=1)


class TaskUpdate(BaseModel):
    description: str | None = None
    is_completed: bool | None = None


class TaskOut(BaseModel):
    id: int
    ticket_id: int
    description: str
    is_completed: bool

    model_config = {"from_attributes": True}
