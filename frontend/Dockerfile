# (c) 2026 AgentFlow-Eval / 李凯昕
# Frontend multi-stage: Vite build + nginx reverse-proxy to backend
# Production twin: Dockerfile.frontend (exposes 8080 for non-root)

# ---- Build stage ----
FROM node:22-alpine AS builder

WORKDIR /build

ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Runtime stage (nginx) ----
FROM nginx:1.27-alpine AS runtime

LABEL org.opencontainers.image.title="AgentFlow-Eval Frontend" \
      org.opencontainers.image.version="1.0.0"

COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint-af.sh
RUN chmod +x /docker-entrypoint-af.sh \
    && chown -R nginx:nginx /usr/share/nginx/html

# Entrypoint needs root to rewrite conf + write runtime-config; nginx workers drop privileges.
# For fully non-root images use Dockerfile.frontend (port 8080).
ENV API_KEYS=""

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/health || exit 1

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint-af.sh"]
