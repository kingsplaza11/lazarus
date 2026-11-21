# Design Document: Intake

## Overview

Intake turns three kinds of input (zip upload, GitHub URL, demo corpse) into one result: a `Corpse` with its files stored under `MEDIA_ROOT/corpses/<id>/`, a saved file tree and a language summary. All extraction goes through one safe-extraction function. Nothing uploaded is ever executed. Processing is synchronous for now (archives are small); it can move to django-q2 later without changing the service interface.

## Architecture

```
Upload form ─┐
GitHub URL ──┼─► intake/services.py ─► safe_extract() ─► build_tree() ─► Corpse (tree, languages, status)
Demo button ─┘          │                                                     │
                        └─ github.fetch_zip()                    web: graveyard + corpse detail
```

## Components and Interfaces

### `intake/safety.py`
```python
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_FILES = 500
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
SKIP_DIRS = {".git", "node_modules", "vendor", "__MACOSX"}

class UnsafeArchive(Exception):
    """Raised with a user-facing message when an archive is rejected."""

def is_safe_member(name: str, root: Path) -> bool: ...
def safe_extract(zip_path: Path, dest: Path) -> int:
    """Validate every entry first (paths, symlinks, count, total size), then extract.
    Skips SKIP_DIRS. Flattens a single top-level folder. Returns the number of files written.
    Raises UnsafeArchive; on any error removes dest."""
```
- Validation happens before writing anything (two passes: check, then extract).
- Symlinks detected via `ZipInfo.external_attr >> 16` having the `S_IFLNK` bit; skipped.
- Path check: `(dest / name).resolve()` must be inside `dest.resolve()`; absolute paths and `..` rejected.

### `intake/github.py`
```python
GITHUB_RE = r"^https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?(?:/tree/(?P<branch>[^/]+))?/?$"

def parse_github_url(url: str) -> tuple[str, str, str | None]: ...
def fetch_zip(url: str, dest_file: Path, timeout: int = 30) -> None:
    """Download https://api.github.com/repos/{owner}/{repo}/zipball/{branch or ''}
    with urllib (stdlib), streaming to dest_file, aborting past MAX_UPLOAD_BYTES."""
```
- Uses only the Python standard library (`urllib.request`), no API token, public repos only.

### `intake/tree.py`
```python
LANGUAGES = {".php": "PHP", ".inc": "PHP", ".sql": "SQL", ".html": "HTML", ".htm": "HTML",
             ".css": "CSS", ".js": "JavaScript"}

def detect_language(path: str) -> str: ...          # falls back to "Other"
def build_tree(root: Path) -> dict: ...             # {"name", "type": "dir"|"file", "children"?, "size"?}
def language_summary(root: Path) -> dict[str, int]: ...
```
- Children sorted: folders first, then files, both alphabetical.

### `intake/services.py`
```python
def create_from_zip(name: str, uploaded_file) -> Corpse: ...
def create_from_github(name: str, url: str) -> Corpse: ...
def summon_demo() -> Corpse: ...
```
- Each: create `Corpse(status=running)`, write to `MEDIA_ROOT/corpses/<id>/`, call `safe_extract` (or `shutil.copytree` for the demo, ignoring `SKIP_DIRS`), then `build_tree` + `language_summary`, save, set `done`.
- On `UnsafeArchive` or fetch error: delete the folder, set `failed`, save the message to a `Job` log, re-raise a `IntakeError(message)` for the view.
- `summon_demo` returns the existing corpse if one with `is_demo=True` exists.

### Forms (`intake/forms.py`)
- `CorpseUploadForm`: `name` (required, max 200), `archive` (FileField, optional), `github_url` (URLField, optional). `clean()` requires exactly one of `archive` or `github_url`; validates size ≤ 20 MB and `.zip` extension.

### Views and URLs
| URL | View | Purpose |
|---|---|---|
| `/` | `web.views.home` | Graveyard: tombstones + buttons |
| `/corpses/new/` | `intake.views.upload` | GET form, POST create |
| `/corpses/demo/` | `intake.views.demo` | POST only; summon demo |
| `/corpses/<int:pk>/` | `intake.views.detail` | Detail page with tree |

### Templates
- `web/home.html`: tombstone grid (CSS cards with rounded tops), empty-state message, two buttons.
- `intake/upload.html`: tabs "Zip file" / "GitHub URL" using Alpine.js `x-data`.
- `intake/detail.html`: header, language summary as small badges, tree, disabled "Begin autopsy".
- `intake/_tree.html`: recursive include; folders use `<details><summary>` (native expand/collapse, no reload).

## Data Model Changes

Add to `Corpse` (new migration):
| Field | Type |
|---|---|
| `file_tree` | JSONField(default=dict) |
| `languages` | JSONField(default=dict) |
| `is_demo` | BooleanField(default=False) |
| `error` | TextField(blank=True) |

## Error Handling

| Situation | Result |
|---|---|
| Invalid zip / too big / unsafe / too many files / too large expanded | Corpse `failed`, folder removed, form re-shown with the exact message from requirements |
| GitHub URL invalid | Form error before any download |
| GitHub fetch fails or times out | Corpse `failed`, message "Couldn't fetch that repository. Is it public?" |
| No PHP files | Corpse saved as `done`; warning shown on detail page |

## Testing Strategy

- Unit tests (`tests/intake/`): `parse_github_url` (plain, `.git`, `/tree/branch`, invalid hosts), `detect_language`, `build_tree` ordering, form validation.
- Safety tests build zips in memory with `zipfile` and `tmp_path`: `../evil.php`, absolute `/etc/x`, a symlink entry, 501 files, a 101 MB-expanding entry (use `ZipInfo.file_size` with a small compressed payload), a single top-level folder.
- Demo test: `summon_demo()` twice returns the same corpse; `samples/corpse/` file count unchanged.
- GitHub fetch is mocked (no network in tests).
- Property tests (Hypothesis):
  - `test_prop_safe_member_never_escapes`: for any generated path string, if `is_safe_member` returns True then the resolved path is inside root.
  - `test_prop_tree_counts_match`: for any generated set of file paths written to `tmp_path`, the number of file nodes in `build_tree` equals the number of files written, and `sum(language_summary.values())` equals it too.
- View tests: home empty state, home lists tombstones, upload happy path redirects, demo POST redirects to detail.
