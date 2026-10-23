"""AI quality: review sampled live AI results and see how good they are over time."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from autoflow import audit, quality
from autoflow.api.deps import AdminAccess, MemberAccess, Session, ViewerAccess
from autoflow.engine import limits
from autoflow.storage.db import utc_now
from autoflow.storage.models import QualitySample, Workflow

router = APIRouter(prefix="/workspaces/{workspace_id}/quality", tags=["quality"])


class Verdict(BaseModel):
    verdict: Literal["good", "bad"]
    note: str | None = Field(None, max_length=1000)


class Settings(BaseModel):
    sample_percent: int = Field(ge=0, le=quality.MAX_PERCENT)


def _out(sample, names):
    return {
        "id": sample.id, "execution_id": sample.execution_id, "workflow": names.get(sample.workflow_id),
        "step_id": sample.step_id, "action": sample.action, "input": sample.input, "output": sample.output,
        "confidence": sample.confidence, "verdict": sample.verdict, "note": sample.note,
        "reviewed_at": sample.reviewed_at, "created_at": sample.created_at,
    }


@router.get("")
def overview(membership: ViewerAccess, session: Session):
    workspace = limits.get_workspace(session, membership.workspace_id)
    return {"sample_percent": workspace.quality_sample_percent, **quality.summary(session, workspace.id)}


@router.get("/samples")
def samples(membership: ViewerAccess, session: Session, status: Literal["waiting", "reviewed"] = "waiting"):
    query = select(QualitySample).where(QualitySample.workspace_id == membership.workspace_id)
    query = query.where(QualitySample.verdict.is_(None) if status == "waiting" else QualitySample.verdict.is_not(None))
    rows = session.scalars(query.order_by(QualitySample.id.desc()).limit(100)).all()
    names = dict(session.execute(select(Workflow.id, Workflow.name).where(
        Workflow.workspace_id == membership.workspace_id)).all())
    return [_out(row, names) for row in rows]


@router.post("/samples/{sample_id}")
def judge(sample_id: int, request: Verdict, membership: MemberAccess, session: Session):
    sample = session.get(QualitySample, sample_id)
    if sample is None or sample.workspace_id != membership.workspace_id:
        raise HTTPException(status_code=404, detail="Sample not found")
    sample.verdict = request.verdict
    sample.note = request.note
    sample.reviewed_by_user_id = membership.user_id
    sample.reviewed_at = utc_now()
    session.commit()
    return {"id": sample.id, "verdict": sample.verdict}


@router.put("/settings")
def settings(request: Settings, membership: AdminAccess, session: Session):
    workspace = limits.get_workspace(session, membership.workspace_id)
    workspace.quality_sample_percent = request.sample_percent
    session.commit()
    audit.for_member(membership, session, "quality.sampling_changed", details={"percent": request.sample_percent})
    return {"sample_percent": workspace.quality_sample_percent}
