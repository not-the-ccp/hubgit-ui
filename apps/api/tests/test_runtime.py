from fastapi.testclient import TestClient

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
        rejected = test_client.delete("/api/v1/auth/session")
        assert rejected.status_code == 403
        assert rejected.headers["content-type"].startswith("application/problem+json")
        assert test_client.delete("/api/v1/auth/session", headers={"X-CSRF-Token": csrf}).status_code == 204
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
