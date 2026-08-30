# `@hubgit/contracts`

The provider-neutral HTTP contract between HubGit's UI and backend adapters. The
checked-in `openapi.json` document is the source of truth. It deliberately models
Git collaboration concepts instead of Forgejo, Gitea, or GitHub response shapes.

## Conventions

- All endpoints are rooted at `/api/v1` and exchange camel-case JSON.
- Identifiers are opaque strings and dates are RFC 3339 UTC timestamps.
- Lists use cursor pagination through `PageInfo`.
- Errors use `application/problem+json` and stable `ProblemDetails.code` values.
- `CapabilitySet` describes provider/instance support; `ResourcePermissions`
  describes what the current viewer may do to one resource.
- Mutating create/merge/dispatch requests accept `Idempotency-Key`. Concurrent
  settings updates use `If-Match` and return an `ETag`.
- Authentication uses an HTTP-only session cookie plus the `X-CSRF-Token` header.

Run `pnpm --filter @hubgit/contracts validate` (or `node scripts/validate.mjs`)
to perform dependency-free structural and `$ref` validation.
