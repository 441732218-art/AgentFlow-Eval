# (c) 2026 AgentFlow-Eval
# Frontend multi-stage Dockerfile

# ---- Build stage ----
FROM node:22-alpine AS builder

WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm ci --omit=dev

COPY . .
RUN npm run build

# ---- Runtime stage (nginx) ----
FROM nginx:1.27-alpine AS runtime

# Copy built assets
COPY --from=builder /build/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
