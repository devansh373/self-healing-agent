"""
ORM models for the deployments and healing_attempts tables.

These classes define the shape of our database tables using SQLAlchemy 2.0's
declarative "Mapped[...]" syntax. Alembic reads these to auto-generate
migration scripts.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


# ── Status Enum ───────────────────────────────────────────────────────────
# Python 3.11+ StrEnum: values are strings, so DeploymentStatus.FAILED == "FAILED".
# This gives us type safety in application code (IDE autocomplete, type checkers)
# while the database column stores a plain String — no Postgres ENUM type needed,
# which avoids messy migration headaches when adding new statuses later.
class DeploymentStatus(str, enum.Enum):
    FAILED = "FAILED"
    HEALING = "HEALING"
    HEALED = "HEALED"
    FAILED_TO_HEAL = "FAILED_TO_HEAL"


# ── Deployment Model ──────────────────────────────────────────────────────
class Deployment(Base):
    """
    Represents a single deployment that was detected as broken.

    Lifecycle: FAILED → HEALING → (HEALED | FAILED_TO_HEAL)

    Each deployment has one or more HealingAttempts (just one in Phase 1).
    """

    __tablename__ = "deployments"

    # Primary key: UUID generated in Python, not by the database.
    # Using uuid.uuid4 (random UUID) — no sequential IDs to guess.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # What category of fault this is. Phase 1 always "missing_required_argument".
    fault_category: Mapped[str] = mapped_column(String(100), nullable=False)

    # Snapshot of the broken Terraform file at trigger time.
    # Text type = unlimited length (vs String which has a max length).
    broken_code: Mapped[str] = mapped_column(Text, nullable=False)

    # Snapshot of the error log from the simulated deployment pipeline.
    error_log: Mapped[str] = mapped_column(Text, nullable=False)

    # Current status in the healing lifecycle.
    # Stored as a plain string in the DB, but typed as DeploymentStatus in Python.
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DeploymentStatus.FAILED.value,
    )

    # When this deployment was first recorded.
    # server_default=func.now() tells Postgres to use its own clock,
    # not the Python process's clock — more reliable if clocks differ.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # When the healing process finished (either success or failure).
    # Null until the deployment reaches a terminal state.
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # ── Relationship ──────────────────────────────────────────────────────
    # This is NOT a database column — it's a Python-level convenience.
    # deployment.attempts gives you a list of HealingAttempt objects
    # without writing a separate query.
    #
    # back_populates="deployment" links this to HealingAttempt.deployment
    # (bidirectional: you can go from deployment → attempts AND attempt → deployment)
    #
    # lazy="selectin" means: when you load a Deployment, also load its attempts
    # in the same round-trip using a SELECT ... IN (...) query. This avoids the
    # "N+1 query problem" where loading 10 deployments would trigger 10 extra queries.
    attempts: Mapped[list["HealingAttempt"]] = relationship(
        back_populates="deployment",
        lazy="selectin",
        order_by="HealingAttempt.attempt_number",
    )


# ── Healing Attempt Model ─────────────────────────────────────────────────
class HealingAttempt(Base):
    """
    Records one attempt to fix a broken deployment.

    Phase 1: always exactly one attempt per deployment (attempt_number=1).
    Phase 2 will add a retry loop, producing multiple attempts per deployment.
    The column exists now so that migration won't be needed later.
    """

    __tablename__ = "healing_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Foreign key linking this attempt to its parent deployment.
    # If the deployment is deleted, this attempt would be orphaned — but
    # we don't delete deployments in this system, so no cascade needed.
    deployment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deployments.id"),
        nullable=False,
    )

    # Which attempt this is (1st, 2nd, 3rd...). Always 1 in Phase 1.
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # The LLM's explanation of what was wrong and how to fix it.
    # If the LLM call itself failed, this contains the error message instead.
    llm_explanation: Mapped[str] = mapped_column(Text, nullable=False)

    # The LLM's proposed corrected Terraform file (full file, not a diff).
    # Empty string if the LLM call failed before producing one.
    fixed_code: Mapped[str] = mapped_column(Text, nullable=False)

    # Did `terraform validate` pass on the fixed code?
    validation_success: Mapped[bool] = mapped_column(nullable=False)

    # Raw JSON output from `terraform validate -json`.
    # Nullable because if the LLM call fails, we never reach validation.
    validation_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # ── Relationship (back-reference) ─────────────────────────────────────
    # attempt.deployment gives you the parent Deployment object.
    deployment: Mapped["Deployment"] = relationship(back_populates="attempts")
