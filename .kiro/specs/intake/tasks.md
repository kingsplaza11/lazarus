# Implementation Plan: Intake

- [X] 1. Extend the Corpse model
  - Add `file_tree`, `languages`, `is_demo`, `error`; create and run the migration
  - _Requirements: 3.3, 5.1_

- [X] 2. Safe extraction
  - [X] 2.1 Implement `intake/safety.py`: limits, `UnsafeArchive`, `is_safe_member`, two-pass `safe_extract`
    - Reject unsafe paths, >500 files, >100 MB expanded; skip symlinks and `SKIP_DIRS`; flatten single top-level folder; clean up on failure
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_
  - [x] 2.2 Unit tests with in-memory malicious zips
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.7_
  - [x] 2.3 Property test `test_prop_safe_member_never_escapes`
    - _Requirements: 4.2_

- [x] 3. File tree and languages
  - [x] 3.1 Implement `intake/tree.py`: `detect_language`, `build_tree`, `language_summary`
    - _Requirements: 5.1, 5.2_
  - [x] 3.2 Unit tests and property test `test_prop_tree_counts_match`
    - _Requirements: 5.1, 5.2_

- [x] 4. GitHub import
  - [x] 4.1 Implement `intake/github.py`: `parse_github_url`, streaming `fetch_zip` with 30 s timeout and size cap (stdlib only)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [x] 4.2 Tests for URL parsing and a mocked fetch (success, timeout, 404)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 5. Intake services
  - [x] 5.1 `create_from_zip` and `create_from_github` with status changes, cleanup and `IntakeError`
    - _Requirements: 1.1, 2.1, 2.5, 4.6, 5.3_
  - [x] 5.2 `summon_demo` copying `samples/corpse/` without modifying it; return existing demo if present
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 5.3 Service tests, including "samples/corpse file count unchanged after summon"
    - _Requirements: 3.2, 3.3_

- [x] 6. Upload form and views
  - [x] 6.1 `CorpseUploadForm` with exactly-one-input validation, `.zip` check and 20 MB limit
    - _Requirements: 1.2, 1.3, 2.3_
  - [x] 6.2 Views and URLs: `upload` (GET/POST), `demo` (POST), `detail`
    - _Requirements: 1.1, 1.4, 3.1, 6.1_
  - [x] 6.3 Templates: `upload.html` with Alpine.js tabs, `detail.html`, recursive `_tree.html` using `<details>`
    - Show no-PHP warning and disabled "Begin autopsy"
    - _Requirements: 5.4, 6.1, 6.2, 6.3_

- [x] 7. The Graveyard
  - [x] 7.1 Update `home` view and `web/home.html`: tombstone grid newest first, empty state, enabled upload button, demo button
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  - [x] 7.2 View tests for empty state, tombstone list, upload redirect, demo redirect
    - _Requirements: 1.4, 3.1, 7.1, 7.2_

- [x] 8. Verify locally
  - Run `pytest` (all green), then `python manage.py runserver`
  - Summon the demo corpse: expect about 183 PHP files and a tree showing `include/`, `install/`, `skins/`
  - Upload a small zip and import a small public GitHub repo; try a zip with `../` paths and confirm it's rejected
  - _Requirements: 1.1, 2.1, 3.1, 4.2, 5.1_
