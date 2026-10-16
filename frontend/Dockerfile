# Multi-stage build for the Expense Tracker frontend.
#
#   docker build -t ghcr.io/om-malviya/expense-tracker-frontend:local frontend
#   docker run -p 3000:8080 -e BACKEND_HOST=host.docker.internal ghcr.io/om-malviya/expense-tracker-frontend:local
#
# Stage 1 compiles the React app with Node; stage 2 serves the static output with
# nginx. Splitting them keeps Node, npm and node_modules (hundreds of MB and a
# large CVE surface) out of the image that actually runs in production.

# ---------- Stage 1: build ----------
FROM node:22-alpine AS build
WORKDIR /app

# Copy the lockfile first so the dependency layer is cached between builds and
# only invalidated when package.json / package-lock.json change.
COPY package.json package-lock.json ./
# `npm ci` installs exactly what the lockfile says (reproducible builds) and
# refuses to run if the lockfile is out of sync with package.json.
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

# ---------- Stage 2: runtime ----------
# The "unprivileged" nginx variant already runs as uid 101 and listens on 8080,
# which satisfies the non-root requirement without any extra setup.
# 1.30-alpine is the current stable line; older 1.27 Alpine builds carried
# fixable HIGH OS CVEs that would fail the Trivy gate in CI.
FROM nginxinc/nginx-unprivileged:1.30-alpine

# Defaults for the envsubst template. docker-compose and the Helm chart override
# these with the real backend service name for their environment.
ENV BACKEND_HOST=expense-tracker-backend \
    BACKEND_PORT=8000

COPY --from=build /app/dist /usr/share/nginx/html

# The image entrypoint renders every /etc/nginx/templates/*.template into
# /etc/nginx/conf.d/ with envsubst before starting nginx.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# The base image already switches to 101; declaring it again makes the intent
# explicit for reviewers and for scanners that check for a USER instruction.
USER 101

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
