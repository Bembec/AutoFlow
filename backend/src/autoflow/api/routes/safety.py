"""Trust and safety: public abuse reports and staff tools to act on them."""

from datetime import timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from autoflow import audit
from autoflow.api.deps import Session
from autoflow.api.middleware import client_ip
from autoflow.api.routes.billing import staff_user
from autoflow.engine import service as engine
from autoflow.storage.db import utc_now
from autoflow.storage.models import AbuseReport, Workspace


router = APIRouter(tags=["trust and safety"])
Staff = Annotated[object, Depends(staff_user)]

# Reports per IP address per hour, so the form can't be used to flood staff
REPORTS_PER_HOUR = 5


class AbuseReportIn(BaseModel):
    category: Literal["spam", "phishing", "other"]
    message: str = Field(min_length=10, max_length=5000)
    reporter_email: str | None = Field(None, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    # The X-AutoFlow-Workspace header value from the email, if the reporter has it
    workspace_id: int | None = None


class Suspension(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.post("/abuse-reports", status_code=201)
def report_abuse(report: AbuseReportIn, request: Request, session: Session):
    ip = client_ip(request)
    recent = session.scalar(
        select(func.count(AbuseReport.id)).where(
            AbuseReport.ip == ip, AbuseReport.created_at >= utc_now() - timedelta(hours=1)
        )
    )
    if recent >= REPORTS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many reports from this address. Please try again later.")

    # Unknown workspace ids are kept in the message rather than rejected
    workspace_id = report.workspace_id if report.workspace_id and session.get(Workspace, report.workspace_id) else None
    message = report.message
    if report.workspace_id and workspace_id is None:
        message += f"\n\n(Reported workspace id {report.workspace_id} was not found.)"

    row = AbuseReport(
        workspace_id=workspace_id, reporter_email=report.reporter_email, category=report.category,
        message=message, ip=ip,
    )
    session.add(row)
    session.commit()
    audit.record(session, "abuse.reported", workspace_id=workspace_id, target=f"abuse_report:{row.id}",
                 details={"category": report.category}, ip=ip)
    return {"id": row.id, "received": True}


@router.get("/staff/abuse-reports")
def list_abuse_reports(staff: Staff, session: Session, status: Literal["open", "closed"] = "open"):
    rows = session.scalars(
        select(AbuseReport).where(AbuseReport.status == status).order_by(AbuseReport.id.desc()).limit(200)
    ).all()
    return [
        {
            "id": row.id, "workspace_id": row.workspace_id, "category": row.category, "message": row.message,
            "reporter_email": row.reporter_email, "status": row.status, "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post("/staff/abuse-reports/{report_id}/close")
def close_abuse_report(report_id: int, staff: Staff, session: Session):
    row = session.get(AbuseReport, report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    row.status = "closed"
    session.commit()
    audit.record(session, "abuse.closed", workspace_id=row.workspace_id, user_id=staff.id, target=f"abuse_report:{row.id}")
    return {"id": row.id, "status": row.status}


def _workspace(session, workspace_id):
    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.post("/staff/workspaces/{workspace_id}/trust")
def trust_workspace(workspace_id: int, staff: Staff, session: Session):
    """Lift new-account limits early (e.g. a known design partner)."""
    workspace = _workspace(session, workspace_id)
    workspace.trusted_at = utc_now()
    session.commit()
    audit.record(session, "safety.trusted", workspace_id=workspace_id, user_id=staff.id)
    return {"workspace_id": workspace_id, "trusted_at": workspace.trusted_at}


@router.post("/staff/workspaces/{workspace_id}/suspend")
def suspend_workspace(workspace_id: int, request: Suspension, staff: Staff, session: Session):
    """Stop all automations for an acceptable-use breach; owners can't resume."""
    workspace = _workspace(session, workspace_id)
    workspace.staff_suspended_reason = request.reason
    cancelled = engine.emergency_stop(session, workspace_id, reason=f"Paused by AutoFlow staff: {request.reason}")
    audit.record(session, "safety.suspended", workspace_id=workspace_id, user_id=staff.id,
                 details={"reason": request.reason, "cancelled": cancelled})
    return {"workspace_id": workspace_id, "suspended": True, "executions_cancelled": cancelled}


@router.post("/staff/workspaces/{workspace_id}/unsuspend")
def unsuspend_workspace(workspace_id: int, staff: Staff, session: Session):
    workspace = _workspace(session, workspace_id)
    workspace.staff_suspended_reason = None
    session.commit()
    engine.resume_automations(session, workspace_id)
    audit.record(session, "safety.unsuspended", workspace_id=workspace_id, user_id=staff.id)
    return {"workspace_id": workspace_id, "suspended": False}
