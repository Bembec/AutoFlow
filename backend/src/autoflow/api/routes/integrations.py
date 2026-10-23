"""Integrations API: app catalogue, connections, OAuth and webhooks."""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from autoflow import audit
from autoflow.api.deps import AdminAccess, MemberAccess, Session, ViewerAccess
from autoflow.engine import service as engine
from autoflow.integrations import catalog, connections, oauth, webhooks


router = APIRouter(tags=["integrations"])
workspace_router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["integrations"])


class ConnectionCreate(BaseModel):
    provider: str
    name: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9 _.\-]+$")
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, str] = Field(default_factory=dict)


class SecretsUpdate(BaseModel):
    secrets: dict[str, str]


class OAuthStart(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9 _.\-]+$")


class WebhookEnable(BaseModel):
    signature_scheme: Literal["autoflow", "shopify", "woocommerce"] = "autoflow"
    secret: str | None = Field(
        None, min_length=16, description="Shopify: your app's webhook secret. Otherwise generated."
    )


def _connection_out(connection):
    return {
        "id": connection.id,
        "provider": connection.provider,
        "name": connection.name,
        "config": connection.config,
        "secrets": connections.masked_secrets(connection),
        "status": connection.status,
        "last_error": connection.last_error,
        "created_at": connection.created_at,
        "last_used_at": connection.last_used_at,
        "last_checked_at": connection.last_checked_at,
    }


def _get_connection(session, membership, connection_id):
    connection = connections.get_connection(session, membership.workspace_id, connection_id)

    if connection is None or connection.status == "revoked":
        raise HTTPException(status_code=404, detail="Connection not found")

    return connection


@router.get("/integrations")
def list_integrations():
    """Apps that can be connected, and the fields each one needs."""
    return catalog.describe()


@workspace_router.get("/connections")
def list_connections(membership: ViewerAccess, session: Session):
    return [_connection_out(c) for c in connections.list_connections(session, membership.workspace_id)]


@workspace_router.post("/connections", status_code=201)
def create_connection(request: ConnectionCreate, membership: AdminAccess, session: Session):
    if catalog.PROVIDERS.get(request.provider) and catalog.PROVIDERS[request.provider].auth == "oauth2":
        raise HTTPException(status_code=409, detail="Use the OAuth sign-in flow for this app.")

    try:
        connection = connections.create_connection(
            session,
            membership.workspace_id,
            request.provider,
            request.name,
            request.secrets,
            request.config,
            user_id=membership.user_id,
        )
    except connections.ConnectionError_ as error:
        raise HTTPException(status_code=409, detail=str(error))

    audit.for_member(membership, session, "connection.created", target=connection.name, details={"provider": connection.provider})
    return _connection_out(connection)


@workspace_router.put("/connections/{connection_id}/secrets")
def update_connection_secrets(
    connection_id: int, request: SecretsUpdate, membership: AdminAccess, session: Session
):
    connection = _get_connection(session, membership, connection_id)

    try:
        connections.update_secrets(session, connection, request.secrets)
    except connections.ConnectionError_ as error:
        raise HTTPException(status_code=409, detail=str(error))

    audit.for_member(membership, session, "connection.secrets_updated", target=connection.name)

    return _connection_out(connection)


@workspace_router.post("/connections/{connection_id}/check")
def check_connection(connection_id: int, membership: MemberAccess, session: Session):
    """Test the stored credentials with a read-only call."""
    from autoflow.integrations import health

    connection = _get_connection(session, membership, connection_id)
    result = health.check(session, connection)
    return {**result, "status": connection.status, "last_checked_at": connection.last_checked_at}


@workspace_router.delete("/connections/{connection_id}", status_code=204)
def revoke_connection(connection_id: int, membership: AdminAccess, session: Session):
    connection = _get_connection(session, membership, connection_id)
    connections.revoke(session, connection)
    audit.for_member(membership, session, "connection.revoked", target=connection.name)


@workspace_router.post("/connections/oauth/{provider}/start")
def start_oauth(provider: str, request: OAuthStart, membership: AdminAccess):
    try:
        url = oauth.start(provider, membership.workspace_id, membership.user_id, request.name)
    except oauth.OAuthError as error:
        raise HTTPException(status_code=409, detail=str(error))

    return {"authorization_url": url}


@router.get("/oauth/callback/{provider}")
def oauth_callback(
    provider: str,
    session: Session,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    if error or not code or not state:
        raise HTTPException(status_code=400, detail=f"Sign-in was not completed: {error or 'missing code'}")

    try:
        connection = oauth.finish(session, provider, code, state)
    except (oauth.OAuthError, connections.ConnectionError_) as failure:
        raise HTTPException(status_code=400, detail=str(failure))

    return {"connected": True, "connection": connection.name, "provider": provider}


# --- webhooks ---------------------------------------------------------------

@workspace_router.get("/workflows/{workflow_id}/webhook")
def get_webhook(workflow_id: int, membership: ViewerAccess, session: Session):
    endpoint = webhooks.get_endpoint(session, membership.workspace_id, workflow_id)

    if endpoint is None:
        raise HTTPException(status_code=404, detail="No webhook for this workflow")

    return {
        "url": webhooks.url_for(endpoint),
        "signature_scheme": endpoint.signature_scheme,
        "last_called_at": endpoint.last_called_at,
    }


@workspace_router.post("/workflows/{workflow_id}/webhook", status_code=201)
def enable_webhook(
    workflow_id: int,
    membership: MemberAccess,
    session: Session,
    request: WebhookEnable | None = None,
):
    request = request or WebhookEnable()

    try:
        endpoint, secret = webhooks.enable(
            session, membership.workspace_id, workflow_id, request.signature_scheme, request.secret
        )
    except engine.NotFound:
        raise HTTPException(status_code=404, detail="Workflow not found")

    audit.for_member(membership, session, "webhook.secret_set", target=f"workflow {workflow_id}", details={"scheme": endpoint.signature_scheme})
    return {
        "url": webhooks.url_for(endpoint),
        "signature_scheme": endpoint.signature_scheme,
        # Shown once; store it in the sending app
        "secret": secret,
    }


@workspace_router.delete("/workflows/{workflow_id}/webhook", status_code=204)
def disable_webhook(workflow_id: int, membership: MemberAccess, session: Session):
    webhooks.disable(session, membership.workspace_id, workflow_id)
    audit.for_member(membership, session, "webhook.disabled", target=f"workflow {workflow_id}")


@router.post("/hooks/{public_id}", status_code=202)
async def receive_webhook(public_id: str, request: Request, response: Response, session: Session):
    body = await request.body()

    try:
        execution, created = webhooks.receive(session, public_id, body, dict(request.headers))
    except webhooks.WebhookPing:
        response.status_code = 200
        return {"ping": True}
    except webhooks.WebhookRejected as rejected:
        raise HTTPException(status_code=rejected.status_code, detail=str(rejected))

    if not created:
        response.status_code = 200

    return {"execution_id": execution.id, "status": execution.status, "duplicate": not created}
