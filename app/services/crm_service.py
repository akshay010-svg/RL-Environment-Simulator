"""
CRM service – business logic for Users, Tickets, and Tasks.
Decoupled from HTTP so it can be reused by the RL engine.
"""

from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.models.task import Task
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole


# ══════════════════════════════════════════════════════════════════════════════
#  USER OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    role: UserRole = UserRole.support_agent,
) -> User:
    """Create a new user with a hashed password."""
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        role=role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> Optional[User]:
    """Return the User if credentials are valid, else None."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(
    db: AsyncSession, username: str
) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def list_users(db: AsyncSession) -> Sequence[User]:
    result = await db.execute(select(User).order_by(User.id))
    return result.scalars().all()


# ══════════════════════════════════════════════════════════════════════════════
#  TICKET OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

async def create_ticket(
    db: AsyncSession,
    title: str,
    description: str | None = None,
    priority: TicketPriority = TicketPriority.medium,
    episode_id: int | None = None,
) -> Ticket:
    ticket = Ticket(
        title=title,
        description=description,
        priority=priority,
        episode_id=episode_id,
    )
    db.add(ticket)
    await db.flush()
    await db.refresh(ticket)
    return ticket


async def get_ticket_by_id(
    db: AsyncSession, ticket_id: int
) -> Optional[Ticket]:
    result = await db.execute(
        select(Ticket)
        .options(selectinload(Ticket.tasks), selectinload(Ticket.assignee))
        .where(Ticket.id == ticket_id)
    )
    return result.scalar_one_or_none()


async def list_tickets(
    db: AsyncSession, episode_id: int | None = None
) -> Sequence[Ticket]:
    stmt = (
        select(Ticket)
        .options(selectinload(Ticket.tasks), selectinload(Ticket.assignee))
        .order_by(Ticket.id)
    )
    if episode_id is not None:
        stmt = stmt.where(Ticket.episode_id == episode_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def update_ticket(
    db: AsyncSession,
    ticket_id: int,
    **kwargs,
) -> Optional[Ticket]:
    """Update specific fields on a ticket. Returns refreshed ticket or None."""
    # Filter out None values so we only SET explicitly provided fields
    values = {k: v for k, v in kwargs.items() if v is not None}
    if not values:
        return await get_ticket_by_id(db, ticket_id)

    await db.execute(
        update(Ticket).where(Ticket.id == ticket_id).values(**values)
    )
    await db.flush()
    return await get_ticket_by_id(db, ticket_id)


async def assign_ticket(
    db: AsyncSession, ticket_id: int, user_id: int
) -> Optional[Ticket]:
    """Assign a ticket to a user and set status to in_progress."""
    return await update_ticket(
        db,
        ticket_id,
        assignee_id=user_id,
        status=TicketStatus.in_progress,
    )


async def resolve_ticket(
    db: AsyncSession, ticket_id: int
) -> Optional[Ticket]:
    """Mark a ticket as resolved."""
    return await update_ticket(
        db, ticket_id, status=TicketStatus.resolved
    )


async def delete_ticket(db: AsyncSession, ticket_id: int) -> bool:
    ticket = await get_ticket_by_id(db, ticket_id)
    if ticket is None:
        return False
    await db.delete(ticket)
    await db.flush()
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  TASK OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

async def create_task(
    db: AsyncSession, ticket_id: int, description: str
) -> Task:
    task = Task(ticket_id=ticket_id, description=description)
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def get_task_by_id(db: AsyncSession, task_id: int) -> Optional[Task]:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def complete_task(db: AsyncSession, task_id: int) -> Optional[Task]:
    await db.execute(
        update(Task).where(Task.id == task_id).values(is_completed=True)
    )
    await db.flush()
    return await get_task_by_id(db, task_id)


async def list_tasks(
    db: AsyncSession, ticket_id: int | None = None
) -> Sequence[Task]:
    stmt = select(Task).order_by(Task.id)
    if ticket_id is not None:
        stmt = stmt.where(Task.ticket_id == ticket_id)
    result = await db.execute(stmt)
    return result.scalars().all()
