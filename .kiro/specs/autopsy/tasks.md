# Implementation Plan: Autopsy

- [x] 1. SQL and schema parser (`autopsy/parsers/sql.py`) with tests
  - _Requirements: 2.2, 4.4, 4.5_

- [x] 2. Form parser with PHP masking (`autopsy/parsers/forms.py`) with tests
  - _Requirements: 2.4_

- [x] 3. Tree-sitter PHP parser (`autopsy/parsers/php.py`)
  - [x] 3.1 Structure: functions, classes, methods, includes, superglobals, redirects, session
    - _Requirements: 2.1, 2.5_
  - [x] 3.2 SQL in strings and flattened concatenations
    - _Requirements: 2.2, 2.3_
  - [x] 3.3 Removed-function detection (cause of death)
    - _Requirements: 3.1_
  - [x] 3.4 Tests, including property test `test_prop_parse_php_never_crashes`
    - _Requirements: 2.1, 2.5, 3.1_

- [x] 4. Report builder (`autopsy/report.py`)
  - Include resolution, pages, per-page aggregation, table usage, cause-of-death summary, translation skipping
  - _Requirements: 3.2, 3.3, 4.1, 4.2, 4.3, 4.5, 5.1, 5.2_

- [x] 5. Service, views, URLs and report template
  - `run_autopsy`, POST run view, GET report view, `report.html`, detail page buttons
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.1, 6.2, 6.3_

- [x] 6. Management command `autopsy` with `--file` and `--tree`
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 7. Verify on TaskFreak
  - `pytest` all green; run `python manage.py autopsy <demo id>`; open the report page and check the cause of death lists `mysql_*` functions from `include/classes/tzn_mysql.php`
  - _Requirements: 3.1, 6.1_
