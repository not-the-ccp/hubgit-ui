from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings
from .models import Session, User

password_hasher = PasswordHasher(time_cost=2, memory_cost=19_456, parallelism=1)


class ProblemError(Exception):
    """A deliberately safe, stable client error exposed as problem+json."""

    def __init__(self, status_code: int, title: str, code: str, detail: str | None = None) -> None:
        self.status_code = status_code
        self.title = title
        self.code = code
        self.detail = detail


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if password_hash is None:
        return False
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def get_db(request: Request):
    async with request.app.state.database.sessions() as session:
        yield session


def settings(request: Request) -> Settings:
    return request.app.state.settings


async def current_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Session | None:
    value = request.cookies.get(request.app.state.settings.cookie_name)
    if not value:
        return None
    query = select(Session).where(Session.token_hash == token_hash(value))
    record = (await db.execute(query)).scalar_one_or_none()
    if record is None:
        return None
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        await db.delete(record)
        await db.commit()
        return None
    await db.refresh(record, ["user"])
    return record


async def optional_user(session: Session | None = Depends(current_session)) -> User | None:
    return session.user if session else None


async def require_user(session: Session | None = Depends(current_session)) -> User:
    if session is None:
        raise ProblemError(401, "Authentication required", "auth.required")
    return session.user


async def require_csrf(
    request: Request,
    session: Session | None = Depends(current_session),
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> User:
    if session is None:
        raise ProblemError(401, "Authentication required", "auth.required")
    validate_unsafe_request_origin(request)
    if csrf is None or not secrets.compare_digest(csrf, session.csrf_token):
        raise ProblemError(403, "Forbidden", "auth.csrf_invalid")
    return session.user


def validate_unsafe_request_origin(request: Request) -> None:
    """Only accept browser cookie mutations from explicitly trusted origins."""
    value = request.headers.get("origin")
    if value is None:
        referer = request.headers.get("referer")
        if referer:
            try:
                value = Settings.origin_from_url(referer)
            except ValueError:
                value = None
    else:
        try:
            value = Settings._origin(value)
        except ValueError:
            value = None
    if value not in request.app.state.settings.trusted_request_origins:
        raise ProblemError(403, "Forbidden", "auth.origin_invalid")


def new_session(user_id: int, config: Settings) -> tuple[str, Session]:
    raw = secrets.token_urlsafe(32)
    return raw, Session(
        token_hash=token_hash(raw),
        csrf_token=secrets.token_urlsafe(24),
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=config.session_hours),
    )
