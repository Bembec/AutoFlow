"""
AutoFlow database tables.

Every business record belongs to a workspace (tenant). Repository
functions always filter by workspace_id, so one business can never
read or change another business's data.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text, UniqueConstraint, false, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from autoflow.storage.db import Base, UTCDateTime, utc_now


# Ordered from least to most powerful
ROLES = ("viewer", "member", "admin", "owner")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    # --- safety policies (V13) ---
    # Emergency stop: no workflow in this workspace may run
    automation_paused: Mapped[bool] = mapped_column(default=False, server_default=false())
    paused_reason: Mapped[str | None] = mapped_column(Text)
    # Every side effect (not only sensitive ones) waits for a human
    approve_all_side_effects: Mapped[bool] = mapped_column(default=False, server_default=false())
    max_executions_per_day: Mapped[int] = mapped_column(default=1000, server_default=text("1000"))
    max_ai_calls_per_day: Mapped[int] = mapped_column(default=200, server_default=text("200"))
    max_emails_per_day: Mapped[int] = mapped_column(default=100, server_default=text("100"))

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "workspace_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    user: Mapped[User] = relationship(back_populates="memberships")
    workspace: Mapped[Workspace] = relationship(back_populates="memberships")


class AccessToken(Base):
    """A login session. Only a hash of the token is stored."""

    __tablename__ = "access_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    user: Mapped[User] = relationship()


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("workspace_id", "email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320))
    message: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(20))
    classification_source: Mapped[str] = mapped_column(String(50))
    classification_reason: Mapped[str] = mapped_column(Text)
    quote_eur: Mapped[str | None] = mapped_column(String(20))
    quote_usd: Mapped[str | None] = mapped_column(String(20))
    rate_date: Mapped[str | None] = mapped_column(String(20))
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now
    )


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    run_timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    customer_count: Mapped[int]
    ai_enabled: Mapped[bool]
    status: Mapped[str] = mapped_column(String(20))


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (
        # Re-running the enquiry workflow refreshes a pending request
        # instead of creating a duplicate (engine step approvals are
        # unique per execution step instead)
        Index(
            "one_pending_approval",
            "workspace_id",
            "kind",
            "customer_email",
            unique=True,
            sqlite_where=text("status = 'pending' AND kind != 'step'"),
            postgresql_where=text("status = 'pending' AND kind != 'step'"),
        ),
        UniqueConstraint(
            "execution_id", "step_id", name="uq_approvals_execution_id_step_id"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    customer_email: Mapped[str] = mapped_column(String(320))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    decision: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    decided_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    # Set for approvals that gate a workflow-engine step
    execution_id: Mapped[int | None] = mapped_column(
        ForeignKey("workflow_executions.id", ondelete="CASCADE")
    )
    step_id: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


# --- Workflow engine (V10) --------------------------------------------------

class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    # active | paused | archived
    status: Mapped[str] = mapped_column(String(20), default="active")
    # Owner's estimate of manual work one successful run replaces
    minutes_saved_per_run: Mapped[int] = mapped_column(default=5, server_default=text("5"))
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now
    )

    versions: Mapped[list["WorkflowVersion"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowVersion.number",
    )


class WorkflowVersion(Base):
    """One saved definition. At most one draft and one published per workflow."""

    __tablename__ = "workflow_versions"
    __table_args__ = (UniqueConstraint("workflow_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int]
    # draft | published | archived
    state: Mapped[str] = mapped_column(String(20), default="draft")
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    workflow: Mapped[Workflow] = relationship(back_populates="versions")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    __table_args__ = (
        # The same idempotency key never starts a second execution
        UniqueConstraint("workspace_id", "idempotency_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    version_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_versions.id", ondelete="CASCADE")
    )
    # test (side effects simulated) | live
    mode: Mapped[str] = mapped_column(String(10))
    # queued | running | waiting_approval | succeeded | failed |
    # cancelled | needs_attention
    status: Mapped[str] = mapped_column(String(20), default="queued")
    trigger_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    idempotency_key: Mapped[str | None] = mapped_column(String(200))
    error: Mapped[str | None] = mapped_column(Text)
    triggered_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # --- background queue (V17) ---
    # A queued execution is not picked up before this time (delay steps)
    run_after: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    # Worker currently running it, and its last sign of life
    claimed_by: Mapped[str | None] = mapped_column(String(100))
    heartbeat_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    version: Mapped[WorkflowVersion] = relationship()
    steps: Mapped[list["StepExecution"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
        order_by="StepExecution.position",
    )


class StepExecution(Base):
    __tablename__ = "step_executions"
    __table_args__ = (UniqueConstraint("execution_id", "step_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_executions.id", ondelete="CASCADE"), index=True
    )
    step_id: Mapped[str] = mapped_column(String(50))
    position: Mapped[int]
    action: Mapped[str] = mapped_column(String(100))
    # pending | running | waiting_approval | approved | succeeded |
    # skipped | failed | rejected
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    input: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    execution: Mapped[WorkflowExecution] = relationship(back_populates="steps")


# --- Integrations (V12) -----------------------------------------------------

class Connection(Base):
    """A workspace's credentials for one external app.

    Secrets are stored encrypted (autoflow.security.vault) and never
    returned by the API.
    """

    __tablename__ = "connections"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_connections_workspace_id_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100))
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    encrypted_secrets: Mapped[str] = mapped_column(Text)
    # active | error (needs reconnecting) | revoked
    status: Mapped[str] = mapped_column(String(20), default="active")
    last_error: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class WebhookEndpoint(Base):
    """A public URL that starts a workflow when it receives a signed request."""

    __tablename__ = "webhook_endpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), unique=True
    )
    public_id: Mapped[str] = mapped_column(String(64), unique=True)
    # autoflow (hex HMAC-SHA256) | shopify (base64 HMAC-SHA256)
    signature_scheme: Mapped[str] = mapped_column(String(20), default="autoflow")
    encrypted_secret: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    last_called_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


# --- Billing (V15) ----------------------------------------------------------

class Subscription(Base):
    """A workspace's plan. Workspaces without a row are on the free plan."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True
    )
    plan: Mapped[str] = mapped_column(String(30), default="free")
    # active | trialing | past_due | canceled
    status: Mapped[str] = mapped_column(String(20), default="active")
    # manual (invoiced pilots) | stripe
    provider: Mapped[str] = mapped_column(String(20), default="manual")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100))
    current_period_start: Mapped[datetime | None] = mapped_column(UTCDateTime)
    current_period_end: Mapped[datetime | None] = mapped_column(UTCDateTime)
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False, server_default=false())
    # Stop billable steps when the included tasks are used up
    hard_cap: Mapped[bool] = mapped_column(default=True, server_default=true())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, onupdate=utc_now)


class BillableEvent(Base):
    """One billable task. Unique per step run, so nothing is billed twice."""

    __tablename__ = "billable_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    step_execution_id: Mapped[int] = mapped_column(
        ForeignKey("step_executions.id", ondelete="CASCADE"), unique=True
    )
    action: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, index=True)
    # When the event was sent to the payment provider's usage meter
    reported_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class ProcessedStripeEvent(Base):
    """Stripe webhook events already handled (Stripe may deliver twice)."""

    __tablename__ = "processed_stripe_events"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    type: Mapped[str] = mapped_column(String(100))
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
