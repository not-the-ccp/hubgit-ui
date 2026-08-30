# Third-Party Notices

HubGit is an independent project. GitHub, the GitHub logo, and related marks are trademarks of GitHub, Inc. Their appearance in documentation as names of reference products does not imply sponsorship or endorsement.

This file records the planned direct dependency inventory. The package lockfiles and generated software bill of materials are authoritative for the exact dependencies and versions included in a release. Release automation must regenerate and review the license inventory before distribution.

## Primer and Octicons

HubGit uses or plans to use the following projects from GitHub's open-source Primer design system:

| Project | Source | License |
| --- | --- | --- |
| Primer React | <https://github.com/primer/react> | MIT |
| Primer CSS | <https://github.com/primer/css> | MIT |
| Primer Primitives | <https://github.com/primer/primitives> | MIT |
| Octicons | <https://github.com/primer/octicons> | MIT |

Copyright GitHub, Inc. and contributors.

Only material obtained from these canonical licensed projects and installed package artifacts may be used. GitHub-served proprietary application bundles, logos, fonts, illustrations, screenshots, and other brand assets are not part of HubGit.

## Planned Web Dependencies

| Project | Source | License |
| --- | --- | --- |
| React and React DOM | <https://github.com/facebook/react> | MIT |
| React Router | <https://github.com/remix-run/react-router> | MIT |
| Vite | <https://github.com/vitejs/vite> | MIT |
| TanStack Query | <https://github.com/TanStack/query> | MIT |
| TanStack Virtual | <https://github.com/TanStack/virtual> | MIT |
| React Hook Form | <https://github.com/react-hook-form/react-hook-form> | MIT |
| Zod | <https://github.com/colinhacks/zod> | MIT |
| Shiki | <https://github.com/shikijs/shiki> | MIT |
| CodeMirror | <https://github.com/codemirror> | MIT |
| react-markdown | <https://github.com/remarkjs/react-markdown> | MIT |
| remark-gfm | <https://github.com/remarkjs/remark-gfm> | MIT |
| DOMPurify | <https://github.com/cure53/DOMPurify> | Apache-2.0 OR MPL-2.0 |
| Storybook | <https://github.com/storybookjs/storybook> | MIT |
| Vitest | <https://github.com/vitest-dev/vitest> | MIT |
| Testing Library | <https://github.com/testing-library> | MIT |
| Mock Service Worker | <https://github.com/mswjs/msw> | MIT |
| Playwright | <https://github.com/microsoft/playwright> | Apache-2.0 |
| pnpm | <https://github.com/pnpm/pnpm> | MIT |

## Planned API and Data Dependencies

| Project | Source | License |
| --- | --- | --- |
| Python | <https://github.com/python/cpython> | Python Software Foundation License Version 2 |
| FastAPI | <https://github.com/fastapi/fastapi> | MIT |
| Pydantic | <https://github.com/pydantic/pydantic> | MIT |
| SQLAlchemy | <https://github.com/sqlalchemy/sqlalchemy> | MIT |
| Alembic | <https://github.com/sqlalchemy/alembic> | MIT |
| Uvicorn | <https://github.com/encode/uvicorn> | BSD-3-Clause |
| Dulwich | <https://github.com/jelmer/dulwich> | Apache-2.0 OR GPL-2.0-or-later |
| argon2-cffi | <https://github.com/hynek/argon2-cffi> | MIT |
| SQLite | <https://sqlite.org/copyright.html> | Public domain |
| uv | <https://github.com/astral-sh/uv> | Apache-2.0 OR MIT |

Transitive dependencies, optional extras, syntax grammars, generated clients, container bases, and CI actions may carry additional notices. They must be included in the release license report when actually distributed.

## MIT License Text

The following text applies to the MIT-licensed components listed above, subject to each project's own copyright notice:

> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Other License Texts

Full license texts and required copyright notices for Apache-2.0, MPL-2.0, BSD-3-Clause, Python, GPL alternatives when selected, and all transitive dependencies are supplied by their packages and must be collected into each distributable release. Dependency license choices that offer alternatives should be documented in the release manifest; HubGit should select permissive alternatives where the package permits that choice and the distribution satisfies their conditions.

## Review Procedure

Before a release:

1. Generate an inventory from the resolved pnpm and uv lockfiles, container images, bundled assets, syntax grammars, and CI/release tooling.
2. Compare the inventory with this file and add missing licenses, copyright notices, and attribution requirements.
3. Confirm that no dependency marked unknown, proprietary, source-available-only, or license-incompatible is distributed.
4. Confirm that no GitHub-served proprietary bundle, source map, screenshot, font, logo, or private capture is present.
5. Include the applicable license texts and notices with source and binary distributions.

This notice is informational and does not replace the terms included with each dependency.
