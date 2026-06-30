"""
Deployments API router.

Three endpoints (§8):
  - POST /api/deployments/trigger  → create a deployment, start healing
  - GET  /api/deployments          → list all deployments
  - GET  /api/deployments/{id}     → get one deployment with full detail

Design decisions:
  - The trigger endpoint uses `asyncio.create_task` to schedule the healing
    cycle as a background task. This was chosen over FastAPI's `BackgroundTasks`
    because the healing cycle needs its OWN database session (not the request-
    scoped one, which closes when the response is sent). With create_task,
    we explicitly open a new session inside the task.
  - Never returns raw ORM objects — always converts to Pydantic schemas.
"""

import asyncio
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import AsyncSessionLocal, get_db
from app.models.deployment import Deployment, DeploymentStatus
from app.schemas.deployment import DeploymentDetail, DeploymentSummary
from app.services.healing_service import run_healing_cycle
from app.ws.manager import manager

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/deployments", tags=["deployments"])

# Path to the Phase 1 fixture directory (relative to the backend root)
FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "fault_missing_required_argument"


async def _healing_task(deployment_id: uuid.UUID) -> None:
    """
    Wrapper that opens a NEW database session for the background task.

    Why a new session? The request-scoped session (from get_db) is closed
    as soon as the HTTP response is sent. But the healing cycle runs AFTER
    the response — it needs its own session that lives for the duration
    of the healing work.
    """
    async with AsyncSessionLocal() as session:
        try:
            await run_healing_cycle(deployment_id, session)
        except Exception:
            logger.exception(
                "healing.task_crashed",
                deployment_id=str(deployment_id),
            )


# ── POST /api/deployments/trigger ─────────────────────────────────────────
@router.post(
    "/trigger",
    response_model=DeploymentSummary,
    status_code=status.HTTP_201_CREATED,
)
async def trigger_deployment(
    db: AsyncSession = Depends(get_db),
) -> DeploymentSummary:
    """
    Start a new healing cycle.

    Loads the Phase 1 fixture from disk, creates a deployment row with
    status=FAILED, kicks off the healing pipeline as a background task,
    and returns immediately (well under a second).
    """
    # Load fixture files from disk (never mutated, just read)
    broken_code = (FIXTURE_DIR / "main.tf").read_text(encoding="utf-8")
    error_log = (FIXTURE_DIR / "error_log.txt").read_text(encoding="utf-8")

    # Create the deployment row
    deployment = Deployment(
        fault_category="missing_required_argument",
        broken_code=broken_code,
        error_log=error_log,
        status=DeploymentStatus.FAILED.value,
    )
    db.add(deployment)
    await db.commit()
    # Refresh to get server-generated defaults (id, created_at)
    await db.refresh(deployment)

    logger.info(
        "deployment.created",
        deployment_id=str(deployment.id),
        fault_category=deployment.fault_category,
    )

    # Broadcast the initial FAILED state to all WebSocket clients
    # Need to load with attempts for the broadcast shape
    detail = DeploymentDetail.model_validate(deployment)
    await manager.broadcast({
        "type": "deployment_update",
        "data": detail.model_dump(mode="json"),
    })

    # Schedule the healing cycle as a background task
    # This returns immediately — the LLM call and terraform validation
    # happen asynchronously after the response is sent.
    asyncio.create_task(_healing_task(deployment.id))

    return DeploymentSummary.model_validate(deployment)


# ── GET /api/deployments ──────────────────────────────────────────────────
@router.get(
    "",
    response_model=list[DeploymentSummary],
)
async def list_deployments(
    db: AsyncSession = Depends(get_db),
) -> list[DeploymentSummary]:
    """
    List all deployments, newest first.

    No pagination in Phase 1 — there will only be a handful of rows.
    """
    result = await db.execute(
        select(Deployment).order_by(Deployment.created_at.desc())
    )
    deployments = result.scalars().all()

    return [DeploymentSummary.model_validate(d) for d in deployments]


# ── GET /api/deployments/{deployment_id} ──────────────────────────────────
@router.get(
    "/{deployment_id}",
    response_model=DeploymentDetail,
)
async def get_deployment(
    deployment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DeploymentDetail:
    """
    Get a single deployment with full detail including all healing attempts.

    Returns 404 if the deployment doesn't exist.
    """
    result = await db.execute(
        select(Deployment)
        .where(Deployment.id == deployment_id)
        .options(selectinload(Deployment.attempts))
    )
    deployment = result.scalar_one_or_none()

    if deployment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    return DeploymentDetail.model_validate(deployment)
