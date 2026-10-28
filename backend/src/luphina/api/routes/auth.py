"""Registration, login, logout and the current user."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from luphina import audit, config
from luphina.accounts import service as accounts
from luphina.accounts import two_factor
from luphina.api import schemas
from luphina.api.deps import CurrentUser, Session, get_token
from luphina.api.middleware import client_ip


router = APIRouter(tags=["auth"])


@router.post(
    "/auth/register",
    response_model=schemas.UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register(request: schemas.RegisterRequest, session: Session):
    try:
        user = accounts.register_user(
            session, request.email, request.name, request.password
        )
    except accounts.AccountError as error:
        raise HTTPException(status_code=409, detail=str(error))

    session.commit()
    return user


@router.post("/auth/login", response_model=schemas.TokenResponse)
def login(request: schemas.LoginRequest, session: Session, http: Request):
    ip = client_ip(http)
    user = accounts.get_user_by_email(session, request.email)

    try:
        token = accounts.authenticate(session, request.email, request.password, request.code)
    except accounts.TwoFactorRequired:
        # The client shows the code field and sends the request again
        raise HTTPException(status_code=401, detail="two_factor_required")

    if token is None:
        if user is not None:
            audit.record(session, "auth.login_failed", user_id=user.id, ip=ip)
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    session.commit()
    audit.record(session, "auth.login", user_id=user.id, ip=ip, details={"two_factor": user.totp_enabled})
    return {
        "access_token": token,
        "expires_in": config.ACCESS_TOKEN_TTL_HOURS * 3600,
    }


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: CurrentUser, session: Session, token: str = Depends(get_token)):
    accounts.revoke_token(session, token)
    session.commit()


@router.get("/me", response_model=schemas.Me)
def me(user: CurrentUser, session: Session):
    memberships = accounts.list_user_memberships(session, user.id)

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at,
        "workspaces": [
            {
                "id": membership.workspace.id,
                "name": membership.workspace.name,
                "slug": membership.workspace.slug,
                "created_at": membership.workspace.created_at,
                "role": membership.role,
            }
            for membership in memberships
        ],
    }


# --- two-factor login ---------------------------------------------------------

class CodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=20)


class DisableTwoFactor(BaseModel):
    password: str
    code: str = Field(min_length=6, max_length=20)


@router.get("/auth/2fa")
def two_factor_status(user: CurrentUser):
    return {"enabled": user.totp_enabled, "recovery_codes_left": two_factor.recovery_codes_left(user)}


@router.post("/auth/2fa/setup")
def two_factor_setup(user: CurrentUser, session: Session):
    """Start setup: add the secret to an authenticator app, then confirm with a code."""

    try:
        secret, uri = two_factor.start_setup(session, user)
    except two_factor.TwoFactorError as error:
        raise HTTPException(status_code=409, detail=str(error))

    session.commit()
    return {"secret": secret, "otpauth_uri": uri}


@router.post("/auth/2fa/enable")
def two_factor_enable(request: CodeRequest, user: CurrentUser, session: Session):
    try:
        codes = two_factor.enable(session, user, request.code)
    except two_factor.TwoFactorError as error:
        raise HTTPException(status_code=409, detail=str(error))

    session.commit()
    audit.record(session, "auth.2fa_enabled", user_id=user.id)
    # Shown once: the user must store them somewhere safe
    return {"enabled": True, "recovery_codes": codes}


@router.post("/auth/2fa/disable")
def two_factor_disable(request: DisableTwoFactor, user: CurrentUser, session: Session):
    try:
        two_factor.disable(session, user, request.password, request.code)
    except two_factor.TwoFactorError as error:
        raise HTTPException(status_code=409, detail=str(error))

    session.commit()
    audit.record(session, "auth.2fa_disabled", user_id=user.id)
    return {"enabled": False}


@router.get("/auth/activity")
def my_sign_ins(user: CurrentUser, session: Session):
    """Recent sign-ins and security changes on your own account."""

    from sqlalchemy import select

    from luphina.storage.models import AuditEvent

    events = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.user_id == user.id, AuditEvent.action.like("auth.%"))
        .order_by(AuditEvent.id.desc())
        .limit(50)
    ).all()
    return [
        {"action": e.action, "ip": e.ip, "details": e.details, "created_at": e.created_at}
        for e in events
    ]
