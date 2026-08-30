import json
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from hubgit_api.config import Settings
from hubgit_api.main import create_app


OPENAPI = json.loads(
    (Path(__file__).parents[3] / "packages/contracts/openapi.json").read_text()
)
REGISTRY = Registry().with_resource(
    "urn:hubgit:openapi",
    Resource.from_contents(OPENAPI, default_specification=DRAFT202012),
)


def validate(schema_name: str, payload: object) -> None:
    validator = Draft202012Validator(
        {"$ref": f"urn:hubgit:openapi#/components/schemas/{schema_name}"},
        registry=REGISTRY,
    )
    validator.validate(payload)


def test_collaboration_responses_match_the_public_contract(tmp_path):
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path}/conformance.db",
        cookie_secure=False,
    )
    with TestClient(create_app(settings)) as test_client:
        login = test_client.post(
            "/api/v1/auth/login",
            json={"login": "demo", "password": "demo-password"},
        )
        security_headers = {
            "Origin": "http://localhost:3000",
            "X-CSRF-Token": login.json()["csrfToken"],
        }

        dashboard = test_client.get("/api/v1/dashboard").json()
        validate("Dashboard", dashboard)

        notifications = test_client.get("/api/v1/notifications").json()
        validate("NotificationPage", notifications)
        validate("Notification", notifications["items"][0])

        repository_search = test_client.get(
            "/api/v1/search", params={"q": "repository", "type": "repositories"}
        ).json()
        validate("SearchResultPage", repository_search)

        code_search = test_client.get(
            "/api/v1/search", params={"q": "provider", "type": "code"}
        ).json()
        validate("SearchResultPage", code_search)

        issue_page = test_client.get(
            "/api/v1/repositories/demo/hubgit-demo/issues"
        ).json()
        validate("IssuePage", issue_page)
        validate("Issue", issue_page["items"][0])

        comment_page = test_client.get(
            "/api/v1/repositories/demo/hubgit-demo/issues/1/comments"
        ).json()
        validate("CommentPage", comment_page)
        validate("Comment", comment_page["items"][0])

        pull_page = test_client.get(
            "/api/v1/repositories/demo/hubgit-demo/pulls"
        ).json()
        validate("PullRequestPage", pull_page)
        validate("PullRequest", pull_page["items"][0])

        checks = test_client.get(
            "/api/v1/repositories/demo/hubgit-demo/pulls/2/checks"
        ).json()
        validate("CheckSuitePage", checks)

        files = test_client.get(
            "/api/v1/repositories/demo/hubgit-demo/pulls/2/files"
        ).json()
        validate("DiffFilePage", files)

        review = test_client.post(
            "/api/v1/repositories/demo/hubgit-demo/pulls/2/reviews",
            headers={**security_headers, "Idempotency-Key": "review-contract-001"},
            json={"event": "approve", "body": "Ready to merge."},
        ).json()
        validate("Review", review)
        reviews = test_client.get(
            "/api/v1/repositories/demo/hubgit-demo/pulls/2/reviews"
        ).json()
        validate("ReviewPage", reviews)

        pull = test_client.get(
            "/api/v1/repositories/demo/hubgit-demo/pulls/2"
        ).json()
        merge = test_client.post(
            "/api/v1/repositories/demo/hubgit-demo/pulls/2/merge",
            headers={**security_headers, "Idempotency-Key": "merge-contract-001"},
            json={"method": "merge", "expectedHeadSha": pull["head"]["sha"]},
        ).json()
        validate("MergeResult", merge)
