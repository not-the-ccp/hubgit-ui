from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from hubgit_api.config import Settings
from hubgit_api.github_auth import (
    AccessPolicyUnavailable,
    GitHubCredentials,
    GitHubAuthClient,
    GitHubIdentity,
)
from hubgit_api.main import create_app


OPENAPI = json.loads(
    (Path(__file__).parents[3] / "packages/contracts/openapi.json").read_text()
)
REGISTRY = Registry().with_resource(
    "urn:hubgit:openapi",
    Resource.from_contents(OPENAPI, default_specification=DRAFT202012),
)


def validate_contract(schema_name: str, payload: object) -> None:
    Draft202012Validator(
        {"$ref": f"urn:hubgit:openapi#/components/schemas/{schema_name}"},
        registry=REGISTRY,
    ).validate(payload)


@dataclass
class FakeGitHubAuth:
    organizations: dict[str, bool] | None = None
    teams: dict[str, bool] | None = None
    membership_unavailable: bool = False
    expired_credentials: bool = False
    refresh_calls: int = 0

    def authorization_url(self, state: str) -> str:
        return f"https://github.test/login/oauth/authorize?client_id=test-client&state={state}"

    async def exchange_code(self, code: str) -> GitHubCredentials:
        if code != "valid-code":
            raise AssertionError("unexpected authorization code")
        return GitHubCredentials(
            access_token="ghu_private-access-token",
            expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1))
            if self.expired_credentials
            else None,
            refresh_token="ghr_private-refresh-token",
            refresh_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

    async def refresh_credentials(self, refresh_token: str) -> GitHubCredentials:
        assert refresh_token == "ghr_private-refresh-token"
        self.refresh_calls += 1
        return GitHubCredentials(
            access_token="ghu_rotated-access-token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
            refresh_token="ghr_rotated-refresh-token",
            refresh_expires_at=datetime.now(timezone.utc) + timedelta(days=180),
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


def test_github_repository_reads_are_canonical_and_require_provider_session(tmp_path):
    repository = {
        "id": 99,
        "owner": {
            "id": 42,
            "login": "trusted-org",
            "type": "Organization",
            "avatar_url": "https://avatars.example.test/org",
        },
        "name": "private-repo",
        "full_name": "trusted-org/private-repo",
        "description": "Private provider data",
        "visibility": "private",
        "default_branch": "main",
        "size": 12,
        "archived": False,
        "fork": False,
        "parent": None,
        "language": "Python",
        "license": {"spdx_id": "MIT"},
        "topics": ["hubgit"],
        "permissions": {"pull": True, "triage": True, "push": True, "maintain": True, "admin": False},
        "stargazers_count": 5,
        "forks_count": 2,
        "subscribers_count": 3,
        "open_issues_count": 4,
        "clone_url": "https://github.test/trusted-org/private-repo.git",
        "ssh_url": "git@github.test:trusted-org/private-repo.git",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-08-30T12:00:00Z",
        "pushed_at": "2026-08-30T11:00:00Z",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer ghu_private-access-token"
        path = request.url.path
        if path == "/user/repos":
            return httpx.Response(200, json=[repository])
        if path == "/repos/trusted-org/private-repo":
            return httpx.Response(200, json=repository)
        if path == "/repos/trusted-org/private-repo/commits/main":
            return httpx.Response(
                200,
                json={
                    "sha": "a" * 40,
                    "commit": {
                        "message": "Provider commit",
                        "author": {
                            "name": "Octo User",
                            "email": "octo@example.test",
                            "date": "2026-08-30T11:00:00Z",
                        },
                        "tree": {"sha": "root-tree"},
                    },
                },
            )
        if path == "/repos/trusted-org/private-repo/git/trees/root-tree":
            return httpx.Response(
                200,
                json={
                    "sha": "root-tree",
                    "tree": [
                        {"path": "README.md", "mode": "100644", "type": "blob", "sha": "readme", "size": 20},
                        {"path": "src", "mode": "040000", "type": "tree", "sha": "src-tree"},
                    ],
                },
            )
        if path == "/repos/trusted-org/private-repo/git/trees/src-tree":
            return httpx.Response(
                200,
                json={
                    "sha": "src-tree",
                    "tree": [
                        {"path": "main.py", "mode": "100755", "type": "blob", "sha": "main", "size": 30}
                    ],
                },
            )
        return httpx.Response(404)

    config = github_settings(tmp_path)
    transport = httpx.MockTransport(handler)
    with TestClient(
        create_app(config, github_auth=FakeGitHubAuth(), github_transport=transport)
    ) as client:
        anonymous = client.get("/api/v1/repositories")
        assert anonymous.status_code == 401
        assert anonymous.json()["code"] == "provider.authorization_required"

        state = begin(client)
        client.get(
            "/api/v1/auth/providers/github/callback",
            params={"code": "valid-code", "state": state},
            follow_redirects=False,
        )
        listing = client.get("/api/v1/repositories").json()
        assert listing["totalCount"] == 1
        assert listing["items"][0]["id"] == "github-repository-99"
        assert listing["items"][0]["owner"]["kind"] == "organization"
        assert listing["items"][0]["freshness"]["provider"] == "github"
        validate_contract("Repository", listing["items"][0])
        capabilities = client.get("/api/v1/capabilities").json()
        assert capabilities["features"]["issues"] is False
        unsupported = client.get(
            "/api/v1/repositories/trusted-org/private-repo/issues"
        )
        assert unsupported.status_code == 501
        assert unsupported.json()["code"] == "capability.unsupported"

        detail = client.get("/api/v1/repositories/trusted-org/private-repo").json()
        assert detail["permissions"]["write"] is True
        assert "access_token" not in str(detail)

        root = client.get(
            "/api/v1/repositories/trusted-org/private-repo/tree/main"
        ).json()
        assert [item["kind"] for item in root["entries"]] == ["file", "directory"]
        assert root["commit"]["message"] == "Provider commit"
        validate_contract("GitTree", root)
        child = client.get(
            "/api/v1/repositories/trusted-org/private-repo/tree/main",
            params={"path": "src"},
        ).json()
        assert child["sha"] == "src-tree"
        assert child["entries"][0]["path"] == "src/main.py"


def test_expired_github_credentials_rotate_before_repository_reads(tmp_path):
    provider_auth = FakeGitHubAuth(expired_credentials=True)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/user/repos"
        assert request.headers["Authorization"] == "Bearer ghu_rotated-access-token"
        return httpx.Response(200, json=[])

    config = github_settings(tmp_path)
    with TestClient(
        create_app(
            config,
            github_auth=provider_auth,
            github_transport=httpx.MockTransport(handler),
        )
    ) as client:
        state = begin(client)
        client.get(
            "/api/v1/auth/providers/github/callback",
            params={"code": "valid-code", "state": state},
            follow_redirects=False,
        )
        assert client.get("/api/v1/repositories").status_code == 200
        assert provider_auth.refresh_calls == 1

    database_bytes = (tmp_path / "github.db").read_bytes()
    assert b"ghu_rotated-access-token" not in database_bytes
    assert b"ghr_rotated-refresh-token" not in database_bytes


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
