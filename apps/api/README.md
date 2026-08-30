# HubGit API

The bounded Wave 1 backend is a FastAPI application with a SQLite-backed local
session store and a deterministic, provider-neutral mock repository adapter.

Run it from this directory:

```bash
python -m pip install -e '.[dev]'
hubgit-api --reload
```

The seeded local account is `demo` with password `demo-password`. Login creates
an HttpOnly session cookie; send the returned `csrfToken` in `X-CSRF-Token` for
the logout request. The only repository operations in this slice are listing,
repository detail, and tree reads.
