# DiveOps

A comprehensive dive operations management system built on Django and the django-primitives ecosystem.

## Features

- **Diver Management**: Track diver profiles, certifications, and medical clearances
- **Booking System**: Manage dive excursions, bookings, and rosters
- **CRM**: Lead management, conversations, and customer communications
- **Agreements**: Digital waivers and liability agreements with e-signatures
- **Medical Questionnaires**: RSTC medical form processing and clearance tracking
- **Invoicing**: Generate and manage invoices for dive services
- **E-commerce**: Online store for dive gear and courses

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Development Setup

1. Clone the repository with submodules:
   ```bash
   git clone --recursive https://github.com/your-org/django-diveops.git
   cd django-diveops
   ```

2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

3. Start the development containers:
   ```bash
   make up
   ```

4. Run migrations:
   ```bash
   make migrate
   ```

5. Create a superuser:
   ```bash
   make createsuperuser
   ```

6. Access the application:
   - Admin: http://localhost:8000/admin/
   - Staff Portal: http://localhost:8000/staff/diveops/
   - Customer Portal: http://localhost:8000/portal/

### Running Tests

```bash
make test
```

### Code Quality

```bash
make lint    # Check code style
make format  # Auto-format code
```

## Architecture

DiveOps is built on the [django-primitives](https://github.com/your-org/django-primitives) ecosystem, which provides reusable Django packages for building business applications:

- **django-parties**: Person and organization management
- **django-catalog**: Product and service catalog
- **django-agreements**: Digital agreement and e-signature handling
- **django-questionnaires**: Form builder and response collection
- **django-documents**: Document management and storage
- **django-ledger**: Double-entry accounting
- **django-communication**: Messaging and conversations

## Project Structure

```
django-diveops/
├── src/diveops/           # Main Django project
│   ├── core/              # User model, middleware
│   ├── operations/        # Dive operations (main app)
│   ├── pricing/           # Pricing engine
│   ├── invoicing/         # Invoice generation
│   └── store/             # E-commerce
├── templates/             # Django templates
├── static/                # Static assets
├── lib/django-primitives/ # Git submodule
└── docker/                # Docker configuration
```

## Deployment

### Production with Docker Compose

1. Configure environment variables in `.env`
2. Build and start production containers:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Environment Variables

See `.env.example` for all available configuration options.

## License

Proprietary - All rights reserved.
# Deployed Sun Jan 11 11:28:32 PM EST 2026
