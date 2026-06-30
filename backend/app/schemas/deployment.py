"""
Pydantic schemas for API request/response shapes.

These are separate from the ORM models (app.models.deployment) by design:
- ORM models define the DATABASE shape (table columns, relationships).
- Pydantic schemas define the API shape (what the client sees).

This separation means we can change the database structure without breaking
the API contract, and vice versa. FastAPI automatically serialises these
schemas to JSON in responses and generates OpenAPI documentation from them.

All schemas use Pydantic v2 syntax (model_config instead of inner Config class).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── Healing Attempt (nested inside DeploymentDetail) ──────────────────────
class HealingAttemptOut(BaseModel):
    """
    API representation of a single healing attempt.

    Returned as a nested list inside DeploymentDetail — never as a
    standalone top-level response in Phase 1.
    """

    id: uuid.UUID
    attempt_number: int
    llm_explanation: str
    fixed_code: str
    validation_success: bool
    validation_output: str | None
    created_at: datetime

    # from_attributes=True tells Pydantic to read data from ORM model
    # attributes (e.g., attempt.id) instead of expecting a dict.
    # This is what makes `HealingAttemptOut.model_validate(orm_object)` work.
    model_config = ConfigDict(from_attributes=True)


# ── Deployment Summary (list view) ────────────────────────────────────────
class DeploymentSummary(BaseModel):
    """
    Lightweight deployment representation for list endpoints.

    Used by:
    - POST /api/deployments/trigger (201 response)
    - GET  /api/deployments         (array of these)

    Intentionally omits the heavy text fields (broken_code, error_log,
    attempts) — those are only needed in the detail view.
    """

    id: uuid.UUID
    fault_category: str
    status: str
    created_at: datetime
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ── Deployment Detail (single deployment with full context) ───────────────
class DeploymentDetail(BaseModel):
    """
    Full deployment representation including all text content and attempts.

    Used by:
    - GET /api/deployments/{deployment_id} (200 response)
    - WebSocket broadcast messages          (the "data" field)

    This is the richest view — everything a reviewer needs to understand
    what was broken, what the LLM said, and whether the fix validated.
    """

    id: uuid.UUID
    fault_category: str
    status: str
    broken_code: str
    error_log: str
    created_at: datetime
    resolved_at: datetime | None
    attempts: list[HealingAttemptOut]

    model_config = ConfigDict(from_attributes=True)
