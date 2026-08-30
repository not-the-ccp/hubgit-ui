# Deployment and Operations

HubGit is designed for private self-hosting. The first real-provider profile is
GitHub, while the API contract remains provider-neutral so a Forgejo, Gitea, or
other adapter can be selected without changing the web application. Keep the
service, database, private cache, and provider connection on a trusted network
or behind an access-controlled reverse proxy.

## Configuration

Copy `.env.example` to an environment-specific secret store and set values
before starting the service. Do not commit the resulting file. At minimum,
production deployments must set a non-development environment, a persistent
database and data directory, secure cookies, an exact HTTPS origin allowlist, a
deployment-managed encryption key for provider credentials, and the GitHub
client secret through a file or secret manager.

Branding is fully configurable through the `HUBGIT_BRAND_*` settings. The safe
defaults use HubGit's original identity and do not load third-party fonts,
analytics, or remote active content. Custom logos and policy links must use
same-origin or reviewed HTTPS URLs. Product identity and authentication copy
must remain explicit about whether a user is signing in locally or being
redirected to GitHub.

## GitHub connection

GitHub authentication is redirect-only. The API starts an OAuth authorization-
code flow with PKCE, binds state and nonce to the HubGit session, validates the
callback against the configured redirect URI, and exchanges the code server-side.
No HubGit form accepts a GitHub password, token, passkey, recovery code, session
cookie, SSH key, or device code. Use the minimum provider scopes required by the
enabled ports and rotate the client secret through the deployment secret store.

The GitHub adapter is responsible for mapping provider responses to canonical
ports, preserving permission boundaries, reporting unsupported capabilities, and
redacting upstream errors. A provider URL or token must never be placed in a
browser response, log, cache key, query string, or redirect parameter.

## Private cache and offline behavior

The API may cache an authorized response automatically after a read and may
maintain a per-repository cache for expensive Git data. Cache keys include the
provider, tenant, repository, contract version, and authorization subject (or a
cryptographically equivalent authorization context). Entries have bounded TTL,
size, and content types; private responses are never publicly cacheable. Store
the cache on protected persistent storage, encrypt it when the threat model
requires, and purge it on logout, session revocation, provider disconnect,
repository transfer, or permission changes.

When the provider or network is unavailable, a user may see previously
authorized cached reads only during `HUBGIT_OFFLINE_AUTH_WINDOW_SECONDS`. The
interface marks those responses stale and the API fails closed after the window
or any revocation signal. Offline mode never creates a mutation queue, retries a
command, uploads data, merges, changes settings, or otherwise mutates a
repository or account. `HUBGIT_OFFLINE_MUTATIONS` must remain `false`; the API
must enforce that value independently of the client.

## Reverse proxy and runtime hardening

- Terminate TLS at a trusted edge, enable HSTS, and set secure, HTTP-only,
  SameSite cookies in production.
- Forward only the exact web origin and required API/SSE routes; do not expose
  the database, cache, provider endpoint, or secret files.
- Set a restrictive CSP, `frame-ancestors 'none'`, `nosniff`, a strict referrer
  policy, and a conservative permissions policy. Authentication pages do not
  use analytics or remote fonts.
- Run containers as a non-root user with a read-only filesystem where possible,
  drop Linux capabilities, use `no-new-privileges`, and mount only the data
  volume that the API needs.
- Back up the database and Git data with encryption and access controls. Test
  restore and provider-token rotation procedures; never place secrets in backup
  names or diagnostic output.
- Apply request, upload, archive, diff, search, SSE, and provider concurrency
  limits. Configure bounded retries only for safe/idempotent reads and honor
  provider rate limits.

The root `docker-compose.yml` describes these runtime boundaries, but the
repository currently has no application-owned Dockerfiles or API entrypoint.
Compose therefore references the future `apps/api/Dockerfile` and
`apps/web/Dockerfile` paths and is a deployment contract, not a runnable image
build until the application work adds those files. Do not add a substitute
entrypoint that bypasses API authorization or cache policy.

## Verification and change control

Pull requests run root pnpm checks, OpenAPI validation, Python compilation/tests,
secret scanning, dependency review, and JavaScript/Python dependency audits.
Run the cross-persona private-data, redirect, cache-isolation, offline-expiry,
revocation, and mutation-rejection suites before a production release. Record
the route evidence in the [route completion ledger](route-state-fidelity-matrix.md#route-completion-ledger).
