# TaskFreak!, resurrected

This is the Django rebuild of TaskFreak! 0.6.4 that Kiro produced from the Lazarus spec, in a single unattended run of `tasks.md`. It's kept here exactly as Kiro left it, along with the `.kiro/` spec it was built from.

Resurrection check: **100%** (16/16 pages · 1/1 forms · 9/9 tables · 4/4 safety · 2/2 look and feel).

## Run it

```bash
cd examples/taskfreak-resurrected
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python seed_demo.py
python manage.py runserver 8001
```

Open http://127.0.0.1:8001 and sign in as `admin` with the password `lazarus-demo`.

## Score it

From the Lazarus root, with the rebuild running:

```bash
python manage.py resurrection_check <TaskFreak corpse id> \
    --url http://127.0.0.1:8001 --source examples/taskfreak-resurrected \
    --username admin --password lazarus-demo
```

## What's here

| Path | What it is |
|---|---|
| `.kiro/` | The spec, steering and task plan Lazarus generated and Kiro ran |
| `accounts/`, `core/` | The Django apps Kiro wrote |
| `taskfreak/` | Project settings and URLs |
| `templates/`, `static/` | Pages ported from the legacy PHP |
| `legacy-assets/` | TaskFreak's original stylesheets and skins, as exported by Lazarus |
| `locale/` | Translations |
| `seed_demo.py` | Creates the demo admin and sample data |

## Licence

The original TaskFreak! is GPL-licensed. This rebuild is derived from its behaviour, and `legacy-assets/` contains its original stylesheets, so this folder is distributed under the GPL as well. The rest of Lazarus is MIT.
