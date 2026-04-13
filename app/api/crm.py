"""
CRM CRUD endpoints for Tickets and Tasks.
These are available for manual inspection / debugging alongside the RL loop.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.task import TaskCreate, TaskOut
from app.schemas.ticket import TicketCreate, TicketOut, TicketUpdate
from app.schemas.user import UserOut
from app.services import crm_service

router = APIRouter(prefix="/crm", tags=["CRM"])


# ══════════════════════════════════════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/users", response_model=list[UserOut], summary="List all CRM users")
async def list_users(db: AsyncSession = Depends(get_db)):
    return await crm_service.list_users(db)


@router.get("/users/me", response_model=UserOut, summary="Get current user profile")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ══════════════════════════════════════════════════════════════════════════════
#  TICKETS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/tickets", response_model=list[TicketOut], summary="List all tickets")
async def list_tickets(
    episode_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await crm_service.list_tickets(db, episode_id=episode_id)


@router.get("/tickets/{ticket_id}", response_model=TicketOut, summary="Get ticket by ID")
async def get_ticket(ticket_id: int, db: AsyncSession = Depends(get_db)):
    ticket = await crm_service.get_ticket_by_id(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post(
    "/tickets",
    response_model=TicketOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ticket",
)
async def create_ticket(
    payload: TicketCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return await crm_service.create_ticket(
        db,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
    )


@router.patch("/tickets/{ticket_id}", response_model=TicketOut, summary="Update a ticket")
async def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    ticket = await crm_service.update_ticket(
        db,
        ticket_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.delete(
    "/tickets/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a ticket",
)
async def delete_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    deleted = await crm_service.delete_ticket(db, ticket_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ticket not found")


# ══════════════════════════════════════════════════════════════════════════════
#  TASKS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/tasks", response_model=list[TaskOut], summary="List tasks")
async def list_tasks(
    ticket_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await crm_service.list_tasks(db, ticket_id=ticket_id)


@router.post(
    "/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task for a ticket",
)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    ticket = await crm_service.get_ticket_by_id(db, payload.ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return await crm_service.create_task(
        db, payload.ticket_id, payload.description
    )


@router.patch(
    "/tasks/{task_id}/complete",
    response_model=TaskOut,
    summary="Mark a task as completed",
)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    task = await crm_service.complete_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
