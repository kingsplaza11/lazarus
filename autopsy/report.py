"""Assemble the full autopsy report for a stored corpse."""
from __future__ import annotations

import posixpath
from collections import Counter, deque
from pathlib import Path

from intake.tree import detect_language, iter_files

from .parsers.forms import find_forms
from .parsers.php import parse_php
from .parsers.sql import match_table, parse_schema

I18N_DIR_NAMES = {"language", "languages", "lang", "locale", "locales", "i18n"}
PREFERRED_LANGUAGES = ("en", "english", "en_us", "en-us")
REPORT_VERSION = 1


def find_i18n(root: Path) -> dict | None:
    """Find a translations folder with two or more language subfolders."""
    for folder in sorted(p for p in root.rglob("*") if p.is_dir()):
        if folder.name.lower() in I18N_DIR_NAMES:
            languages = sorted(c.name for c in folder.iterdir() if c.is_dir())
            if len(languages) >= 2:
                kept = next((l for l in languages if l.lower() in PREFERRED_LANGUAGES), languages[0])
                return {"path": folder.relative_to(root).as_posix(), "languages": languages, "kept": kept}
    return None


def resolve_include(target: str, from_path: str, known: set[str]) -> str | None:
    """Match an include target (possibly with dynamic "?" parts) to a known file path."""
    cleaned = target.replace("\\", "/")
    if "?" in cleaned:
        cleaned = cleaned.rsplit("?", 1)[-1]
    cleaned = cleaned.strip().lstrip("/")
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    if not cleaned or not cleaned.lower().endswith((".php", ".inc", ".php3", ".php4", ".php5", ".html", ".tpl")):
        return None
    relative = posixpath.normpath(posixpath.join(posixpath.dirname(from_path), cleaned))
    if relative in known:
        return relative
    if cleaned in known:
        return cleaned
    candidates = sorted(p for p in known if p.endswith("/" + cleaned.lstrip("./")) or p == cleaned.lstrip("./"))
    if not candidates:
        return None
    from_dir = posixpath.dirname(from_path)
    candidates.sort(key=lambda p: (not p.startswith(from_dir + "/") if from_dir else False, p.count("/"), p))
    return candidates[0]


def _reachable(start: str, graph: dict[str, list[str]]) -> list[str]:
    seen, queue, order = {start}, deque([start]), []
    while queue:
        current = queue.popleft()
        for nxt in graph.get(current, []):
            if nxt not in seen:
                seen.add(nxt)
                order.append(nxt)
                queue.append(nxt)
    return order


def build_report(root: Path) -> dict:
    """Analyse every PHP file under `root` and return the autopsy report (JSON-serialisable)."""
    root = Path(root)
    i18n = find_i18n(root)
    skipped_translations = 0

    analyses: dict[str, dict] = {}
    for path in iter_files(root):
        if detect_language(path.name) != "PHP":
            continue
        rel = path.relative_to(root).as_posix()
        if i18n and rel.startswith(i18n["path"] + "/") and not rel.startswith(f"{i18n['path']}/{i18n['kept']}/"):
            skipped_translations += 1
            continue
        source = path.read_bytes()
        analysis = parse_php(source)
        analysis["forms"] = find_forms(source.decode("utf-8", "replace"))
        analysis["path"] = rel
        analysis["lines"] = source.count(b"\n") + 1
        analyses[rel] = analysis

    # Database schema from .sql files.
    tables: list[dict] = []
    for path in iter_files(root):
        if path.suffix.lower() == ".sql":
            tables.extend(parse_schema(path.read_text("utf-8", "replace")))
    schema_names = [t["name"] for t in tables]

    # Resolve includes into a graph.
    known = set(analyses)
    graph: dict[str, list[str]] = {}
    unresolved = 0
    for rel, analysis in analyses.items():
        targets = []
        for inc in analysis["includes"]:
            resolved = resolve_include(inc["target"], rel, known)
            inc["resolved"] = resolved
            if resolved and resolved != rel:
                targets.append(resolved)
            elif not resolved:
                unresolved += 1
        graph[rel] = sorted(set(targets))
        for statement in analysis["sql"]:
            statement["tables"] = sorted({match_table(t, schema_names) for t in statement["tables"]})

    included = {t for targets in graph.values() for t in targets}

    # Pages: files nothing includes, that take input, show a form, or sit at the root.
    pages = []
    for rel in sorted(analyses):
        if rel in included:
            continue
        analysis = analyses[rel]
        is_root = "/" not in rel
        if not (is_root or analysis["superglobals"] or analysis["forms"] or analysis["redirects"]):
            continue
        reach = [rel] + _reachable(rel, graph)
        reads: dict[str, list[str]] = {}
        forms, page_tables, redirects, session = [], set(), [], False
        for file in reach:
            a = analyses[file]
            for kind, keys in a["superglobals"].items():
                bucket = reads.setdefault(kind, [])
                bucket.extend(k for k in keys if k not in bucket)
            forms.extend({**f, "file": file} for f in a["forms"])
            for statement in a["sql"]:
                page_tables.update(statement["tables"])
            redirects.extend({**r, "file": file} for r in a["redirects"])
            session = session or a["uses_session"]
        pages.append({
            "path": rel,
            "includes": graph.get(rel, []),
            "reads": {k: sorted(v) for k, v in sorted(reads.items())},
            "forms": forms,
            "tables": sorted(page_tables),
            "redirects": redirects,
            "uses_session": session,
        })

    # Table usage across all files.
    usage: dict[str, dict] = {name: {"verbs": set(), "files": set()} for name in schema_names}
    for rel, analysis in analyses.items():
        for statement in analysis["sql"]:
            for table in statement["tables"]:
                entry = usage.setdefault(table, {"verbs": set(), "files": set()})
                entry["verbs"].add(statement["verb"])
                entry["files"].add(rel)
    for table in tables:
        entry = usage.get(table["name"], {"verbs": set(), "files": set()})
        table["verbs"] = sorted(entry["verbs"])
        table["used_in"] = sorted(entry["files"])

    # Cause of death.
    dead = Counter(call["name"] for a in analyses.values() for call in a["dead_calls"])
    dead_files = sorted(rel for rel, a in analyses.items() if a["dead_calls"])
    reasons = {call["name"]: call["why"] for a in analyses.values() for call in a["dead_calls"]}
    cause = None
    if dead:
        total = sum(dead.values())
        versions = sorted({reasons[name] for name in dead})
        cause = (
            f"{total} call{'s' if total != 1 else ''} to {len(dead)} function{'s' if len(dead) != 1 else ''} "
            f"{' and '.join(versions)}, in {len(dead_files)} file{'s' if len(dead_files) != 1 else ''}."
        )

    files = [
        {
            "path": rel,
            "lines": a["lines"],
            "functions": a["functions"],
            "classes": a["classes"],
            "includes": a["includes"],
            "superglobals": a["superglobals"],
            "sql": a["sql"],
            "forms": a["forms"],
            "redirects": a["redirects"],
            "dead_calls": a["dead_calls"],
            "uses_session": a["uses_session"],
            "has_errors": a["has_errors"],
        }
        for rel, a in sorted(analyses.items())
    ]

    return {
        "version": REPORT_VERSION,
        "summary": {
            "php_files": len(analyses),
            "lines_of_code": sum(a["lines"] for a in analyses.values()),
            "pages": len(pages),
            "forms": sum(len(a["forms"]) for a in analyses.values()),
            "sql_statements": sum(len(a["sql"]) for a in analyses.values()),
            "tables": len(tables),
            "classes": sum(len(a["classes"]) for a in analyses.values()),
            "functions": sum(len(a["functions"]) for a in analyses.values()),
            "unresolved_includes": unresolved,
            "files_with_errors": sum(1 for a in analyses.values() if a["has_errors"]),
            "skipped_translation_files": skipped_translations,
        },
        "cause_of_death": {
            "summary": cause,
            "functions": [{"name": n, "count": c, "why": reasons[n]} for n, c in dead.most_common()],
            "files": dead_files,
        },
        "i18n": i18n,
        "pages": pages,
        "tables": tables,
        "files": files,
    }
