"""Local development CLI."""

from __future__ import annotations

import argparse

import uvicorn

from .main import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the HubGit local mock API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    if args.reload:
        uvicorn.run("hubgit_api.main:app", host=args.host, port=args.port, reload=True)
    else:
        uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
