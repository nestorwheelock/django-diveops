# ================================
# Stage 1: Build dependencies
# ================================
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip

# Install requirements FIRST
COPY requirements/base.txt requirements/prod.txt ./
RUN pip install --no-cache-dir -r prod.txt

# Install django-primitives packages from submodule
# Use --no-deps to prevent PyPI lookups for inter-package dependencies
COPY lib/django-primitives/packages/ /tmp/packages/

RUN pip install --no-cache-dir --no-deps /tmp/packages/django-basemodels && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-singleton && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-sequence && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-modules && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-layers && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-money && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-parties && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-rbac && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-decisioning && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-audit-log && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-communication && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-catalog && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-encounters && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-worklog && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-geo && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-ledger && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-documents && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-notes && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-agreements && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-questionnaires && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-cms-core && \
    pip install --no-cache-dir --no-deps /tmp/packages/django-ai-services

# Install django-portal-ui from lib/ (not a submodule, part of main repo)
COPY lib/django-portal-ui/ /tmp/django-portal-ui/
RUN pip install --no-cache-dir --no-deps /tmp/django-portal-ui

# ================================
# Stage 2: Production image
# ================================
FROM python:3.12-slim as production

# Create non-root user
RUN groupadd -r diveops && useradd -r -g diveops diveops

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=diveops:diveops src/ ./src/
COPY --chown=diveops:diveops templates/ ./templates/
COPY --chown=diveops:diveops static/ ./static/
COPY --chown=diveops:diveops manage.py ./
COPY --chown=diveops:diveops docker/entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Create directories for runtime
RUN mkdir -p /app/staticfiles /app/media /app/logs && \
    chown -R diveops:diveops /app

# Collect static files
RUN DJANGO_SETTINGS_MODULE=diveops.settings.prod \
    SECRET_KEY=build-time-secret \
    POSTGRES_HOST=localhost \
    python manage.py collectstatic --noinput || true

USER diveops

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "diveops.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--access-logfile", "-", "--error-logfile", "-"]
