# Lazarus

🧟 Lazarus resurrects dead legacy code. It performs an autopsy on an abandoned PHP + MySQL app (pages, forms, tables, SQL queries, includes, sessions), generates a Kiro spec (requirements, design, tasks, steering), and lets Kiro rebuild it as a Django app. `lazarus parity` then compares old and new behavior and gives a score. Built with Kiro for Kiroween 2026 (Resurrection).

Uploaded code is only analyzed, never executed.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then set DJANGO_SECRET_KEY (and DEBUG=True for local work)
python manage.py migrate
python manage.py runserver
```

Optional: run the background task worker in a second terminal.

```bash
python manage.py qcluster
```

`GROQ_API_KEY` and `GEMINI_API_KEY` in `.env` are optional. Lazarus works without AI; it only polishes wording.

## Tests

```bash
pytest
```

## Deploying to Render

1. Push the repo and create a Render Blueprint from `render.yaml` (free web service).
2. Render runs `./build.sh` and starts `gunicorn lazarus.wsgi:application`. The health check is `/health/`.
3. `render.yaml` sets `DJANGO_SECRET_KEY` (generated), `DEBUG=False` and `PYTHON_VERSION`. Optionally add `ALLOWED_HOSTS`, `GROQ_API_KEY` and `GEMINI_API_KEY` in the Render dashboard. `RENDER_EXTERNAL_HOSTNAME` is provided by Render.

## Demo corpse and credits

`samples/corpse/` contains TaskFreak! 0.6.4 (multi user) by Stan Ozier, licensed under the GNU GPL (see `samples/corpse/LICENSE-NOTE.txt`). It is included unmodified as demo input and is not part of the Lazarus source.

## License

Lazarus is released under the MIT License (see `LICENSE`).
