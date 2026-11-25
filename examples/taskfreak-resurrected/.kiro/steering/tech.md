---
inclusion: always
---

# Tech stack

- Python 3.12+, Django 6, SQLite for development (PostgreSQL in production)
- Server-rendered Django templates; HTMX for partial updates; no frontend build step
- `django.contrib.auth` for accounts and sessions; passwords hashed by Django
- All data access through the ORM (no raw SQL string building)
- CSRF protection on every form; `pytest` + `pytest-django` for tests
- Keep legacy table and column names via `db_table` / `db_column` so old data loads directly
