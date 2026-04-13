"""
RL Engine API – Reset / Step endpoints for AI agent interaction.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.rl import RLResetResponse, RLStepRequest, RLStepResponse
from app.services import rl_engine

router = APIRouter(prefix="/rl", tags=["RL Engine"])


@router.post(
    "/reset",
    response_model=RLResetResponse,
    summary="Reset the environment and start a new episode",
    description=(
        "Terminates any active episodes, seeds a fresh randomized CRM scenario "
        "(support agents + open tickets), and returns the initial observation."
    ),
)
async def rl_reset(db: AsyncSession = Depends(get_db)):
    return await rl_engine.reset(db)


@router.post(
    "/step",
    response_model=RLStepResponse,
    summary="Execute one RL step",
    description=(
        "Submit an action for the given episode. The engine validates the action, "
        "applies the state transition, computes the reward signal, and checks "
        "terminal conditions. Returns the new observation, reward, done flag, "
        "and debug info."
    ),
)
async def rl_step(
    payload: RLStepRequest,
    db: AsyncSession = Depends(get_db),
):
    return await rl_engine.step(db, payload.episode_id, payload.action)
