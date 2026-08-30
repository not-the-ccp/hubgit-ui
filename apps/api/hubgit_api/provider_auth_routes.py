"""Provider-neutral browser authorization routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings
from .github_auth import (
    AccessPolicyUnavailable,
    CredentialCipher,
    GitHubAuthError,
    GitHubAuthPort,
    evaluate_access_policy,
    new_oauth_state,
    safe_return_path,
)
from .models import OAuthState, ProviderIdentity, Session, User
from .security import ProblemError, get_db, new_session, settings, token_hash

router = APIRouter(prefix="/api/v1/auth/providers", tags=["auth"])


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _github(request: Request) -> GitHubAuthPort:
    client = getattr(request.app.state, "github_auth_client", None)
    if client is None:
        raise ProblemError(
            503,
            "Provider unavailable",
            "provider.not_configured",
            "This authorization provider is not configured.",
        )
    return client


@router.get("/{provider}/start")
async def start_provider_auth(
    provider: str,
    request: Request,
    redirect_uri: str | None = Query(default=None, alias="redirectUri"),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if provider != "github" or request.app.state.settings.provider != "github":
        raise ProblemError(404, "Provider not found", "provider.not_found")
    client = _github(request)
    return_to = safe_return_path(redirect_uri)
    raw_state = new_oauth_state()
    db.add(
        OAuthState(
            provider=provider,
            state_hash=token_hash(raw_state),
            return_to=return_to,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
    )
    await db.commit()
    response = RedirectResponse(client.authorization_url(raw_state), status_code=302)
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/{provider}/callback")
async def complete_provider_auth(
    provider: str,
    request: Request,
    code: str | None = Query(default=None, max_length=500),
    state: str | None = Query(default=None, min_length=16, max_length=500),
    error: str | None = Query(default=None, max_length=200),
    error_description: str | None = Query(default=None, alias="errorDescription", max_length=500),
    db: AsyncSession = Depends(get_db),
    config: Settings = Depends(settings),
) -> RedirectResponse:
    if provider != "github" or config.provider != "github":
        raise ProblemError(404, "Provider not found", "provider.not_found")
    client = _github(request)
    if error or request.query_params.get("error_description"):
        raise ProblemError(400, "Authorization cancelled", "auth.provider_cancelled")
    if not code or not state:
        raise ProblemError(400, "Invalid authorization response", "auth.provider_response_invalid")

    transaction = await db.scalar(
        select(OAuthState).where(
            OAuthState.provider == provider,
            OAuthState.state_hash == token_hash(state),
        )
    )
    now = datetime.now(timezone.utc)
    if (
        transaction is None
        or transaction.consumed_at is not None
        or _aware(transaction.expires_at) <= now
    ):
        raise ProblemError(400, "Invalid authorization state", "auth.state_invalid")
    transaction.consumed_at = now
    await db.commit()

    try:
        credentials = await client.exchange_code(code)
        identity = await client.identity(credentials.access_token)
        allowed = await evaluate_access_policy(
            client, credentials, identity, config.github_access_policy
        )
    except AccessPolicyUnavailable as exc:
        raise ProblemError(
            503,
            "Access verification unavailable",
            "auth.access_policy_unverifiable",
            "GitHub access requirements could not be verified. Try again later.",
        ) from exc
    except GitHubAuthError as exc:
        raise ProblemError(
            502,
            "Provider authentication failed",
            "auth.provider_failed",
            "GitHub could not complete authentication.",
        ) from exc
    if not allowed:
        raise ProblemError(
            403,
            "Access denied",
            "auth.access_policy_denied",
            "This GitHub account does not satisfy the deployment access policy.",
        )

    provider_identity = await db.scalar(
        select(ProviderIdentity).where(
            ProviderIdentity.provider == provider,
            ProviderIdentity.provider_user_id == str(identity.user_id),
        )
    )
    if provider_identity is None:
        login = identity.login
        if await db.scalar(select(User.id).where(User.login == login)) is not None:
            login = f"{identity.login}-github-{identity.user_id}"
        email = identity.email or f"{identity.user_id}@users.noreply.github.local"
        if await db.scalar(select(User.id).where(User.email == email)) is not None:
            email = f"{identity.user_id}@users.noreply.github.local"
        user = User(
            login=login,
            display_name=identity.display_name,
            email=email,
            password_hash=None,
            role="member",
            avatar_url=identity.avatar_url,
            bio="",
        )
        db.add(user)
        await db.flush()
        provider_identity = ProviderIdentity(
            provider=provider,
            provider_user_id=str(identity.user_id),
            provider_login=identity.login,
            user_id=user.id,
            encrypted_credentials="",
        )
        db.add(provider_identity)
    else:
        user = await db.get(User, provider_identity.user_id)
        if user is None:
            raise ProblemError(500, "Identity unavailable", "auth.identity_invalid")
        provider_identity.provider_login = identity.login
        user.display_name = identity.display_name
        user.avatar_url = identity.avatar_url

    cipher: CredentialCipher = request.app.state.credential_cipher
    provider_identity.encrypted_credentials = cipher.encrypt(credentials)
    provider_identity.credential_expires_at = credentials.expires_at
    provider_identity.refresh_expires_at = credentials.refresh_expires_at
    provider_identity.last_authorized_at = now

    old_cookie = request.cookies.get(config.cookie_name)
    if old_cookie:
        old_session = await db.scalar(
            select(Session).where(Session.token_hash == token_hash(old_cookie))
        )
        if old_session:
            await db.delete(old_session)
    raw_session, session = new_session(user.id, config)
    db.add(session)
    await db.commit()

    response = RedirectResponse(transaction.return_to, status_code=302)
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        config.cookie_name,
        raw_session,
        max_age=config.session_hours * 3600,
        httponly=True,
        secure=config.cookie_secure,
        samesite=config.cookie_samesite,
        domain=config.cookie_domain,
        path="/",
    )
    return response
