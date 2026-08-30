# Route Completion Ledger

This ledger tracks route and state evidence against the [route and state
fidelity matrix](route-state-fidelity-matrix.md). Add one row for every affected
route/state in an implementation pull request. Link each evidence cell to a
checked-in artifact or CI run; use `none` only for a deliberately inapplicable
field. Keep reference observations sanitized and keep credentials, private data,
and provider captures outside the repository.

Status values are `not-started`, `in-progress`, `blocked`, and `complete`.
`complete` requires every applicable evidence column to be present and passing.
For `blocked`, describe the dependency in the final column and do not imply
that the route is release-ready.

| Route/state | Owner/updated (UTC) | Status | Contract | Fixtures | Unit/component | E2E | Visual | Keyboard/a11y | Reference record | Blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/:owner/:repo` · `M/PRI/OK` | `@owner` · `YYYY-MM-DD` | `not-started` | `none` | `none` | `none` | `none` | `none` | `none` | `none` | `none` |

Evidence requirements:

- Contract: OpenAPI operation and generated-client type.
- Fixtures: deterministic normal, empty, loading, permission, and failure data.
- Unit/component: state logic, URL synchronization, and critical accessibility semantics.
- E2E: primary read and write workflows against the mock API.
- Visual: approved D1, D2, and M1 baselines in light and dark themes for representative states.
- Keyboard/a11y: keyboard workflow and Axe scan.
- Reference record: date, route, viewport, theme, state, measurements, and observations without checked-in provider screenshots or proprietary assets.
