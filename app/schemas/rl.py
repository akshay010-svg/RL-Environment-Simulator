"""
Pydantic schemas for the RL Engine API.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Action Schemas ────────────────────────────────────────────────────────────

class RLAction(BaseModel):
    """
    An action the RL agent wants to perform.

    Supported action_types:
      - assign_ticket   : requires ticket_id, user_id
      - resolve_ticket  : requires ticket_id
      - create_task     : requires ticket_id, task_description
      - complete_task   : requires task_id
      - update_priority : requires ticket_id, new_priority (low/medium/high)
    """
    action_type: str = Field(
        ...,
        description="One of: assign_ticket, resolve_ticket, create_task, complete_task, update_priority",
    )
    ticket_id: Optional[int] = None
    user_id: Optional[int] = None
    task_id: Optional[int] = None
    task_description: Optional[str] = None
    new_priority: Optional[str] = None


class RLStepRequest(BaseModel):
    episode_id: int
    action: RLAction


# ── Response Schemas ──────────────────────────────────────────────────────────

class TicketObservation(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    assignee_id: Optional[int] = None
    num_tasks: int = 0
    num_completed_tasks: int = 0


class UserObservation(BaseModel):
    id: int
    username: str
    role: str
    num_assigned_tickets: int = 0


class Observation(BaseModel):
    """The state observation returned to the RL agent."""
    episode_id: int
    current_step: int
    max_steps: int
    tickets: list[TicketObservation]
    users: list[UserObservation]


class RLResetResponse(BaseModel):
    observation: Observation
    episode_id: int


class RLStepResponse(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: dict[str, Any] = {}
