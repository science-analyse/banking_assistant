# AI Banking Assistant - Multi-Stage Production Dockerfile
# Version 2.0.0 with Security and Performance Optimizations

# =============================================================================
# ARGUMENTS AND BASE CONFIGURATION
# =============================================================================

ARG PYTHON_VERSION=3.11
ARG ALPINE_VERSION=3.19
ARG POETRY_VERSION=1.7.1

# =============================================================================
# STAGE 1: Base Python Image with System Dependencies
# =============================================================================

FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS python-base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies
RUN apk add --no-cache \
    # Build dependencies
    build-base \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    # PostgreSQL dependencies
    postgresql-dev \
    postgresql-client \
    # Git for version control
    git \
    # Curl for health checks
    curl \
    # Additional utilities
    bash \
    tzdata \
    && rm -rf /var/cache/apk/*

# Set timezone
ENV TZ=Asia/Baku
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create application user for security
RUN addgroup -g 1000 -S appgroup && \
    adduser -u 1000 -S appuser -G appgroup

# =============================================================================
# STAGE 2: Poetry Dependencies Builder
# =============================================================================

FROM python-base AS poetry-base

# Install Poetry
RUN pip install poetry==$POETRY_VERSION

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set work directory
WORKDIR /app

# Copy Poetry configuration
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# =============================================================================
# STAGE 3: Requirements-based Dependencies (Alternative to Poetry)
# =============================================================================

FROM python-base AS requirements-base

# Set work directory
WORKDIR /app

# Copy requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# STAGE 4: Development Image
# =============================================================================

FROM requirements-base AS development

# Install development dependencies
COPY requirements-dev.txt* ./
RUN if [ -f requirements-dev.txt ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

# Install development tools
RUN apk add --no-cache \
    vim \
    nano \
    htop \
    redis \
    && rm -rf /var/cache/apk/*

# Copy application code
COPY --chown=appuser:appgroup . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/static /app/uploads && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Development command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "info"]

# =============================================================================
# STAGE 5: Production Build
# =============================================================================

FROM requirements-base AS production-build

# Copy source code
COPY . .

# Build static assets (if any)
RUN if [ -f package.json ]; then \
        apk add --no-cache nodejs npm && \
        npm ci --only=production && \
        npm run build && \
        rm -rf node_modules && \
        apk del nodejs npm; \
    fi

# Remove development files
RUN find . -name "*.pyc" -delete && \
    find . -name "__pycache__" -delete && \
    rm -rf .git .github .gitignore .env.example *.md \
           tests/ docs/ .pytest_cache/ .coverage \
           Dockerfile* docker-compose* .dockerignore

# =============================================================================
# STAGE 6: Production Runtime
# =============================================================================

FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS production

# Set environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    ENVIRONMENT=production \
    WORKERS=1 \
    WORKER_CLASS=uvicorn.workers.UvicornWorker

# Install only runtime dependencies
RUN apk add --no-cache \
    # Runtime dependencies
    postgresql-client \
    curl \
    bash \
    tzdata \
    # Security updates
    && apk upgrade \
    && rm -rf /var/cache/apk/*

# Set timezone
ENV TZ=Asia/Baku
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create application user
RUN addgroup -g 1000 -S appgroup && \
    adduser -u 1000 -S appuser -G appgroup

# Set work directory
WORKDIR /app

# Copy Python dependencies from build stage
COPY --from=production-build /usr/local/lib/python*/site-packages /usr/local/lib/python*/site-packages
COPY --from=production-build /usr/local/bin /usr/local/bin

# Copy application code from build stage
COPY --from=production-build --chown=appuser:appgroup /app .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/uploads /tmp && \
    chown -R appuser:appgroup /app /tmp && \
    chmod -R 755 /app && \
    chmod -R 777 /tmp

# Security hardening
RUN chmod 600 /etc/passwd /etc/group && \
    rm -rf /tmp/* /var/tmp/* /var/cache/apk/*

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check with improved reliability
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Production command with Gunicorn
CMD ["gunicorn", "main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "1", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--keep-alive", "2", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--preload", \
     "--log-level", "warning", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

# =============================================================================
# STAGE 7: Security Scanner (Optional)
# =============================================================================

FROM production AS security-scan

# Switch back to root for security scanning
USER root

# Install security scanning tools
RUN apk add --no-cache \
    bandit \
    safety \
    && rm -rf /var/cache/apk/*

# Run security scans
RUN bandit -r . -f json -o /tmp/bandit-report.json || true
RUN safety check --json --output /tmp/safety-report.json || true

# Copy scan results
COPY --from=security-scan /tmp/*-report.json /app/security-reports/

# Switch back to app user
USER appuser

# =============================================================================
# STAGE 8: Testing Image
# =============================================================================

FROM development AS testing

# Install testing dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov httpx[testing]

# Copy test files
COPY tests/ ./tests/

# Run tests
RUN python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term

# =============================================================================
# MULTI-ARCH BUILD SUPPORT
# =============================================================================

# Build for multiple architectures
# docker buildx build --platform linux/amd64,linux/arm64 -t banking-assistant .

# =============================================================================
# BUILD ARGUMENTS AND LABELS
# =============================================================================

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL maintainer="Banking Assistant Team" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="AI Banking Assistant" \
      org.label-schema.description="AI-powered banking assistant for Azerbaijan" \
      org.label-schema.url="https://github.com/your-repo/banking-assistant" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/your-repo/banking-assistant" \
      org.label-schema.vendor="Banking Assistant Team" \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0"

# =============================================================================
# BUILD INSTRUCTIONS
# =============================================================================

# Development Build:
# docker build --target development -t banking-assistant:dev .

# Production Build:
# docker build --target production -t banking-assistant:latest .

# Build with Build Args:
# docker build \
#   --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
#   --build-arg VCS_REF=$(git rev-parse --short HEAD) \
#   --build-arg VERSION=$(git describe --tags --always) \
#   --target production \
#   -t banking-assistant:latest .

# Multi-architecture Build:
# docker buildx build \
#   --platform linux/amd64,linux/arm64 \
#   --target production \
#   -t banking-assistant:latest \
#   --push .

# Security Scan:
# docker build --target security-scan -t banking-assistant:scan .

# Testing:
# docker build --target testing -t banking-assistant:test .

# =============================================================================
# OPTIMIZATION NOTES
# =============================================================================

# 1. Multi-stage builds reduce final image size
# 2. Alpine Linux provides security and small footprint
# 3. Non-root user improves security
# 4. Layer caching optimizes build times
# 5. Health checks ensure container reliability
# 6. Production optimizations for performance
# 7. Security scanning for vulnerability detection

# =============================================================================
# SECURITY CONSIDERATIONS
# =============================================================================

# 1. Regular base image updates
# 2. Minimal attack surface with Alpine
# 3. Non-privileged user execution
# 4. Read-only root filesystem (can be enabled)
# 5. Security scanning integration
# 6. Secrets management (never in image)
# 7. Resource limits and constraints
# 8. Network security policies

# =============================================================================
# MAINTENANCE
# =============================================================================

# 1. Automated security updates
# 2. Dependency vulnerability scanning
# 3. Image size monitoring
# 4. Performance benchmarking
# 5. Regular base image updates
# 6. Container resource optimization
# 7. Log aggregation and monitoring