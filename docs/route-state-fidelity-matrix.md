# Route and State Fidelity Matrix

## Purpose

This matrix defines the visual and behavioral acceptance surface for HubGit. GitHub's current web interface is a reference for information architecture, interaction density, spacing, and state behavior. HubGit uses original branding and provider-neutral data contracts.

The matrix is the source of truth for route coverage, fixture requirements, screenshot coverage, and release readiness. A route is complete only when every applicable state class has a deterministic fixture and the required tests pass.

## Fidelity Standard

| Property | Acceptance rule |
| --- | --- |
| Desktop geometry | Major regions, controls, and baselines are within 2 CSS px of the approved reference at 1440×900 and 1280×800. |
| Mobile geometry | Major regions and controls are within 3 CSS px of the approved reference at 390×844. |
| Themes | Light and dark are required for every representative visual test. High contrast is required for global shells and critical workflows. |
| Responsive behavior | Navigation, tables, code, diffs, dialogs, and sidebars use the same collapse, overflow, and stacking behavior as the approved reference. |
| Interaction | Keyboard order, focus restoration, menu dismissal, dialog modality, URL state, optimistic feedback, and error recovery match the documented reference behavior. |
| Content variance | Layout remains usable with empty, minimal, typical, long, Unicode, right-to-left, binary, and high-volume fixtures where applicable. |
| Accessibility | WCAG 2.2 AA, keyboard-only operation, visible focus, correct names/roles/states, reduced motion, and Axe checks are release gates. |
| Dynamic content | Dates, counters, avatars, random IDs, animations, and network timing are deterministic or masked in screenshot tests. |

## State Dimensions

Every route row refers to the following reusable state codes.

### Identity and authorization

| Code | State |
| --- | --- |
| `G` | Logged-out guest. |
| `M` | Authenticated member with normal read/write access. |
| `T` | Repository maintainer or organization owner. |
| `A` | Instance administrator. |
| `F` | Authenticated user without access to the requested private resource. |
| `S` | Suspended, expired, or reauthentication-required session. |

### Resource visibility and lifecycle

| Code | State |
| --- | --- |
| `PUB` | Public resource. |
| `PRI` | Private resource. |
| `INT` | Instance-internal resource when supported. |
| `EMP` | Empty or newly created resource. |
| `ARC` | Archived/read-only repository. |
| `FRK` | Fork with upstream relationship. |
| `TPL` | Template repository. |
| `DIS` | Feature disabled by repository settings. |
| `CAP` | Feature unsupported by the active provider. |

### Request and result lifecycle

| Code | State |
| --- | --- |
| `LD` | Initial skeleton/loading state. |
| `RF` | Background refresh with stale data retained. |
| `OK` | Typical successful response. |
| `E0` | Empty result. |
| `E4` | Not found or deliberately concealed private resource. |
| `E403` | Visible resource with insufficient permission. |
| `E409` | Conflict, stale ETag, or no-longer-valid operation. |
| `E422` | Field or semantic validation failure. |
| `E429` | Rate limited. |
| `E5` | Provider or server failure with retry affordance. |
| `OFF` | Network unavailable or SSE disconnected. |

### Required viewports

| Code | Viewport |
| --- | --- |
| `D1` | 1440×900 desktop. |
| `D2` | 1280×800 compact desktop. |
| `M1` | 390×844 mobile. |

## Global Shells and Authentication

| Area | Route or surface | Roles | Required fixtures and behavior |
| --- | --- | --- | --- |
| Public shell | `/` | G, M | Logged-out marketing/entry state; logged-in redirect or dashboard state; D1/D2/M1; light/dark/high contrast. |
| Sign in | `/login` | G, S | Empty, invalid credentials, locked/rate-limited, return URL, expired session, password manager/autofill, 2FA continuation; configurable product identity and local-credential explanation. |
| Registration | `/signup` | G | Available/disabled registration, field errors, duplicate identity, verification pending, server error; configurable product identity and local-credential explanation. |
| Verification | `/verify`, `/verify/:token` | G, M | Pending, accepted, expired, already used, invalid token; configurable product identity and local-credential explanation. |
| Recovery | `/password-reset`, `/password-reset/:token` | G | Request accepted without account enumeration, expired/invalid token, password policy errors; configurable product identity and local-credential explanation. |
| Second factor | `/sessions/2fa` | G, S | TOTP, recovery code, mock passkey prompt, invalid code, rate limit, cancel/back; configurable product identity and local-credential explanation. |
| Dashboard | `/dashboard` | M, T, A | First-use empty, populated feed, recent repositories, organizations, failed widget, notification counts, responsive sidebars. |
| Global navigation | all application routes | G, M, T, A | Search, create menu, account menu, breadcrumbs, unread indicator, responsive drawer, command palette, focus restoration, outside-click and Escape dismissal. |
| Notifications | `/notifications` | M, T, A | All/participating, read/unread, repository/reason filters, grouped rows, bulk mark/read/unsubscribe, E0, optimistic rollback, OFF. |
| Search | `/search`, `/search/:kind` | G, M | Repositories, code, commits, issues, pull requests, discussions, users, organizations; qualifier parsing, suggestions, invalid query, E0, pagination. Private hits never leak to G/F. |
| New repository | `/new` | M, T | Owner selection, visibility, initialization choices, name availability, validation, create failure, idempotent retry. |
| New organization | `/organizations/new` | M | Field validation, unavailable slug, create failure; billing is absent. |

## Repository and Git Data

All repository routes use `/:owner/:repo` as their base. Unless narrowed below, each route requires `G/M/T`, `PUB/PRI/INT`, `LD/OK/E4/E403/E5`, D1/D2/M1, and light/dark coverage.

| Area | Route template | Additional required fixtures and behavior |
| --- | --- | --- |
| Overview | `/:owner/:repo` | README absent/present/long, about metadata, topics, languages, license, latest release, contributors, `EMP/ARC/FRK/TPL`, feature cards, clone menu. |
| Tree | `/:owner/:repo/tree/:ref/*path` | Root/nested directory, branch/tag/SHA refs, long names, Unicode, symlink, submodule, LFS pointer, large tree virtualization, ref-not-found. |
| Blob | `/:owner/:repo/blob/:ref/*path` | Text, Markdown, rendered notebook summary, image, PDF download, binary, generated, minified, large/truncated, raw/download/copy, line anchors/ranges, syntax failure. |
| Raw content | `/:owner/:repo/raw/:ref/*path` | Correct content type/disposition, private authorization, cache validator, range request, missing ref/path, active-content download safety. |
| Edit/create file | `/:owner/:repo/edit/:ref/*path`, `/:owner/:repo/new/:ref/*path` | CodeMirror editing, preview where applicable, direct commit/new branch, stale base, protected branch, validation, `ARC`, write forbidden. |
| Delete/move file | `/:owner/:repo/delete/:ref/*path` | Confirmation, commit metadata, protected branch, stale base, last-file/empty result. |
| History | `/:owner/:repo/commits/:ref/*path?` | Repository and path history, signed/unsigned commits, merge commits, pagination, renamed file, E0. |
| Commit detail | `/:owner/:repo/commit/:sha` | Metadata, parents, signature, checks, comments, short/full SHA, changed-file navigation, binary/rename/mode-only/submodule diffs. |
| Compare | `/:owner/:repo/compare/:base...:head` | Ahead/behind, identical, unrelated, missing ref, cross-fork, merge-base warning, large diff, create-PR affordance. |
| Blame | `/:owner/:repo/blame/:ref/*path` | Grouped hunks, prior revision, line anchors, long file, binary unsupported, moved/deleted path. |
| Branches | `/:owner/:repo/branches` | Default/active/stale/all, protection badges, ahead/behind, rename/delete/restore controls, no branches, permission gating. |
| Tags | `/:owner/:repo/tags` | Annotated/lightweight/signed tags, download menu, pagination, no tags. |
| Network/forks | `/:owner/:repo/forks` | No forks, fork list, filtering/sorting, private visibility boundaries. |
| Archive download | `/:owner/:repo/archive/:ref.:format` | Zip/tar capability, missing ref, permission failure, provider unavailable, download response. |
| Releases list | `/:owner/:repo/releases` | Latest, pre-release, draft-visible-to-maintainer, no releases, pagination. |
| Release detail/edit | `/:owner/:repo/releases/:tag`, `/releases/new`, `/releases/:tag/edit` | Assets, checksums, generated notes, duplicate tag, upload progress/failure, draft/publish, delete confirmation. |

## Issues, Pull Requests, and Collaboration

| Area | Route template | Roles | Required fixtures and behavior |
| --- | --- | --- | --- |
| Issue list | `/:owner/:repo/issues` | G, M, T | Open/closed, qualifier search, labels/milestones/assignee filters, sorting, E0, pagination, disabled issues. |
| New issue chooser | `/:owner/:repo/issues/new/choose` | M, T | No templates, Markdown template, structured form, blank allowed/forbidden, permission failure. |
| New issue | `/:owner/:repo/issues/new` | M, T | Draft persistence, Markdown preview, uploads, validation, issue form fields, idempotent submit. |
| Issue detail | `/:owner/:repo/issues/:number` | G, M, T | Timeline events, edited/deleted/hidden comments, reactions, labels, milestone, assignees, lock, transfer, pin, close/reopen, stale update, archived repository. |
| Labels | `/:owner/:repo/labels` | G, M, T | E0, create/edit/delete, invalid/duplicate name, color contrast, permission gating. |
| Milestones | `/:owner/:repo/milestones`, `/:owner/:repo/milestones/:number` | G, M, T | Open/closed, progress, due/overdue/no date, create/edit/delete, filtering. |
| Pull request list | `/:owner/:repo/pulls` | G, M, T | Open/closed/draft/merged, qualifier search, review/check status, E0, pagination. |
| New pull request | `/:owner/:repo/compare/:base...:head?expand=1` | M, T | Branch/fork selection, identical refs, conflicts, title/body validation, draft, permission failure. |
| PR conversation | `/:owner/:repo/pull/:number` | G, M, T | Full timeline, draft/open/closed/merged, mergeability pending/conflict/clean, checks, review requirement, branch deleted, stale head, all merge methods, admin override. |
| PR commits | `/:owner/:repo/pull/:number/commits` | G, M, T | One/many commits, signature/check badges, rewritten history, pagination. |
| PR checks | `/:owner/:repo/pull/:number/checks` | G, M, T | Queued/running/success/failure/cancelled/skipped, annotations, log unavailable, rerun authorization, live/offline update. |
| PR files | `/:owner/:repo/pull/:number/files` | G, M, T | Unified/split, whitespace toggle, viewed state, file tree, inline threads, pending review, suggestion, outdated thread, binary/rename/large diff. |
| Review submit | PR files/conversation modal | M, T | Comment/approve/request changes, empty review validation, pending comments, stale head conflict, dismiss review. |
| Repository discussions | `/:owner/:repo/discussions`, `/:owner/:repo/discussions/:number` | G, M, T | Categories, answered/unanswered, nested replies, reactions, mark answer, lock, delete/hide, `DIS/CAP`. |

## Automation, Projects, Wiki, Security, and Insights

| Area | Route template | Roles | Required fixtures and behavior |
| --- | --- | --- | --- |
| Workflow list | `/:owner/:repo/actions` | G, M, T | No workflows, active/disabled workflows, run status filters, `DIS/CAP`. |
| Workflow detail | `/:owner/:repo/actions/workflows/:workflow` | G, M, T | Runs, branch/event filters, manual dispatch fields, disable/enable, permission gating. |
| Run detail | `/:owner/:repo/actions/runs/:runId` | G, M, T | Queued/running/completed/cancelled, job graph, artifacts, rerun/cancel, live SSE and polling fallback. |
| Job logs | `/:owner/:repo/actions/runs/:runId/job/:jobId` | G, M, T | Streaming, collapsed groups, annotations, timestamps, retry, expired/unavailable logs, secret redaction. |
| Projects | `/:owner/:repo/projects`, `/:owner/:repo/projects/:projectId` | G, M, T | E0, table/board, filters, fields, draft items, issue/PR links, reorder, permission gating, `DIS/CAP`. |
| Wiki | `/:owner/:repo/wiki`, `/:owner/:repo/wiki/:page` | G, M, T | Home absent/present, sidebar/footer, create/edit, preview, history/diff, clone info, invalid title, conflict, `DIS/CAP`. |
| Security overview | `/:owner/:repo/security` | G, M, T | Policy absent/present, capability summaries, private findings visibility, `CAP`. |
| Advisories | `/:owner/:repo/security/advisories`, `/:owner/:repo/security/advisories/:id` | T | Draft/published/closed, collaborators, CVSS fields, credits, validation, confidentiality. |
| Insights | `/:owner/:repo/pulse`, `/graphs/:kind` | G, M, T | Contributors, traffic, commits, code frequency, dependency/network views, E0, partial metrics, `CAP`. |

## Identity, Organizations, and Settings

| Area | Route template | Roles | Required fixtures and behavior |
| --- | --- | --- | --- |
| User profile | `/:user` | G, M | Bio, avatar, organizations, followers, contribution graph, pinned repositories, no activity, private contribution preference, blocked/not found. |
| User repositories | `/:user?tab=repositories` | G, M | Public/private visibility, search/filter/sort, archived/fork/source badges, E0. |
| Stars/followers | `/:user?tab=stars`, `/:user?tab=followers`, `/:user?tab=following` | G, M | Lists, E0, follow/unfollow optimistic update, privacy boundaries. |
| Organization overview | `/orgs/:org` | G, M, T | Public/member/owner views, README, pinned repositories, people/teams summary. |
| Organization repositories | `/orgs/:org/repositories` | G, M, T | Public/private/internal visibility, filters, E0, create permission. |
| People and teams | `/orgs/:org/people`, `/orgs/:org/teams`, `/orgs/:org/teams/:team` | M, T | Public/private membership, role filters, invite/remove/change role, child teams, repository grants. |
| User settings | `/settings/:section?` | M | Profile, account, appearance, accessibility, notifications, emails, password/authentication, sessions, keys, tokens, applications; unsaved/stale/conflict states. Billing is absent. |
| Repository settings | `/:owner/:repo/settings/:section?` | T | General, access, branches/rules, webhooks, deploy keys, security, secrets metadata, variables, automation, archive/transfer/delete; validation and ETag conflict. |
| Organization settings | `/organizations/:org/settings/:section?` | T | Profile, member privileges, roles, teams, repository defaults, webhooks, security, audit placeholder, danger zone. Billing and enterprise administration are absent. |
| Instance administration | `/admin/:section?` | A | Users, organizations, repositories, registration/auth policy, provider health, capabilities, audit events; non-admin concealment. |

## Error, Empty, and Boundary Pages

| Surface | Required behavior |
| --- | --- |
| 404/concealed resource | Same outward response for nonexistent resources and unauthorized private resources where concealment is required. No owner, repository, ref, issue, or user metadata leakage. |
| 403 | Explain the missing permission only when resource existence is already visible. Provide a useful return path. |
| 409 | Preserve user input, explain stale/conflicting state, and offer reload or retry. Never silently overwrite. |
| 422 | Associate field errors with controls, provide a summary for long forms, and retain valid input. |
| 429 | Show retry timing when available; do not create a request loop. |
| 5xx/provider unavailable | Preserve navigation shell when safe, expose a retry action, and avoid leaking provider responses or stack traces. |
| Offline | Retain cached read-only data, mark it stale, queue no destructive mutation, and recover SSE through backoff plus polling. |
| Capability absent | Omit feature navigation and creation affordances. A direct URL renders an explicit unsupported-feature page. |
| Feature disabled | Preserve discoverability for authorized maintainers and link to the enabling setting; ordinary users see the repository-specific disabled state. |

## Route Completion Ledger

The ledger is committed with each implementation pull request and has one row
per affected route and state. Status values are `not-started`, `in-progress`,
`blocked`, or `complete`; a route is `complete` only when every required evidence
column links to a checked-in artifact or a CI run. Keep reference observations
sanitized and keep provider credentials, private data, and reference captures
outside the repository.

Each implementation pull request updates the following record for every affected route:

| Field | Required evidence |
| --- | --- |
| Route/state | Canonical route template plus state codes from this matrix. |
| Owner/updated | Responsible team or contributor and UTC update date. |
| Status | `not-started`, `in-progress`, `blocked`, or `complete`; blockers name the missing dependency. |
| Contract | OpenAPI operation and generated-client type exist. |
| Fixtures | Deterministic normal, empty, loading, permission, and failure data exist. |
| Unit/component | State logic, URL synchronization, and critical accessibility semantics pass. |
| End-to-end | Primary read and write workflows pass against the mock API. |
| Visual | Approved D1, D2, and M1 baselines in light/dark for representative states. |
| Keyboard/a11y | Keyboard workflow and Axe scan pass. |
| Reference record | Date, route, viewport, theme, state, measurements, and observations are recorded without checked-in GitHub screenshots or proprietary assets. |

Use the standalone `docs/route-completion-ledger.md` template or copy this
compact format into the pull request description:

```markdown
| Route/state | Owner/updated | Status | Contract | Fixtures | Unit/component | E2E | Visual | Keyboard/a11y | Reference record | Blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/:owner/:repo` · `M/PRI/OK` | @contributor · 2026-08-30 | in-progress | PR #123 | `fixtures/repo.ts` | CI #456 | CI #456 | D1/D2/M1 light+dark | Axe CI #456 | `docs/reference-records/repo.md` | none |
```

## Explicit Exclusions

The fidelity program excludes Copilot and agent features, Codespaces and the dot-key web editor, billing, Sponsors, Marketplace, package registries, enterprise administration, and GitHub corporate, careers, support, status, and marketing-site content. Links to excluded surfaces must not lead to unfinished local imitations; omit them or label a capability boundary.
