# Django DiveOps Development Instructions

You are developing a dive shop operations system. Follow these instructions exactly.

---

## PROJECT CONTEXT

**django-diveops** is a full-stack dive shop management system:

- **Backend:** Django 5.x with PostgreSQL, Django Channels for WebSocket
- **Frontend (Public):** Rust/Axum serving CMS pages and blog
- **Frontend (Admin):** Django admin, staff portal, customer portal
- **Mobile:** Android native app (Kotlin/Jetpack Compose)
- **Infrastructure:** Docker Compose, nginx, GitHub Actions CI/CD

**Architecture Layers:**
- `src/diveops/` - Django application code
- `rust/` - Rust frontend for public pages
- `android/` - Android mobile app
- `lib/` - Submodule dependencies (django-primitives, etc.)

---

## CRITICAL SECURITY REQUIREMENT: NO AI ATTRIBUTION

**NEVER include in any deliverable:**
- "Generated with Claude"
- "Co-Authored-By: Claude"
- "Built with Claude Code"
- Any AI/assistant/Claude references

**This applies to:**
- Git commit messages
- Code comments
- Documentation
- README files
- Any file in the repository

**This is a compliance and security requirement. Violations will be rejected.**

---

## DATABASE: PostgreSQL Only

All code assumes PostgreSQL. No SQLite fallback.

**Use PostgreSQL features:**
- UUID primary keys (native type)
- JSONB fields where appropriate
- Partial indexes, constraints
- Row-level locking for concurrency

---

## TDD WORKFLOW (MANDATORY)

### TDD Stop Gate

BEFORE writing ANY implementation code, output this confirmation:

```
=== TDD STOP GATE ===
Task: [current task]
[ ] I have identified the test cases
[ ] I am writing TESTS FIRST
[ ] Tests will fail because implementation doesn't exist
=== PROCEEDING WITH FAILING TESTS ===
```

### Write Failing Tests First

1. Create test file
2. Write test cases
3. Run pytest and SHOW failing output
4. Confirm tests fail because code doesn't exist

### Implement Minimal Code

1. Write minimum code to make ONE test pass
2. Run pytest and show output
3. Repeat until all tests pass

### Output Completion

```
=== TDD CYCLE COMPLETE ===
Tests written BEFORE implementation: YES
All tests passing: [X/X]
=== READY FOR COMMIT ===
```

---

## GIT WORKFLOW

### Commit Messages

Use conventional commit format:

```
feat(component): brief description

- Detail 1
- Detail 2
```

Prefixes:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Tests only
- `refactor`: Code change without feature/fix

### When to Commit

Commit after:
1. All tests pass
2. No import errors
3. Documentation updated if needed

### FORBIDDEN in Commits

NEVER include:
- "Generated with Claude"
- "Co-Authored-By: Claude"
- Any AI/assistant references

---

## DJANGO PATTERNS

### Model Patterns

**UUID Primary Key:**
```python
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
```

**Timestamps:**
```python
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)
```

**Soft Delete:**
```python
deleted_at = models.DateTimeField(null=True, blank=True)

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

objects = SoftDeleteManager()
all_objects = models.Manager()
```

### Service Layer

Put business logic in services, not models:

```python
from django.db import transaction

def do_operation(entity, **kwargs):
    """Perform operation atomically."""
    with transaction.atomic():
        # validate
        # execute
        # save
        return result
```

---

## RUST PATTERNS

### Route Handlers

```rust
pub async fn handler(State(state): State<AppState>) -> Result<Html<String>> {
    let template = MyTemplate { /* fields */ };
    Ok(Html(template.render().unwrap()))
}
```

### Templates

Use Askama templates in `rust/templates/`. Extend `base.html`.

---

## ANDROID PATTERNS

### Compose UI

Use Jetpack Compose for all UI:

```kotlin
@Composable
fun MyScreen(
    viewModel: MyViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    // UI implementation
}
```

### API Calls

Use Retrofit with coroutines:

```kotlin
suspend fun fetchData(): Response<DataResponse>
```

---

## TESTING

### Django Tests

```python
import pytest

@pytest.mark.django_db
class TestMyFeature:
    def test_scenario(self):
        # Arrange
        # Act
        # Assert
```

### Coverage Requirement

Target >95% coverage for new code:

```bash
pytest --cov=src/diveops -v
```

---

## CI/CD

### GitHub Actions

- Tests run on every push
- Deploy to production on main branch merge
- Docker images built and pushed to GHCR

### Deployment

Production deployment is automatic after tests pass. Manual verification required for:
- Database migrations
- Breaking changes

---

## CHECKLISTS

### Pre-Commit Checklist

```
□ pytest passes
□ No AI attribution in commit message
□ Commit message uses conventional format
□ No TODO comments left in code
```

### Feature Checklist

```
□ Tests written BEFORE implementation
□ All tests passing
□ Documentation updated
□ No AI attribution anywhere
```

---

## QUICK REFERENCE

### Run Tests

```bash
pytest tests/ -v
pytest --cov=src/diveops -v
```

### Run Development Server

```bash
# Django
python manage.py runserver

# Rust
cd rust && cargo run

# Full stack
docker-compose up
```

### Create Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```
