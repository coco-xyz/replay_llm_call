# Multi-stage build for optimized production image

# ================================
# Builder Stage
# ================================
FROM python:3.11-slim AS builder

# Build argument to control dev dependencies installation
ARG INSTALL_DEV=false

# Set environment variables for build stage
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

# Install system dependencies for building
# Only install development tools if INSTALL_DEV=true
RUN apt-get update && \
    if [ "$INSTALL_DEV" = "true" ]; then \
        apt-get install -y \
            build-essential \
            git \
            vim \
            htop \
            procps \
            curl; \
    else \
        apt-get install -y \
            build-essential \
            curl; \
    fi && \
    rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files and README (required by hatchling)
COPY pyproject.toml uv.lock README.md ./

# Install Python dependencies using UV with conditional dev dependencies
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        echo "Installing with dev dependencies..." && \
        uv sync --frozen; \
    else \
        echo "Installing without dev dependencies..." && \
        uv sync --frozen --no-dev; \
    fi

# ================================
# Runtime Stage
# ================================
FROM python:3.11-slim as runtime

# Build argument to control dev dependencies installation (for runtime tools)
ARG INSTALL_DEV=false

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH" \
    AI_AGENTS_DEBUG=false

# Install minimal runtime dependencies
RUN apt-get update && \
    if [ "$INSTALL_DEV" = "true" ]; then \
        apt-get install -y \
            curl \
            vim \
            htop \
            procps; \
    else \
        apt-get install -y \
            curl; \
    fi && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application source code with proper ownership
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser static/ ./static/
COPY --chown=appuser:appuser templates/ ./templates/
COPY --chown=appuser:appuser main.py ./

# Copy init scripts (optional directory)
COPY --chown=appuser:appuser initdb/ ./initdb/

# Create runtime directories with proper permissions
# Note: We create empty directories instead of copying existing logs
# to ensure containers start with clean state
RUN mkdir -p logs uploads && \
    chown -R appuser:appuser logs uploads && \
    chmod 755 logs uploads

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/v1/health || exit 1

# Start command
CMD ["python", "main.py", "--mode", "api"]