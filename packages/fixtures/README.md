# `@hubgit/fixtures`

Deterministic scenarios shared by the mock backend, MSW handlers, unit tests, and
visual tests. Fixture timestamps and IDs are stable. Consumers should reset mutable
state by reloading these files rather than modifying the source JSON.

| File | Purpose |
| --- | --- |
| `scenarios/viewers.json` | Guest, member, maintainer, and administrator personas |
| `scenarios/repositories.json` | Public, private, archived, and empty repositories |
| `scenarios/issues.json` | Open/closed issues, labels, milestones, and comments |
| `scenarios/pull-requests.json` | Draft/mergeable/conflicted PRs and check suites |

All objects follow `@hubgit/contracts/openapi.json`: camel-case properties, opaque
string IDs, and RFC 3339 UTC timestamps.
