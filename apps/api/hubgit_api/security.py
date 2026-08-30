from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings
from .models import Session, User

password_hasher = PasswordHasher(time_cost=2, memory_cost=19_456, parallelism=1)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return session.user


async def require_csrf(
    session: Session | None = Depends(current_session),
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> User:
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if csrf is None or not secrets.compare_digest(csrf, session.csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
    return session.user


def new_session(user_id: int, config: Settings) -> tuple[str, Session]:
    raw = secrets.token_urlsafe(32)
    return raw, Session(
        token_hash=token_hash(raw),
        csrf_token=secrets.token_urlsafe(24),
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=config.session_hours),
    )

