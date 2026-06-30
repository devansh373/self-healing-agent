"""
FastAPI application entry point.

Creates the app, wires up middleware and routers, and runs one-time
startup logic (logging configuration) via the lifespan context manager.

No business logic lives here — this file is purely wiring/glue.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.health import router as health_router
from app.api.deployments import router as deployments_router
from app.api.websocket import router as websocket_router


# ── Lifespan ──────────────────────────────────────────────────────────────
# The lifespan context manager runs code at two points:
#   1. Before the first request is served (startup)
#   2. After the last request is served (shutdown)
#
# It replaces the older @app.on_event("startup") / @app.on_event("shutdown")
# decorators, which are deprecated in recent FastAPI versions.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ── Startup ───────────────────────────────────────────────────────────
    setup_logging()

    # yield marks the boundary: startup code above, shutdown code below.
    # The app serves requests while "paused" at this yield.
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────
    # Nothing to clean up in Phase 1 (connection pool disposal is handled
    # automatically by SQLAlchemy's engine). Add cleanup here if needed later.


# ── App creation ──────────────────────────────────────────────────────────
app = FastAPI(
    title="Self-Healing Infrastructure Agent",
    description="Phase 1 — Local Foundation / Walking Skeleton",
    version="0.1.0",
    lifespan=lifespan,
)


# ── CORS middleware ───────────────────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) controls which websites can call
# this API from a browser. Without this, the Next.js frontend at
# localhost:3000 would be blocked from making requests to this API at
# localhost:8000 — browsers enforce same-origin policy by default.
#
# We restrict origins to ONLY what's in our config (the frontend URL),
# not allow_origins=["*"] which would let any website call our API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────
# Each router is a modular group of endpoints defined in its own file.
# include_router() attaches them to the main app.
app.include_router(health_router)
app.include_router(deployments_router)
app.include_router(websocket_router)
