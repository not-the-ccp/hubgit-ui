# HubGit API

The backend is a FastAPI application with SQLite-backed sessions and mutable
collaboration state plus a deterministic, provider-neutral mock adapter.

Run it from this directory:

```bash
python -m pip install -e '.[dev]'
hubgit-api --reload
```

The seeded local account is `demo` with password `demo-password`. Login creates
an HttpOnly session cookie. Cookie-authenticated mutations require the returned
`csrfToken` in `X-CSRF-Token` and a trusted `Origin` or `Referer` header.

The mock runtime currently covers instance metadata, capabilities, sessions,
repositories and trees, issues and comments, pull requests and reviews, check
summaries, structured diff files, expected-head merges, dashboard data,
notifications, and search. Mutations are persisted in SQLite; conflicting
edits use ETags and replay-safe creates and merges use idempotency keys.

GitHub-backed deployments use the provider-neutral redirect endpoints under
`/api/v1/auth/providers/{provider}`. A short-lived, single-use state binds the
authorization callback to its local return path. GitHub user-to-server tokens
and refresh tokens are encrypted in SQLite with the operator-managed Fernet key
from `HUBGIT_GITHUB_CREDENTIAL_KEY_FILE`; they are never returned by the API.
Access can be allowed for any authorized user or restricted by immutable GitHub
user IDs, active organization memberships, and active team memberships. A
membership lookup failure denies login.

The first GitHub repository port maps authenticated repository lists, repository
details, and Git trees into the same OpenAPI objects as the mock adapter. Expired
user tokens rotate before a provider read. Unsupported GitHub collaboration
operations return `capability.unsupported`, and a GitHub deployment never falls
back to mock repository data.
