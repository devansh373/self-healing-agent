"""
Healing service — the Phase 1 orchestrator.

This is the "brain" of the self-healing pipeline. It coordinates:
  1. Status transitions on the deployment row
  2. LLM call to generate a fix
  3. Terraform validation of the proposed fix
  4. Recording the attempt in the database
  5. Broadcasting updates over WebSocket at each transition

Exposes one function: `run_healing_cycle(deployment_id, db)`.

Design decisions:
  - Takes a `db: AsyncSession` parameter — the caller (API route) opens a
    NEW session scoped to the background task, not the request-scoped one.
  - Error handling wraps the LLM call (§11.4, §14) so every failure path
    still produces exactly one healing_attempts row and one final broadcast.
  - WebSocket broadcasts happen at each status transition (FAILED → HEALING
    → terminal) so the frontend updates live.
"""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.deployment import Deployment, DeploymentStatus, HealingAttempt
from app.schemas.deployment import DeploymentDetail
from app.services import llm_service
from app.services.terraform_service import validate_terraform
from app.ws.manager import manager

logger = structlog.get_logger(__name__)


async def _fetch_deployment_with_attempts(
    db: AsyncSession, deployment_id: uuid.UUID
) -> Deployment | None:
    """
    Load a deployment with its attempts eagerly loaded.

    Uses selectinload to avoid the N+1 query problem — a single query
    fetches the deployment and all its attempts.
    """
    result = await db.execute(
        select(Deployment)
        .where(Deployment.id == deployment_id)
        .options(selectinload(Deployment.attempts))
    )
    return result.scalar_one_or_none()


async def _broadcast_deployment(deployment: Deployment) -> None:
    """
    Broadcast a deployment's current state to all WebSocket clients.

    Message shape matches §9:
    {
        "type": "deployment_update",
        "data": { ...DeploymentDetail... }
    }
    """
    detail = DeploymentDetail.model_validate(deployment)
    await manager.broadcast({
        "type": "deployment_update",
        "data": detail.model_dump(mode="json"),
    })


async def run_healing_cycle(deployment_id: uuid.UUID, db: AsyncSession) -> None:
    """
    Execute the full healing pipeline for a single deployment.

    This is the entire Phase 1 "brain" — one LLM call, one validation,
    one attempt recorded. Phase 2 will add a retry loop around steps 3-6.

    Steps (§13):
    1. Fetch the deployment row
    2. Set status = HEALING, commit, broadcast
    3. Call LLM to generate a fix
       - On exception: record failure, set FAILED_TO_HEAL, return
    4. Call terraform validate on the proposed fix
    5. Create a healing_attempts row with the results
    6. Set final status (HEALED or FAILED_TO_HEAL), commit, broadcast

    Args:
        deployment_id: UUID of the deployment to heal.
        db: An AsyncSession scoped to THIS background task (not request-scoped).
    """
    log = logger.bind(deployment_id=str(deployment_id))

    # ── Step 1: Fetch the deployment ──────────────────────────────────────
    deployment = await _fetch_deployment_with_attempts(db, deployment_id)
    if deployment is None:
        log.error("healing.deployment_not_found")
        return

    # ── Step 2: Transition to HEALING ─────────────────────────────────────
    deployment.status = DeploymentStatus.HEALING.value
    await db.commit()
    log.info("healing.started")

    # Re-fetch after commit to get fresh state for broadcast
    deployment = await _fetch_deployment_with_attempts(db, deployment_id)
    await _broadcast_deployment(deployment)

    # ── Step 3: Call the LLM ──────────────────────────────────────────────
    try:
        fix_result = await llm_service.generate_fix(
            broken_code=deployment.broken_code,
            error_log=deployment.error_log,
        )
        log.info("llm.fix_generated")
    except Exception as exc:
        # LLM call failed — record the failure and bail out (§14, §11.4)
        log.error("llm.call_failed", error=str(exc), exc_info=True)

        attempt = HealingAttempt(
            deployment_id=deployment_id,
            attempt_number=1,
            llm_explanation=f"LLM call failed: {exc}",
            fixed_code="",
            validation_success=False,
            validation_output=None,
        )
        db.add(attempt)

        deployment.status = DeploymentStatus.FAILED_TO_HEAL.value
        deployment.resolved_at = datetime.now(timezone.utc)
        await db.commit()

        log.info("deployment.resolved", final_status=DeploymentStatus.FAILED_TO_HEAL.value)

        await db.refresh(deployment, attribute_names=["attempts"])
        await _broadcast_deployment(deployment)
        return

    # ── Step 4: Validate the proposed fix ─────────────────────────────────
    validation_result = await validate_terraform(fix_result.fixed_code)
    log.info(
        "terraform.validation_result",
        valid=validation_result.valid,
    )

    # ── Step 5: Record the healing attempt ────────────────────────────────
    attempt = HealingAttempt(
        deployment_id=deployment_id,
        attempt_number=1,
        llm_explanation=fix_result.explanation,
        fixed_code=fix_result.fixed_code,
        validation_success=validation_result.valid,
        validation_output=validation_result.raw_output,
    )
    db.add(attempt)

    # ── Step 6: Set final status ──────────────────────────────────────────
    final_status = (
        DeploymentStatus.HEALED if validation_result.valid
        else DeploymentStatus.FAILED_TO_HEAL
    )
    deployment.status = final_status.value
    deployment.resolved_at = datetime.now(timezone.utc)
    await db.commit()

    log.info("deployment.resolved", final_status=final_status.value)

    # Final broadcast with the complete state (including the attempt)
    await db.refresh(deployment, attribute_names=["attempts"])
    await _broadcast_deployment(deployment)
