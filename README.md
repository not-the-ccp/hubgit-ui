# HubGit UI

HubGit is a provider-neutral, self-hosted Git collaboration frontend. The
project aims to reproduce the familiar density and workflows of GitHub using a
clean-room implementation, a deterministic mock provider, and a generic REST
contract that can also be implemented by GitHub, Forgejo, Gitea, or another Git
service.

The first development milestone is a broad mock-backed application. GitHub is
the first planned real provider for private self-hosting, while the application
ports remain provider-neutral. Deployed instances can replace the product name,
artwork, colors, authentication explanation, and policy links; safe defaults
retain the original HubGit identity and redirect-only provider authentication.

## Repository layout

- `apps/web` — React 19 frontend using React Router Framework Mode and Vite.
- `apps/api` — FastAPI service, SQLite persistence, and provider adapters.
- `packages/contracts` — checked-in OpenAPI contract and generated client.
- `packages/fixtures` — deterministic scenarios shared by API and browser tests.
- `docs` — architecture, deployment guidance, fidelity matrix, clean-room protocol, and threat model.

## Development status

HubGit is under active construction and is not ready for public deployment.
Private repository caching and real-provider credentials require the same care
as a local Git clone. Cached private reads are authorization-aware and available
offline only during a bounded window; offline mutations are never supported.
Operators should initially run HubGit on a trusted network or behind an
access-controlled reverse proxy. See [deployment and operations](docs/deployment-and-operations.md).

## Development

Requirements are Node.js 22+, pnpm 10+, Python 3.13+, and uv.

```bash
pnpm install
uv sync --project apps/api --all-extras
pnpm dev
```

For an isolated stack, use the Compose contract after application-owned
Dockerfiles and an API entrypoint have been added:

```bash
docker compose up --build
```

## License

HubGit is licensed under the MIT License. See `THIRD_PARTY_NOTICES.md` for
third-party components and their licenses.
