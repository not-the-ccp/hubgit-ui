"""ASGI application factory for HubGit's bounded Wave 1 API."""

from __future__ import annotations

import base64
import binascii
from contextlib import asynccontextmanager
from typing import Annotated, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .config import Settings
from .collaboration import router as collaboration_router, seed_collaboration
from .database import Database
from .discovery import router as discovery_router
from .models import Session, User
from .providers import MockRepositoryProvider, RepositoryNotFoundError, RepositoryProvider
from .schemas import AuthMethods, InstanceMeta, LoginInput
from .security import ProblemError, current_session, get_db, hash_password, new_session, optional_user, require_csrf, require_user, settings, token_hash, verify_password


def _problem(request: Request, status_code: int, title: str, code: str, detail: str | None = None, *, field_errors: list[dict] | None = None) -> JSONResponse:
    body: dict = {"type": f"https://hubgit.dev/problems/{code}", "title": title, "status": status_code, "code": code, "instance": request.url.path}
    if detail:
        body["detail"] = detail
    if field_errors:
        body["fieldErrors"] = field_errors
    return JSONResponse(status_code=status_code, content=body, media_type="application/problem+json")


class RequestSizeLimitMiddleware:
    """Bound unsafe request bodies before FastAPI or a dependency reads them."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH", "DELETE"}:
            await self.app(scope, receive, send)
            return

        headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope["headers"]}
        declared_length = headers.get("content-length")
        if declared_length is not None:
            if not declared_length.isdecimal():
                await self._reject(scope, receive, send, 400, "Invalid request", "request.invalid_content_length")
                return
            if int(declared_length) > self.max_bytes:
                await self._reject(scope, receive, send, 413, "Payload too large", "request.payload_too_large")
                return

        chunks: list[bytes] = []
        received = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            received += len(chunk)
            if received > self.max_bytes:
                await self._reject(scope, receive, send, 413, "Payload too large", "request.payload_too_large")
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if delivered:
                return {"type": "http.disconnect"}
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send, status_code: int, title: str, code: str) -> None:
        response = JSONResponse(
            status_code=status_code,
            content={"type": f"https://hubgit.dev/problems/{code}", "title": title, "status": status_code, "code": code, "instance": scope["path"]},
            media_type="application/problem+json",
        )
        await response(scope, receive, send)


async def _seed_mock_user(database: Database, config: Settings) -> None:
    async with database.sessions() as db:
        present = await db.scalar(select(User.id).where(User.login == config.mock_login))
        if present is None and config.seed_mock_user:
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
        decoded = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True).decode("ascii")
        parsed = int(decoded)
        if parsed < 0 or _cursor(parsed) != value:
            raise ValueError
        return parsed
    except (ValueError, UnicodeDecodeError, binascii.Error):
        raise ProblemError(400, "Invalid cursor", "pagination.invalid_cursor", "The cursor is malformed.") from None


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
        if app.state.repository_provider.provider_name == "mock":
            await seed_collaboration(database)
        try:
            yield
        finally:
            await database.close()

    app = FastAPI(title=app_settings.instance_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=app_settings.cors_origin_list, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "X-CSRF-Token", "If-Match", "Idempotency-Key"])
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=app_settings.max_request_bytes)
    app.include_router(collaboration_router)
    app.include_router(discovery_router)

    @app.exception_handler(ProblemError)
    async def problem_error(request: Request, exc: ProblemError) -> JSONResponse:
        return _problem(request, exc.status_code, exc.title, exc.code, exc.detail)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        codes = {400: ("Invalid request", "request.invalid"), 401: ("Authentication required", "auth.required"), 403: ("Forbidden", "auth.forbidden"), 404: ("Not found", "resource.not_found")}
        title, code = codes.get(exc.status_code, ("Request failed", "request.failed"))
        return _problem(request, exc.status_code, title, code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"field": ".".join(str(part) for part in error["loc"] if part != "body"), "code": error["type"], "message": error["msg"]} for error in exc.errors()]
        return _problem(request, 422, "Validation failed", "request.validation_failed", "One or more fields are invalid.", field_errors=errors)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return _problem(request, 500, "Internal server error", "server.internal_error")

    @app.get("/healthz", include_in_schema=False)
    async def healthz(request: Request) -> dict:
        async with request.app.state.database.sessions() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ok"}

    @app.get("/api/v1/meta", response_model=InstanceMeta, response_model_by_alias=True)
    async def meta(config: Settings = Depends(settings)) -> InstanceMeta:
        return InstanceMeta.model_validate(
            {
                "name": config.instance_name,
                "baseUrl": config.public_base_url,
                "branding": config.branding_manifest,
                "registrationEnabled": config.registration_enabled,
                "version": "0.1.0",
            }
        )

    @app.get("/api/v1/capabilities")
    async def capabilities(request: Request) -> dict:
        return {"provider": request.app.state.repository_provider.provider_name, "version": "1", "features": {"issues": True, "pullRequests": True, "releases": False, "wiki": False, "discussions": False, "projects": False, "actions": False, "security": False, "insights": False, "webhooks": False, "repositoryRules": False, "serverSentEvents": False}, "limits": {"maxPageSize": 100, "maxUploadBytes": 0}}

    @app.get("/api/v1/auth/methods", response_model=AuthMethods, response_model_by_alias=True)
    async def auth_methods(config: Settings = Depends(settings)) -> AuthMethods:
        providers = []
        if config.provider == "github":
            providers.append(
                {
                    "id": "github",
                    "displayName": config.brand_provider_label,
                    "enabled": True,
                    "supportsRegistration": True,
                }
            )
        return AuthMethods.model_validate(
            {
                "password": config.provider == "mock",
                "passkey": False,
                "twoFactor": False,
                "providers": providers,
            }
        )

    @app.get("/api/v1/auth/session")
    async def auth_session(session: Session | None = Depends(current_session)) -> dict:
        return _session_body(session, session.user if session else None)

    @app.post("/api/v1/auth/login")
    async def login(request: Request, payload: LoginInput, response: Response, db: AsyncSession = Depends(get_db), config: Settings = Depends(settings)) -> dict:
        user = await db.scalar(select(User).where(User.login == payload.login))
        if user is None or not verify_password(user.password_hash, payload.password):
            raise ProblemError(status.HTTP_401_UNAUTHORIZED, "Authentication failed", "auth.invalid_credentials", "Invalid credentials.")
        # Rotate a supplied identifier so an old cookie cannot survive login.
        prior_token = request.cookies.get(config.cookie_name)
        if prior_token:
            await db.execute(delete(Session).where(Session.token_hash == token_hash(prior_token)))
        raw_token, session = new_session(user.id, config)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        response.set_cookie(config.cookie_name, raw_token, max_age=config.session_hours * 3600, httponly=True, secure=config.cookie_secure, samesite=config.cookie_samesite, domain=config.cookie_domain, path="/")
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
    async def list_repositories(request: Request, cursor: str | None = Query(default=None, max_length=64), limit: Annotated[int, Query(ge=1, le=100)] = 30, q: str | None = Query(default=None, max_length=200), viewer: User | None = Depends(optional_user)) -> dict:
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
            return _problem(request, 404, "Repository not found", "repository.not_found", "The repository does not exist or is not accessible.")

    return app


app = create_app()
