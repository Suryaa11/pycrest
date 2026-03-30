# ── Stage 1: Install prod dependencies ────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

COPY package*.json ./
# --omit=dev skips devDependencies (jest, eslint, etc.)
RUN npm ci --omit=dev --frozen-lockfile

# ── Stage 2: Runtime image ─────────────────────────────────────
FROM node:20-alpine AS runtime

LABEL maintainer="paycrest-team"

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Copy only production node_modules from the deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy application source (owned by appuser)
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1

# server.js is the entry point based on your existing Dockerfile
CMD ["node", "server.js"]
