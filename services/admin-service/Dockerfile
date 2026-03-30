# ── Stage 1: Install Python packages ──────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /install

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 2: Lean runtime image ────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="paycrest-team"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Create non-root user + install curl for healthcheck
RUN groupadd -r appgroup && useradd -r -g appgroup appuser \
 && apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy app source (owned by appuser)
COPY --chown=appuser:appgroup app ./app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# NOTE: PORT env var in .env is for the API Gateway to CALL this service,
# not what uvicorn binds to. Uvicorn always binds to 8000 here.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
