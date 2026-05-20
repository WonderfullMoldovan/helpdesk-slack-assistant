# syntax=docker/dockerfile:1.7

# ============================================================
# Stage 1: Build — install dependencies in a virtualenv
# ============================================================
FROM python:3.11-slim AS builder

# Prevent Python from writing .pyc files (smaller image)
ENV PYTHONDONTWRITEBYTECODE=1
# Show Python output unbuffered (important for Docker logs)
ENV PYTHONUNBUFFERED=1
# Don't store pip cache in image
ENV PIP_NO_CACHE_DIR=1
# Don't check for new pip version on every command
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system build dependencies that some Python packages need
# (e.g., asyncpg compiles native extensions)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment inside the image
# (cleaner than installing into system Python)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Copy ONLY dependency manifest first — for layer caching
COPY pyproject.toml ./

# Install dependencies (without the project code itself yet)
# --no-deps because pyproject doesn't have a way to install "just deps"
# So we install deps via a temporary trick: install with a dummy app dir
RUN mkdir -p app && touch app/__init__.py \
    && pip install --upgrade pip setuptools wheel \
    && pip install .

# ============================================================
# Stage 2: Runtime — minimal image with only what's needed
# ============================================================
FROM python:3.11-slim AS runtime

# Same Python environment hygiene
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install only runtime system dependencies (not build tools)
# libpq5 is the runtime library for PostgreSQL client (used by asyncpg)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user to run the application
# Security best practice: never run containers as root
RUN groupadd --system app && useradd --system --gid app --create-home app

# Copy the virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set up application directory
WORKDIR /app

# Copy application code (owned by app user)
COPY --chown=app:app app ./app
COPY --chown=app:app pyproject.toml ./

# Drop root privileges
USER app

# Document which port the container listens on
# (this is metadata, doesn't actually open the port)
EXPOSE 8000

# Default command: run FastAPI with uvicorn
# --host 0.0.0.0 = listen on all interfaces inside container
# (not just localhost — otherwise Docker port mapping wouldn't work)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]