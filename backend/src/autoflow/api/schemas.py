"""Request and response models that define the public shape of the API."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from autoflow.engine.definition import WorkflowDefinition


Role = Literal["viewer", "member", "admin", "owner"]
Category = Literal["Sales", "Support", "Other"]


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- system ---

class Health(BaseModel):
    status: str
    version: str


# --- accounts ---

class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    # Authenticator or recovery code, for accounts with two-factor login
    code: str | None = Field(None, max_length=20)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(OrmModel):
    id: int
    email: str
    name: str
    created_at: datetime


class WorkspaceOut(OrmModel):
    id: int
    name: str
    slug: str
    created_at: datetime


class WorkspaceWithRole(WorkspaceOut):
    role: Role


class Me(UserOut):
    workspaces: list[WorkspaceWithRole]


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class MemberCreate(BaseModel):
    email: EmailStr
    role: Role = "member"


class MemberOut(BaseModel):
    user_id: int
    email: str
    name: str
    role: Role


# --- workspace data ---

class CustomerSummary(OrmModel):
    id: int
    name: str
    email: str
    category: str
    classification_source: str
    updated_at: datetime


class CustomerDetail(CustomerSummary):
    customer_id: str | None
    message: str
    classification_reason: str
    quote_eur: str | None
    quote_usd: str | None
    rate_date: str | None


class WorkflowRun(OrmModel):
    id: int
    run_timestamp: datetime
    customer_count: int
    ai_enabled: bool
    status: str


class EmailDecision(BaseModel):
    status: str
    recipient: str


class WorkflowRunResult(BaseModel):
    run_id: int
    customer_count: int
    ai_enabled: bool
    categories: dict[str, int]
    emails: list[EmailDecision]


class Approval(OrmModel):
    id: int
    kind: Literal["classification", "email", "step"]
    status: str
    customer_email: str
    payload: dict[str, Any]
    decision: dict[str, Any] | None
    decided_by_user_id: int | None
    execution_id: int | None
    step_id: str | None
    created_at: datetime
    decided_at: datetime | None


class ApprovalDecision(BaseModel):
    category: Category | None = None
    output: dict[str, Any] | None = Field(
        None, description="AI result reviews: corrected step output, e.g. {\"data\": {...}}"
    )


# --- workflow engine ---

class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    definition: WorkflowDefinition
    minutes_saved_per_run: int = Field(5, ge=0, le=10_000)


class WorkflowFromTemplate(BaseModel):
    template: str
    name: str | None = Field(None, min_length=1, max_length=200)


class WorkflowUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    definition: WorkflowDefinition | None = None
    minutes_saved_per_run: int | None = Field(None, ge=0, le=10_000)
    mcp_enabled: bool | None = None


class WorkflowVersionOut(OrmModel):
    number: int
    state: Literal["draft", "published", "archived"]
    definition: dict[str, Any]
    created_at: datetime
    published_at: datetime | None


class WorkflowOut(OrmModel):
    id: int
    name: str
    description: str
    status: str
    minutes_saved_per_run: int
    mcp_enabled: bool = False
    created_at: datetime
    updated_at: datetime
    versions: list[WorkflowVersionOut]


class DraftAnswer(BaseModel):
    question: str = Field(max_length=1000)
    answer: str = Field(max_length=2000)


class AIDraftRequest(BaseModel):
    request: str = Field(
        min_length=10,
        max_length=4000,
        description="What should be automated, in plain words",
    )
    answers: list[DraftAnswer] = Field(default_factory=list, max_length=20)
    save: bool = Field(False, description="Save a valid draft as a new workflow")


class AIDraftOut(BaseModel):
    status: Literal["ready", "needs_details"]
    name: str
    description: str
    definition: dict[str, Any] | None
    questions: list[str]
    assumptions: list[str]
    unsupported: list[str]
    provider: str
    attempts: int
    workflow: WorkflowOut | None = None


class PublishRequest(BaseModel):
    version: int | None = Field(None, description="Omit to publish the draft; set to roll back")


class ExecutionStart(BaseModel):
    mode: Literal["test", "live"] = "live"
    payload: dict[str, Any] | None = Field(
        None, description="Trigger data; test runs default to the sample payload"
    )


class ExecutionRetry(BaseModel):
    confirm_not_completed: bool = False


class StepExecutionOut(OrmModel):
    step_id: str
    position: int
    action: str
    status: str
    attempts: int
    input: dict[str, Any] | None
    output: dict[str, Any] | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class ExecutionOut(OrmModel):
    id: int
    workflow_id: int
    version_id: int
    mode: str
    status: str
    trigger_payload: dict[str, Any]
    idempotency_key: str | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    run_after: datetime | None = None
    steps: list[StepExecutionOut]
    ai_calls: int = 0
    ai_cost_usd: float = 0
