FROM node:22.22-alpine AS build
WORKDIR /workspace
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/contracts/package.json packages/contracts/package.json
COPY packages/fixtures/package.json packages/fixtures/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web apps/web
COPY packages packages
RUN pnpm --filter @hubgit/web build

FROM node:22.22-alpine AS runtime
WORKDIR /workspace
ENV NODE_ENV=production PORT=3000
RUN corepack enable && addgroup -S hubgit && adduser -S -G hubgit hubgit
COPY --from=build --chown=hubgit:hubgit /workspace/node_modules ./node_modules
COPY --from=build --chown=hubgit:hubgit /workspace/apps/web/node_modules ./apps/web/node_modules
COPY --from=build --chown=hubgit:hubgit /workspace/apps/web/build ./apps/web/build
COPY --from=build --chown=hubgit:hubgit /workspace/apps/web/package.json ./apps/web/package.json
COPY --from=build --chown=hubgit:hubgit /workspace/apps/web/server.mjs ./apps/web/server.mjs
USER hubgit
WORKDIR /workspace/apps/web
EXPOSE 3000
CMD ["node", "server.mjs"]

