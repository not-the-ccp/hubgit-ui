"""Provider-neutral repository read port and deterministic local mock adapter."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol

from .models import User


class RepositoryNotFoundError(LookupError):
    """The requested repository, ref, or tree path does not exist."""


class RepositoryProvider(Protocol):
    """Minimum provider surface needed by the first application slice."""

    async def list_repositories(self, *, query: str | None, viewer: User | None) -> list[dict]: ...

    async def get_repository(self, owner: str, repo: str, *, viewer: User | None) -> dict: ...

    async def get_tree(self, owner: str, repo: str, ref: str, path: str, *, viewer: User | None) -> dict: ...


_COMMIT = {
    "sha": "a21bd771e53b4d2c6f4a88f1ca8e218c17ab0001",
    "shortSha": "a21bd771e53",
    "message": "Build the first complete HubGit product slice",
    "author": {"name": "Demo User", "email": "demo@example.test", "date": "2026-08-29T12:00:00+00:00"},
    "authoredAt": "2026-08-29T12:00:00+00:00",
}


def _repository(owner: str, name: str, *, visibility: str = "public", language: str | None = "Python") -> dict:
    return {
        "id": f"mock_repo_{owner}_{name}", "kind": "repository",
        "owner": {"id": f"mock_user_{owner}", "kind": "user", "login": owner,
                  "avatarUrl": f"https://api.dicebear.com/9.x/identicon/svg?seed={owner}"},
        "name": name, "fullName": f"{owner}/{name}",
        "description": "A deterministic local repository supplied by the mock provider.",
        "visibility": visibility, "defaultBranch": "main", "empty": False, "archived": False,
        "fork": False, "forkedFrom": None, "language": language, "license": "MIT", "topics": ["hubgit", "mock"],
        "permissions": {"read": True, "triage": True, "write": owner == "demo", "maintain": owner == "demo", "admin": owner == "demo"},
        "counts": {"stars": 18, "forks": 3, "watchers": 18, "issues": 2, "pullRequests": 1},
        "cloneUrls": {"http": f"https://git.example.test/{owner}/{name}.git", "ssh": f"git@git.example.test:{owner}/{name}.git"},
        "createdAt": "2026-08-01T00:00:00+00:00", "updatedAt": "2026-08-29T12:00:00+00:00", "pushedAt": "2026-08-29T12:00:00+00:00",
    }


@dataclass(frozen=True)
class MockRepositoryProvider:
    """Fixed fixtures make local API and UI testing repeatable without a Git host."""

    provider_name: str = "mock"

    def _repos(self) -> list[dict]:
        return [_repository("demo", "hubgit-demo"), _repository("octocat", "hello-world", language="TypeScript"), _repository("demo", "private-notes", visibility="private", language=None)]

    def _visible(self, repository: dict, viewer: User | None) -> bool:
        return repository["visibility"] == "public" or (viewer is not None and viewer.login == repository["owner"]["login"])

    async def list_repositories(self, *, query: str | None, viewer: User | None) -> list[dict]:
        repositories = [item for item in self._repos() if self._visible(item, viewer)]
        if query:
            normalized = query.casefold()
            repositories = [item for item in repositories if normalized in item["fullName"].casefold() or normalized in (item["description"] or "").casefold()]
        return deepcopy(repositories)

    async def get_repository(self, owner: str, repo: str, *, viewer: User | None) -> dict:
        for item in self._repos():
            if item["owner"]["login"] == owner and item["name"] == repo and self._visible(item, viewer):
                return deepcopy(item)
        raise RepositoryNotFoundError(f"{owner}/{repo}")

    async def get_tree(self, owner: str, repo: str, ref: str, path: str, *, viewer: User | None) -> dict:
        await self.get_repository(owner, repo, viewer=viewer)
        if ref != "main":
            raise RepositoryNotFoundError(ref)
        clean_path = path.strip("/")
        entries_by_path = {
            "": [
                {"name": "README.md", "path": "README.md", "kind": "file", "sha": "f0e1d2c3b4a5", "size": 142, "lastCommit": _COMMIT},
                {"name": "src", "path": "src", "kind": "directory", "sha": "d0c0ffee0001", "size": None, "lastCommit": _COMMIT},
            ],
            "src": [{"name": "main.py", "path": "src/main.py", "kind": "file", "sha": "123456789abc", "size": 87, "lastCommit": _COMMIT}],
        }
        if clean_path not in entries_by_path:
            raise RepositoryNotFoundError(clean_path)
        return {"sha": "d0c0ffee0001", "ref": ref, "path": clean_path, "entries": deepcopy(entries_by_path[clean_path]), "commit": deepcopy(_COMMIT)}
