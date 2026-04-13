"""
Pydantic schemas for Ticket request/response payloads.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.ticket import TicketPriority, TicketStatus


# ── Request Schemas ───────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: TicketPriority = TicketPriority.medium


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assignee_id: Optional[int] = None


# ── Response Schemas ──────────────────────────────────────────────────────────

class TaskOut(BaseModel):
    id: int
    description: str
    is_completed: bool

    model_config = {"from_attributes": True}


class TicketOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TicketStatus
    priority: TicketPriority
    assignee_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskOut] = []

    model_config = {"from_attributes": True}
