# Architecture and Provider Adapter Contract

## Goals

HubGit presents one stable, provider-neutral API to the web application. The initial stateful mock backend and future GitHub, Forgejo, Gitea, or other provider adapters implement the same application ports. GitHub is the first production integration target for private self-hosted installations, but it is an adapter choice rather than a frontend dependency. The browser never interprets provider-specific payloads, pagination headers, permissions, error bodies, authentication mechanisms, or feature names.

The architecture optimizes for:

- Faithful, fast UI iteration against deterministic data.
- A contract that can be mapped onto real Git servers without redesigning route components.
- Explicit capability and permission boundaries.
- Secure server-side custody of provider credentials.
- Consistent conflict, pagination, idempotency, and event semantics.

Private self-hosting is the default deployment posture. An operator runs the HubGit
API, web application, database, cache, and provider connection inside a private
network or behind an access-controlled reverse proxy. The deployment can select a
GitHub adapter first and later add another adapter without changing route
components or the public contract.

Branding is configuration, not a route-level assumption. Operators may set the
product name, logo, colors, favicon, support text, authentication explanation,
legal/policy links, and external-provider labels. The safe defaults identify the
product as HubGit, use original artwork, avoid third-party assets and analytics,
and keep all authentication copy explicit about the configured provider. Config
validation rejects empty identity fields, unsafe URLs, and active-content logo
sources before startup.

## Runtime Components

```text
Browser
  │  HTTP-only HubGit session + CSRF header
  ▼
HubGit REST API (/api/v1) ───────────────► SSE stream (/api/v1/events/stream)
  │
  ├── application services and policy enforcement
  │     ├── identity port
  │     ├── repositories port
  │     ├── Git data port
  │     ├── collaboration port
  │     ├── automation port
  │     ├── releases port
  │     ├── search port
  │     └── administration port
  │
  ├── mock adapter ─► SQLite + deterministic Dulwich repositories
  └── future provider adapter ─► provider REST/Git APIs
```

The API process owns authentication, authorization, normalization, caching, error translation, and provider calls. Provider credentials are never exposed to the browser or encoded in HubGit session state returned to the browser. The web process may serve public static assets, but it does not become a provider proxy and never receives provider credentials.

## Layer Responsibilities

| Layer | Responsibilities | Must not do |
| --- | --- | --- |
| Web application | Rendering, accessible interactions, URL state, optimistic UI, query caching, form validation, SSE invalidation. | Import provider schemas, store provider tokens, infer access from capability flags, or synthesize provider URLs. |
| Generated client | Typed request/response models, operation calls, problem parsing, pagination primitives. | Contain view logic or provider-specific branches. |
| HTTP boundary | Session and CSRF enforcement, input parsing, OpenAPI response shape, ETags, idempotency keys, SSE framing. | Leak adapter exceptions or provider response bodies. |
| Application services | Use-case orchestration, permission policy, validation, transaction boundary, event publication. | Depend on HTTP framework request objects or provider DTOs. |
| Ports | Provider-neutral operations and domain values grouped by capability. | Model a provider's endpoint layout one-for-one. |
| Adapters | Translate domain calls to mock persistence or provider APIs; normalize identity, pagination, errors, and feature gaps. | Return raw provider payloads outside the adapter. |

## Canonical Wire Rules

- Base path: `/api/v1`.
- JSON field names: camel case.
- IDs: opaque strings; clients must not parse or sort them as numbers.
- Timestamps: RFC 3339 UTC with an explicit `Z` or offset.
- Polymorphic objects: a stable `kind` discriminator.
- Pagination: `{ "items": [...], "pageInfo": { "hasNextPage": true, "endCursor": "..." }, "totalCount": 42 }`; `totalCount` is optional when expensive or unavailable.
- Errors: `application/problem+json` with `type`, `title`, `status`, `detail`, `instance`, stable `code`, optional `fieldErrors`, and optional safe retry metadata.
- Conditional writes: mutable resources return an ETag; stale `If-Match` returns `409` or `412` without applying the mutation.
- Idempotent commands: create, merge, workflow dispatch, rerun, and other retry-sensitive commands require an idempotency key. Reuse returns the original result or a stable conflict.
- Raw and archive responses use explicit content types, safe filenames, private-cache directives, and range support where the adapter can provide it.
- Dates, counts, and identifiers retain provider precision; adapters do not invent total counts or timestamps.
- Private cache entries are keyed by provider, tenant, repository, contract version, and authorization subject. A repository cache is never shared across authorization subjects, even when the upstream provider marks the response public.
- The API may maintain a per-repository cache and automatically populate it after an authorized read. Automatic caching is bounded by size and TTL, stores only canonical responses, and is invalidated on permission, session, provider, or repository changes. Cache misses fail closed when authorization cannot be re-established.
- Offline access is a bounded read-only grace window over data that was already authorized and cached. The API records the last successful authorization and refuses cached reads after the configured window or a revocation event. Offline mode never queues, retries, or applies a mutation.

## Domain Boundary

Canonical resources include:

- `Viewer`, `User`, `Organization`, `Team`, `Membership`, `Session`.
- `Repository`, `RepositoryPermissions`, `Ref`, `Branch`, `Tag`, `TreeEntry`, `Blob`, `Commit`, `Comparison`, `DiffFile`, `DiffHunk`, `BlameRange`.
- `Issue`, `PullRequest`, `TimelineEvent`, `Comment`, `Reaction`, `Label`, `Milestone`, `Review`, `ReviewThread`, `CheckSuite`, `CheckRun`.
- `Discussion`, `WikiPage`, `Project`, `ProjectItem`, `Workflow`, `Run`, `Job`, `Artifact`, `Release`, `ReleaseAsset`.
- `SecurityAdvisory`, `RepositoryRule`, `Webhook`, `DeployKey`, `SecretMetadata`, `Variable`, `Notification`, `SearchHit`.

Domain models expose provider-independent semantic fields. Provider-only data may be retained inside an adapter's private persistence but must not be included as an untyped escape hatch in public responses. Adding a widely useful concept requires an OpenAPI change and mock-adapter fixture before a real adapter may expose it.

## Ports

### Identity port

Resolves viewers, users, organizations, teams, memberships, follows, stars, dashboard data, and local/provider account linkage. Authentication methods are advertised separately from identity data.

### Repositories port

Lists, retrieves, creates, updates, archives, transfers, and deletes repositories; manages collaborators, teams, visibility, subscriptions, topics, and repository-level feature settings.

### Git data port

Resolves refs and commits; lists trees; reads blobs and raw content; compares commits; produces structured diffs and blame; creates file commits; manages branches and tags; streams archives. Diff normalization must preserve old/new paths, modes, binary status, rename similarity when known, truncation, hunks, and line positions required for review comments.

### Collaboration port

Manages issues, pull requests, comments, reactions, labels, milestones, assignments, timelines, reviews, threads, suggestions, mergeability, checks, and merge commands. Provider event vocabularies are normalized into explicit timeline `kind` values.

### Automation port

Lists workflows, runs, jobs, logs, annotations, and artifacts; dispatches workflows and controls runs. Log access uses server-side streaming or bounded chunks and applies redaction before browser delivery.

### Releases port

Manages releases and assets, generated notes when supported, draft/prerelease state, and safe upload/download streams.

### Search port

Parses HubGit's documented query grammar, authorizes search scope, executes provider-native search where safe, and supplies deterministic fallback indexes for the mock adapter. Unsupported qualifiers produce a validation problem rather than being silently ignored.

### Administration port

Manages repository settings, rules, webhooks, deploy keys, safe secret metadata, variables, instance configuration, audit events, and provider health. Secret values are write-only and are never returned after creation.

## Capabilities and Permissions

Capabilities answer whether the configured adapter and instance can represent an operation. Permissions answer whether the current viewer may perform it on a specific resource. They must never be conflated.

`GET /api/v1/capabilities` returns a versioned capability document with stable keys and optional constraints, such as supported merge methods, archive formats, maximum upload size, diff limits, authentication methods, registration policy, discussions, projects, wiki, automation, security advisories, and administration features.

Each protected resource returns an explicit `permissions` object derived by the API. The web application:

- Omits navigation and creation controls for absent capabilities.
- Renders an unsupported-feature page for a direct route when the capability is absent.
- Renders a permission state when the capability exists but the viewer lacks access.
- Never grants access because a button is visible; every API operation reauthorizes.

The capability schema is additive within `/api/v1`. Unknown keys are ignored by older clients. Removing or changing the meaning of a key requires a new API version.

## Authentication and Provider Credential Model

HubGit authentication terminates at the HubGit API. The browser receives an opaque, HTTP-only, Secure-in-production, SameSite session cookie and a separately readable CSRF value bound to that session. State-changing cookie-authenticated requests require the CSRF header and an allowed Origin.

The mock adapter uses local accounts and Argon2 password hashes. A future provider adapter may support one or more server-side connection modes:

- OAuth/OIDC authorization code flow with PKCE, when supported by the provider.
- A provider token entered on a dedicated provider-connection page and encrypted at rest.
- An administrator-configured service credential plus mapped local identity, only when the provider and deployment policy permit impersonation safely.

Provider passwords are not an accepted connection method. When GitHub authentication is enabled, it is redirect-only: the API starts a server-side OAuth authorization-code flow, validates a short-lived single-use state, and exchanges the code at the provider. HubGit forms never collect a GitHub password, token, passkey, recovery code, session cookie, SSH key, or OAuth device code. Return paths are application-local relative paths. PKCE is used for adapters whose documented authorization flow supports it; GitHub's current GitHub App web flow does not advertise PKCE parameters.

Branding configuration cannot change this authentication boundary. A custom
authentication explanation must identify the configured provider and local
credential boundary, and a provider connection must remain a separately named
settings operation. If GitHub authentication is not configured, the GitHub
redirect is unavailable rather than replaced with a credential form.

## Request Flow

1. The HTTP boundary validates origin, session, CSRF when applicable, media type, and request size.
2. The application service validates domain input and resolves the viewer.
3. Authorization policy evaluates the action against resource permissions and instance policy.
4. The selected port executes through the configured adapter.
5. The adapter maps provider pagination, statuses, and errors to canonical results.
6. The application commits its transaction, records an audit event for sensitive operations, and publishes invalidation events.
7. The HTTP boundary returns the canonical result with cache and ETag headers.

Adapter error translation uses stable categories: unauthenticated, forbidden, concealed not found, visible not found, conflict, validation, rate limited, provider unavailable, timeout, and unexpected provider response. Raw upstream bodies, headers, URLs with credentials, and stack traces are logged only after redaction and are never returned to the browser.

## Event Stream

`GET /api/v1/events/stream` is an authenticated SSE endpoint. Events contain an opaque event ID, canonical event kind, affected resource keys, and a timestamp. Events are cache invalidations rather than complete sensitive resources.

- Clients reconnect with `Last-Event-ID` and exponential backoff with jitter.
- The server emits heartbeat comments and enforces per-session connection limits.
- Authorization is checked at connection time and when an event is selected for delivery.
- Session revocation closes the stream.
- Missed or unsupported replay causes a `resync` event.
- Polling remains the fallback for notifications, repositories, pull requests, and runs.

## Mock Adapter

The mock adapter is a reference implementation of every port and a conformance oracle for future adapters.

- SQLite persists accounts, sessions, repository metadata, collaboration objects, settings, idempotency records, and audit entries.
- Deterministic bare repositories generated with Dulwich provide realistic branches, tags, commits, trees, blobs, renames, merge commits, and diffs.
- Fixture clocks, IDs, avatars, and event order are seeded and resettable.
- Personas cover guest, member, maintainer, organization owner, administrator, suspended session, and forbidden viewer.
- Repository fixtures cover public/private/internal, empty, archived, fork, template, binary, symlink, submodule, LFS pointer, large file, large tree, and protected branch behavior.
- Failure injection covers validation, conflict, rate limit, timeout, partial provider response, unavailable logs, and SSE disconnect.

The mock must not implement behavior only in the UI's MSW layer. Backend and browser-mocking fixtures share scenario definitions so contract and visual tests describe the same states.

## Real Provider Adapter Requirements

A provider adapter is eligible for release only when it:

- Implements the required port subset and returns an accurate capability document for everything else.
- Passes the shared adapter conformance suite, including permission and private-resource non-disclosure tests.
- Uses server-side credential storage and redacted structured logging.
- Normalizes provider cursors without exposing tokens containing credentials or unstable implementation detail.
- Implements bounded retries only for safe/idempotent operations and respects provider rate-limit reset data.
- Preserves ETags or creates safe application revisions for conditional writes.
- Documents every semantic mismatch, disabled operation, and degraded fallback.
- Provides contract fixtures recorded from a dedicated synthetic provider instance, with all identifiers and secrets sanitized.
- Supports authorization-aware per-repository caching and an explicit offline read-only policy without allowing offline commands.

### Forgejo-oriented mapping notes

A Forgejo adapter is expected to map repositories, Git contents, issues, pull requests, releases, organizations, teams, webhooks, keys, and actions through Forgejo APIs. HubGit retains its own session boundary and translates Forgejo tokens server-side. Forgejo-specific differences such as numeric IDs, page-number pagination, feature availability by version, status names, review positioning, or missing totals remain inside the adapter.

The adapter must perform a version and capability probe during startup and periodically thereafter. Startup may continue in degraded read-only mode only when configured explicitly; otherwise an incompatible provider fails health checks with an administrator-visible reason.

## Compatibility and Evolution

- OpenAPI is checked in and generated-client output must match it in CI.
- Additive optional response fields and capability keys are backward compatible.
- Required-field additions, changed semantics, enum removals, and operation rewrites require a new API version or a documented migration period.
- Adapters declare the HubGit contract version they implement.
- Contract tests run against the mock adapter and every supported provider/version matrix.
- Database migrations are forward-only in releases and include rollback guidance for operators.
- Client and API versions expose build metadata through `/api/v1/meta`; incompatible versions fail visibly instead of misrendering data.

## Operational Health

Health surfaces distinguish process liveness, database readiness, fixture repository readiness, provider reachability, provider authentication validity, and event-stream health. Public health output contains no provider URL, account name, repository name, or token detail. Detailed diagnostics require administrator authorization and remain redacted.
