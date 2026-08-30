"""ASGI application factory for HubGit's bounded Wave 1 API."""

from __future__ import annotations

import base64
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings
from .database import Database
from .models import Session, User
from .providers import MockRepositoryProvider, RepositoryNotFoundError, RepositoryProvider
from .schemas import LoginInput
from .security import current_session, get_db, hash_password, new_session, optional_user, require_csrf, require_user, settings, token_hash, verify_password


def _problem(request: Request, status_code: int, title: str, code: str, detail: str | None = None, *, field_errors: list[dict] | None = None) -> JSONResponse:
    body: dict = {"type": f"https://hubgit.dev/problems/{code}", "title": title, "status": status_code, "code": code, "instance": request.url.path}
    if detail:
        body["detail"] = detail
    if field_errors:
        body["fieldErrors"] = field_errors
    return JSONResponse(status_code=status_code, content=body, media_type="application/problem+json")


async def _seed_mock_user(database: Database, config: Settings) -> None:
    async with database.sessions() as db:
        present = await db.scalar(select(User.id).where(User.login == config.mock_login))
        if present is None:
            db.add(User(login=config.mock_login, display_name="Demo User", email="demo@example.test", password_hash=hash_password(config.mock_password), role="member", bio="Local mock account."))
            await db.commit()


def _viewer(user: User) -> dict:
    result = user.public()
    result.update({"email": user.email, "roles": ["administrator" if user.role == "admin" else user.role], "unreadNotificationCount": 0})
    return result


def _session_body(session, user: User | None) -> dict:
    if session is None:
        return {"authenticated": False, "csrfToken": "", "expiresAt": None, "viewer": None}
    return {"authenticated": True, "csrfToken": session.csrf_token, "expiresAt": session.expires_at.isoformat(), "viewer": _viewer(user) if user else None}


def _cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode().rstrip("=")


def _offset(value: str | None) -> int:
    if not value:
        return 0
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
        parsed = int(decoded)
        return parsed if parsed >= 0 else 0
    except (ValueError, UnicodeDecodeError):
        return 0


def create_app(config: Settings | None = None, provider: RepositoryProvider | None = None) -> FastAPI:
    """Create an independently configurable ASGI application."""
    app_settings = config or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database = Database(app_settings.database_url)
        app.state.database = database
        app.state.settings = app_settings
        app.state.repository_provider = provider or MockRepositoryProvider()
        await database.create_all()
        await _seed_mock_user(database, app_settings)
        try:
            yield
        finally:
            await database.close()

    app = FastAPI(title=app_settings.instance_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=app_settings.cors_origin_list, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "X-CSRF-Token", "If-Match", "Idempotency-Key"])

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        codes = {401: ("Authentication required", "auth.required"), 403: ("Forbidden", "auth.csrf_invalid"), 404: ("Not found", "resource.not_found")}
        title, code = codes.get(exc.status_code, ("Request failed", "request.failed"))
        return _problem(request, exc.status_code, title, code, str(exc.detail) if exc.detail else None)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"field": ".".join(str(part) for part in error["loc"] if part != "body"), "code": error["type"], "message": error["msg"]} for error in exc.errors()]
        return _problem(request, 422, "Validation failed", "request.validation_failed", "One or more fields are invalid.", field_errors=errors)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return _problem(request, 500, "Internal server error", "server.internal_error")

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/api/v1/meta")
    async def meta(config: Settings = Depends(settings)) -> dict:
        return {"name": config.instance_name, "baseUrl": config.public_base_url, "branding": config.branding, "registrationEnabled": config.registration_enabled, "version": "0.1.0"}

    @app.get("/api/v1/capabilities")
    async def capabilities(request: Request) -> dict:
        return {"provider": request.app.state.repository_provider.provider_name, "version": "1", "features": {"issues": False, "pullRequests": False, "releases": False, "wiki": False, "discussions": False, "projects": False, "actions": False, "security": False, "insights": False, "webhooks": False, "repositoryRules": False, "serverSentEvents": False}, "limits": {"maxPageSize": 100, "maxUploadBytes": 0}}

    @app.get("/api/v1/auth/methods")
    async def auth_methods() -> dict:
        return {"password": True, "passkey": False, "twoFactor": False}

    @app.get("/api/v1/auth/session")
    async def auth_session(session: Session | None = Depends(current_session)) -> dict:
        return _session_body(session, session.user if session else None)

    @app.post("/api/v1/auth/login")
    async def login(payload: LoginInput, response: Response, db: AsyncSession = Depends(get_db), config: Settings = Depends(settings)) -> dict:
        user = await db.scalar(select(User).where(User.login == payload.login))
        if user is None or not verify_password(user.password_hash, payload.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login or password")
        raw_token, session = new_session(user.id, config)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        response.set_cookie(config.cookie_name, raw_token, max_age=config.session_hours * 3600, httponly=True, secure=config.cookie_secure, samesite="lax", path="/")
        return _session_body(session, user)

    @app.delete("/api/v1/auth/session", status_code=status.HTTP_204_NO_CONTENT)
    async def logout(request: Request, user: User = Depends(require_csrf), db: AsyncSession = Depends(get_db)) -> Response:
        cookie = request.cookies.get(request.app.state.settings.cookie_name)
        if cookie:
            record = await db.scalar(select(Session).where(Session.token_hash == token_hash(cookie)))
            if record:
                await db.delete(record)
                await db.commit()
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(request.app.state.settings.cookie_name, path="/")
        return response

    @app.get("/api/v1/viewer")
    async def viewer(user: User = Depends(require_user)) -> dict:
        return _viewer(user)

    @app.get("/api/v1/repositories")
    async def list_repositories(request: Request, cursor: str | None = None, limit: int = 30, q: str | None = None, viewer: User | None = Depends(optional_user)) -> dict:
        limit = min(max(limit, 1), 100)
        items = await request.app.state.repository_provider.list_repositories(query=q, viewer=viewer)
        start = _offset(cursor)
        page = items[start:start + limit]
        next_offset = start + len(page)
        return {"items": page, "pageInfo": {"startCursor": _cursor(start) if page else None, "endCursor": _cursor(next_offset) if page else None, "hasNextPage": next_offset < len(items), "hasPreviousPage": start > 0}, "totalCount": len(items)}

    @app.get("/api/v1/repositories/{owner}/{repo}")
    async def repository(request: Request, owner: str, repo: str, viewer: User | None = Depends(optional_user)) -> dict:
        try:
            return await request.app.state.repository_provider.get_repository(owner, repo, viewer=viewer)
        except RepositoryNotFoundError:
            return _problem(request, 404, "Repository not found", "repository.not_found", "The repository does not exist or is not accessible.")

    @app.get("/api/v1/repositories/{owner}/{repo}/tree/{ref}")
    async def tree(request: Request, owner: str, repo: str, ref: str, path: str = "", viewer: User | None = Depends(optional_user)) -> dict:
        try:
            return await request.app.state.repository_provider.get_tree(owner, repo, ref, path, viewer=viewer)
        except RepositoryNotFoundError:
            return _problem(request, 404, "Tree not found", "git.tree_not_found", "The requested repository, ref, or path does not exist.")

    return app


app = create_app()
