"""
FastAPI application entry point.

Wires together routers, database lifecycle events, and middleware.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, crm, rl
from app.db.base import Base
from app.models.user import User
from app.models.ticket import Ticket
from app.models.task import Task
from app.models.episode import Episode
from app.db.session import engine

logger = logging.getLogger("uvicorn.error")


# ── Lifespan: startup / shutdown ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup:  create tables if they don't exist (dev convenience).
    On shutdown: dispose of the database engine.
    """
    logger.info("Creating database tables (if not present) …")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database ready.")

    yield  # ← application runs here

    logger.info("Shutting down – disposing DB engine …")
    await engine.dispose()


# ── Application Factory ───────────────────────────────────────────────────────

app = FastAPI(
    title="RL Environment Simulator – B2B Workflows",
    description=(
        "A sandboxed Reinforcement Learning environment that replicates a "
        "realistic CRM workflow. AI agents interact via the /rl endpoints "
        "to learn how to manage B2B support tickets."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (allow everything for local development) ─────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ─────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(crm.router)
app.include_router(rl.router)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "rl-environment-simulator"}
