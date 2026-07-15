# ── Stage 1: grab the uv binary ──────────────────────────────────
FROM ghcr.io/astral-sh/uv:0.5 AS uv

# ── Stage 2: runtime ─────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="StanS"
LABEL description="Multi-agent content generation framework"

WORKDIR /app

# Copy uv binary from builder
COPY --from=uv /uv /uvx /bin/

# Install dependencies (cached layer — only rebuilds when lock changes)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-cache --no-install-project

# Copy application code, then install the project itself
COPY src/ ./src/
COPY personas/ ./personas/
RUN uv sync --frozen --no-dev --no-cache

# Create non-root user; only the output dir needs to be writable
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/output \
    && chown appuser:appuser /app/output

USER appuser

# Default: run the factory CLI (venv python directly — no package
# manager needed at runtime, keeps the image immutable for appuser)
CMD ["/app/.venv/bin/python", "-m", "crewai_factory"]
