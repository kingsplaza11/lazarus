---
inclusion: always
---

# Tech stack and conventions

## Stack
- Python 3.12, Django 5.x, Django REST Framework
- Database: SQLite (local and hosted); switch to Neon Postgres only if the host wipes files
- Background jobs: django-q2 using the Django ORM broker (no Redis)
- Parsing: `tree-sitter` + `tree-sitter-php` Python packages
- AI polish (optional): Groq free tier first, Gemini free tier as fallback, plain templates as final fallback
- Frontend: Django templates + HTMX + Alpine.js; plain CSS (no build step)
- Tests: pytest, pytest-django, Hypothesis (property-based tests)
- Parity sandbox: Docker (local only, never on the hosted server)
- Hosting: Render or Koyeb free web service

## Hard rules
- No paid services, SDKs or APIs
- No Celery, Redis, Node build tools or frontend frameworks
- Never `eval`, `exec`, `include` or run uploaded PHP on the server; only read it as text
- Secrets come from environment variables via `python-dotenv`; never hard-code keys
- All AI calls go through one interface in `specgen/llm.py`:
  - `polish(text: str) -> str`
  - try Groq → Gemini → return input unchanged
  - catch every exception and rate-limit (HTTP 429); AI failure must never break a request
  - cache results by content hash
- Upload limits: 20 MB, 500 files; unzip with path-traversal checks

## Code style
- Type hints on all functions; docstrings on public functions
- Small pure functions in `autopsy/` so they can be property-tested
- Django: class-based views for CRUD, function views for HTMX partials
- Settings split: `lazarus/settings.py` reads env vars; `DEBUG` false in production

## Testing expectations
- Every parser function has unit tests and at least one Hypothesis property test
- Use TaskFreak files in `samples/corpse/` as real-world fixtures
- `pytest` must pass before every commit

## Common commands
```bash
python manage.py runserver
python manage.py qcluster          # background worker
pytest
python manage.py lazarus_parity --old http://localhost:8080 --new http://localhost:8000
```
