from fastapi.testclient import TestClient

from hubgit_api.config import Settings
from hubgit_api.main import create_app


def client(tmp_path):
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path}/collaboration.db",
        cookie_secure=False,
    )
    return TestClient(create_app(settings))


def login(test_client: TestClient) -> dict[str, str]:
    response = test_client.post(
        "/api/v1/auth/login",
        json={"login": "demo", "password": "demo-password"},
    )
    assert response.status_code == 200
    return {
        "Origin": "http://localhost:3000",
        "X-CSRF-Token": response.json()["csrfToken"],
    }


def test_seeded_issue_and_pull_are_public_but_private_repo_is_concealed(tmp_path):
    with client(tmp_path) as test_client:
        issues = test_client.get("/api/v1/repositories/demo/hubgit-demo/issues")
        assert issues.status_code == 200
        assert issues.json()["items"][0]["kind"] == "issue"
        assert issues.json()["items"][0]["permissions"]["write"] is False

        pulls = test_client.get("/api/v1/repositories/demo/hubgit-demo/pulls")
        assert pulls.status_code == 200
        assert pulls.json()["items"][0]["kind"] == "pullRequest"

        hidden = test_client.get("/api/v1/repositories/demo/private-notes/issues")
        assert hidden.status_code == 404
        assert hidden.json()["code"] == "repository.not_found"


def test_issue_mutations_are_idempotent_and_etag_protected(tmp_path):
    with client(tmp_path) as test_client:
        security_headers = login(test_client)
        create_headers = {**security_headers, "Idempotency-Key": "issue-create-001"}
        created = test_client.post(
            "/api/v1/repositories/demo/hubgit-demo/issues",
            headers=create_headers,
            json={"title": "Exercise the stateful mock", "body": "First body"},
        )
        assert created.status_code == 201
        number = created.json()["number"]
        assert created.json()["permissions"]["write"] is True

        replay = test_client.post(
            "/api/v1/repositories/demo/hubgit-demo/issues",
            headers=create_headers,
            json={"title": "Exercise the stateful mock", "body": "First body"},
        )
        assert replay.status_code == 201
        assert replay.json()["id"] == created.json()["id"]

        mismatch = test_client.post(
            "/api/v1/repositories/demo/hubgit-demo/issues",
            headers=create_headers,
            json={"title": "A different payload"},
        )
        assert mismatch.status_code == 409
        assert mismatch.json()["code"] == "idempotency.payload_mismatch"

        detail = test_client.get(
            f"/api/v1/repositories/demo/hubgit-demo/issues/{number}"
        )
        etag = detail.headers["etag"]
        stale = test_client.patch(
            f"/api/v1/repositories/demo/hubgit-demo/issues/{number}",
            headers={**security_headers, "If-Match": '"stale"'},
            json={"state": "closed", "stateReason": "completed"},
        )
        assert stale.status_code == 412

        updated = test_client.patch(
            f"/api/v1/repositories/demo/hubgit-demo/issues/{number}",
            headers={**security_headers, "If-Match": etag},
            json={"state": "closed", "stateReason": "completed"},
        )
        assert updated.status_code == 200
        assert updated.json()["state"] == "closed"
        assert updated.headers["etag"] != etag


def test_comments_and_expected_head_merge_are_durable(tmp_path):
    with client(tmp_path) as test_client:
        security_headers = login(test_client)
        comment = test_client.post(
            "/api/v1/repositories/demo/hubgit-demo/issues/1/comments",
            headers={**security_headers, "Idempotency-Key": "comment-create-001"},
            json={"body": "A persisted mock comment."},
        )
        assert comment.status_code == 201
        assert comment.json()["body"] == "A persisted mock comment."
        assert (
            test_client.get(
                "/api/v1/repositories/demo/hubgit-demo/issues/1"
            ).json()["commentCount"]
            == 2
        )

        pull = test_client.get(
            "/api/v1/repositories/demo/hubgit-demo/pulls/2"
        ).json()
        wrong_head = test_client.post(
            "/api/v1/repositories/demo/hubgit-demo/pulls/2/merge",
            headers={**security_headers, "Idempotency-Key": "merge-wrong-001"},
            json={"method": "squash", "expectedHeadSha": "0000000"},
        )
        assert wrong_head.status_code == 409
        assert wrong_head.json()["code"] == "pull.expected_head_mismatch"

        headers = {**security_headers, "Idempotency-Key": "merge-success-001"}
        merged = test_client.post(
            "/api/v1/repositories/demo/hubgit-demo/pulls/2/merge",
            headers=headers,
            json={"method": "squash", "expectedHeadSha": pull["head"]["sha"]},
        )
        assert merged.status_code == 200
        assert merged.json()["merged"] is True
        assert len(merged.json()["sha"]) == 40

        replay = test_client.post(
            "/api/v1/repositories/demo/hubgit-demo/pulls/2/merge",
            headers=headers,
            json={"method": "squash", "expectedHeadSha": pull["head"]["sha"]},
        )
        assert replay.status_code == 200
        assert replay.json() == merged.json()


def test_dashboard_notifications_and_search_respect_session_state(tmp_path):
    with client(tmp_path) as test_client:
        assert test_client.get("/api/v1/dashboard").status_code == 401
        assert test_client.get("/api/v1/notifications").status_code == 401

        security_headers = login(test_client)
        dashboard = test_client.get("/api/v1/dashboard")
        assert dashboard.status_code == 200
        assert dashboard.json()["repositories"]["totalCount"] == 4

        unread = test_client.get(
            "/api/v1/notifications", params={"unread": True}
        ).json()
        assert unread["totalCount"] == 1
        notification_id = unread["items"][0]["id"]
        updated = test_client.patch(
            "/api/v1/notifications",
            headers=security_headers,
            json={"ids": [notification_id]},
        )
        assert updated.status_code == 204
        assert (
            test_client.get(
                "/api/v1/notifications", params={"unread": True}
            ).json()["totalCount"]
            == 0
        )

        search = test_client.get(
            "/api/v1/search", params={"q": "repository", "type": "repositories"}
        )
        assert search.status_code == 200
        assert all(item["kind"] == "repository" for item in search.json()["items"])
        assert test_client.get("/api/v1/search", params={"q": ""}).status_code == 422
