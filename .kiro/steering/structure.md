---
inclusion: always
---

# Project structure

```
lazarus/
├── .kiro/
│   ├── steering/          product.md, tech.md, structure.md, ears.md
│   ├── specs/             one folder per feature (intake, autopsy, spec-generator, parity-cli, web-ui)
│   └── hooks/
├── lazarus/               Django project: settings, urls, wsgi
├── intake/                upload (GitHub URL or zip), safe unzip, file tree, language detection
├── autopsy/               tree-sitter PHP parsing → autopsy report (JSON)
│   ├── parsers/           one module per concern: pages.py, forms.py, sql.py, includes.py, sessions.py
│   └── report.py          assembles the full autopsy report
├── specgen/               autopsy report → Kiro spec files
│   ├── templates/         markdown templates for requirements, design, tasks, steering
│   ├── llm.py             optional AI polish (Groq → Gemini → passthrough)
│   └── export.py          builds the downloadable .kiro/ zip
├── parity/                record, replay and score old vs new app behavior (CLI)
├── web/                   views, templates, static (graveyard, autopsy, spec, resurrection screens)
├── samples/corpse/        TaskFreak! 0.6.4 (third-party GPL input, never edit)
├── docs/                  kiro-diary.md, corpse.md
├── tests/                 mirrors app folders: tests/autopsy/, tests/specgen/, ...
├── requirements.txt
├── LICENSE                MIT
└── README.md
```

## Data model
- `Corpse`: an uploaded legacy project (name, source URL, upload path, file count, created_at)
- `Autopsy`: one per Corpse; JSON report + status
- `Spec`: generated files for an Autopsy (requirements, design, tasks, steering) + zip path
- `Job`: background task status and log lines

## Naming
- Apps: lowercase single words
- Templates: `<app>/<page>.html`, HTMX partials prefixed with `_` (e.g. `web/_autopsy_table.html`)
- URLs: kebab-case paths, `app:name` route names
- Tests: `test_<module>.py`; property tests named `test_prop_<behavior>`

## Where things go
- New parsing logic → `autopsy/parsers/`
- New spec output → template in `specgen/templates/` + function in `specgen/`
- UI change → `web/`
- Never add code to `samples/corpse/`
