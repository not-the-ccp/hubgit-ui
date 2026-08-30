"""Dashboard, notifications, and search over provider-neutral mock resources."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .collaboration import _cursor, _offset, _page, _public, _repository
from .models import CollaborationItem, Notification, User
from .schemas import NotificationUpdate
from .security import ProblemError, get_db, optional_user, require_csrf, require_user

router = APIRouter(prefix="/api/v1")


@router.get("/dashboard")
async def dashboard(
    request: Request,
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    user: User = Depends(require_user),
) -> dict:
    repositories = await request.app.state.repository_provider.list_repositories(
        query=None, viewer=user
    )
    start = _offset(cursor)
    page = repositories[start : start + limit]
    return {
        "repositories": _page(page, start, len(repositories)),
        "activity": [] if request.app.state.repository_provider.provider_name != "mock" else [
            {
                "id": "activity_mock_push",
                "kind": "commit",
                "actor": user.public(),
                "subject": {
                    "kind": "repository",
                    "id": "mock_repo_demo_hubgit-demo",
                    "title": "demo/hubgit-demo",
                    "url": "/demo/hubgit-demo",
                },
                "createdAt": "2026-08-29T12:00:00+00:00",
                "metadata": {"commits": 3},
            }
        ],
    }


@router.get("/notifications")
async def list_notifications(
    unread: bool | None = None,
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Notification).where(Notification.user_id == user.id)
    if unread is not None:
        query = query.where(Notification.unread == unread)
    records = list(
        (await db.scalars(query.order_by(Notification.updated_at.desc()))).all()
    )
    start = _offset(cursor)
    return _page(
        [item.public() for item in records[start : start + 30]],
        start,
        len(records),
    )


@router.patch("/notifications", status_code=204)
async def mark_notifications_read(
    payload: NotificationUpdate,
    user: User = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> Response:
    query = select(Notification).where(Notification.user_id == user.id)
    records = list((await db.scalars(query)).all())
    selected = set(payload.ids)
    for item in records:
        if payload.all or f"notification_{item.id}" in selected:
            item.unread = False
    await db.commit()
    return Response(status_code=204)


SearchType = Literal[
    "repositories",
    "code",
    "commits",
    "issues",
    "pulls",
    "discussions",
    "users",
    "organizations",
]


@router.get("/search")
async def search(
    request: Request,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    result_type: Annotated[SearchType | None, Query(alias="type")] = None,
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    user: User | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    needle = q.casefold()
    results: list[dict] = []
    if result_type in {None, "repositories"}:
        repositories = await request.app.state.repository_provider.list_repositories(
            query=q, viewer=user
        )
        results.extend(
            {"kind": "repository", "score": 1.0, "repository": repository}
            for repository in repositories
        )

    if result_type in {None, "issues", "pulls"}:
        items = list(
            (
                await db.scalars(
                    select(CollaborationItem).where(
                        CollaborationItem.kind.in_(["issue", "pullRequest"])
                    )
                )
            ).all()
        )
        for item in items:
            if result_type == "issues" and item.kind != "issue":
                continue
            if result_type == "pulls" and item.kind != "pullRequest":
                continue
            if needle not in str(item.data.get("title", "")).casefold() and needle not in str(
                item.data.get("body", "")
            ).casefold():
                continue
            owner, repo = item.repository_key.split("/", 1)
            try:
                await _repository(request, owner, repo, user)
            except ProblemError as error:
                if error.status_code == 404:
                    continue
                raise
            results.append(
                {
                    "kind": item.kind,
                    "score": 0.9,
                    "repository": item.repository_key,
                    "issue": _public(item, user, owner),
                }
            )

    if result_type in {None, "users"}:
        users = list((await db.scalars(select(User))).all())
        results.extend(
            {"kind": "user", "score": 0.8, "user": candidate.public()}
            for candidate in users
            if needle in candidate.login.casefold()
            or needle in candidate.display_name.casefold()
        )

    if (
        request.app.state.repository_provider.provider_name == "mock"
        and result_type == "code"
        and needle in "provider-neutral git frontend"
    ):
        results.append(
            {
                "kind": "code",
                "score": 0.7,
                "repository": "demo/hubgit-demo",
                "path": "README.md",
                "matches": [
                    {"line": 3, "fragment": "Provider-neutral Git frontend"}
                ],
            }
        )

    start = _offset(cursor)
    return _page(results[start : start + 30], start, len(results))
