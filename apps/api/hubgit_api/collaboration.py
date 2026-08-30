"""Stateful provider-neutral issue and pull-request mock routes."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from .database import Database
from .models import CollaborationItem, IdempotencyRecord, Notification, User, now_utc
from .providers import MockRepositoryProvider, RepositoryNotFoundError
from .schemas import CommentInput, IssueInput, MergeInput, PullInput, ReviewInput
from .security import ProblemError, get_db, optional_user, require_csrf


def require_collaboration_capability(request: Request) -> None:
    if request.app.state.repository_provider.provider_name != "mock":
        raise ProblemError(
            501,
            "Capability unsupported",
            "capability.unsupported",
            "The configured provider adapter does not support this collaboration operation.",
        )


router = APIRouter(
    prefix="/api/v1", dependencies=[Depends(require_collaboration_capability)]
)

_FIXTURE_TIME = "2026-08-29T12:00:00+00:00"
_HEAD_SHA = "b21bd771e53b4d2c6f4a88f1ca8e218c17ab0042"
_BASE_SHA = "a21bd771e53b4d2c6f4a88f1ca8e218c17ab0001"
_FIXTURE_AUTHOR = {
    "id": "mock_user_demo",
    "kind": "user",
    "username": "demo",
    "displayName": "Demo User",
    "avatarUrl": "https://api.dicebear.com/9.x/identicon/svg?seed=demo",
    "profileUrl": "/demo",
}


async def seed_collaboration(database: Database) -> None:
    """Create deterministic collaboration state once per database."""
    async with database.sessions() as db:
        present = await db.scalar(select(CollaborationItem.id).limit(1))
        if present is None:
            db.add_all(
                [
                CollaborationItem(
                    repository_key="demo/hubgit-demo",
                    kind="issue",
                    number=1,
                    data={
                        "kind": "issue",
                        "title": "Add keyboard navigation to the ref selector",
                        "body": "The branch and tag selector should support roving focus.",
                        "state": "open",
                        "stateReason": None,
                        "author": _FIXTURE_AUTHOR,
                        "labels": [
                            {
                                "id": "label_accessibility",
                                "name": "accessibility",
                                "color": "0969da",
                                "description": "Accessibility improvement",
                            }
                        ],
                        "assignees": [],
                        "milestone": None,
                        "commentCount": 1,
                        "createdAt": _FIXTURE_TIME,
                        "closedAt": None,
                    },
                ),
                CollaborationItem(
                    repository_key="demo/hubgit-demo",
                    kind="issueComment",
                    number=1,
                    data={
                        "issueNumber": 1,
                        "body": "I can take the keyboard behavior and tests.",
                        "author": _FIXTURE_AUTHOR,
                        "reactions": [],
                        "createdAt": _FIXTURE_TIME,
                    },
                ),
                CollaborationItem(
                    repository_key="demo/hubgit-demo",
                    kind="pullRequest",
                    number=2,
                    data={
                        "kind": "pullRequest",
                        "title": "Build provider-neutral repository overview payload",
                        "body": "Connect the repository shell to the canonical API response.",
                        "state": "open",
                        "draft": False,
                        "author": _FIXTURE_AUTHOR,
                        "base": {
                            "repository": "demo/hubgit-demo",
                            "ref": "main",
                            "sha": _BASE_SHA,
                        },
                        "head": {
                            "repository": "demo/hubgit-demo",
                            "ref": "feature/repository-payload",
                            "sha": _HEAD_SHA,
                        },
                        "mergeability": "mergeable",
                        "reviewDecision": "review_required",
                        "checks": {
                            "total": 2,
                            "queued": 0,
                            "inProgress": 0,
                            "successful": 2,
                            "failed": 0,
                        },
                        "labels": [],
                        "createdAt": _FIXTURE_TIME,
                        "mergedAt": None,
                    },
                ),
                ]
            )
        notification = await db.scalar(select(Notification.id).limit(1))
        user = await db.scalar(select(User).where(User.login == "demo"))
        if notification is None and user is not None:
            repository = await MockRepositoryProvider().get_repository(
                "demo", "hubgit-demo", viewer=user
            )
            db.add(
                Notification(
                    user_id=user.id,
                    reason="review_requested",
                    unread=True,
                    subject={
                        "kind": "pullRequest",
                        "id": "pullRequest_2",
                        "title": "Build provider-neutral repository overview payload",
                        "url": "/demo/hubgit-demo/pulls/2",
                    },
                    repository=repository,
                )
            )
        await db.commit()


def _cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode().rstrip("=")


def _offset(value: str | None) -> int:
    if value is None:
        return 0
    try:
        decoded = base64.b64decode(
            value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
        ).decode("ascii")
        offset = int(decoded)
        if offset < 0 or _cursor(offset) != value:
            raise ValueError
        return offset
    except (ValueError, UnicodeDecodeError, binascii.Error):
        raise ProblemError(
            400,
            "Invalid cursor",
            "pagination.invalid_cursor",
            "The cursor is malformed.",
        ) from None


def _page(items: list[dict], start: int, total: int) -> dict:
    end = start + len(items)
    return {
        "items": items,
        "pageInfo": {
            "startCursor": _cursor(start) if items else None,
            "endCursor": _cursor(end) if items else None,
            "hasNextPage": end < total,
            "hasPreviousPage": start > 0,
        },
        "totalCount": total,
    }


def _permissions(user: User | None, owner: str) -> dict[str, bool]:
    admin = user is not None and (user.login == owner or user.role == "admin")
    write = user is not None and (admin or user.role == "maintainer")
    return {
        "read": True,
        "triage": user is not None,
        "write": write,
        "maintain": write,
        "admin": admin,
    }


def _public(item: CollaborationItem, user: User | None, owner: str) -> dict:
    body = item.public()
    body.pop("issueNumber", None)
    body["permissions"] = _permissions(user, owner)
    return body


async def _repository(
    request: Request, owner: str, repo: str, user: User | None
) -> dict:
    try:
        return await request.app.state.repository_provider.get_repository(
            owner, repo, viewer=user
        )
    except RepositoryNotFoundError:
        raise ProblemError(
            404,
            "Repository not found",
            "repository.not_found",
            "The repository does not exist or is not accessible.",
        ) from None


async def _writable_repository(
    request: Request, owner: str, repo: str, user: User
) -> dict:
    repository = await _repository(request, owner, repo, user)
    if not repository["permissions"]["write"]:
        raise ProblemError(403, "Forbidden", "repository.write_forbidden")
    return repository


async def _item(
    db: AsyncSession, repository_key: str, kind: str, number: int
) -> CollaborationItem:
    item = await db.scalar(
        select(CollaborationItem).where(
            CollaborationItem.repository_key == repository_key,
            CollaborationItem.kind == kind,
            CollaborationItem.number == number,
        )
    )
    if item is None:
        raise ProblemError(404, "Not found", f"{kind}.not_found")
    return item


def _fingerprint(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


async def _replay(
    db: AsyncSession, scope: str, key: str, fingerprint: str
) -> IdempotencyRecord | None:
    record = await db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.scope == scope, IdempotencyRecord.key == key
        )
    )
    if record is not None and record.request_hash != fingerprint:
        raise ProblemError(
            409,
            "Idempotency conflict",
            "idempotency.payload_mismatch",
            "The idempotency key was already used with another request.",
        )
    return record


async def _store_replay(
    db: AsyncSession,
    scope: str,
    key: str,
    fingerprint: str,
    response: dict,
    status_code: int,
) -> None:
    db.add(
        IdempotencyRecord(
            scope=scope,
            key=key,
            request_hash=fingerprint,
            response=response,
            status_code=status_code,
        )
    )


@router.get("/repositories/{owner}/{repo}/issues")
async def list_issues(
    request: Request,
    owner: str,
    repo: str,
    state: Literal["open", "closed", "all"] = "open",
    q: Annotated[str | None, Query(max_length=200)] = None,
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    user: User | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _repository(request, owner, repo, user)
    query = select(CollaborationItem).where(
        CollaborationItem.repository_key == f"{owner}/{repo}",
        CollaborationItem.kind == "issue",
    )
    records = list((await db.scalars(query.order_by(CollaborationItem.number.desc()))).all())
    if state != "all":
        records = [item for item in records if item.data.get("state") == state]
    if q:
        needle = q.casefold()
        records = [
            item
            for item in records
            if needle in str(item.data.get("title", "")).casefold()
            or needle in str(item.data.get("body", "")).casefold()
        ]
    start = _offset(cursor)
    return _page(
        [_public(item, user, owner) for item in records[start : start + 30]],
        start,
        len(records),
    )


@router.post(
    "/repositories/{owner}/{repo}/issues", status_code=status.HTTP_201_CREATED
)
async def create_issue(
    request: Request,
    owner: str,
    repo: str,
    payload: IssueInput,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=8, max_length=200)
    ],
    user: User = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await _writable_repository(request, owner, repo, user)
    if payload.title is None:
        raise ProblemError(422, "Validation failed", "issue.title_required")
    request_body = payload.model_dump(by_alias=True, exclude_none=True)
    fingerprint = _fingerprint(request_body)
    scope = f"user:{user.id}:{owner}/{repo}:issue:create"
    replay = await _replay(db, scope, idempotency_key, fingerprint)
    if replay is not None:
        return JSONResponse(replay.response, status_code=replay.status_code)
    next_number = (
        await db.scalar(
            select(func.max(CollaborationItem.number)).where(
                CollaborationItem.repository_key == f"{owner}/{repo}",
                CollaborationItem.kind == "issue",
            )
        )
        or 0
    ) + 1
    item = CollaborationItem(
        repository_key=f"{owner}/{repo}",
        kind="issue",
        number=next_number,
        data={
            "kind": "issue",
            "title": payload.title,
            "body": payload.body or "",
            "state": payload.state or "open",
            "stateReason": payload.state_reason,
            "author": user.public(),
            "labels": [],
            "assignees": [],
            "milestone": None,
            "commentCount": 0,
            "closedAt": None,
        },
    )
    db.add(item)
    await db.flush()
    response_body = _public(item, user, owner)
    await _store_replay(
        db, scope, idempotency_key, fingerprint, response_body, status.HTTP_201_CREATED
    )
    await db.commit()
    return JSONResponse(
        response_body, status_code=status.HTTP_201_CREATED, headers={"ETag": item.etag}
    )


@router.get("/repositories/{owner}/{repo}/issues/{number}")
async def get_issue(
    request: Request,
    owner: str,
    repo: str,
    number: Annotated[int, Path(ge=1)],
    response: Response,
    user: User | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _repository(request, owner, repo, user)
    item = await _item(db, f"{owner}/{repo}", "issue", number)
    response.headers["ETag"] = item.etag
    return _public(item, user, owner)


@router.patch("/repositories/{owner}/{repo}/issues/{number}")
async def update_issue(
    request: Request,
    owner: str,
    repo: str,
    number: Annotated[int, Path(ge=1)],
    payload: IssueInput,
    response: Response,
    if_match: Annotated[str, Header(alias="If-Match")],
    user: User = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _writable_repository(request, owner, repo, user)
    item = await _item(db, f"{owner}/{repo}", "issue", number)
    if if_match != item.etag:
        raise ProblemError(
            412, "Edit conflict", "resource.etag_mismatch", "Reload before editing."
        )
    changes = payload.model_dump(by_alias=True, exclude_unset=True)
    field_map = {
        "title": "title",
        "body": "body",
        "state": "state",
        "stateReason": "stateReason",
    }
    for source, destination in field_map.items():
        if source in changes:
            item.data[destination] = changes[source]
    if changes.get("state") == "closed":
        item.data["closedAt"] = now_utc().isoformat()
    elif changes.get("state") == "open":
        item.data["closedAt"] = None
    item.version += 1
    flag_modified(item, "data")
    await db.commit()
    await db.refresh(item)
    response.headers["ETag"] = item.etag
    return _public(item, user, owner)


@router.get("/repositories/{owner}/{repo}/issues/{number}/comments")
async def list_issue_comments(
    request: Request,
    owner: str,
    repo: str,
    number: Annotated[int, Path(ge=1)],
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    user: User | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _repository(request, owner, repo, user)
    await _item(db, f"{owner}/{repo}", "issue", number)
    records = list(
        (
            await db.scalars(
                select(CollaborationItem).where(
                    CollaborationItem.repository_key == f"{owner}/{repo}",
                    CollaborationItem.kind == "issueComment",
                )
            )
        ).all()
    )
    records = [item for item in records if item.data.get("issueNumber") == number]
    start = _offset(cursor)
    return _page(
        [_public(item, user, owner) for item in records[start : start + 30]],
        start,
        len(records),
    )


@router.post(
    "/repositories/{owner}/{repo}/issues/{number}/comments",
    status_code=status.HTTP_201_CREATED,
)
async def create_issue_comment(
    request: Request,
    owner: str,
    repo: str,
    number: Annotated[int, Path(ge=1)],
    payload: CommentInput,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=8, max_length=200)
    ],
    user: User = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await _writable_repository(request, owner, repo, user)
    issue = await _item(db, f"{owner}/{repo}", "issue", number)
    request_body = payload.model_dump(by_alias=True)
    fingerprint = _fingerprint(request_body)
    scope = f"user:{user.id}:{owner}/{repo}:issue:{number}:comment:create"
    replay = await _replay(db, scope, idempotency_key, fingerprint)
    if replay is not None:
        return JSONResponse(replay.response, status_code=replay.status_code)
    next_number = (
        await db.scalar(
            select(func.max(CollaborationItem.number)).where(
                CollaborationItem.repository_key == f"{owner}/{repo}",
                CollaborationItem.kind == "issueComment",
            )
        )
        or 0
    ) + 1
    item = CollaborationItem(
        repository_key=f"{owner}/{repo}",
        kind="issueComment",
        number=next_number,
        data={
            "issueNumber": number,
            "body": payload.body,
            "author": user.public(),
            "reactions": [],
        },
    )
    db.add(item)
    await db.flush()
    issue.data["commentCount"] = int(issue.data.get("commentCount", 0)) + 1
    issue.version += 1
    flag_modified(issue, "data")
    response_body = _public(item, user, owner)
    await _store_replay(
        db, scope, idempotency_key, fingerprint, response_body, status.HTTP_201_CREATED
    )
    await db.commit()
    return JSONResponse(response_body, status_code=status.HTTP_201_CREATED)


@router.get("/repositories/{owner}/{repo}/pulls")
async def list_pull_requests(
    request: Request,
    owner: str,
    repo: str,
    state: Literal["open", "closed", "all"] = "open",
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    user: User | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _repository(request, owner, repo, user)
    records = list(
        (
            await db.scalars(
                select(CollaborationItem)
                .where(
                    CollaborationItem.repository_key == f"{owner}/{repo}",
                    CollaborationItem.kind == "pullRequest",
                )
                .order_by(CollaborationItem.number.desc())
            )
        ).all()
    )
    if state != "all":
        records = [item for item in records if item.data.get("state") == state]
    start = _offset(cursor)
    return _page(
        [_public(item, user, owner) for item in records[start : start + 30]],
        start,
        len(records),
    )


@router.post(
    "/repositories/{owner}/{repo}/pulls", status_code=status.HTTP_201_CREATED
)
async def create_pull_request(
    request: Request,
    owner: str,
    repo: str,
    payload: PullInput,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=8, max_length=200)
    ],
    user: User = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await _writable_repository(request, owner, repo, user)
    request_body = payload.model_dump(by_alias=True)
    fingerprint = _fingerprint(request_body)
    scope = f"user:{user.id}:{owner}/{repo}:pull:create"
    replay = await _replay(db, scope, idempotency_key, fingerprint)
    if replay is not None:
        return JSONResponse(replay.response, status_code=replay.status_code)
    next_number = (
        await db.scalar(
            select(func.max(CollaborationItem.number)).where(
                CollaborationItem.repository_key == f"{owner}/{repo}",
                CollaborationItem.kind == "pullRequest",
            )
        )
        or 0
    ) + 1
    item = CollaborationItem(
        repository_key=f"{owner}/{repo}",
        kind="pullRequest",
        number=next_number,
        data={
            "kind": "pullRequest",
            "title": payload.title,
            "body": payload.body,
            "state": "open",
            "draft": payload.draft,
            "author": user.public(),
            "base": {
                "repository": f"{owner}/{repo}",
                "ref": payload.base,
                "sha": _BASE_SHA,
            },
            "head": {
                "repository": f"{owner}/{repo}",
                "ref": payload.head,
                "sha": _HEAD_SHA,
            },
            "mergeability": "checking",
            "reviewDecision": "review_required",
            "checks": {
                "total": 0,
                "queued": 0,
                "inProgress": 0,
                "successful": 0,
                "failed": 0,
            },
            "labels": [],
            "mergedAt": None,
        },
    )
    db.add(item)
    await db.flush()
    response_body = _public(item, user, owner)
    await _store_replay(
        db, scope, idempotency_key, fingerprint, response_body, status.HTTP_201_CREATED
    )
    await db.commit()
    return JSONResponse(
        response_body, status_code=status.HTTP_201_CREATED, headers={"ETag": item.etag}
    )


@router.get("/repositories/{owner}/{repo}/pulls/{number}")
async def get_pull_request(
    request: Request,
    owner: str,
    repo: str,
    number: Annotated[int, Path(ge=1)],
    response: Response,
    user: User | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _repository(request, owner, repo, user)
    item = await _item(db, f"{owner}/{repo}", "pullRequest", number)
    response.headers["ETag"] = item.etag
    return _public(item, user, owner)


@router.patch("/repositories/{owner}/{repo}/pulls/{number}")
async def update_pull_request(
    request: Request,
    owner: str,
    repo: str,
    number: Annotated[int, Path(ge=1)],
    payload: IssueInput,
    response: Response,
    if_match: Annotated[str, Header(alias="If-Match")],
    user: User = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _writable_repository(request, owner, repo, user)
    item = await _item(db, f"{owner}/{repo}", "pullRequest", number)
    if if_match != item.etag:
        raise ProblemError(
            412, "Edit conflict", "resource.etag_mismatch", "Reload before editing."
        )
    changes = payload.model_dump(by_alias=True, exclude_unset=True)
    for field in ("title", "body", "state"):
        if field in changes:
            item.data[field] = changes[field]
    item.version += 1
    flag_modified(item, "data")
    await db.commit()
    await db.refresh(item)
    response.headers["ETag"] = item.etag
    return _public(item, user, owner)


@router.get("/repositories/{owner}/{repo}/pulls/{number}/checks")
async def get_pull_request_checks(
    request: Request,
    owner: str,
    repo: str,
    number: Annotated[int, Path(ge=1)],
    user: User | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _repository(request, owner, repo, user)
    await _item(db, f"{owner}/{repo}", "pullRequest", number)
    return {
        "items": [
            {
                "id": f"check_suite_{number}",
                "name": "HubGit CI",
                "status": "completed",
                "conclusion": "success",
                "checks": [
                    {
                        "id": f"check_{number}_tests",
                        "name": "tests",
                        "status": "completed",
                        "conclusion": "success",
                        "detailsUrl": None,
                        "summary": "All deterministic mock checks passed.",
                    }
                ],
                "startedAt": _FIXTURE_TIME,
                "completedAt": _FIXTURE_TIME,
            }
        ],
        "pageInfo": {
            "startCursor": _cursor(0),
            "endCursor": _cursor(1),
            "hasNextPage": False,
            "hasPreviousPage": False,
        },
    }


@router.get("/repositories/{owner}/{repo}/pulls/{number}/files")
async def list_pull_request_files(
    request: Request,
    owner: str,
    repo: str,
    number: Annotated[int, Path(ge=1)],
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    user: User | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _repository(request, owner, repo, user)
    await _item(db, f"{owner}/{repo}", "pullRequest", number)
    files = [
        {
            "oldPath": "README.md",
            "newPath": "README.md",
            "status": "modified",
            "binary": False,
            "additions": 2,
            "deletions": 1,
            "hunks": [
                {
                    "header": "@@ -1,2 +1,3 @@",
                    "lines": [
                        {
                            "kind": "context",
                            "oldLine": 1,
                            "newLine": 1,
                            "content": "# HubGit",
                        },
                        {
                            "kind": "deletion",
                            "oldLine": 2,
                            "newLine": None,
                            "content": "Prototype",
                        },
                        {
                            "kind": "addition",
                            "oldLine": None,
                            "newLine": 2,
                            "content": "Provider-neutral Git frontend",
                        },
                        {
                            "kind": "addition",
                            "oldLine": None,
                            "newLine": 3,
                            "content": "Deterministic mock backend",
                        },
                    ],
                }
            ],
        }
    ]
    start = _offset(cursor)
    return _page(files[start : start + 30], start, len(files))


@router.get("/repositories/{owner}/{repo}/pulls/{number}/reviews")
async def list_pull_request_reviews(
    request: Request,
    owner: str,
    repo: str,
    number: Annotated[int, Path(ge=1)],
    user: User | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _repository(request, owner, repo, user)
    await _item(db, f"{owner}/{repo}", "pullRequest", number)
    records = list(
        (
            await db.scalars(
                select(CollaborationItem).where(
                    CollaborationItem.repository_key == f"{owner}/{repo}",
                    CollaborationItem.kind == "pullReview",
                )
            )
        ).all()
    )
    items = []
    for record in records:
        if record.data.get("pullNumber") != number:
            continue
        body = record.public()
        body.pop("pullNumber", None)
        body.pop("number", None)
        body.pop("kind", None)
        items.append(body)
    return _page(items, 0, len(items))


@router.post(
    "/repositories/{owner}/{repo}/pulls/{number}/reviews",
    status_code=status.HTTP_201_CREATED,
)
async def submit_pull_request_review(
    request: Request,
    owner: str,
    repo: str,
    number: Annotated[int, Path(ge=1)],
    payload: ReviewInput,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=8, max_length=200)
    ],
    user: User = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await _writable_repository(request, owner, repo, user)
    pull = await _item(db, f"{owner}/{repo}", "pullRequest", number)
    request_body = payload.model_dump(by_alias=True)
    fingerprint = _fingerprint(request_body)
    scope = f"user:{user.id}:{owner}/{repo}:pull:{number}:review:create"
    replay = await _replay(db, scope, idempotency_key, fingerprint)
    if replay is not None:
        return JSONResponse(replay.response, status_code=replay.status_code)
    next_number = (
        await db.scalar(
            select(func.max(CollaborationItem.number)).where(
                CollaborationItem.repository_key == f"{owner}/{repo}",
                CollaborationItem.kind == "pullReview",
            )
        )
        or 0
    ) + 1
    state_map = {
        "comment": "commented",
        "approve": "approved",
        "request_changes": "changes_requested",
    }
    item = CollaborationItem(
        repository_key=f"{owner}/{repo}",
        kind="pullReview",
        number=next_number,
        data={
            "pullNumber": number,
            "author": user.public(),
            "state": state_map[payload.event],
            "body": payload.body,
            "commitSha": pull.data["head"]["sha"],
            "submittedAt": now_utc().isoformat(),
        },
    )
    db.add(item)
    await db.flush()
    if payload.event == "approve":
        pull.data["reviewDecision"] = "approved"
    elif payload.event == "request_changes":
        pull.data["reviewDecision"] = "changes_requested"
    pull.version += 1
    flag_modified(pull, "data")
    response_body = item.public()
    response_body.pop("pullNumber", None)
    response_body.pop("number", None)
    response_body.pop("kind", None)
    await _store_replay(
        db, scope, idempotency_key, fingerprint, response_body, status.HTTP_201_CREATED
    )
    await db.commit()
    return JSONResponse(response_body, status_code=status.HTTP_201_CREATED)


@router.post("/repositories/{owner}/{repo}/pulls/{number}/merge")
async def merge_pull_request(
    request: Request,
    owner: str,
    repo: str,
    number: Annotated[int, Path(ge=1)],
    payload: MergeInput,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=8, max_length=200)
    ],
    user: User = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await _writable_repository(request, owner, repo, user)
    item = await _item(db, f"{owner}/{repo}", "pullRequest", number)
    request_body = payload.model_dump(by_alias=True)
    fingerprint = _fingerprint(request_body)
    scope = f"user:{user.id}:{owner}/{repo}:pull:{number}:merge"
    replay = await _replay(db, scope, idempotency_key, fingerprint)
    if replay is not None:
        return JSONResponse(replay.response, status_code=replay.status_code)
    if item.data["state"] != "open":
        raise ProblemError(409, "Pull request is not open", "pull.merge_not_open")
    if payload.expected_head_sha != item.data["head"]["sha"]:
        raise ProblemError(
            409,
            "Head changed",
            "pull.expected_head_mismatch",
            "Reload the pull request before merging.",
        )
    merge_sha = hashlib.sha1(
        f"{item.data['base']['sha']}:{item.data['head']['sha']}:{payload.method}".encode(),
        usedforsecurity=False,
    ).hexdigest()
    result = {"merged": True, "sha": merge_sha, "message": "Pull request merged."}
    item.data["state"] = "merged"
    item.data["mergedAt"] = now_utc().isoformat()
    item.version += 1
    flag_modified(item, "data")
    await _store_replay(db, scope, idempotency_key, fingerprint, result, 200)
    await db.commit()
    return JSONResponse(result)
