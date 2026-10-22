"""Registration, login, logout and the current user."""

from fastapi import APIRouter, Depends, HTTPException, status

from autoflow import config
from autoflow.accounts import service as accounts
from autoflow.api import schemas
from autoflow.api.deps import CurrentUser, Session, get_token


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
def login(request: schemas.LoginRequest, session: Session):
    token = accounts.authenticate(session, request.email, request.password)

    if token is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    session.commit()
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
