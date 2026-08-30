from fastapi.testclient import TestClient
from pydantic import ValidationError

from hubgit_api.config import Settings
from hubgit_api.main import create_app


def client(tmp_path):
    settings = Settings(database_url=f"sqlite+aiosqlite:///{tmp_path}/test.db", cookie_secure=False)
    return TestClient(create_app(settings))


def test_health_meta_and_capabilities(tmp_path):
    with client(tmp_path) as test_client:
        assert test_client.get("/healthz").json() == {"status": "ok"}
        assert test_client.get("/api/v1/meta").json()["branding"] == "hubgit"
        response = test_client.get("/api/v1/capabilities")
        assert response.json()["provider"] == "mock"
        assert response.json()["features"]["issues"] is False
        cors = test_client.options("/api/v1/auth/session", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "DELETE"})
        assert cors.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_session_login_viewer_and_logout(tmp_path):
    with client(tmp_path) as test_client:
        anonymous = test_client.get("/api/v1/auth/session")
        assert anonymous.json()["authenticated"] is False
        denied = test_client.get("/api/v1/viewer")
        assert denied.status_code == 401
        assert denied.headers["content-type"].startswith("application/problem+json")

        login = test_client.post("/api/v1/auth/login", json={"login": "demo", "password": "demo-password"})
        assert login.status_code == 200
        csrf = login.json()["csrfToken"]
        assert test_client.get("/api/v1/viewer").json()["username"] == "demo"
        rejected = test_client.delete("/api/v1/auth/session", headers={"Origin": "http://localhost:3000"})
        assert rejected.status_code == 403
        assert rejected.json()["code"] == "auth.csrf_invalid"
        assert rejected.headers["content-type"].startswith("application/problem+json")
        assert test_client.delete("/api/v1/auth/session", headers={"X-CSRF-Token": csrf, "Origin": "http://localhost:3000"}).status_code == 204
        assert test_client.get("/api/v1/auth/session").json()["authenticated"] is False


def test_problem_validation_and_repository_reads(tmp_path):
    with client(tmp_path) as test_client:
        invalid = test_client.post("/api/v1/auth/login", json={"login": "", "password": ""})
        assert invalid.status_code == 422
        assert invalid.headers["content-type"].startswith("application/problem+json")
        listing = test_client.get("/api/v1/repositories", params={"limit": 1})
        assert listing.status_code == 200
        assert listing.json()["totalCount"] == 2
        repo = test_client.get("/api/v1/repositories/demo/hubgit-demo")
        assert repo.json()["cloneUrls"]["http"].startswith("https://")
        tree = test_client.get("/api/v1/repositories/demo/hubgit-demo/tree/main", params={"path": "src"})
        assert tree.json()["entries"][0]["path"] == "src/main.py"
        missing = test_client.get("/api/v1/repositories/demo/nope")
        assert missing.status_code == 404
        assert missing.json()["code"] == "repository.not_found"


def test_cookie_authentication_rejects_cross_origin_mutations(tmp_path):
    with client(tmp_path) as test_client:
        login = test_client.post("/api/v1/auth/login", json={"login": "demo", "password": "demo-password"})
        csrf = login.json()["csrfToken"]

        cross_origin = test_client.delete(
            "/api/v1/auth/session",
            headers={"X-CSRF-Token": csrf, "Origin": "https://attacker.example"},
        )
        assert cross_origin.status_code == 403
        assert cross_origin.json()["code"] == "auth.origin_invalid"

        absent_provenance = test_client.delete("/api/v1/auth/session", headers={"X-CSRF-Token": csrf})
        assert absent_provenance.status_code == 403
        assert absent_provenance.json()["code"] == "auth.origin_invalid"

        referer_fallback = test_client.delete(
            "/api/v1/auth/session",
            headers={"X-CSRF-Token": csrf, "Referer": "http://localhost:3000/settings"},
        )
        assert referer_fallback.status_code == 204


def test_login_failure_rotation_and_logout_revocation(tmp_path):
    with client(tmp_path) as test_client:
        failed = test_client.post("/api/v1/auth/login", json={"login": "demo", "password": "incorrect"})
        assert failed.status_code == 401
        assert failed.json()["code"] == "auth.invalid_credentials"
        assert "incorrect" not in failed.text

        first = test_client.post("/api/v1/auth/login", json={"login": "demo", "password": "demo-password"})
        original_cookie = test_client.cookies.get("hubgit_session")
        second = test_client.post("/api/v1/auth/login", json={"login": "demo", "password": "demo-password"})
        assert second.status_code == 200
        replacement_cookie = test_client.cookies.get("hubgit_session")
        assert replacement_cookie != original_cookie

        rotated = test_client.get("/api/v1/viewer", headers={"Cookie": f"hubgit_session={original_cookie}"})
        assert rotated.status_code == 401

        csrf = second.json()["csrfToken"]
        assert test_client.delete("/api/v1/auth/session", headers={"X-CSRF-Token": csrf, "Origin": "http://localhost:3000"}).status_code == 204
        revoked = test_client.get("/api/v1/viewer", headers={"Cookie": f"hubgit_session={replacement_cookie}"})
        assert revoked.status_code == 401


def test_private_repository_is_concealed_and_authenticated_owner_can_read(tmp_path):
    with client(tmp_path) as test_client:
        anonymous_listing = test_client.get("/api/v1/repositories").json()
        assert all(item["fullName"] != "demo/private-notes" for item in anonymous_listing["items"])

        repository = test_client.get("/api/v1/repositories/demo/private-notes")
        tree = test_client.get("/api/v1/repositories/demo/private-notes/tree/main")
        assert repository.status_code == tree.status_code == 404
        assert repository.json()["code"] == tree.json()["code"] == "repository.not_found"
        assert repository.json()["detail"] == tree.json()["detail"]

        test_client.post("/api/v1/auth/login", json={"login": "demo", "password": "demo-password"})
        assert test_client.get("/api/v1/repositories/demo/private-notes").status_code == 200


def test_pagination_and_request_size_are_bounded(tmp_path):
    with client(tmp_path) as test_client:
        malformed = test_client.get("/api/v1/repositories", params={"cursor": "not-a-cursor"})
        assert malformed.status_code == 400
        assert malformed.json()["code"] == "pagination.invalid_cursor"
        assert test_client.get("/api/v1/repositories", params={"limit": 0}).status_code == 422
        assert test_client.get("/api/v1/repositories", params={"limit": 101}).status_code == 422

        oversized = test_client.post("/api/v1/auth/login", content=b"x" * 1_048_577, headers={"Content-Type": "application/json"})
        assert oversized.status_code == 413
        assert oversized.json()["code"] == "request.payload_too_large"


def test_cookie_attributes_and_production_configuration_validation(tmp_path):
    settings = Settings(database_url=f"sqlite+aiosqlite:///{tmp_path}/test.db", cookie_secure=True, cookie_samesite="strict")
    with TestClient(create_app(settings)) as test_client:
        response = test_client.post("/api/v1/auth/login", json={"login": "demo", "password": "demo-password"})
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie
        assert "secure" in cookie
        assert "samesite=strict" in cookie
        assert "path=/" in cookie

    for invalid in (
        {"cookie_samesite": "none", "cookie_secure": False},
        {"environment": "production", "cookie_secure": False},
        {"environment": "production", "cookie_secure": True, "public_base_url": "http://api.example.test", "cors_origins": "http://app.example.test", "seed_mock_user": False},
    ):
        try:
            Settings(**invalid)
        except ValidationError:
            pass
        else:
            raise AssertionError("unsafe configuration was accepted")


def test_unexpected_errors_do_not_disclose_provider_secrets(tmp_path):
    class BrokenProvider:
        provider_name = "broken"

        async def list_repositories(self, *, query, viewer):
            raise RuntimeError("postgres://admin:very-secret-password@db.example.test/hubgit")

        async def get_repository(self, owner, repo, *, viewer):
            raise AssertionError

        async def get_tree(self, owner, repo, ref, path, *, viewer):
            raise AssertionError

    settings = Settings(database_url=f"sqlite+aiosqlite:///{tmp_path}/test.db", cookie_secure=False)
    with TestClient(create_app(settings, BrokenProvider()), raise_server_exceptions=False) as test_client:
        response = test_client.get("/api/v1/repositories")
        assert response.status_code == 500
        assert response.json()["code"] == "server.internal_error"
        assert "very-secret-password" not in response.text
        assert "postgres://" not in response.text
