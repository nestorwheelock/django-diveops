# Django DiveOps Deployment Architecture

Technical reference for understanding and working with the production deployment pipeline.

## Overview

Django DiveOps deploys to a VPS using Docker containers orchestrated by docker-compose, with GitHub Actions handling CI/CD. Nginx serves as the reverse proxy with SSL termination.

**Production Domains**: `happydiving.mx` (English), `buceofeliz.com` (Spanish)

## Request Flow

```
Internet Request
       │
       ▼
┌──────────────────┐
│   Nginx (443)    │  ← SSL termination, security headers
│   nginx:alpine   │
└────────┬─────────┘
         │
         ├── /static/* → Served directly from volume (1yr cache)
         ├── /media/*  → Served directly from volume (1d cache)
         ├── /health/  → Proxied (no rate limit)
         └── /*        → Proxied with headers
                │
       ┌────────┴────────┐
       │  Docker Network │  (diveops_network - internal)
       └────────┬────────┘
                │
                ▼
┌──────────────────────────┐
│   Django Web (8000)      │
│   Gunicorn + Django 5    │
│   4 workers, 2 threads   │
└────────┬─────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│Postgres│ │ Redis  │
│  5432  │ │  6379  │
└────────┘ └────────┘
```

## Container Architecture

### Production Containers

| Container | Image | Exposed Port | Purpose |
|-----------|-------|--------------|---------|
| `diveops_nginx_prod` | nginx:alpine | 80, 443 | Reverse proxy, SSL, static files |
| `diveops_web_prod` | ghcr.io/nestorwheelock/django-diveops | 8000 (internal) | Django application |
| `diveops_db_prod` | postgres:16-alpine | None (internal) | PostgreSQL database |
| `diveops_redis_prod` | redis:7-alpine | None (internal) | Cache and sessions |

### Docker Compose Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local development |
| `docker-compose.prod.yml` | Full production (4+ GB RAM) |
| `docker-compose.small.yml` | Small VPS (1 vCPU, 2 GB RAM) |

## GitHub Actions CI/CD

### Workflows

#### `ci.yml` - Continuous Integration

Triggered on every push to any branch.

```
Push → Checkout → Test → Lint → Build
                   │       │      │
                   │       │      └─ Docker image (not pushed)
                   │       └─ ruff, black, isort
                   └─ pytest with coverage
```

#### `deploy.yml` - Production Deployment

Triggered on push to `main` or manual dispatch.

```
1. Build Phase
   └─ Build Docker image
   └─ Tag: ghcr.io/nestorwheelock/django-diveops:latest
   └─ Push to GitHub Container Registry

2. Deploy Phase (SSH to VPS)
   └─ Pull image from registry
   └─ Copy docker-compose and nginx configs
   └─ Detect SSL certificates
   └─ Select nginx config (HTTPS or HTTP-only)
   └─ docker compose up -d --force-recreate
   └─ Wait for health check (60s timeout)
   └─ Run migrations
   └─ Collect static files
   └─ Prune old images
```

#### `setup-ssl.yml` - SSL Certificate Setup

Manual trigger to obtain Let's Encrypt certificates.

```
1. Copy init-ssl.sh to server
2. Run certbot for both domains
3. Store certs in volume
4. Switch nginx to HTTPS config
5. Enable SECURE_SSL_REDIRECT
6. Restart containers
```

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `SERVER_HOST` | VPS IP or hostname |
| `SERVER_USER` | SSH username |
| `SERVER_SSH_KEY` | Private SSH key for deployment |
| `GHCR_TOKEN` | GitHub Container Registry token |

## Configuration Files

### Settings Hierarchy

```
src/diveops/settings/
├── base.py      # Shared config (apps, middleware, templates)
├── dev.py       # DEBUG=True, local cache, console email
├── prod.py      # DEBUG=False, Redis cache, SMTP email, SSL
└── test.py      # Test database, in-memory cache
```

### Environment Variables (Production)

```bash
# Core Django
SECRET_KEY=<secure-random-key>
DEBUG=False
ALLOWED_HOSTS=happydiving.mx,buceofeliz.com
CSRF_TRUSTED_ORIGINS=https://happydiving.mx,https://buceofeliz.com

# Database
POSTGRES_DB=diveops
POSTGRES_USER=diveops
POSTGRES_PASSWORD=<secure-password>
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Cache
REDIS_URL=redis://redis:6379/0

# Email (SES or SMTP)
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=<username>
EMAIL_HOST_PASSWORD=<password>

# SSL
SECURE_SSL_REDIRECT=true

# Optional
AWS_ACCESS_KEY_ID=<for-s3-media>
AWS_SECRET_ACCESS_KEY=<for-s3-media>
SENTRY_DSN=<for-error-tracking>
```

## Nginx Configuration

### Production Config (`docker/nginx/nginx.conf`)

- HTTP (80) → Redirects to HTTPS
- HTTPS (443) → Proxies to Django
- Separate server blocks for each domain
- TLS 1.2/1.3 with modern ciphers
- HSTS enabled (1 year)

### Security Headers (`docker/nginx/conf.d/common.conf`)

```nginx
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
```

### Rate Limiting

- API endpoints: 10 requests/second per IP
- Health endpoint: No rate limiting

## Docker Build Process

### Production Dockerfile (`docker/Dockerfile`)

Multi-stage build:

```dockerfile
# Stage 1: Builder
FROM python:3.12-slim AS builder
- Install build tools
- Create virtualenv
- Install requirements
- Install django-primitives packages
- Install django-portal-ui

# Stage 2: Production
FROM python:3.12-slim
- Create non-root user (diveops)
- Copy virtualenv from builder
- Install runtime deps only
- Copy application code
- Run collectstatic
- Expose 8000
- CMD: gunicorn
```

### Entrypoint (`docker/entrypoint.sh`)

On container start:
1. Wait for PostgreSQL to be ready
2. Run migrations (if `MIGRATE=true`)
3. Create superuser (if credentials provided)
4. Start Gunicorn

## Volumes (Persistent Data)

| Volume | Mount Point | Purpose |
|--------|-------------|---------|
| `postgres_data_prod` | /var/lib/postgresql/data | Database files |
| `redis_data_prod` | /data | Cache persistence |
| `static_data_prod` | /app/staticfiles | Collected static files |
| `media_data_prod` | /app/media | User uploads |
| `logs_data_prod` | /app/logs | Application logs |
| `certs_data` | /etc/nginx/certs | SSL certificates |

## Health Checks

### Web Container
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 5s
```

### Database Container
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U diveops -d diveops"]
  interval: 10s
  timeout: 5s
  retries: 5
```

## Deployment Commands

### Deploy via GitHub Actions

Push to main branch or manually trigger `deploy.yml` workflow.

### Manual Deployment (SSH)

```bash
# SSH to server
ssh user@server

# Navigate to app directory
cd /opt/diveops

# Pull latest image
docker compose -f docker-compose.prod.yml pull

# Recreate containers
docker compose -f docker-compose.prod.yml up -d --force-recreate

# Run migrations
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Collect static files
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### View Logs

```bash
# All containers
docker compose -f docker-compose.prod.yml logs -f

# Specific container
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f nginx
```

### Database Operations

```bash
# Django shell
docker compose -f docker-compose.prod.yml exec web python manage.py shell

# Database shell
docker compose -f docker-compose.prod.yml exec db psql -U diveops -d diveops

# Backup
docker compose -f docker-compose.prod.yml exec db pg_dump -U diveops diveops > backup.sql
```

## Troubleshooting

### Container Won't Start

1. Check logs: `docker compose logs web`
2. Verify environment: `docker compose config`
3. Check health: `docker inspect diveops_web_prod | grep -A5 Health`

### Database Connection Failed

1. Verify db container running: `docker compose ps`
2. Check db logs: `docker compose logs db`
3. Test connection: `docker compose exec db pg_isready`

### Static Files 404

1. Verify collectstatic ran: `docker compose exec web ls /app/staticfiles`
2. Check nginx config: `docker compose exec nginx cat /etc/nginx/nginx.conf`
3. Check volume mount: `docker compose config | grep static`

### SSL Certificate Issues

1. Check cert existence: `ls /opt/diveops/certs/`
2. Verify nginx config uses correct paths
3. Run `setup-ssl.yml` workflow to regenerate

## Server Requirements

### Minimum (docker-compose.small.yml)
- 1 vCPU
- 2 GB RAM
- 20 GB disk

### Recommended (docker-compose.prod.yml)
- 2+ vCPU
- 4+ GB RAM
- 40+ GB disk
