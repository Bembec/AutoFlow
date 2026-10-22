"""Request and response models that define the public shape of the API."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    kind: Literal["classification", "email"]
    status: str
    customer_email: str
    payload: dict[str, Any]
    decision: dict[str, Any] | None
    decided_by_user_id: int | None
    created_at: datetime
    decided_at: datetime | None


class ApprovalDecision(BaseModel):
    category: Category | None = None
