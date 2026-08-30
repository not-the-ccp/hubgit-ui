# `@hubgit/fixtures`

Deterministic scenarios shared by the mock backend, MSW handlers, unit tests, and
visual tests. Fixture timestamps and IDs are stable. Consumers should reset mutable
state by reloading these files rather than modifying the source JSON.

| File | Purpose |
| --- | --- |
| `scenarios/users.json` | Guest, member, and maintainer user personas |
| `scenarios/repositories.json` | Public and private empty/non-empty repositories |
| `scenarios/collaboration.json` | Repository grants, issues, pull requests, and comments |
| `scenarios/failures.json` | Stable authentication, concealment, ETag, idempotency, and validation problems |

All objects use camel-case properties, opaque string IDs, and RFC 3339 UTC
timestamps. Run `pnpm --filter @hubgit/fixtures validate` to verify references
and deterministic timestamps.
