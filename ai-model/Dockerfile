# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="devops@example.com"
LABEL description="AI Chat API – FastAPI wrapper for Ollama open-source LLM"
LABEL org.opencontainers.image.source="https://github.com/example/ai-chat-app"

# Runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash appuser

# Copy application source
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

# Healthcheck – polls the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 2 workers; tune via UVICORN_WORKERS env var
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2}"]
