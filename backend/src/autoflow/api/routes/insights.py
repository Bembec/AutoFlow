"""Insights: time and money saved, and suggestions for what to do next."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from autoflow import insights
from autoflow.api.deps import AdminAccess, Session, ViewerAccess
from autoflow.engine import limits


router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["insights"])


class TimeValue(BaseModel):
    # None clears it (money saved is then not shown)
    per_hour: float | None = Field(None, ge=0, le=100_000)
    currency: str = Field("USD", pattern=r"^[A-Z]{3}$")


@router.get("/insights")
def get_insights(membership: ViewerAccess, session: Session):
    return insights.summary(session, limits.get_workspace(session, membership.workspace_id))


@router.put("/insights/time-value")
def set_time_value(request: TimeValue, membership: AdminAccess, session: Session):
    workspace = limits.get_workspace(session, membership.workspace_id)
    workspace.time_value_per_hour = request.per_hour
    workspace.time_value_currency = request.currency
    session.commit()
    return insights.summary(session, workspace)
