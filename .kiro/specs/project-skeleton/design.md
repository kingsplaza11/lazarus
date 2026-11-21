# Design Document: Project Skeleton

## Overview

A standard Django 5 project with five feature apps, environment-based settings, four core models, django-q2 for background work, a placeholder UI, pytest + Hypothesis tests, and Render deployment. Everything is free and runs on SQLite.

## Architecture

```
Browser ──► Gunicorn ──► Django (lazarus)
                           ├── web/      pages: home (graveyard), health
                           ├── intake/   models: Corpse          (logic in a later spec)
                           ├── autopsy/  models: Autopsy         (logic in a later spec)
                           ├── specgen/  models: Spec            (logic in a later spec)
                           ├── parity/   models: Job + job helpers
                           └── SQLite  ◄── django-q2 worker (qcluster), ORM broker
```

Static files are served by WhiteNoise. No Redis, no Node build step.

## Components and Interfaces

### Settings (`lazarus/settings.py`)
- Load `.env` with `python-dotenv` if it exists.
- `SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")`; if missing and `DEBUG` is true, fall back to a fixed dev-only key; if missing and `DEBUG` is false, raise `ImproperlyConfigured`.
- `DEBUG = os.environ.get("DEBUG", "False").lower() == "true"`
- `ALLOWED_HOSTS` from a comma-separated env var, default `localhost,127.0.0.1`; also add `RENDER_EXTERNAL_HOSTNAME` when set.
- `CSRF_TRUSTED_ORIGINS` built from the Render hostname when set.
- When not `DEBUG`: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`.
- `Q_CLUSTER = {"name": "lazarus", "orm": "default", "workers": 1, "timeout": 300, "retry": 360}`.
- `STATIC_ROOT = BASE_DIR / "staticfiles"`, WhiteNoise middleware right after `SecurityMiddleware`, `CompressedManifestStaticFilesStorage` in production.
- `MEDIA_ROOT = BASE_DIR / "uploads"` (git-ignored).

### Shared status choices (`lazarus/choices.py`)
```python
class Status(models.TextChoices):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
```

### Job helpers (`parity/jobs.py`, later moved if needed)
- `run_job(job_id: int, func: Callable[[Job], None]) -> None`: sets `running`, calls `func`, sets `done`; on exception sets `failed` and appends the traceback to `log`.
- `Job.append_log(line: str) -> None`.

### Views (`web/views.py`)
- `home(request)`: renders `web/home.html`.
- `health(request)`: returns `JsonResponse({"status": "ok"})`.

### Templates
- `web/templates/web/base.html`: HTML5 shell, dark theme CSS link, HTMX + Alpine.js from CDN, `{% block content %}`.
- `web/templates/web/home.html`: extends base; title "Lazarus", tagline "Dead code walks again.", one-sentence description, disabled "Upload a corpse" button.
- `web/static/web/lazarus.css`: minimal dark styles (near-black background, bone-white text, one green accent).

### URLs (`lazarus/urls.py`)
- `""` → `web.home` (name `web:home`)
- `"health/"` → `web.health` (name `web:health`)
- `"admin/"` → Django admin

## Data Models

| Model | App | Fields |
|---|---|---|
| `Corpse` | intake | `name` CharField(200), `source_url` URLField(blank), `storage_path` CharField(500, blank), `file_count` PositiveIntegerField(default 0), `status` CharField(choices=Status, default pending), `created_at` DateTimeField(auto_now_add) |
| `Autopsy` | autopsy | `corpse` OneToOneField(Corpse, CASCADE, related_name="autopsy"), `report` JSONField(default dict), `status`, `created_at`, `updated_at` |
| `Spec` | specgen | `autopsy` ForeignKey(Autopsy, CASCADE, related_name="specs"), `requirements_md` TextField(blank), `design_md` TextField(blank), `tasks_md` TextField(blank), `steering_md` TextField(blank), `export_path` CharField(500, blank), `created_at` |
| `Job` | parity | `kind` CharField(50), `corpse` ForeignKey(Corpse, SET_NULL, null, blank, related_name="jobs"), `status`, `log` TextField(blank), `created_at`, `updated_at` |

Each model gets `__str__` and `class Meta: ordering = ["-created_at"]`. All four are registered in their app's `admin.py` with `list_display` including `status`.

## Error Handling
- Missing production secret key → `ImproperlyConfigured` at startup.
- Job exceptions → caught in `run_job`, recorded on the `Job`, never re-raised into the web request.
- 404/500 use Django defaults for now (styled pages come in the web-ui spec).

## Testing Strategy
- `pytest.ini`: `DJANGO_SETTINGS_MODULE = lazarus.settings`, `python_files = test_*.py`.
- `tests/web/test_views.py`: `/` returns 200 and contains "Lazarus"; `/health/` returns `{"status": "ok"}`.
- `tests/test_models.py`: create one of each model; check `__str__`; check `Corpse` → `Autopsy` relation.
- `tests/test_jobs.py`: `run_job` marks done on success, failed + log on exception.
- `tests/test_choices.py` (Hypothesis): `test_prop_status_rejects_unknown_values`: for any text not in the four statuses, `full_clean()` on a `Corpse` raises `ValidationError`.
- Tests must pass with no `.env` (dev fallback key, `DEBUG` treated as true in tests via `pytest.ini` env or a settings override).

## Deployment
- `requirements.txt` adds `gunicorn` and `whitenoise`.
- `build.sh`: `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate`.
- `render.yaml`: one free web service, Python runtime, build command `./build.sh`, start command `gunicorn lazarus.wsgi:application`, env vars `DJANGO_SECRET_KEY` (generateValue: true), `DEBUG=False`, `PYTHON_VERSION=3.12.7`.
- The django-q2 worker is not deployed on the free tier in this phase; later specs run short jobs synchronously on the hosted app when no worker is available.
