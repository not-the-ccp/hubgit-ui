# HubGit UI

HubGit is a provider-neutral, self-hosted Git collaboration frontend. The
project aims to reproduce the familiar density and workflows of GitHub using a
clean-room implementation, a deterministic mock provider, and a generic REST
contract that can also be implemented by GitHub, Forgejo, Gitea, or another Git
service.

The first development milestone is a broad mock-backed application. The initial
GitHub adapter now implements redirect-only login plus repository list, detail,
and tree reads; all other GitHub feature families remain capability-gated while
their provider-neutral implementations are built. Deployed instances can replace the product name,
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
as a local Git clone. The offline private cache is not implemented yet; its
contract requires authorization-aware reads during a bounded window and never
permits offline mutations.
Operators should initially run HubGit on a trusted network or behind an
access-controlled reverse proxy. See [deployment and operations](docs/deployment-and-operations.md).

## Development

Requirements are Node.js 22+, pnpm 10+, Python 3.13+, and uv.

```bash
pnpm install
uv sync --project apps/api --all-extras
pnpm dev
```

For an isolated local stack, build and start both services with:

```bash
docker compose up --build
```

The defaults expose the web application at `http://localhost:3000` and the API
at `http://localhost:8000`. Production deployments must set an HTTPS public
base URL, secure cookies, disable the seeded mock user, and place private data
on protected persistent storage. The API rejects an unsafe production
configuration at startup.

## License

HubGit is licensed under the MIT License. See `THIRD_PARTY_NOTICES.md` for
third-party components and their licenses.
