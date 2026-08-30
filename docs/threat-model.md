# HubGit Threat Model

## Security Objectives

HubGit must protect local accounts, provider credentials, private repository data, source code, collaboration content, administrative controls, and the integrity of Git operations. Fully configurable branding must not create a credential-harvesting surface or imply that users are authenticating with a provider when they are signing in to HubGit.

Primary objectives:

- Never transmit HubGit credentials to GitHub or any unconfigured external provider.
- Never request or store a real provider password, passkey, recovery code, session cookie, or personal access token through an authentication screen. GitHub connections are redirect-only OAuth authorization-code flows with single-use state validation.
- Keep provider credentials server-side, encrypted at rest, scoped, revocable, and absent from logs and browser responses.
- Prevent private-resource discovery through status, search, counts, timing, errors, events, or caches.
- Permit cached private reads only for a bounded authorization window; never permit offline mutations or a mutation queue.
- Authorize every read and mutation at the API boundary and again at the adapter/provider boundary where available.
- Preserve the integrity of commits, reviews, merges, settings, rules, workflows, releases, and administrative actions.
- Make destructive, privileged, and stale-state operations explicit and auditable.

## System and Trust Boundaries

```text
Untrusted browser/content
  │
  │ TLS, HubGit session cookie, CSRF header
  ▼
HubGit API trust boundary
  ├── application policy and canonical data
  ├── SQLite/session/secret storage
  ├── bare Git repositories used by the mock
  ├── event and background workers
  └── provider adapter trust boundary
        └── configured Git service
```

External links, Markdown, uploaded files, Git contents, provider responses, webhook bodies, workflow logs, search queries, archive paths, and repository metadata are untrusted. Administrators are privileged but are not assumed to be immune to phishing, stored XSS, CSRF, or accidental disclosure.

## Assets

- HubGit passwords and password hashes, sessions, CSRF values, recovery and verification tokens.
- Provider OAuth tokens, access tokens, webhook secrets, deploy keys, and encryption keys.
- Private/internal repositories, raw files, archives, diffs, issues, pull requests, discussions, wikis, workflow logs, artifacts, security advisories, and notification metadata.
- Authorization policy, organization/team membership, branch rules, approvals, merge state, settings, audit history, and idempotency records.
- Application integrity: frontend assets, API binaries, migrations, dependency graph, CI credentials, releases, and container images.
- User trust in HubGit's identity and the distinction between HubGit and GitHub.

## Threat Actors

- Anonymous internet attacker.
- Authenticated user attempting horizontal or vertical privilege escalation.
- Malicious repository contributor controlling names, Git data, Markdown, patches, assets, workflow logs, or webhook payloads.
- Compromised or malicious configured provider.
- Attacker with read access to logs, backups, CI artifacts, browser history, or local reference captures.
- Supply-chain attacker affecting a dependency, package registry, build action, or container base.
- Operator or administrator making an unsafe configuration change.

## Configurable Branding and Authentication Controls

Branding is tenant or deployment configuration. It may change the product name,
logo, colors, favicon, support and policy links, and authentication explanation,
but it must not change security semantics. Safe defaults use HubGit's original
identity, do not load third-party fonts or analytics, and keep provider names
explicit in explanatory copy. Logo and policy URLs are validated as safe HTTPS or
same-origin URLs and active-content sources are rejected.

Every authentication, registration, recovery, second-factor, and provider-
connection route identifies the configured product and explains whether the
operation is a local HubGit sign-in or a provider redirect. Forms accept only
HubGit-local credentials. A GitHub connection is redirect-only: the API creates
an OAuth authorization request, validates single-use state on callback, and exchanges
the code server-side. No HubGit form accepts a GitHub password, token,
passkey, recovery code, session cookie, SSH key, or OAuth device code.

No credential-page form action, image beacon, analytics call, font request,
error-reporting payload, or redirect may send input to an unconfigured host.
Return URLs are same-origin relative paths selected from an allowlist, and
authentication errors never echo credentials or provider response bodies.
Automated acceptance tests cover each configured branding preset, auth route,
outbound host, password-manager identifier, and redirect destination.

## Threat Register

| ID | Threat | Impact | Required controls | Verification |
| --- | --- | --- | --- | --- |
| AUTH-01 | Configured branding or provider copy is mistaken for a provider login and captures real credentials. | Critical credential compromise and user deception. | Safe HubGit defaults, explicit configured-product identity, local-only account wording, redirect-only GitHub OAuth, no provider password/token fields, no unapproved third-party requests. | Playwright auth-route matrix and outbound-host/redirect assertions. |
| AUTH-02 | Session theft through XSS or insecure cookies. | Account takeover. | HTTP-only, Secure production cookie; SameSite; CSP; output encoding; sanitized Markdown; no tokens in local/session storage. | Cookie/header tests, XSS corpus, CSP test. |
| AUTH-03 | CSRF performs issue, merge, settings, or admin mutations. | Unauthorized state change. | Per-session CSRF value, Origin allowlist, SameSite cookie, unsafe-method enforcement, no state-changing GET. | Cross-origin integration tests. |
| AUTH-04 | Login, recovery, or registration enumerates accounts. | Privacy loss and targeted attack. | Uniform outward response, bounded timing, rate limits keyed by network and account, no identity in logs. | Enumeration timing/status tests. |
| AUTH-05 | Weak password storage or token lifetime. | Offline compromise or durable takeover. | Argon2id with reviewed parameters, unique salts, token hashing, rotation, short-lived one-use recovery/verification tokens, session revocation. | Configuration/unit tests and security review. |
| AUTH-06 | Open redirect after login or provider connection. | Phishing and token leakage. | Same-origin relative return paths, canonical parsing, allowlisted provider callback destinations. | Encoded/ambiguous URL test corpus. |
| ACCESS-01 | IDOR exposes private repositories or collaboration objects. | Private source disclosure. | Resource authorization per operation, opaque IDs treated only as locators, concealment policy, adapter reauthorization. | Cross-persona contract suite. |
| ACCESS-02 | Search, counts, notifications, SSE, or timing reveals private-resource existence. | Metadata disclosure. | Permission-filter before aggregation and event delivery; no private totals; equivalent concealed errors; cache partition by identity. | Guest/forbidden differential tests. |
| ACCESS-03 | Capability flags are treated as authorization. | Privilege escalation. | Separate capability and permission documents; server authorization on every operation. | Adapter conformance tests. |
| ACCESS-04 | Admin routes or fields appear through client-only gating. | Administrative compromise. | Server-enforced administrator role, narrow schemas, audit logs, reauthentication for sensitive actions. | Non-admin API and direct-route tests. |
| ACCESS-05 | A cached private response is served to a different subject or after authorization is revoked. | Private source or metadata disclosure. | Cache key includes tenant, provider, repository, contract version, and authorization subject; purge on revocation; fail closed on an authorization miss. | Cross-user cache isolation and revocation tests. |
| INPUT-01 | Stored/reflected XSS through Markdown, code, filenames, diffs, logs, SVG, or metadata. | Session and data compromise. | Contextual React escaping, allowlist sanitizer, raw HTML disabled by default, untrusted SVG download/sandbox, CSP, safe code rendering. | OWASP XSS corpus and upload tests. |
| INPUT-02 | Command, path, or argument injection through Git refs, archive paths, or filenames. | Server compromise or arbitrary file access. | Dulwich/library APIs, no shell interpolation, canonical path validation, traversal rejection, safe temporary directories. | Fuzz/property tests. |
| INPUT-03 | SSRF through avatars, webhooks, imports, submodules, release assets, or provider URLs. | Internal network and credential exposure. | Egress policy, URL validation, DNS/IP recheck, blocked private/link-local ranges, size/time limits, explicit admin allowlists. | SSRF redirect/DNS rebinding suite. |
| INPUT-04 | Malicious archive or upload causes traversal, decompression bomb, or content sniffing. | File overwrite or denial of service. | Stream limits, safe filenames, no unsafe extraction, type/disposition headers, archive entry validation, quotas. | Malformed archive and large-stream tests. |
| PROVIDER-01 | Provider token leaks to browser, log, error, trace, or URL. | Provider account compromise. | Server-side encrypted custody, header-only use, structured redaction, schema allowlists, query-string prohibition. | Secret canary scans across responses/logs/traces. |
| PROVIDER-02 | Compromised provider returns malicious or inconsistent data. | XSS, corruption, confused authorization. | Treat provider data as untrusted, validate schemas and sizes, escape output, fail closed on identity/permission ambiguity. | Malformed provider fixture suite. |
| PROVIDER-03 | Retry duplicates merge, release, comment, or workflow dispatch. | Integrity loss. | Idempotency keys, safe retry policy, provider request reconciliation, durable command record. | Timeout/replay tests. |
| PROVIDER-04 | Provider rate limit or outage causes retry storm. | Denial of service. | Bounded exponential backoff with jitter, circuit breaker, Retry-After support, polling caps, visible degraded state. | Failure-injection load tests. |
| GIT-01 | Stale UI overwrites settings, refs, or review state. | Integrity loss. | ETag/If-Match, expected head/base SHA, explicit 409/412 recovery, preserved form input. | Concurrent mutation tests. |
| GIT-02 | Merge or review applies to an unexpected head commit. | Supply-chain/code integrity failure. | Display and submit expected head SHA, invalidate approvals as policy requires, re-evaluate rules and checks at command time. | Head-change race tests. |
| GIT-03 | Crafted diff exhausts memory/CPU or mispositions review comments. | DoS or review integrity loss. | Size/time/hunk caps, streaming/virtualization, truncation flags, canonical line-position model, server validation. | Large/adversarial diff tests. |
| EVENT-01 | SSE crosses users, survives logout, or leaks full sensitive objects. | Private data disclosure. | Session-bound stream, authorization per event, invalidation-only payloads, connection limits, close on revocation. | Multi-user and logout tests. |
| EVENT-02 | Replay or ordering gap leaves stale authorization state. | Incorrect UI/security decisions. | Opaque ordered event IDs, bounded replay, `resync`, client refetch; UI never authorizes. | Reconnect/gap tests. |
| OFFLINE-01 | Offline mode applies a mutation or extends access beyond the authorization grace window. | Unauthorized state change or stale private-data disclosure. | Read-only cached responses, bounded last-authorization window, revocation invalidation, no queue/retry/command replay, visible stale state. | Offline expiry, revocation, and mutation rejection tests. |
| OPS-01 | Logs/backups/reference captures contain secrets or private data. | Durable disclosure. | Redaction, minimization, encrypted backups, retention rules, local-only clean-room captures, access controls. | Canary secret and artifact scans. |
| OPS-02 | Dependency or CI compromise injects malicious assets. | Broad application compromise. | Lockfiles, checksum verification, least-privilege CI, pinned actions/images, dependency/license/SBOM review, signed releases where possible. | CI policy and reproducible-build checks. |
| OPS-03 | Destructive UI action is accidental or clickjacked. | Repository or account loss. | CSP `frame-ancestors`, confirmation naming target, reauthentication for high risk, authorization recheck, audit record, idempotency. | E2E confirmation and framing tests. |

## Browser Security Baseline

Production responses must establish:

- TLS with secure cookies and HSTS at the deployment edge.
- A restrictive Content Security Policy with no `unsafe-eval`; nonces or hashes for necessary scripts; narrow `connect-src`; `frame-ancestors 'none'`; and provider/avatar hosts explicitly reviewed.
- `X-Content-Type-Options: nosniff`, strict referrer policy, a conservative permissions policy, and anti-framing protection.
- No third-party analytics or remote fonts on authentication pages.
- Trusted Types where browser support and framework integration permit it.
- Uploaded active content served from a separate origin or forced to download when practical.

Markdown links receive safe `rel` attributes and visually disclose external destinations. Syntax highlighting and Markdown processing occur with bounded input and no execution of repository code.

## API and Data Controls

- Validate request types, maximum sizes, enum values, cursor structure, ref/path syntax, and mutually dependent fields at the boundary.
- Apply object-level authorization after lookup and before serialization.
- Partition caches by authorization context; private responses are never publicly cacheable.
- Cache per repository only after an authorized read, with tenant/provider/subject-aware keys, bounded TTL and size, encryption or filesystem permissions appropriate to the deployment, and purge on logout, revocation, repository transfer, or provider disconnect.
- Allow an offline client to read previously authorized cached data only within the configured authorization window. Offline reads are visibly stale and no offline mutation, retry queue, or command replay is supported.
- Use transactions for multi-resource mutations and durable idempotency records for retry-sensitive commands.
- Return stable problem codes without stack traces, SQL text, filesystem paths, provider bodies, secrets, or private identifiers.
- Rate-limit authentication, search, diff generation, archive generation, uploads, provider connection, workflow control, and administrative operations separately.
- Store secret values encrypted with a deployment-managed key; return only metadata such as name and update time.
- Record security-relevant audit events with actor, action, target, outcome, request correlation ID, and timestamp, excluding content and secrets.

## Abuse and Availability Limits

Set configurable bounds for request bodies, Markdown, comments, filenames, tree entries, diff files/hunks/lines, code rendering, uploads, archive size, workflow log chunks, SSE connections, search complexity, pagination depth, and concurrent provider calls. Limit failures must return a clear safe state with truncation metadata where partial display is valid.

The frontend must virtualize large views without implying that truncated data is complete. The backend must enforce limits independently of the frontend.

## Privacy and Retention

- Seed and test data are synthetic.
- Authentication attempts, IP-derived rate-limit keys, audit data, logs, and provider metadata have documented retention periods.
- Deletion and transfer workflows state what is immediate, queued, retained for recovery, or controlled by the provider.
- Local clean-room references follow `clean-room-protocol.md` and never enter repository history or CI artifacts.
- Security advisory data receives the strictest repository permission and logging rules.

## Security Verification Gates

Release gates include:

- Cross-persona authorization and private-resource non-disclosure tests for every resource family.
- CSRF, CORS/origin, cookie, session fixation, session revocation, recovery, rate-limit, and open-redirect tests.
- Stored/reflected XSS corpus across Markdown, filenames, diffs, logs, assets, releases, wiki, discussions, and search.
- Path traversal, ref injection, SSRF, malicious redirect, content-sniffing, large-input, and malformed-provider tests.
- ETag race, expected-head merge/review, idempotency replay, SSE cross-user/reconnect, and provider failure tests.
- Secret scanning of source, history, build output, containers, logs, screenshots, traces, and test artifacts.
- Dependency vulnerability, license, SBOM, container, and infrastructure configuration review.
- Manual review of every configured authentication route at all required viewports and themes, including redirect-only GitHub authentication and custom branding identity.

## Incident Handling

Credential exposure requires immediate revocation, session invalidation, provider-token rotation, artifact removal, scope analysis, and user/operator notification appropriate to the deployment. Private-data or provenance incidents additionally follow the clean-room incident procedure. Security fixes receive regression tests that exercise the original failure without retaining real secrets or private data.

## Residual Risks

Custom branding can still confuse users if operators choose a provider-like name,
logo, or domain. Deployments should retain the original HubGit identity for
public or untrusted audiences and review every custom asset and redirect. Real
provider behavior and version differences can create semantic gaps; unsupported
operations must fail visibly and safely. A compromised host or deployment
encryption key can expose server-held credentials and requires operational
controls beyond application code. Offline windows reduce availability impact;
they do not make cached data current or authorize a command.
