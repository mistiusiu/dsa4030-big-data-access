# syntax=docker/dockerfile:1

# ── STAGE 1: deps ────────────────────────────────────────────
FROM node:24-slim AS deps
RUN npm install -g corepack && corepack enable pnpm
WORKDIR /app/frontend
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# ── STAGE 2: development (vite dev server) ───────────────────
FROM deps AS development
COPY . .
EXPOSE 5173
CMD ["pnpm", "run", "dev", "--host", "0.0.0.0"]

# ── STAGE 3: build ───────────────────────────────────────────
FROM deps AS build
COPY . .
RUN pnpm run build

# ── STAGE 4: production (default) ────────────────────────────
# Unprivileged nginx serves the SPA and reverse-proxies /api and /admin to Django,
# so the browser talks to a single origin and no CORS is needed.
FROM nginxinc/nginx-unprivileged:alpine AS production
USER root
RUN rm -rf /etc/nginx/conf.d/*
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html
USER 101
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
