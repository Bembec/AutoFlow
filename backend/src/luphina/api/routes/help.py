"""Help assistant API: questions answered only from the help articles."""

from datetime import timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from luphina import features, help_assistant
from luphina.api.deps import Session, ViewerAccess
from luphina.engine import limits
from luphina.storage.db import utc_now
from luphina.storage.models import AIUsageEvent

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["help"])

# Questions per workspace per hour (help is free for customers, so it's rate limited)
QUESTIONS_PER_HOUR = 30


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=help_assistant.MAX_QUESTION_CHARS)
    language: str = Field("en", pattern=r"^[a-z]{2}$")


@router.post("/help/ask")
def ask(request: Question, membership: ViewerAccess, session: Session):
    workspace = limits.get_workspace(session, membership.workspace_id)
    if not features.enabled("help_assistant", workspace):
        raise HTTPException(status_code=403, detail="The help assistant is switched off for this workspace.")

    asked = session.scalar(select(func.count(AIUsageEvent.id)).where(
        AIUsageEvent.workspace_id == workspace.id,
        AIUsageEvent.kind == limits.HELP_KIND,
        AIUsageEvent.created_at >= utc_now() - timedelta(hours=1),
    ))
    if asked >= QUESTIONS_PER_HOUR:
        raise HTTPException(status_code=429, detail="That's a lot of questions! Please try again in a little while.")

    session.add(AIUsageEvent(workspace_id=workspace.id, kind=limits.HELP_KIND))
    session.commit()
    return help_assistant.answer(request.question, request.language)
