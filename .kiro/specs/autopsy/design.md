# Design Document: Autopsy

## Overview

A pipeline of small, pure parsers feeding one report builder. Tree-sitter reads PHP structure; regex handles HTML forms (PHP blocks masked first) and SQL text. The report is plain JSON stored on `Autopsy.report`.

```
corpse files ─► parsers/php.py   (tree-sitter: functions, classes, includes, superglobals, SQL, redirects, dead calls)
             ─► parsers/forms.py (regex: forms + fields, PHP masked)
  .sql files ─► parsers/sql.py   (CREATE TABLE → tables, columns, primary keys)
                       │
                       ▼
                 report.py  (include graph, pages, table usage, cause of death, i18n skip)
                       │
                       ▼
             services.run_autopsy ─► Autopsy.report (JSON) ─► report.html
```

## Components

| Module | Key functions |
|---|---|
| `autopsy/parsers/php.py` | `parse_php(source: bytes) -> dict`, `flatten(node)`, `literal_value(node)`, `death_reason(name)`, `debug_tree(source)` |
| `autopsy/parsers/forms.py` | `find_forms(source: str) -> list[dict]`, `mask_php(source)` |
| `autopsy/parsers/sql.py` | `detect_sql(text)`, `parse_schema(sql_text)`, `match_table(ref, names)`, `clean_table_name(name)` |
| `autopsy/report.py` | `build_report(root) -> dict`, `resolve_include(target, from_path, known)`, `find_i18n(root)` |
| `autopsy/services.py` | `run_autopsy(corpse) -> Autopsy`, `AutopsyError` |
| `autopsy/views.py` | `run` (POST `/corpses/<pk>/autopsy/run/`), `report` (GET `/corpses/<pk>/autopsy/`) |
| `autopsy/management/commands/autopsy.py` | `autopsy <id>`, `--file`, `--tree` |

### Tree-sitter details
- `Parser(Language(tree_sitter_php.language_php()))`, cached.
- Walk by node type, no queries: `function_definition`, `class_declaration` (+ `base_clause`), `method_declaration`, `include_*`/`require_*` expressions, `function_call_expression`, `subscript_expression`, `variable_name`, `binary_expression` with operator `.`, string types `string`/`encapsulated_string`/`heredoc`/`nowdoc`.
- Concatenations are flattened once at the outermost node; non-literal parts become `?`.

### Removed functions
- PHP 7.0: the whole `mysql_*` extension, `ereg*`, `split`, `spliti`, `sql_regcase`, magic-quotes setters, `call_user_method*`.
- PHP 8.0: `each`, `create_function`, `get_magic_quotes_*`, `money_format`, `__autoload`, and others.

## Report schema (version 1)

```json
{
  "version": 1,
  "summary": {"php_files", "lines_of_code", "pages", "forms", "sql_statements", "tables", "classes",
              "functions", "unresolved_includes", "files_with_errors", "skipped_translation_files"},
  "cause_of_death": {"summary": "...", "functions": [{"name", "count", "why"}], "files": ["..."]},
  "i18n": {"path", "languages", "kept"} | null,
  "pages": [{"path", "includes", "reads": {"GET": []}, "forms", "tables", "redirects", "uses_session"}],
  "tables": [{"name", "columns": [{"name", "type"}], "primary_key", "verbs", "used_in"}],
  "files": [{"path", "lines", "functions", "classes", "includes", "superglobals", "sql", "forms",
             "redirects", "dead_calls", "uses_session", "has_errors"}]
}
```

## Error Handling
- Malformed PHP: tree-sitter is error-tolerant; files are flagged with `has_errors`, never skipped.
- Any exception in `build_report`: autopsy `failed`, traceback in the `Job` log, user sees "The autopsy failed: …".
- Deep syntax trees: recursion limit raised temporarily during the walk.

## Testing Strategy
- `tests/autopsy/test_sql_forms.py`: SQL detection, schema parsing, prefix matching, forms (masked and echoed). Property tests: `test_prop_detect_sql_never_crashes_and_tables_are_clean`, `test_prop_find_forms_never_crashes`.
- `tests/autopsy/test_php.py`: includes with constant prefixes, superglobals, dead calls, SQL in concatenations, redirects, classes. Property test: `test_prop_parse_php_never_crashes` on arbitrary bytes.
- `tests/autopsy/test_report.py`: a miniature TaskFreak-shaped corpse checks pages, per-page reads, schema usage, cause of death, translation skipping, determinism.
- `tests/autopsy/test_autopsy_views.py`: full autopsy on the real TaskFreak demo corpse; view redirects and rendering.
