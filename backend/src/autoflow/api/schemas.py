"""Response models that define the public shape of the API."""

from typing import Any, Literal

from pydantic import BaseModel


class Health(BaseModel):
    status: str
    version: str


class CustomerSummary(BaseModel):
    id: int
    name: str
    email: str
    category: str
    classification_source: str
    updated_at: str


class CustomerDetail(CustomerSummary):
    customer_id: str | None
    message: str
    classification_reason: str
    quote_eur: str | None
    quote_usd: str | None
    rate_date: str | None


class WorkflowRun(BaseModel):
    id: int
    run_timestamp: str
    customer_count: int
    ai_enabled: str
    status: str


class EmailDecision(BaseModel):
    status: str
    recipient: str


class Approval(BaseModel):
    id: int
    kind: Literal["classification", "email"]
    status: str
    customer_email: str
    payload: dict[str, Any]
    decision: dict[str, Any] | None
    created_at: str
    decided_at: str | None


class ApprovalDecision(BaseModel):
    category: Literal["Sales", "Support", "Other"] | None = None


class WorkflowRunResult(BaseModel):
    run_id: int
    customer_count: int
    ai_enabled: bool
    categories: dict[str, int]
    emails: list[EmailDecision]
