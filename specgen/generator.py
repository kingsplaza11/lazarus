"""Turn an autopsy report into a Kiro spec: requirements.md, design.md, tasks.md and steering files.

Pure functions only (no Django, no network), so the whole generator is unit-testable.
Every acceptance criterion is EARS and ends with its source, e.g. "(source: login.php:31)".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .naming import (
    app_for_group, common_prefix, field_name, human, model_name, page_group, page_title, page_tokens,
    page_url, table_base, view_name,
)

EARS = re.compile(r"^(WHEN .+ THEN |WHILE .+ |IF .+ THEN |WHERE .+ )?THE .+ SHALL .+$")
VISITOR_PAGES = {"login", "register", "public", "rss", "error", "install", "password"}
LIBRARY_REPLACEMENTS = {
    "jscalendar": "native HTML date inputs",
    "xajax": "HTMX partial requests",
    "jquery": "small vanilla JavaScript or Alpine.js",
    "prototype": "small vanilla JavaScript or Alpine.js",
    "scriptaculous": "CSS transitions or Alpine.js",
    "tinymce": "a maintained rich-text editor",
    "fckeditor": "a maintained rich-text editor",
    "ckeditor": "a maintained rich-text editor",
    "phpmailer": "Django's email framework",
    "smarty": "Django templates",
    "adodb": "the Django ORM",
}


# ---------------------------------------------------------------- helpers

def clean(text: object, limit: int = 80) -> str:
    """Single-line, backtick-free, length-limited text safe to put inside a criterion."""
    value = " ".join(str(text).replace("`", "'").replace("{php}", "…").split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def src(path: str, line: int | None = None) -> str:
    return f"(source: {path}:{line})" if line else f"(source: {path})"


def join_names(items: list[str], limit: int = 6) -> str:
    items = [i for i in items if i]
    if len(items) > limit:
        return ", ".join(items[:limit]) + f" and {len(items) - limit} more"
    if len(items) > 1:
        return ", ".join(items[:-1]) + " and " + items[-1]
    return items[0] if items else ""


@dataclass
class Requirement:
    title: str
    story: str
    criteria: list[str] = field(default_factory=list)
    number: int = 0
    page: str = ""

    def ref(self, index: int) -> str:
        return f"{self.number}.{index}"

    def refs(self) -> list[str]:
        return [self.ref(i + 1) for i in range(len(self.criteria))]


# ---------------------------------------------------------------- data model

def parse_type(sql_type: str) -> tuple[str, list[str]]:
    match = re.match(r"([a-z]+)(?:\((.*?)\))?", (sql_type or "").lower())
    if not match:
        return "", []
    args = [a.strip(" '\"") for a in (match.group(2) or "").split(",") if a.strip()]
    return match.group(1), args


def django_field(sql_type: str, is_pk: bool) -> str:
    base, args = parse_type(sql_type)
    if base in {"int", "integer", "mediumint", "smallint", "bigint", "tinyint"}:
        if is_pk:
            return "models.BigAutoField(primary_key=True)" if base == "bigint" else "models.AutoField(primary_key=True)"
        if base == "tinyint" and args == ["1"]:
            return "models.BooleanField(default=False)"
        return "models.IntegerField(default=0)"
    if base in {"varchar", "char"}:
        length = args[0] if args and args[0].isdigit() else "255"
        return f"models.CharField(max_length={length}, blank=True)"
    if base in {"text", "tinytext", "mediumtext", "longtext"}:
        return "models.TextField(blank=True)"
    if base == "date":
        return "models.DateField(null=True, blank=True)"
    if base in {"datetime", "timestamp"}:
        return "models.DateTimeField(null=True, blank=True)"
    if base == "time":
        return "models.TimeField(null=True, blank=True)"
    if base in {"decimal", "numeric"}:
        digits = args[0] if args and args[0].isdigit() else "10"
        places = args[1] if len(args) > 1 and args[1].isdigit() else "2"
        return f"models.DecimalField(max_digits={digits}, decimal_places={places}, default=0)"
    if base in {"float", "double", "real"}:
        return "models.FloatField(default=0)"
    if base == "enum":
        width = max((len(a) for a in args), default=20)
        return f"models.CharField(max_length={max(width, 1)}, blank=True)"
    if base in {"blob", "mediumblob", "longblob"}:
        return "models.BinaryField(blank=True)"
    return "models.TextField(blank=True)"


def table_app(table: str) -> str:
    """People tables go to `accounts`; link tables and everything else to `core`."""
    people = any(word in table for word in ("member", "user", "account"))
    link = any(word in table for word in ("project", "item", "group", "role"))
    return "accounts" if people and not link else "core"


@dataclass
class ModelSpec:
    table: str
    name: str
    app: str
    fields: list[tuple[str, str]]
    composite: list[str]


def build_models(tables: list[dict]) -> list[ModelSpec]:
    names = [t["name"] for t in tables]
    prefix = common_prefix(names)
    bases = {table_base(n, prefix) for n in names}
    model_of = {t["name"]: model_name(t["name"], prefix, bases) for t in tables}
    pk_owner = {t["primary_key"][0]: t["name"] for t in tables if len(t.get("primary_key", [])) == 1}
    app_of = {t["name"]: table_app(t["name"]) for t in tables}

    models_out = []
    for table in tables:
        pk = table.get("primary_key", [])
        single_pk = pk[0] if len(pk) == 1 else None
        fields, composite = [], []
        for column in table["columns"]:
            col = column["name"]
            owner = pk_owner.get(col)
            if owner and owner != table["name"] and col.endswith("id") and col != single_pk:
                fname = field_name(col[:-2]) or field_name(col)
                target = f"{app_of[owner]}.{model_of[owner]}"
                fields.append((fname, f"models.ForeignKey(\"{target}\", on_delete=models.CASCADE, db_column=\"{col}\")"))
                if col in pk:
                    composite.append(fname)
                continue
            fname = field_name(col)
            fields.append((fname, django_field(column["type"], col == single_pk)))
            if col in pk and not single_pk:
                composite.append(fname)
        models_out.append(ModelSpec(table["name"], model_of[table["name"]], app_of[table["name"]], fields, composite))
    return models_out


def model_code(model: ModelSpec) -> str:
    lines = [f"class {model.name}(models.Model):"]
    lines += [f"    {name} = {definition}" for name, definition in model.fields] or ["    pass"]
    lines += ["", "    class Meta:", f"        db_table = \"{model.table}\""]
    if len(model.composite) > 1:
        fields = ", ".join(f'"{f}"' for f in model.composite)
        lines.append(f"        constraints = [models.UniqueConstraint(fields=[{fields}], name=\"{model.table}_pk\")]")
    return "\n".join(lines)


# ---------------------------------------------------------------- requirements

def page_verbs(page: dict, sql_by_file: dict[str, list[dict]], shared: set[str]) -> dict[str, tuple[set[str], str, int]]:
    """table -> (verbs, file, first line) from the page and the includes only it uses.

    Includes shared by several pages (config, session bootstrap) are skipped: their queries
    run everywhere and would make every page look like it edits the same tables.
    """
    found: dict[str, tuple[set[str], str, int]] = {}
    files = [page["path"]] + [f for f in page.get("includes", []) if f not in shared]
    for file in files:
        for statement in sorted(sql_by_file.get(file, []), key=lambda s: s["line"]):
            for table in statement["tables"]:
                verbs, first_file, first_line = found.get(table, (set(), file, statement["line"]))
                verbs.add(statement["verb"])
                found[table] = (verbs, first_file, first_line)
    return found


def shared_includes(pages: list[dict]) -> set[str]:
    counts: dict[str, int] = {}
    for page in pages:
        for inc in set(page.get("includes", [])):
            counts[inc] = counts.get(inc, 0) + 1
    return {inc for inc, count in counts.items() if count > 1}


def user_story(page: dict, title: str, noun: str) -> str:
    tokens = page_tokens(page["path"])
    visitor = any(t in VISITOR_PAGES for t in tokens)
    role = "visitor" if visitor else "signed-in user"
    last = tokens[-1] if tokens else ""
    purposes = {
        "login": "sign in", "logout": "sign out", "register": "create an account", "password": "change my password",
        "list": f"see the list of {noun}s", "edit": f"create and edit {noun}s", "details": f"view {noun} details",
        "view": f"view {noun} details", "rss": "follow updates in a feed reader", "print": "print a clean list",
        "error": "understand what went wrong", "install": "install the application", "public": "see public information",
    }
    purpose = purposes.get(last) or purposes.get(tokens[0] if tokens else "", f"use the {title} screen")
    return f"As a {role}, I want to {purpose}, so that the resurrected app does everything the original {title} page did."


def page_requirement(page: dict, sql_by_file: dict, model_by_table: dict[str, ModelSpec], shared: set[str] = frozenset()) -> Requirement:
    path, title = page["path"], page_title(page["path"])
    tokens = page_tokens(path)
    noun = next((t for t in tokens if t not in {"list", "edit", "details", "view", "index", "xajax"}), "item")
    req = Requirement(title=f"{title} page", story=user_story(page, title, noun), page=path)
    c = req.criteria
    c.append(f"WHEN a user opens the {title} page THEN THE system SHALL display the {title} screen at {page_url(path)}. {src(path, 1)}")

    form_fields = {f["name"] for form in page.get("forms", []) for f in form["fields"]}
    for form in page.get("forms", []):
        names = [clean(f["name"], 30) for f in form["fields"] if "{php}" not in f["name"] and "?" not in f["name"]]
        fields = f"the fields {join_names(names)}" if names else "its fields"
        target = clean(form["action"], 40) or "the same page"
        c.append(f"WHEN a user submits the {title} form with {fields} THEN THE system SHALL process the submission as a {form['method']} request to {target}. {src(form['file'], form['line'])}")

    for key in page.get("reads", {}).get("GET", []):
        if key == "?":
            continue
        if key == "*":
            c.append(f"WHEN the {title} page is requested with query parameters THEN THE system SHALL handle them as the original did. {src(path)}")
        else:
            c.append(f"WHEN the {title} page is requested with the '{clean(key, 30)}' parameter THEN THE system SHALL apply that value as the original did. {src(path)}")
    for key in page.get("reads", {}).get("POST", []):
        if key in ("?", "*") or key in form_fields:
            continue
        c.append(f"WHEN the {title} page receives a submitted '{clean(key, 30)}' value THEN THE system SHALL process it as the original did. {src(path)}")

    verbs_text = {"SELECT": "show", "INSERT": "create", "UPDATE": "update", "DELETE": "delete", "REPLACE": "create or replace"}
    for table, (verbs, file, line) in sorted(page_verbs(page, sql_by_file, set(shared)).items()):
        model = model_by_table.get(table)
        if not model:
            continue
        actions = [verbs_text[v] for v in ("SELECT", "INSERT", "UPDATE", "DELETE", "REPLACE") if v in verbs]
        if actions:
            c.append(f"THE system SHALL {join_names(actions)} {human(model.name)} records on the {title} page. {src(file, line)}")

    for redirect in page.get("redirects", [])[:3]:
        target = clean(redirect["target"], 50) or "another page"
        c.append(f"IF the original conditions for leaving the {title} page are met THEN THE system SHALL redirect the user to {target}. {src(redirect['file'], redirect['line'])}")

    if page.get("uses_session") and "login" in tokens:
        c.append(f"WHEN a user signs in successfully THEN THE system SHALL start an authenticated session. {src(path)}")
    if "logout" in tokens:
        c.append(f"WHEN a user opens the {title} page THEN THE system SHALL end the user's session. {src(path)}")
    return req


def data_requirement(models_: list[ModelSpec], tables: list[dict]) -> Requirement:
    req = Requirement(
        title="Data model",
        story="As the operator, I want every record type of the original database preserved, so that existing data can be migrated without loss.",
    )
    by_table = {m.table: m for m in models_}
    for table in tables:
        columns = join_names([c["name"] for c in table["columns"]], limit=8)
        req.criteria.append(f"THE system SHALL store {human(by_table[table['name']].name)} records with the fields {columns}. {src('schema: ' + table['name'])}")
    return req


def modernisation_requirement(report: dict) -> Requirement:
    req = Requirement(
        title="Modernisation",
        story="As the operator, I want the resurrected app to run safely on a supported platform, so that it can stay online for years.",
    )
    cause = report.get("cause_of_death", {})
    dead = [f["name"] for f in cause.get("functions", [])]
    if dead:
        req.criteria.append(f"THE system SHALL NOT depend on any of the {len(dead)} removed PHP functions found by the autopsy, such as {join_names(dead, 3)}. {src('cause of death')}")
    req.criteria.append(f"THE system SHALL perform all database access through parameterised queries. {src('autopsy: ' + str(report['summary']['sql_statements']) + ' SQL statements')}")
    req.criteria.append(f"THE system SHALL protect every form against cross-site request forgery. {src('autopsy: ' + str(report['summary']['forms']) + ' forms')}")
    password_tables = [t["name"] for t in report.get("tables", []) if any("pass" in c["name"] for c in t["columns"])]
    if password_tables:
        req.criteria.append(f"WHERE a record stores a password THE system SHALL keep only a salted one-way hash of it. {src('schema: ' + password_tables[0])}")
    for lib in report.get("libraries", []):
        replacement = LIBRARY_REPLACEMENTS.get(lib["name"].lower(), "a maintained equivalent")
        req.criteria.append(f"THE system SHALL replace the bundled {lib['name']} library with {replacement}. {src(lib['path'])}")
    return req


def look_requirement(report: dict) -> Requirement:
    """Always present: the rebuild must not ship unstyled. Cites the original stylesheets when found."""
    req = Requirement(
        title="Look and feel",
        story="As a returning user, I want the resurrected app to look finished and familiar, so that I can use it without relearning it.",
    )
    assets = report.get("assets") or {}
    sheets = assets.get("stylesheets", [])
    skins = assets.get("skins", [])
    req.criteria.append(f"THE system SHALL style every page through one shared stylesheet linked from the base template. {src(sheets[0]['path'] if sheets else 'autopsy: no stylesheets found')}")
    if sheets:
        req.criteria.append(f"THE system SHALL keep the layout, colours, images and typography of the original stylesheet {sheets[0]['path']}, provided in legacy-assets/. {src(sheets[0]['path'])}")
    else:
        req.criteria.append(f"THE system SHALL present forms, tables and navigation with consistent spacing, readable type and clear focus states. {src('autopsy: no stylesheets found')}")
    if skins and len(skins[0]["names"]) > 1:
        names = join_names(skins[0]["names"], 6)
        req.criteria.append(f"WHERE more than one skin is offered THE system SHALL let the user choose between the original skins {names}. {src(skins[0]['path'])}")
    req.criteria.append(f"THE system SHALL show the signed-in user and the main navigation on every page after sign-in. {src('autopsy: ' + str(report['summary']['pages']) + ' pages')}")
    req.criteria.append(f"THE system SHALL lay out every page so it remains usable on a phone-sized screen. {src('modernisation')}")
    return req


def i18n_requirement(report: dict) -> Requirement | None:
    i18n = report.get("i18n")
    if not i18n:
        return None
    req = Requirement(
        title="Translations",
        story="As a user who doesn't read English, I want the interface in my language, so that I can use the app as before.",
    )
    langs = i18n["languages"]
    req.criteria.append(f"WHERE translations are enabled THE system SHALL offer the interface in the {len(langs)} languages of the original: {join_names(langs, 8)}. {src(i18n['path'])}")
    req.criteria.append(f"THE system SHALL use {i18n['kept']} as the default language. {src(i18n['path'] + '/' + i18n['kept'])}")
    return req


def build_requirements(report: dict, models_: list[ModelSpec]) -> list[Requirement]:
    sql_by_file = {f["path"]: f["sql"] for f in report.get("files", [])}
    model_by_table = {m.table: m for m in models_}
    pages = sorted(report.get("pages", []), key=lambda p: (page_group(p["path"]) != "Authentication", page_group(p["path"]), p["path"]))
    shared = shared_includes(pages)
    reqs = [page_requirement(p, sql_by_file, model_by_table, shared) for p in pages]
    if report.get("tables"):
        reqs.append(data_requirement(models_, report["tables"]))
    reqs.append(modernisation_requirement(report))
    reqs.append(look_requirement(report))
    extra = i18n_requirement(report)
    if extra:
        reqs.append(extra)
    for number, req in enumerate(reqs, start=1):
        req.number = number
    return reqs


# ---------------------------------------------------------------- documents

def requirements_md(name: str, report: dict, reqs: list[Requirement], intro: str) -> str:
    out = [f"# Requirements Document: {name} (resurrected)", "", "## Introduction", "", intro, "", "## Requirements", ""]
    for req in reqs:
        out += [f"### Requirement {req.number}: {req.title}", "", f"**User Story:** {req.story}", "", "#### Acceptance Criteria"]
        out += [f"{i}. {criterion}" for i, criterion in enumerate(req.criteria, start=1)]
        out.append("")
    return "\n".join(out)


def default_intro(name: str, report: dict) -> str:
    s = report["summary"]
    cause = report.get("cause_of_death", {}).get("summary")
    parts = [f"{name} is a legacy PHP application recovered by Lazarus."]
    if cause:
        parts.append(f"Cause of death: {cause}")
    parts.append(
        f"This specification describes its {s['pages']} pages, {s['tables']} database tables and {s['forms']} forms, "
        "so it can be rebuilt as a modern Django application that behaves the same way. "
        "Every acceptance criterion cites the legacy source it was recovered from."
    )
    return " ".join(parts)


def design_md(name: str, report: dict, models_: list[ModelSpec], reqs: list[Requirement]) -> str:
    pages = report.get("pages", [])
    out = [
        f"# Design Document: {name} (resurrected)", "",
        "## Overview", "",
        f"A Django 6 rebuild of {name}. Two apps: `accounts` (sign-in, registration, user management) and `core` "
        "(everything else). Server-rendered templates, HTMX for in-page updates, the Django ORM for all data access.", "",
        "## Architecture", "",
        "```",
        "Browser ──► Django URLs ──► views (accounts, core) ──► templates (+ HTMX partials)",
        "                                   │",
        "                                   └──► Django ORM ──► database (same tables as the original)",
        "```", "",
        "## URL map", "",
        "| Legacy page | New URL | App | View |",
        "|---|---|---|---|",
    ]
    for page in sorted(pages, key=lambda p: p["path"]):
        group = page_group(page["path"])
        out.append(f"| `{page['path']}` | `{page_url(page['path'])}` | {app_for_group(group)} | `{view_name(page['path'])}` |")
    out += ["", "## Data Models", ""]
    if models_:
        out.append("Field names follow the legacy columns; `db_table` and `db_column` keep the original schema so existing data loads directly.")
        out.append("")
        for model in models_:
            out += [f"### {model.name} (`{model.app}` app)", "", "```python", model_code(model), "```", ""]
    else:
        out.append("No CREATE TABLE statements were found; derive models from the SQL statements in the autopsy report.")
        out.append("")
    out += ["## Replacing what killed it", "", "| Legacy | Replacement |", "|---|---|"]
    dead = report.get("cause_of_death", {}).get("functions", [])
    if any(f["name"].startswith("mysql_") for f in dead):
        out.append("| `mysql_*` functions | Django ORM querysets (parameterised by default) |")
    if any(f["name"].startswith(("ereg", "split")) for f in dead):
        out.append("| `ereg*` / `split` | Python `re` module |")
    if any(f["name"] in {"each", "create_function"} for f in dead):
        out.append("| `each` / `create_function` | plain loops and functions |")
    out.append("| Hand-built sessions | `django.contrib.auth` and sessions |")
    for lib in report.get("libraries", []):
        out.append(f"| bundled `{lib['name']}` | {LIBRARY_REPLACEMENTS.get(lib['name'].lower(), 'a maintained equivalent')} |")
    out += [
        "", "## Error Handling", "",
        "- Missing records return 404; forms re-render with field errors; every write is in a transaction.",
        "- Legacy error page behaviour maps to Django's 404/500 templates.", "",
        "## Testing Strategy", "",
        "- One view test per legacy page: status code, key content, and form submission where a form exists.",
        "- Model tests for each table, including uniqueness of composite keys.",
        "- Parity check: replay recorded requests against the legacy app and the rebuild with `lazarus parity`.",
    ]
    return "\n".join(out) + "\n"


def tasks_md(name: str, report: dict, models_: list[ModelSpec], reqs: list[Requirement]) -> str:
    by_title = {r.title: r for r in reqs}
    modern = by_title.get("Modernisation")
    data = by_title.get("Data model")
    page_reqs = [r for r in reqs if r.page]
    page_by_path = {p["path"]: p for p in report.get("pages", [])}
    n = 1
    out = [f"# Implementation Plan: {name} (resurrected)", ""]

    look = by_title.get("Look and feel")
    setup_refs = (modern.refs()[:3] if modern else []) + (look.refs()[:1] if look else [])
    out += [f"- [ ] {n}. Set up the Django project with `accounts` and `core` apps, a styled `base.html` with navigation, and HTMX",
            f"  - _Requirements: {', '.join(setup_refs) or '-'}_", ""]
    n += 1
    if data and models_:
        out += [f"- [ ] {n}. Create the data models"]
        for i, model in enumerate(models_, start=1):
            out += [f"  - [ ] {n}.{i} `{model.name}` in `{model.app}/models.py` (table `{model.table}`)",
                    f"    - _Requirements: {data.ref(i)}_"]
        out += [f"  - [ ] {n}.{len(models_) + 1} Make migrations; write a loader for data from the legacy database",
                f"    - _Requirements: {', '.join(data.refs()[:3])}_", ""]
        n += 1

    groups: dict[str, list[tuple[Requirement, dict]]] = {}
    for req in page_reqs:
        page = page_by_path[req.page]
        groups.setdefault(page_group(page["path"]), []).append((req, page))
    for group, items in groups.items():
        out.append(f"- [ ] {n}. {group}: build the pages")
        for i, (req, page) in enumerate(items, start=1):
            out += [f"  - [ ] {n}.{i} `{view_name(page['path'])}` view at `{page_url(page['path'])}` replacing `{page['path']}`, with template and tests",
                    f"    - _Requirements: {', '.join(req.refs())}_"]
        out.append("")
        n += 1

    if modern:
        out += [f"- [ ] {n}. Modernise: remove legacy dependencies, harden forms and passwords, replace bundled libraries",
                f"  - _Requirements: {', '.join(modern.refs())}_", ""]
        n += 1
    if look:
        sheets = (report.get("assets") or {}).get("stylesheets", [])
        source = f" from `legacy-assets/{sheets[0]['path']}` (included in the download, with its images)" if sheets else ""
        out += [f"- [ ] {n}. Look and feel: port the original styling{source} into `static/` and apply it to every template",
                f"  - _Requirements: {', '.join(look.refs())}_", ""]
        n += 1
    i18n = by_title.get("Translations")
    if i18n:
        out += [f"- [ ] {n}. Translations with Django i18n, porting the original language files",
                f"  - _Requirements: {', '.join(i18n.refs())}_", ""]
        n += 1
    out += [f"- [ ] {n}. Verify parity with the original",
            "  - Run the test suite, then `lazarus parity` against the legacy app; fix differences until the score is acceptable",
            f"  - _Requirements: {', '.join(r.ref(1) for r in page_reqs[:8])}_", ""]
    return "\n".join(out)


def steering(name: str, report: dict, models_: list[ModelSpec]) -> dict[str, str]:
    s = report["summary"]
    pages = ", ".join(f"`{p['path']}`" for p in report.get("pages", []))
    product = (
        f"---\ninclusion: always\n---\n\n# Product: {name} (resurrected)\n\n"
        f"A faithful Django rebuild of the legacy PHP app {name}, recovered by Lazarus.\n\n"
        f"- Original size: {s['php_files']} PHP files, {s['lines_of_code']} lines, {s['pages']} pages, {s['tables']} tables.\n"
        f"- Legacy pages to preserve: {pages}.\n"
        "- Goal: same features and behaviour as the original, on a supported, secure stack.\n"
        "- Do not add features the original did not have until parity is reached.\n"
        "- The original stylesheets and images are in `legacy-assets/`; reuse them rather than inventing a new look.\n"
    )
    tech = (
        "---\ninclusion: always\n---\n\n# Tech stack\n\n"
        "- Python 3.12+, Django 6, SQLite for development (PostgreSQL in production)\n"
        "- Server-rendered Django templates; HTMX for partial updates; no frontend build step\n"
        "- `django.contrib.auth` for accounts and sessions; passwords hashed by Django\n"
        "- All data access through the ORM (no raw SQL string building)\n"
        "- CSRF protection on every form; `pytest` + `pytest-django` for tests\n"
        "- Keep legacy table and column names via `db_table` / `db_column` so old data loads directly\n"
    )
    mapping = "\n".join(
        f"- `{p['path']}` → `{app_for_group(page_group(p['path']))}/views.py::{view_name(p['path'])}` at `{page_url(p['path'])}`"
        for p in sorted(report.get("pages", []), key=lambda p: p["path"])
    )
    model_lines = "\n".join(f"- `{m.table}` → `{m.app}.{m.name}`" for m in models_)
    structure = (
        "---\ninclusion: always\n---\n\n# Structure\n\n"
        "```\nmanage.py\nconfig/        settings, urls\naccounts/      auth, users\ncore/          everything else\n"
        "templates/     base.html, per-app templates\ntests/\n```\n\n"
        f"## Legacy page → new view\n{mapping}\n\n## Legacy table → model\n{model_lines or '- (no tables found)'}\n"
    )
    return {"product.md": product, "tech.md": tech, "structure.md": structure}


# ---------------------------------------------------------------- entry point

def generate_spec(report: dict, name: str, intro: str | None = None) -> dict[str, str]:
    """Return {relative path: content} for the generated .kiro/ folder."""
    models_ = build_models(report.get("tables", []))
    reqs = build_requirements(report, models_)
    spec_dir = "specs/" + (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "app") + "-resurrection"
    files = {
        f"{spec_dir}/requirements.md": requirements_md(name, report, reqs, intro or default_intro(name, report)),
        f"{spec_dir}/design.md": design_md(name, report, models_, reqs),
        f"{spec_dir}/tasks.md": tasks_md(name, report, models_, reqs),
    }
    for filename, content in steering(name, report, models_).items():
        files[f"steering/{filename}"] = content
    return files


def criteria_of(requirements_text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"^\d+\. (.*)$", requirements_text, re.M)]


def validate_ears(requirements_text: str) -> tuple[int, list[str]]:
    """Return (number of criteria, list of criteria that are not valid EARS)."""
    criteria = criteria_of(requirements_text)
    return len(criteria), [c for c in criteria if not EARS.match(c)]
