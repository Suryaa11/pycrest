# ── Stage 1: Build Vite/React app ─────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy manifests first so npm install is cached unless deps change
COPY package*.json ./
RUN npm ci --frozen-lockfile

# Copy source and build
COPY . .
RUN npm run build
# Output is in /app/dist

# ── Stage 2: Serve with Nginx ──────────────────────────────────
FROM nginx:1.27-alpine AS runtime

LABEL maintainer="paycrest-team"

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
