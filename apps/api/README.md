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
