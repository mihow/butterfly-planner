# syntax=docker/dockerfile:1
#
# Multi-stage Dockerfile for Python applications using uv
#
# Build: docker build -t my-project .
# Run:   docker run --rm my-project
#

# =============================================================================
# Base stage: Python with uv
# =============================================================================
FROM python:3.12-slim AS base

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# =============================================================================
# Dependencies stage: Install dependencies
# =============================================================================
FROM base AS dependencies

# Copy files needed for build (pyproject.toml references README.md)
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Create virtual environment and install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv && \
    uv pip install --python=/opt/venv/bin/python .

# =============================================================================
# Development stage: For local development with hot reload
# =============================================================================
FROM base AS development

# Copy virtual environment from dependencies stage
COPY --from=dependencies /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code (needed for editable install)
COPY . .

# Install dev dependencies as editable
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -e ".[dev]"

# Default command for development
CMD ["pytest", "-v"]

# =============================================================================
# Test stage: Run tests
# =============================================================================
FROM development AS test

# Run tests during build to verify image
RUN pytest -v --tb=short

# =============================================================================
# Production stage: Minimal image for deployment
# =============================================================================
FROM python:3.12-slim AS production

# Create non-root user for security
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home app

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production

WORKDIR /app

# Copy virtual environment from dependencies stage
COPY --from=dependencies /opt/venv /opt/venv

# Copy application code
COPY --chown=app:app src/ ./src/

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "from my_project import __version__; print(__version__)" || exit 1

# Default command
CMD ["my-project", "info"]

# =============================================================================
# Labels
# =============================================================================
LABEL org.opencontainers.image.title="my-project" \
      org.opencontainers.image.description="A Claude-first Python application" \
      org.opencontainers.image.source="https://github.com/yourusername/my-project"
