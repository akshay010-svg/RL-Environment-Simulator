"""
RL Engine – core reset / step / observation / reward logic.

This module is the heart of the simulator.  It manages episodes,
generates randomized CRM scenarios, validates agent actions,
computes reward signals, and checks terminal conditions.
"""

import random
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.episode import Episode
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import UserRole
from app.schemas.rl import (
    Observation,
    RLAction,
    RLResetResponse,
    RLStepResponse,
    TicketObservation,
    UserObservation,
)
from app.services import crm_service

# ── Reward constants ──────────────────────────────────────────────────────────

REWARD_ASSIGN_HIGH = 10.0
REWARD_ASSIGN_MEDIUM = 5.0
REWARD_ASSIGN_LOW = 3.0
REWARD_RESOLVE = 15.0
REWARD_RESOLVE_HIGH_BONUS = 5.0
REWARD_COMPLETE_TASK = 5.0
REWARD_CREATE_TASK = 1.0
REWARD_UPDATE_PRIORITY = 0.5
REWARD_INVALID_ACTION = -1.0
REWARD_TIME_PENALTY = -0.1

# ── Dummy data pools ─────────────────────────────────────────────────────────

_TICKET_TITLES = [
    "Login page returns 500 error",
    "Unable to export CSV report",
    "Dashboard widgets not loading",
    "API rate-limiting misconfigured",
    "SSO integration broken after update",
    "Billing invoice shows wrong amount",
    "User permissions not syncing",
    "Search index out of date",
    "Email notifications delayed",
    "Mobile app crashes on launch",
]

_TICKET_DESCRIPTIONS = [
    "Customer reports this issue is blocking their workflow.",
    "Reproducible on multiple browsers. Needs urgent investigation.",
    "Intermittent issue – seems to happen under high load.",
    "Regression introduced in last deployment.",
    "Multiple enterprise clients have escalated this.",
]

_AGENT_NAMES = [
    "agent_alice", "agent_bob", "agent_carol",
    "agent_dave", "agent_eve", "agent_frank",
]


# ══════════════════════════════════════════════════════════════════════════════
#  OBSERVATION BUILDER
# ══════════════════════════════════════════════════════════════════════════════

async def _build_observation(
    db: AsyncSession, episode: Episode
) -> Observation:
    """Build a JSON-serializable observation of the current CRM state."""
    tickets = await crm_service.list_tickets(db, episode_id=episode.id)
    users = await crm_service.list_users(db)

    ticket_obs = [
        TicketObservation(
            id=t.id,
            title=t.title,
            status=t.status.value,
            priority=t.priority.value,
            assignee_id=t.assignee_id,
            num_tasks=len(t.tasks),
            num_completed_tasks=sum(1 for task in t.tasks if task.is_completed),
        )
        for t in tickets
    ]

    # Count tickets assigned per user (scoped to this episode)
    assigned_counts: dict[int, int] = {}
    for t in tickets:
        if t.assignee_id is not None:
            assigned_counts[t.assignee_id] = (
                assigned_counts.get(t.assignee_id, 0) + 1
            )

    user_obs = [
        UserObservation(
            id=u.id,
            username=u.username,
            role=u.role.value,
            num_assigned_tickets=assigned_counts.get(u.id, 0),
        )
        for u in users
    ]

    return Observation(
        episode_id=episode.id,
        current_step=episode.current_step,
        max_steps=episode.max_steps,
        tickets=ticket_obs,
        users=user_obs,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  RESET
# ══════════════════════════════════════════════════════════════════════════════

async def reset(db: AsyncSession) -> RLResetResponse:
    """
    End any active episodes, seed a fresh CRM scenario, and return
    the initial observation.
    """
    # 1. Deactivate all currently active episodes
    await db.execute(
        update(Episode).where(Episode.is_active.is_(True)).values(is_active=False)
    )

    # 2. Create a new episode
    episode = Episode(
        current_step=0,
        max_steps=settings.RL_MAX_STEPS,
        is_active=True,
        total_reward=0.0,
    )
    db.add(episode)
    await db.flush()
    await db.refresh(episode)

    # 3. Ensure we have enough support agents
    existing_users = await crm_service.list_users(db)
    existing_names = {u.username for u in existing_users}
    agents_needed = settings.RL_NUM_AGENTS - len(existing_users)

    available_names = [n for n in _AGENT_NAMES if n not in existing_names]
    for i in range(max(0, agents_needed)):
        name = available_names[i] if i < len(available_names) else f"agent_{i}"
        await crm_service.create_user(
            db, username=name, password="simulated", role=UserRole.support_agent
        )

    # 4. Seed randomized tickets for this episode
    priorities = list(TicketPriority)
    for _ in range(settings.RL_NUM_TICKETS):
        title = random.choice(_TICKET_TITLES)
        desc = random.choice(_TICKET_DESCRIPTIONS)
        priority = random.choice(priorities)
        await crm_service.create_ticket(
            db,
            title=title,
            description=desc,
            priority=priority,
            episode_id=episode.id,
        )

    await db.flush()

    # 5. Build and return initial observation
    observation = await _build_observation(db, episode)
    return RLResetResponse(observation=observation, episode_id=episode.id)


# ══════════════════════════════════════════════════════════════════════════════
#  STEP
# ══════════════════════════════════════════════════════════════════════════════

async def step(
    db: AsyncSession, episode_id: int, action: RLAction
) -> RLStepResponse:
    """
    Execute one RL step: validate action → apply transition → compute reward
    → check terminal condition → return new observation.
    """
    # ── Fetch episode ─────────────────────────────────────────────────────
    from sqlalchemy import select as sa_select
    result = await db.execute(
        sa_select(Episode).where(Episode.id == episode_id)
    )
    episode = result.scalar_one_or_none()

    if episode is None:
        return _error_response(episode_id, "Episode not found.")

    if not episode.is_active:
        obs = await _build_observation(db, episode)
        return RLStepResponse(
            observation=obs,
            reward=0.0,
            done=True,
            info={"error": "Episode is already terminated."},
        )

    # ── Execute action & compute reward ───────────────────────────────────
    reward, info = await _execute_action(db, episode, action)

    # Apply time penalty
    reward += REWARD_TIME_PENALTY

    # ── Update episode state ──────────────────────────────────────────────
    episode.current_step += 1
    episode.total_reward += reward

    # ── Check terminal conditions ─────────────────────────────────────────
    done = False
    tickets = await crm_service.list_tickets(db, episode_id=episode.id)

    all_resolved = all(t.status == TicketStatus.resolved for t in tickets)
    max_steps_reached = episode.current_step >= episode.max_steps

    if all_resolved:
        done = True
        info["termination_reason"] = "all_tickets_resolved"
    elif max_steps_reached:
        done = True
        info["termination_reason"] = "max_steps_reached"

    if done:
        episode.is_active = False

    await db.flush()

    # ── Build observation ─────────────────────────────────────────────────
    observation = await _build_observation(db, episode)

    return RLStepResponse(
        observation=observation,
        reward=round(reward, 4),
        done=done,
        info=info,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ACTION EXECUTOR
# ══════════════════════════════════════════════════════════════════════════════

async def _execute_action(
    db: AsyncSession,
    episode: Episode,
    action: RLAction,
) -> tuple[float, dict[str, Any]]:
    """
    Validate and execute a single action.
    Returns (reward, info_dict).
    """
    action_type = action.action_type
    info: dict[str, Any] = {"action_type": action_type}

    # ── assign_ticket ─────────────────────────────────────────────────────
    if action_type == "assign_ticket":
        if action.ticket_id is None or action.user_id is None:
            info["error"] = "assign_ticket requires ticket_id and user_id"
            return REWARD_INVALID_ACTION, info

        ticket = await crm_service.get_ticket_by_id(db, action.ticket_id)
        user = await crm_service.get_user_by_id(db, action.user_id)

        if ticket is None:
            info["error"] = f"Ticket {action.ticket_id} not found"
            return REWARD_INVALID_ACTION, info
        if ticket.episode_id != episode.id:
            info["error"] = "Ticket does not belong to this episode"
            return REWARD_INVALID_ACTION, info
        if user is None:
            info["error"] = f"User {action.user_id} not found"
            return REWARD_INVALID_ACTION, info
        if ticket.status == TicketStatus.resolved:
            info["error"] = "Cannot assign an already-resolved ticket"
            return REWARD_INVALID_ACTION, info

        await crm_service.assign_ticket(db, action.ticket_id, action.user_id)
        info["result"] = f"Ticket {action.ticket_id} assigned to user {action.user_id}"

        reward_map = {
            TicketPriority.high: REWARD_ASSIGN_HIGH,
            TicketPriority.medium: REWARD_ASSIGN_MEDIUM,
            TicketPriority.low: REWARD_ASSIGN_LOW,
        }
        return reward_map.get(ticket.priority, REWARD_ASSIGN_LOW), info

    # ── resolve_ticket ────────────────────────────────────────────────────
    elif action_type == "resolve_ticket":
        if action.ticket_id is None:
            info["error"] = "resolve_ticket requires ticket_id"
            return REWARD_INVALID_ACTION, info

        ticket = await crm_service.get_ticket_by_id(db, action.ticket_id)
        if ticket is None:
            info["error"] = f"Ticket {action.ticket_id} not found"
            return REWARD_INVALID_ACTION, info
        if ticket.episode_id != episode.id:
            info["error"] = "Ticket does not belong to this episode"
            return REWARD_INVALID_ACTION, info
        if ticket.status == TicketStatus.resolved:
            info["error"] = "Ticket is already resolved"
            return REWARD_INVALID_ACTION, info
        if ticket.assignee_id is None:
            info["error"] = "Cannot resolve an unassigned ticket"
            return REWARD_INVALID_ACTION, info

        await crm_service.resolve_ticket(db, action.ticket_id)
        info["result"] = f"Ticket {action.ticket_id} resolved"

        reward = REWARD_RESOLVE
        if ticket.priority == TicketPriority.high:
            reward += REWARD_RESOLVE_HIGH_BONUS
        return reward, info

    # ── create_task ───────────────────────────────────────────────────────
    elif action_type == "create_task":
        if action.ticket_id is None or not action.task_description:
            info["error"] = "create_task requires ticket_id and task_description"
            return REWARD_INVALID_ACTION, info

        ticket = await crm_service.get_ticket_by_id(db, action.ticket_id)
        if ticket is None:
            info["error"] = f"Ticket {action.ticket_id} not found"
            return REWARD_INVALID_ACTION, info
        if ticket.episode_id != episode.id:
            info["error"] = "Ticket does not belong to this episode"
            return REWARD_INVALID_ACTION, info
        if ticket.status == TicketStatus.resolved:
            info["error"] = "Cannot add tasks to a resolved ticket"
            return REWARD_INVALID_ACTION, info

        task = await crm_service.create_task(
            db, action.ticket_id, action.task_description
        )
        info["result"] = f"Task {task.id} created for ticket {action.ticket_id}"
        return REWARD_CREATE_TASK, info

    # ── complete_task ─────────────────────────────────────────────────────
    elif action_type == "complete_task":
        if action.task_id is None:
            info["error"] = "complete_task requires task_id"
            return REWARD_INVALID_ACTION, info

        task = await crm_service.get_task_by_id(db, action.task_id)
        if task is None:
            info["error"] = f"Task {action.task_id} not found"
            return REWARD_INVALID_ACTION, info
        if task.is_completed:
            info["error"] = "Task is already completed"
            return REWARD_INVALID_ACTION, info

        # Verify the task's ticket belongs to this episode
        ticket = await crm_service.get_ticket_by_id(db, task.ticket_id)
        if ticket is None or ticket.episode_id != episode.id:
            info["error"] = "Task does not belong to this episode"
            return REWARD_INVALID_ACTION, info

        await crm_service.complete_task(db, action.task_id)
        info["result"] = f"Task {action.task_id} completed"
        return REWARD_COMPLETE_TASK, info

    # ── update_priority ───────────────────────────────────────────────────
    elif action_type == "update_priority":
        if action.ticket_id is None or action.new_priority is None:
            info["error"] = "update_priority requires ticket_id and new_priority"
            return REWARD_INVALID_ACTION, info

        try:
            new_priority = TicketPriority(action.new_priority)
        except ValueError:
            info["error"] = (
                f"Invalid priority '{action.new_priority}'. "
                f"Must be one of: {[p.value for p in TicketPriority]}"
            )
            return REWARD_INVALID_ACTION, info

        ticket = await crm_service.get_ticket_by_id(db, action.ticket_id)
        if ticket is None:
            info["error"] = f"Ticket {action.ticket_id} not found"
            return REWARD_INVALID_ACTION, info
        if ticket.episode_id != episode.id:
            info["error"] = "Ticket does not belong to this episode"
            return REWARD_INVALID_ACTION, info
        if ticket.status == TicketStatus.resolved:
            info["error"] = "Cannot update priority of a resolved ticket"
            return REWARD_INVALID_ACTION, info

        await crm_service.update_ticket(
            db, action.ticket_id, priority=new_priority
        )
        info["result"] = (
            f"Ticket {action.ticket_id} priority → {new_priority.value}"
        )
        return REWARD_UPDATE_PRIORITY, info

    # ── Unknown action ────────────────────────────────────────────────────
    else:
        info["error"] = (
            f"Unknown action_type '{action_type}'. Supported: "
            "assign_ticket, resolve_ticket, create_task, complete_task, update_priority"
        )
        return REWARD_INVALID_ACTION, info


# ── Helpers ───────────────────────────────────────────────────────────────────

def _error_response(episode_id: int, message: str) -> RLStepResponse:
    """Return a terminal error response when the episode itself is invalid."""
    return RLStepResponse(
        observation=Observation(
            episode_id=episode_id,
            current_step=0,
            max_steps=0,
            tickets=[],
            users=[],
        ),
        reward=0.0,
        done=True,
        info={"error": message},
    )
