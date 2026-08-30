"""GitHub App user authorization behind HubGit's provider-neutral auth boundary."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, urlencode, urlsplit

import httpx
from cryptography.fernet import Fernet, InvalidToken

from .config import Settings
from .security import ProblemError


class GitHubAuthError(Exception):
    """A provider failure whose details must stay out of public responses."""


class AccessPolicyUnavailable(GitHubAuthError):
    """Membership could not be verified, so the access policy must fail closed."""


@dataclass(frozen=True)
class GitHubCredentials:
    access_token: str
    expires_at: datetime | None
    refresh_token: str | None
    refresh_expires_at: datetime | None


@dataclass(frozen=True)
class GitHubIdentity:
    user_id: int
    login: str
    display_name: str
    email: str | None
    avatar_url: str


class GitHubAuthPort(Protocol):
    def authorization_url(self, state: str) -> str: ...

    async def exchange_code(self, code: str) -> GitHubCredentials: ...

    async def identity(self, access_token: str) -> GitHubIdentity: ...

    async def organization_membership(self, access_token: str, organization: str) -> bool: ...

    async def team_membership(
        self, access_token: str, organization: str, team_slug: str, login: str
    ) -> bool: ...


class CredentialCipher:
    """Encrypt provider credentials at rest with an operator-managed key."""

    def __init__(self, key_file: Path) -> None:
        try:
            key = key_file.read_bytes().strip()
            self._fernet = Fernet(key)
        except (OSError, ValueError) as exc:
            raise GitHubAuthError("Credential encryption key is unavailable or invalid.") from exc

    def encrypt(self, credentials: GitHubCredentials) -> str:
        body = json.dumps(
            {
                "accessToken": credentials.access_token,
                "refreshToken": credentials.refresh_token,
            },
            separators=(",", ":"),
        ).encode()
        return self._fernet.encrypt(body).decode()

    def decrypt(self, value: str) -> dict[str, str | None]:
        try:
            body = self._fernet.decrypt(value.encode())
            result = json.loads(body)
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GitHubAuthError("Stored provider credentials cannot be decrypted.") from exc
        if not isinstance(result, dict) or not isinstance(result.get("accessToken"), str):
            raise GitHubAuthError("Stored provider credentials are malformed.")
        return {"accessToken": result["accessToken"], "refreshToken": result.get("refreshToken")}


def _future(seconds: object) -> datetime | None:
    if not isinstance(seconds, int) or seconds <= 0:
        return None
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def safe_return_path(value: str | None) -> str:
    """Accept only an application-local absolute path after authorization."""
    if not value:
        return "/dashboard"
    parsed = urlsplit(value)
    if (
        len(value) > 500
        or not value.startswith("/")
        or value.startswith("//")
        or parsed.scheme
        or parsed.netloc
        or "\\" in value
    ):
        raise ProblemError(422, "Invalid redirect", "auth.redirect_invalid")
    return value


class GitHubAuthClient:
    """Small GitHub-specific OAuth and access-policy adapter."""

    def __init__(self, config: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not config.github_configured:
            raise GitHubAuthError("GitHub authorization is not configured.")
        try:
            client_secret = config.github_client_secret_file.read_text().strip()  # type: ignore[union-attr]
        except OSError as exc:
            raise GitHubAuthError("GitHub client secret is unavailable.") from exc
        if not client_secret:
            raise GitHubAuthError("GitHub client secret is empty.")
        self.client_id = config.github_client_id or ""
        self.client_secret = client_secret
        self.redirect_uri = config.github_redirect_uri
        self.web_base_url = config.github_web_base_url.rstrip("/")
        self.api_base_url = config.github_api_base_url.rstrip("/")
        self._transport = transport

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "HubGit/0.1",
        }

    def authorization_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "state": state,
            }
        )
        return f"{self.web_base_url}/login/oauth/authorize?{query}"

    async def exchange_code(self, code: str) -> GitHubCredentials:
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=15.0) as client:
                response = await client.post(
                    f"{self.web_base_url}/login/oauth/access_token",
                    headers={"Accept": "application/json", "User-Agent": "HubGit/0.1"},
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                    },
                )
        except httpx.HTTPError as exc:
            raise GitHubAuthError("GitHub token exchange was unavailable.") from exc
        try:
            body = response.json()
        except ValueError as exc:
            raise GitHubAuthError("GitHub returned an invalid token response.") from exc
        token = body.get("access_token") if isinstance(body, dict) else None
        if response.status_code != 200 or not isinstance(token, str) or not token:
            raise GitHubAuthError("GitHub rejected the authorization code.")
        return GitHubCredentials(
            access_token=token,
            expires_at=_future(body.get("expires_in")),
            refresh_token=body.get("refresh_token") if isinstance(body.get("refresh_token"), str) else None,
            refresh_expires_at=_future(body.get("refresh_token_expires_in")),
        )

    async def _get(self, path: str, access_token: str) -> httpx.Response:
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=15.0) as client:
                return await client.get(
                    f"{self.api_base_url}{path}",
                    headers={**self._headers, "Authorization": f"Bearer {access_token}"},
                )
        except httpx.HTTPError as exc:
            raise GitHubAuthError("GitHub API was unavailable.") from exc

    async def identity(self, access_token: str) -> GitHubIdentity:
        response = await self._get("/user", access_token)
        if response.status_code != 200:
            raise GitHubAuthError("GitHub identity lookup failed.")
        try:
            body = response.json()
            user_id = body["id"]
            login = body["login"]
        except (ValueError, KeyError, TypeError) as exc:
            raise GitHubAuthError("GitHub returned an invalid identity response.") from exc
        if not isinstance(user_id, int) or not isinstance(login, str):
            raise GitHubAuthError("GitHub returned an invalid identity response.")
        return GitHubIdentity(
            user_id=user_id,
            login=login,
            display_name=body.get("name") if isinstance(body.get("name"), str) else login,
            email=body.get("email") if isinstance(body.get("email"), str) else None,
            avatar_url=body.get("avatar_url") if isinstance(body.get("avatar_url"), str) else "",
        )

    async def organization_membership(self, access_token: str, organization: str) -> bool:
        response = await self._get(
            f"/user/memberships/orgs/{quote(organization, safe='')}", access_token
        )
        if response.status_code == 404:
            return False
        if response.status_code != 200:
            raise AccessPolicyUnavailable("Organization membership could not be verified.")
        try:
            return response.json().get("state") == "active"
        except ValueError as exc:
            raise AccessPolicyUnavailable("Organization membership response was invalid.") from exc

    async def team_membership(
        self, access_token: str, organization: str, team_slug: str, login: str
    ) -> bool:
        response = await self._get(
            "/orgs/"
            f"{quote(organization, safe='')}/teams/{quote(team_slug, safe='')}"
            f"/memberships/{quote(login, safe='')}",
            access_token,
        )
        if response.status_code == 404:
            return False
        if response.status_code != 200:
            raise AccessPolicyUnavailable("Team membership could not be verified.")
        try:
            return response.json().get("state") == "active"
        except ValueError as exc:
            raise AccessPolicyUnavailable("Team membership response was invalid.") from exc


async def evaluate_access_policy(
    client: GitHubAuthPort,
    credentials: GitHubCredentials,
    identity: GitHubIdentity,
    policy: dict[str, object],
) -> bool:
    """Evaluate every configured rule and fail closed when verification fails."""
    results: list[bool] = []
    if policy["allowAnyAuthorizedUser"]:
        results.append(True)

    user_ids = policy["userIds"]
    if user_ids:
        results.append(identity.user_id in user_ids)  # type: ignore[operator]

    for organization in policy["organizations"]:  # type: ignore[union-attr]
        results.append(await client.organization_membership(credentials.access_token, organization))

    for team in policy["teams"]:  # type: ignore[union-attr]
        organization, team_slug = team.split("/", 1)
        results.append(
            await client.team_membership(
                credentials.access_token, organization, team_slug, identity.login
            )
        )

    if not results:
        return False
    return all(results) if policy["mode"] == "all" else any(results)


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)
