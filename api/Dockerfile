# Multi-stage Dockerfile for JMIE FastAPI Application
# Supports multi-platform builds: linux/amd64, linux/arm64
# Production-optimized with minimal image size and security best-practices

# ===== Stage 1: Dependency Builder =====
FROM python:3.12-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy monorepo configuration files
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies
# Using --frozen to ensure exact version reproducibility
RUN uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python --frozen -e .

# Install production dependencies (without dev dependencies)
RUN uv pip install --python /opt/venv/bin/python --frozen \
    fastapi \
    uvicorn[standard] \
    pydantic \
    pydantic-settings \
    sqlalchemy \
    asyncpg \
    bcrypt \
    python-multipart \
    qdrant-client \
    structlog \
    opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-exporter-trace-otlp \
    opentelemetry-instrumentation-fastapi \
    opentelemetry-instrumentation-sqlalchemy \
    opentelemetry-instrumentation-requests

# ===== Stage 2: Runtime =====
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Copy application source code
COPY --chown=appuser:appuser . /app

# Ensure venv is in PATH
ENV PATH="/opt/venv/bin:$PATH"

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Healthcheck - verify API is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI application with Uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--access-log"]
