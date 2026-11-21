# Requirements Document: Project Skeleton

## Introduction

This feature sets up the foundation of Lazarus: a Django project with its five apps, the core data models, environment-based settings, a background job queue, a placeholder home page, a health check, a test setup, and a free deployment to Render. No legacy-code analysis happens yet. The goal is a running, deployable, tested shell that every later feature (intake, autopsy, spec generator, parity CLI, web UI) plugs into.

## Requirements

### Requirement 1: Django project and apps

**User Story:** As the developer, I want a Django project with one app per feature area, so that each later spec has a clear place to live.

#### Acceptance Criteria
1. THE system SHALL be a Django 5 project named `lazarus` at the repository root.
2. THE system SHALL contain the apps `intake`, `autopsy`, `specgen`, `parity` and `web`, each registered in `INSTALLED_APPS`.
3. THE system SHALL follow the folder layout defined in `.kiro/steering/structure.md`.
4. THE system SHALL NOT modify any file inside `samples/corpse/`.

### Requirement 2: Environment-based settings

**User Story:** As the developer, I want all secrets and environment-specific values read from environment variables, so that no secret is ever committed.

#### Acceptance Criteria
1. THE system SHALL read `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `GROQ_API_KEY` and `GEMINI_API_KEY` from environment variables, loading a local `.env` file when present.
2. IF `DJANGO_SECRET_KEY` is missing WHILE `DEBUG` is false THEN THE system SHALL refuse to start with a clear error message.
3. WHEN `DEBUG` is false THEN THE system SHALL enable secure cookie settings.
4. THE system SHALL provide a `.env.example` file listing every variable with empty values.

### Requirement 3: Core data models

**User Story:** As the developer, I want the core records defined now, so that later features share one data model.

#### Acceptance Criteria
1. THE system SHALL store a `Corpse` with a name, an optional source URL, a storage path, a file count, a status and a creation time.
2. THE system SHALL store one `Autopsy` per `Corpse` with a JSON report, a status and timestamps.
3. THE system SHALL store a `Spec` per `Autopsy` with requirements, design and tasks text, optional steering text, and an optional export file path.
4. THE system SHALL store a `Job` with a kind, a status, an optional link to a `Corpse`, a text log and timestamps.
5. THE system SHALL restrict every status field to the values `pending`, `running`, `done` and `failed`.
6. WHEN an administrator signs in to the Django admin THEN THE system SHALL list `Corpse`, `Autopsy`, `Spec` and `Job` records.

### Requirement 4: Background jobs

**User Story:** As the developer, I want a free background job queue, so that slow work (parsing, spec generation) does not block web requests.

#### Acceptance Criteria
1. THE system SHALL use django-q2 with the Django ORM as its broker.
2. THE system SHALL NOT require Redis, Celery or any paid service.
3. WHEN a job function raises an exception THEN THE system SHALL mark the related `Job` as `failed` and save the error to its log.

### Requirement 5: Home page and health check

**User Story:** As a visitor, I want a landing page that explains Lazarus, so that I understand the product before any features exist.

#### Acceptance Criteria
1. WHEN a visitor opens `/` THEN THE system SHALL show a "Graveyard" placeholder page with the product name, a one-sentence description and a disabled "Upload a corpse" button.
2. THE system SHALL render pages from a shared base template that loads HTMX and Alpine.js from a CDN.
3. WHEN a client requests `/health/` THEN THE system SHALL return HTTP 200 with JSON `{"status": "ok"}`.

### Requirement 6: Testing setup

**User Story:** As the developer, I want tests ready from day one, so that every later feature is built test-first.

#### Acceptance Criteria
1. THE system SHALL run its test suite with `pytest` using pytest-django.
2. THE system SHALL include tests for the health check, the home page and each model's string representation.
3. THE system SHALL include at least one Hypothesis property test for the status field values.
4. WHEN `pytest` runs on a fresh checkout with no `.env` file THEN THE system SHALL pass all tests.

### Requirement 7: Free deployment

**User Story:** As the developer, I want the skeleton deployed early, so that hosting problems show up before the deadline.

#### Acceptance Criteria
1. THE system SHALL serve static files with WhiteNoise and run under Gunicorn.
2. THE system SHALL include a `render.yaml` and a `build.sh` that install dependencies, collect static files and run migrations.
3. WHEN the project is deployed to Render's free web service THEN THE system SHALL respond on `/` and `/health/`.
4. THE system SHALL document local setup and deployment steps in `README.md`.
