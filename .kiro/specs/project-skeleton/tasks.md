# Implementation Plan: Project Skeleton

- [x] 1. Create the Django project and apps
  - Run `django-admin startproject lazarus .` at the repo root
  - Create apps `intake`, `autopsy`, `specgen`, `parity`, `web` and add them plus `django_q` to `INSTALLED_APPS`
  - Confirm `samples/corpse/` is untouched
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Environment-based settings
  - [x] 2.1 Load `.env` with python-dotenv; read `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `GROQ_API_KEY`, `GEMINI_API_KEY`
    - Dev fallback key only when `DEBUG` is true; raise `ImproperlyConfigured` otherwise
    - Add Render hostname to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` when set
    - _Requirements: 2.1, 2.2_
  - [x] 2.2 Production security settings when `DEBUG` is false
    - _Requirements: 2.3_
  - [x] 2.3 Update `.env.example` with every variable
    - _Requirements: 2.4_

- [x] 3. Shared status choices
  - Create `lazarus/choices.py` with the `Status` TextChoices
  - _Requirements: 3.5_

- [x] 4. Core models and admin
  - [x] 4.1 `Corpse` in `intake/models.py`
    - _Requirements: 3.1_
  - [x] 4.2 `Autopsy` in `autopsy/models.py`
    - _Requirements: 3.2_
  - [x] 4.3 `Spec` in `specgen/models.py`
    - _Requirements: 3.3_
  - [x] 4.4 `Job` in `parity/models.py` with `append_log`
    - _Requirements: 3.4_
  - [x] 4.5 Register all four in admin with `list_display` including `status`; run `makemigrations` and `migrate`
    - _Requirements: 3.6_

- [x] 5. Background jobs
  - [x] 5.1 Configure `Q_CLUSTER` with the ORM broker
    - _Requirements: 4.1, 4.2_
  - [x] 5.2 Implement `run_job` in `parity/jobs.py` (running → done, or failed + traceback in log)
    - _Requirements: 4.3_

- [x] 6. Home page and health check
  - [x] 6.1 `base.html` with HTMX + Alpine.js from CDN and `lazarus.css`
    - _Requirements: 5.2_
  - [x] 6.2 `home.html` graveyard placeholder and `home` view at `/`
    - _Requirements: 5.1_
  - [x] 6.3 `health` view at `/health/` returning `{"status": "ok"}`
    - _Requirements: 5.3_

- [x] 7. Tests
  - [x] 7.1 `pytest.ini` and pytest-django setup that works without `.env`
    - _Requirements: 6.1, 6.4_
  - [x] 7.2 View tests for `/` and `/health/`
    - _Requirements: 6.2_
  - [x] 7.3 Model `__str__` and relation tests; `run_job` success and failure tests
    - _Requirements: 6.2, 4.3_
  - [x] 7.4 Hypothesis property test: unknown status values fail validation
    - _Requirements: 6.3_

- [x] 8. Deployment files
  - [x] 8.1 Add `gunicorn` and `whitenoise` to `requirements.txt`; WhiteNoise middleware and static settings
    - _Requirements: 7.1_
  - [x] 8.2 Create `build.sh` (executable) and `render.yaml`
    - _Requirements: 7.2_
  - [x] 8.3 Write `README.md`: what Lazarus is, local setup, running tests, deploying to Render, the TaskFreak corpse credit
    - _Requirements: 7.4_

- [-] 9. Verify and deploy
  - Run `pytest` (all green) and `python manage.py runserver`; check `/` and `/health/`
  - Push to GitHub, connect the repo on Render, confirm `/` and `/health/` respond on the live URL
  - _Requirements: 7.3_
