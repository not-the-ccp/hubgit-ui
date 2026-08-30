from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from hubgit_api.config import Settings
from hubgit_api.github_auth import (
    AccessPolicyUnavailable,
    GitHubCredentials,
    GitHubAuthClient,
    GitHubIdentity,
)
from hubgit_api.main import create_app


@dataclass
class FakeGitHubAuth:
    organizations: dict[str, bool] | None = None
    teams: dict[str, bool] | None = None
    membership_unavailable: bool = False

    def authorization_url(self, state: str) -> str:
        return f"https://github.test/login/oauth/authorize?client_id=test-client&state={state}"

    async def exchange_code(self, code: str) -> GitHubCredentials:
        if code != "valid-code":
            raise AssertionError("unexpected authorization code")
        return GitHubCredentials(
            access_token="ghu_private-access-token",
            expires_at=None,
            refresh_token="ghr_private-refresh-token",
            refresh_expires_at=None,
        )

    async def identity(self, access_token: str) -> GitHubIdentity:
        assert access_token == "ghu_private-access-token"
        return GitHubIdentity(
            user_id=4242,
            login="octo-user",
            display_name="Octo User",
            email="octo@example.test",
            avatar_url="https://avatars.example.test/4242",
        )

    async def organization_membership(self, access_token: str, organization: str) -> bool:
        if self.membership_unavailable:
            raise AccessPolicyUnavailable("upstream diagnostic containing a secret")
        return (self.organizations or {}).get(organization, False)

    async def team_membership(
        self, access_token: str, organization: str, team_slug: str, login: str
    ) -> bool:
        if self.membership_unavailable:
            raise AccessPolicyUnavailable("upstream diagnostic containing a secret")
        return (self.teams or {}).get(f"{organization}/{team_slug}", False)


def github_settings(tmp_path, **overrides) -> Settings:
    secret_file = tmp_path / "github-client-secret"
    secret_file.write_text("client-secret")
    key_file = tmp_path / "credential-key"
    key_file.write_bytes(Fernet.generate_key())
    values = {
        "database_url": f"sqlite+aiosqlite:///{tmp_path}/github.db",
        "provider": "github",
        "seed_mock_user": False,
        "github_client_id": "test-client",
        "github_client_secret_file": secret_file,
        "github_credential_key_file": key_file,
        "github_web_base_url": "https://github.test",
        "github_api_base_url": "https://api.github.test",
    }
    values.update(overrides)
    return Settings(**values)


def begin(client: TestClient, return_to: str = "/dashboard") -> str:
    response = client.get(
        "/api/v1/auth/providers/github/start",
        params={"redirectUri": return_to},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["cache-control"] == "no-store"
    return parse_qs(urlsplit(response.headers["location"]).query)["state"][0]


def test_github_authorization_creates_session_and_keeps_tokens_server_side(tmp_path):
    config = github_settings(tmp_path)
    with TestClient(create_app(config, github_auth=FakeGitHubAuth())) as client:
        methods = client.get("/api/v1/auth/methods").json()
        assert methods["password"] is False
        assert methods["providers"][0]["enabled"] is True
        assert client.post(
            "/api/v1/auth/login", json={"login": "octo-user", "password": "anything"}
        ).status_code == 404

        state = begin(client, "/private?tab=code")
        completed = client.get(
            "/api/v1/auth/providers/github/callback",
            params={"code": "valid-code", "state": state},
            follow_redirects=False,
        )
        assert completed.status_code == 302
        assert completed.headers["location"] == "/private?tab=code"
        assert "httponly" in completed.headers["set-cookie"].lower()
        assert completed.headers["cache-control"] == "no-store"
        assert client.get("/api/v1/viewer").json()["username"] == "octo-user"

        replay = client.get(
            "/api/v1/auth/providers/github/callback",
            params={"code": "valid-code", "state": state},
        )
        assert replay.status_code == 400
        assert replay.json()["code"] == "auth.state_invalid"

    database_bytes = (tmp_path / "github.db").read_bytes()
    assert b"ghu_private-access-token" not in database_bytes
    assert b"ghr_private-refresh-token" not in database_bytes


def test_github_redirects_are_local_and_state_is_required(tmp_path):
    config = github_settings(tmp_path)
    with TestClient(create_app(config, github_auth=FakeGitHubAuth())) as client:
        rejected = client.get(
            "/api/v1/auth/providers/github/start",
            params={"redirectUri": "https://attacker.example/steal"},
            follow_redirects=False,
        )
        assert rejected.status_code == 422
        assert rejected.json()["code"] == "auth.redirect_invalid"

        missing = client.get(
            "/api/v1/auth/providers/github/callback",
            params={"code": "valid-code"},
        )
        assert missing.status_code == 400
        assert missing.json()["code"] == "auth.provider_response_invalid"

        cancelled = client.get(
            "/api/v1/auth/providers/github/callback",
            params={"error": "access_denied", "error_description": "private detail"},
        )
        assert cancelled.status_code == 400
        assert cancelled.json()["code"] == "auth.provider_cancelled"
        assert "private detail" not in cancelled.text


def test_github_access_policy_uses_immutable_ids_and_fails_closed(tmp_path):
    denied_config = github_settings(
        tmp_path,
        github_allow_any_authorized_user=False,
        github_allowed_user_ids="7,8",
    )
    with TestClient(create_app(denied_config, github_auth=FakeGitHubAuth())) as client:
        state = begin(client)
        denied = client.get(
            "/api/v1/auth/providers/github/callback",
            params={"code": "valid-code", "state": state},
        )
        assert denied.status_code == 403
        assert denied.json()["code"] == "auth.access_policy_denied"

    unavailable_config = github_settings(
        tmp_path,
        database_url=f"sqlite+aiosqlite:///{tmp_path}/unavailable.db",
        github_allow_any_authorized_user=False,
        github_required_organizations="trusted-org",
    )
    provider = FakeGitHubAuth(membership_unavailable=True)
    with TestClient(create_app(unavailable_config, github_auth=provider)) as client:
        state = begin(client)
        unavailable = client.get(
            "/api/v1/auth/providers/github/callback",
            params={"code": "valid-code", "state": state},
        )
        assert unavailable.status_code == 503
        assert unavailable.json()["code"] == "auth.access_policy_unverifiable"
        assert "upstream diagnostic" not in unavailable.text


def test_github_all_policy_requires_every_configured_rule(tmp_path):
    config = github_settings(
        tmp_path,
        github_access_policy_mode="all",
        github_allow_any_authorized_user=False,
        github_allowed_user_ids="4242",
        github_required_organizations="trusted-org",
        github_required_teams="trusted-org/core",
    )
    provider = FakeGitHubAuth(
        organizations={"trusted-org": True}, teams={"trusted-org/core": True}
    )
    with TestClient(create_app(config, github_auth=provider)) as client:
        state = begin(client)
        response = client.get(
            "/api/v1/auth/providers/github/callback",
            params={"code": "valid-code", "state": state},
            follow_redirects=False,
        )
        assert response.status_code == 302


@pytest.mark.asyncio
async def test_github_http_adapter_uses_documented_endpoints_and_bearer_auth(tmp_path):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/login/oauth/access_token":
            assert b"client_secret=client-secret" in request.content
            return httpx.Response(
                200,
                json={
                    "access_token": "server-token",
                    "expires_in": 28_800,
                    "refresh_token": "refresh-token",
                    "refresh_token_expires_in": 15_552_000,
                },
            )
        assert request.headers["Authorization"] == "Bearer server-token"
        assert request.headers["X-GitHub-Api-Version"] == "2026-03-10"
        if request.url.path == "/user":
            return httpx.Response(
                200,
                json={
                    "id": 4242,
                    "login": "octo-user",
                    "name": "Octo User",
                    "email": None,
                    "avatar_url": "https://avatars.example.test/4242",
                },
            )
        if request.url.path == "/user/memberships/orgs/trusted-org":
            return httpx.Response(200, json={"state": "active"})
        if request.url.path == "/orgs/trusted-org/teams/core/memberships/octo-user":
            return httpx.Response(200, json={"state": "active", "role": "member"})
        return httpx.Response(404)

    config = github_settings(tmp_path)
    adapter = GitHubAuthClient(config, transport=httpx.MockTransport(handler))
    authorization = urlsplit(adapter.authorization_url("opaque-state"))
    assert authorization.path == "/login/oauth/authorize"
    assert parse_qs(authorization.query)["state"] == ["opaque-state"]

    credentials = await adapter.exchange_code("authorization-code")
    identity = await adapter.identity(credentials.access_token)
    assert identity.user_id == 4242
    assert identity.email is None
    assert await adapter.organization_membership(credentials.access_token, "trusted-org")
    assert await adapter.team_membership(
        credentials.access_token, "trusted-org", "core", identity.login
    )
    assert [request.url.path for request in requests] == [
        "/login/oauth/access_token",
        "/user",
        "/user/memberships/orgs/trusted-org",
        "/orgs/trusted-org/teams/core/memberships/octo-user",
    ]
