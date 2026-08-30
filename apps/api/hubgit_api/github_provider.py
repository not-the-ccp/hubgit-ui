"""Canonical repository reads backed by GitHub user-to-server tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx
from sqlalchemy import select

from .config import Settings
from .database import Database
from .github_auth import CredentialCipher, GitHubAuthError, GitHubAuthPort
from .models import ProviderIdentity, User
from .providers import (
    ProviderAuthenticationError,
    ProviderRateLimitedError,
    ProviderUnavailableError,
    RepositoryNotFoundError,
)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class GitHubCredentialBroker:
    """Resolve and rotate one viewer's encrypted GitHub credential."""

    def __init__(
        self,
        database: Database,
        cipher: CredentialCipher,
        auth: GitHubAuthPort,
    ) -> None:
        self.database = database
        self.cipher = cipher
        self.auth = auth

    async def access_token(self, viewer: User | None) -> tuple[str, datetime]:
        if viewer is None:
            raise ProviderAuthenticationError("GitHub-backed browsing requires a session.")
        async with self.database.sessions() as db:
            identity = await db.scalar(
                select(ProviderIdentity).where(
                    ProviderIdentity.provider == "github",
                    ProviderIdentity.user_id == viewer.id,
                )
            )
            if identity is None:
                raise ProviderAuthenticationError("The session has no GitHub identity.")
            credentials = self.cipher.decrypt(identity.encrypted_credentials)
            now = datetime.now(timezone.utc)
            expires_at = identity.credential_expires_at
            if expires_at is not None and _aware(expires_at) <= now + timedelta(minutes=1):
                refresh_token = credentials.get("refreshToken")
                refresh_expires_at = identity.refresh_expires_at
                if (
                    not refresh_token
                    or (refresh_expires_at is not None and _aware(refresh_expires_at) <= now)
                ):
                    raise ProviderAuthenticationError("The GitHub authorization has expired.")
                try:
                    refreshed = await self.auth.refresh_credentials(refresh_token)
                except GitHubAuthError as exc:
                    raise ProviderAuthenticationError(
                        "The GitHub authorization could not be refreshed."
                    ) from exc
                identity.encrypted_credentials = self.cipher.encrypt(refreshed)
                identity.credential_expires_at = refreshed.expires_at
                identity.refresh_expires_at = refreshed.refresh_expires_at
                identity.last_authorized_at = now
                await db.commit()
                return refreshed.access_token, now
            return credentials["accessToken"] or "", _aware(identity.last_authorized_at)


class GitHubRepositoryProvider:
    """The initial GitHub adapter family: repository list, detail, and trees."""

    provider_name = "github"

    def __init__(
        self,
        config: Settings,
        database: Database,
        cipher: CredentialCipher,
        auth: GitHubAuthPort,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_base_url = config.github_api_base_url.rstrip("/")
        self.credentials = GitHubCredentialBroker(database, cipher, auth)
        self._transport = transport

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "HubGit/0.1",
        }

    async def _get(
        self,
        path: str,
        token: str,
        *,
        params: dict[str, str | int] | None = None,
        conceal: bool = False,
    ) -> Any:
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=20.0) as client:
                response = await client.get(
                    f"{self.api_base_url}{path}",
                    params=params,
                    headers={**self._headers, "Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("GitHub is unavailable.") from exc
        if response.status_code == 401:
            raise ProviderAuthenticationError("GitHub rejected the stored authorization.")
        if response.status_code in {403, 429}:
            if response.headers.get("x-ratelimit-remaining") == "0" or response.status_code == 429:
                raise ProviderRateLimitedError("GitHub rate limit exhausted.")
            if conceal:
                raise RepositoryNotFoundError(path)
            raise ProviderUnavailableError("GitHub denied the repository request.")
        if response.status_code == 404:
            raise RepositoryNotFoundError(path)
        if response.status_code >= 500:
            raise ProviderUnavailableError("GitHub is unavailable.")
        if response.status_code != 200:
            raise ProviderUnavailableError("GitHub returned an unexpected response.")
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderUnavailableError("GitHub returned malformed JSON.") from exc

    @staticmethod
    def _freshness(last_authorized_at: datetime) -> dict[str, object]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "state": "live",
            "lastSyncedAt": now,
            "lastAuthorizedAt": last_authorized_at.isoformat(),
            "provider": "github",
        }

    def _repository(self, body: dict[str, Any], last_authorized_at: datetime) -> dict[str, Any]:
        try:
            owner = body["owner"]
            permissions = body.get("permissions") or {}
            license_body = body.get("license")
            visibility = body.get("visibility") or ("private" if body.get("private") else "public")
            return {
                "id": f"github-repository-{body['id']}",
                "kind": "repository",
                "owner": {
                    "id": f"github-owner-{owner['id']}",
                    "kind": "organization" if owner.get("type") == "Organization" else "user",
                    "login": owner["login"],
                    "avatarUrl": owner.get("avatar_url") or "",
                },
                "name": body["name"],
                "fullName": body["full_name"],
                "description": body.get("description"),
                "visibility": visibility,
                "defaultBranch": body.get("default_branch") or "main",
                "empty": body.get("size", 0) == 0,
                "archived": bool(body.get("archived")),
                "fork": bool(body.get("fork")),
                "forkedFrom": (body.get("parent") or {}).get("full_name"),
                "language": body.get("language"),
                "license": license_body.get("spdx_id") if isinstance(license_body, dict) else None,
                "topics": body.get("topics") if isinstance(body.get("topics"), list) else [],
                "permissions": {
                    "read": True,
                    "triage": bool(permissions.get("triage")),
                    "write": bool(permissions.get("push")),
                    "maintain": bool(permissions.get("maintain")),
                    "admin": bool(permissions.get("admin")),
                },
                "counts": {
                    "stars": int(body.get("stargazers_count") or 0),
                    "forks": int(body.get("forks_count") or 0),
                    "watchers": int(body.get("subscribers_count") or body.get("watchers_count") or 0),
                    "issues": int(body.get("open_issues_count") or 0),
                    "pullRequests": 0,
                },
                "cloneUrls": {"http": body["clone_url"], "ssh": body["ssh_url"]},
                "createdAt": body["created_at"],
                "updatedAt": body["updated_at"],
                "pushedAt": body.get("pushed_at"),
                "freshness": self._freshness(last_authorized_at),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderUnavailableError("GitHub repository data was malformed.") from exc

    async def list_repositories(self, *, query: str | None, viewer: User | None) -> list[dict]:
        token, authorized_at = await self.credentials.access_token(viewer)
        results: list[dict] = []
        for page in range(1, 11):
            body = await self._get(
                "/user/repos",
                token,
                params={
                    "affiliation": "owner,collaborator,organization_member",
                    "visibility": "all",
                    "sort": "updated",
                    "per_page": 100,
                    "page": page,
                },
            )
            if not isinstance(body, list):
                raise ProviderUnavailableError("GitHub repository list was malformed.")
            results.extend(self._repository(item, authorized_at) for item in body)
            if len(body) < 100:
                break
        if query:
            needle = query.casefold()
            results = [
                item
                for item in results
                if needle in item["fullName"].casefold()
                or needle in (item.get("description") or "").casefold()
            ]
        return results

    async def get_repository(self, owner: str, repo: str, *, viewer: User | None) -> dict:
        token, authorized_at = await self.credentials.access_token(viewer)
        body = await self._get(
            f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}", token, conceal=True
        )
        if not isinstance(body, dict):
            raise ProviderUnavailableError("GitHub repository data was malformed.")
        return self._repository(body, authorized_at)

    @staticmethod
    def _commit(body: dict[str, Any]) -> tuple[dict[str, Any], str]:
        try:
            details = body["commit"]
            author = details["author"]
            sha = body["sha"]
            return (
                {
                    "sha": sha,
                    "shortSha": sha[:12],
                    "message": details["message"],
                    "author": {"name": author["name"], "email": author["email"]},
                    "authoredAt": author["date"],
                },
                details["tree"]["sha"],
            )
        except (KeyError, TypeError) as exc:
            raise ProviderUnavailableError("GitHub commit data was malformed.") from exc

    async def get_tree(
        self, owner: str, repo: str, ref: str, path: str, *, viewer: User | None
    ) -> dict:
        token, _ = await self.credentials.access_token(viewer)
        prefix = f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}"
        commit_body = await self._get(
            f"{prefix}/commits/{quote(ref, safe='')}", token, conceal=True
        )
        if not isinstance(commit_body, dict):
            raise ProviderUnavailableError("GitHub commit data was malformed.")
        commit, tree_sha = self._commit(commit_body)
        clean_path = path.strip("/")
        components = [component for component in clean_path.split("/") if component]
        tree_body: dict[str, Any] | None = None
        for component in components:
            body = await self._get(f"{prefix}/git/trees/{quote(tree_sha, safe='')}", token, conceal=True)
            if not isinstance(body, dict) or not isinstance(body.get("tree"), list):
                raise ProviderUnavailableError("GitHub tree data was malformed.")
            match = next(
                (
                    entry
                    for entry in body["tree"]
                    if entry.get("path") == component and entry.get("type") == "tree"
                ),
                None,
            )
            if match is None or not isinstance(match.get("sha"), str):
                raise RepositoryNotFoundError(clean_path)
            tree_sha = match["sha"]
        tree_body = await self._get(
            f"{prefix}/git/trees/{quote(tree_sha, safe='')}", token, conceal=True
        )
        if not isinstance(tree_body, dict) or not isinstance(tree_body.get("tree"), list):
            raise ProviderUnavailableError("GitHub tree data was malformed.")
        entries = []
        for entry in tree_body["tree"]:
            try:
                entry_type = entry["type"]
                mode = entry.get("mode")
                kind = (
                    "directory"
                    if entry_type == "tree"
                    else "submodule"
                    if entry_type == "commit"
                    else "symlink"
                    if mode == "120000"
                    else "file"
                )
                child_path = "/".join(part for part in (clean_path, entry["path"]) if part)
                entries.append(
                    {
                        "name": entry["path"],
                        "path": child_path,
                        "kind": kind,
                        "sha": entry["sha"],
                        "size": entry.get("size"),
                    }
                )
            except (KeyError, TypeError) as exc:
                raise ProviderUnavailableError("GitHub tree entry was malformed.") from exc
        return {
            "sha": tree_sha,
            "ref": ref,
            "path": clean_path,
            "entries": entries,
            "commit": commit,
        }
