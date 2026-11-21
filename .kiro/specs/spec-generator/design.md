# Design Document: Spec Generator

## Overview

`generate_spec(report, name, intro)` is a pure function returning `{path: content}`. Django code only stores, shows and exports the result.

```
Autopsy.report ─► generator.build_models ─► ModelSpec list
               ─► generator.build_requirements ─► Requirement list (numbered)
               ─► requirements_md / design_md / tasks_md / steering  ─► {path: content}
                                   │
llm.polish(intro) (optional) ──────┘
services.generate_for_corpse ─► Spec (files JSON in steering_md) ─► detail view / zip export
```

## Components

| Module | Responsibility |
|---|---|
| `specgen/naming.py` | Table prefix detection, word splitting (`itemcomment` → `ItemComment`), page titles, groups, URLs, view names |
| `specgen/generator.py` | Models, requirements, documents, `validate_ears`, `generate_spec` |
| `specgen/llm.py` | Optional polish: Groq → Gemini → unchanged; number-preservation check; cache |
| `specgen/services.py` | `generate_for_corpse`, `latest_spec`, `spec_files`, `export_zip` |
| `specgen/views.py` | generate (POST), detail, download (zip), download_file |

## Key decisions
- **EARS by construction:** criteria are assembled from fixed templates; legacy names pass through `clean()` (single line, no backticks, length-limited). `validate_ears` checks the output.
- **Traceability:** every criterion ends with `(source: …)`.
- **Shared includes skipped per page:** an include used by 2+ pages (config, bootstrap) would otherwise attach its queries to every page.
- **Apps:** people tables and auth pages → `accounts`; the rest → `core`. Foreign keys are app-qualified.
- **Storage:** the whole file set is stored as JSON in `Spec.steering_md`; `requirements_md`, `design_md`, `tasks_md` hold copies for the admin.

## Testing Strategy
- Pure generator tests on a TaskFreak-shaped fixture: layout, EARS validity, source citations, task refs exist, FK qualification, composite constraint, models compile, naming.
- Property test `test_prop_any_legacy_names_still_give_valid_ears`: random hostile names never break EARS.
- `llm` tests with fake HTTP: disabled, Groq success, number change rejected, Gemini fallback, total failure.
- View tests on the real TaskFreak corpse: generate, show, zip contents, single-file download, path traversal → 404.
