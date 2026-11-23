"""Resurrection check: score a rebuilt app against the legacy app's autopsy.

Pure Python (standard library only) so it runs anywhere and is fully testable.
It never sends POST requests except the single sign-in, and it checks the
sign-out page last so the session stays alive for the other pages.
"""
from __future__ import annotations

import http.cookiejar
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

WEIGHTS = {"pages": 0.35, "forms": 0.20, "tables": 0.20, "safety": 0.15, "look": 0.10}
SKIP_DIRS = {".venv", "venv", "env", "node_modules", ".git", "legacy-assets", "__pycache__", "staticfiles", "media", "uploads"}
IGNORED_FIELD_TYPES = {"submit", "button", "image", "reset", "hidden"}


# ------------------------------------------------------------------ HTTP

@dataclass
class Response:
    status: int
    url: str
    location: str = ""
    body: str = ""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    """A tiny browser: cookies, no automatic redirects, manual follow."""

    def __init__(self, base_url: str, timeout: int = 15):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), _NoRedirect())

    def absolute(self, path: str) -> str:
        return urllib.parse.urljoin(self.base + "/", path)

    def _open(self, request: urllib.request.Request) -> Response:
        try:
            with self.opener.open(request, timeout=self.timeout) as resp:
                return Response(resp.status, resp.geturl(), "", resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8", "replace") if err.fp else ""
            return Response(err.code, request.full_url, err.headers.get("Location", "") or "", body)
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            return Response(0, request.full_url, "", str(err))

    def get(self, path: str) -> Response:
        return self._open(urllib.request.Request(self.absolute(path), headers={"User-Agent": "Lazarus-check/1.0"}))

    def post(self, path: str, data: dict, referer: str) -> Response:
        body = urllib.parse.urlencode(data).encode()
        request = urllib.request.Request(
            self.absolute(path), data=body,
            headers={"User-Agent": "Lazarus-check/1.0", "Referer": referer,
                     "Content-Type": "application/x-www-form-urlencoded"},
        )
        return self._open(request)

    def follow(self, path: str, hops: int = 4) -> Response:
        response = self.get(path)
        while response.status in (301, 302, 303, 307, 308) and response.location and hops > 0:
            response = self.get(urllib.parse.urljoin(response.url, response.location))
            hops -= 1
        return response


# ------------------------------------------------------------------ HTML

class PageParser(HTMLParser):
    """Collects forms (with field names and types), all field names, and stylesheet links."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.forms: list[dict] = []
        self.fields: dict[str, str] = {}
        self.stylesheets: list[str] = []
        self._form: dict | None = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "form":
            self._form = {"action": a.get("action", ""), "method": a.get("method", "get").upper(), "fields": {}}
            self.forms.append(self._form)
        elif tag in ("input", "select", "textarea", "button") and a.get("name"):
            kind = a.get("type", "text").lower() if tag == "input" else tag
            self.fields[a["name"]] = kind
            if self._form is not None:
                self._form["fields"][a["name"]] = {"type": kind, "value": a.get("value", "")}
        elif tag == "link" and "stylesheet" in a.get("rel", "").lower() and a.get("href"):
            self.stylesheets.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "form":
            self._form = None


def parse_page(html: str) -> PageParser:
    parser = PageParser()
    try:
        parser.feed(html or "")
    except Exception:  # malformed HTML must never break the check
        pass
    return parser


def norm_field(name: str) -> str:
    return re.sub(r"\[\]$", "", (name or "").strip().lower())


DB_FIELD = re.compile(r"(^|_)(host|user|username|pass|password|passwd|base|db|dbname|database|table|port|prefix)$")


def is_database_form(fields: list[str]) -> bool:
    """Installer/import forms asking for database credentials: replaced by settings and migrations in a rebuild."""
    if len(fields) < 3:
        return False
    db_like = [f for f in fields if DB_FIELD.search(f)]
    return len(db_like) / len(fields) >= 0.6


def legacy_fields(form: dict) -> list[str]:
    names = []
    for f in form.get("fields", []):
        name = f.get("name", "")
        if f.get("type", "text").lower() in IGNORED_FIELD_TYPES:
            continue
        if not name or any(ch in name for ch in "{}?$<>"):
            continue
        names.append(norm_field(name))
    return sorted(set(names))


# ------------------------------------------------------------------ URL mapping

def page_tokens(path: str) -> list[str]:
    stem = path[:-4] if path.lower().endswith(".php") else path
    return [t for t in re.split(r"[/_.\-]+", stem.lower()) if t]


def expected_url(path: str) -> str:
    tokens = [t for t in page_tokens(path) if t not in {"index", "xajax", "ajax", "inc", "php"}]
    return "/" + "/".join(tokens) + "/" if tokens else "/"


def candidate_urls(path: str) -> list[str]:
    first = expected_url(path)
    out = [first, first.rstrip("/") or "/", "/" + path]
    seen, unique = set(), []
    for url in out:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


# ------------------------------------------------------------------ checks

@dataclass
class Category:
    name: str
    items: list[dict] = field(default_factory=list)

    def add(self, label: str, score: float, detail: str = "") -> None:
        self.items.append({"label": label, "score": round(max(0.0, min(1.0, score)), 3), "detail": detail})

    @property
    def score(self) -> float:
        return sum(i["score"] for i in self.items) / len(self.items) if self.items else 0.0

    @property
    def passed(self) -> int:
        return sum(1 for i in self.items if i["score"] >= 0.999)

    def as_dict(self) -> dict:
        return {"score": round(self.score, 3), "passed": self.passed, "total": len(self.items), "items": self.items}


def find_page(client: Client, path: str) -> tuple[str, Response]:
    """Try the expected URL, then variants. Return (url used, first response)."""
    last = None
    for url in candidate_urls(path):
        response = client.get(url)
        last = (url, response)
        if response.status and response.status != 404:
            return url, response
    return last


def sign_in(client: Client, pages: list[dict], username: str, password: str) -> tuple[bool, str]:
    login = next((p for p in pages if "login" in page_tokens(p["path"])), None)
    if login is None:
        return False, "No legacy login page to test."
    url, _ = find_page(client, login["path"])
    page = client.follow(url)
    parsed = parse_page(page.body)
    form = next((f for f in parsed.forms if any(v["type"] == "password" for v in f["fields"].values())), None)
    if form is None:
        return False, f"No password form found at {url}."
    data = {name: info["value"] for name, info in form["fields"].items() if info["type"] == "hidden"}
    user_field = next((n for n, v in form["fields"].items() if v["type"] in ("text", "email")), None)
    pass_field = next(n for n, v in form["fields"].items() if v["type"] == "password")
    if user_field is None:
        return False, "Sign-in form has no username field."
    data[user_field], data[pass_field] = username, password
    target = form["action"] or page.url
    response = client.post(urllib.parse.urljoin(page.url, target), data, referer=page.url)
    if response.status in (301, 302, 303) and "login" not in response.location.lower():
        return True, f"Signed in as {username} via {url}."
    after = parse_page(response.body)
    if response.status == 200 and not any(v == "password" for v in after.fields.values()):
        return True, f"Signed in as {username} via {url}."
    return False, f"Sign-in at {url} did not succeed (status {response.status})."


def check_pages_and_forms(client: Client, report: dict, username: str | None, password: str | None):
    pages = sorted(report.get("pages", []), key=lambda p: "logout" in page_tokens(p["path"]))
    page_cat, form_cat, look_cat = Category("pages"), Category("forms"), Category("look")
    notes: list[str] = []

    # Read every page signed out first: some pages (sign-in, registration) redirect signed-in users away.
    anonymous_fields: dict[str, set[str]] = {}
    for page in pages:
        if "logout" in page_tokens(page["path"]):
            continue
        url, first = find_page(client, page["path"])
        if first.status and first.status < 400:
            anonymous_fields[page["path"]] = {norm_field(n) for n in parse_page(client.follow(url).body).fields}

    signed_in = False
    if username and password:
        signed_in, message = sign_in(client, pages, username, password)
        notes.append(message)
    else:
        notes.append("No credentials given: pages were checked signed out only.")

    styled, fetched = 0, 0
    for page in pages:
        url, first = find_page(client, page["path"])
        status = first.status
        if status == 0:
            page_cat.add(page["path"], 0, f"{url}: no response ({first.body[:80]})")
            continue
        if status == 404:
            page_cat.add(page["path"], 0, f"none of {', '.join(candidate_urls(page['path']))} exist (404)")
            continue
        if status >= 500:
            page_cat.add(page["path"], 0, f"{url}: server error {status}")
            continue
        final = client.follow(url) if "logout" not in page_tokens(page["path"]) else first
        if final.status >= 500:
            page_cat.add(page["path"], 0.5, f"{url}: responds {status}, but the page behind it errors ({final.status})")
            continue
        page_cat.add(page["path"], 1, f"{url}: {status}" + (f" → {final.status}" if final.status != status else ""))

        parsed = parse_page(final.body)
        if final.status == 200:
            fetched += 1
            styled += 1 if parsed.stylesheets else 0
        new_fields = {norm_field(n) for n in parsed.fields} | anonymous_fields.get(page["path"], set())
        for form in page.get("forms", []):
            wanted = legacy_fields(form)
            if not wanted:
                continue
            if is_database_form(wanted):
                notes.append(f"{form.get('file', page['path'])}:{form.get('line', '?')} asks for database credentials "
                             "(installer/import); not applicable to a rebuild that uses settings and migrations.")
                continue
            found = [f for f in wanted if f in new_fields]
            missing = [f for f in wanted if f not in new_fields]
            detail = f"{url}: {len(found)}/{len(wanted)} fields" + (f"; missing {', '.join(missing)}" if missing else "")
            form_cat.add(f"{form.get('file', page['path'])}:{form.get('line', '?')}", len(found) / len(wanted), detail)

    look_cat.add("Pages load a stylesheet", styled / fetched if fetched else 0, f"{styled}/{fetched} pages link a stylesheet")
    return page_cat, form_cat, look_cat, notes, signed_in


def sqlite_schema(db_path: Path) -> dict[str, set[str]]:
    uri = f"file:{db_path}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {n.lower(): {r[1].lower() for r in conn.execute(f'PRAGMA table_info("{n}")')} for n in names}


def check_tables(report: dict, db_path: Path | None) -> tuple[Category, str]:
    cat = Category("tables")
    tables = report.get("tables", [])
    if not tables:
        return cat, "The legacy app had no CREATE TABLE schema to compare."
    if not db_path or not Path(db_path).is_file():
        for table in tables:
            cat.add(table["name"], 0, "no SQLite database given (--db)")
        return cat, "Tables not checked: pass --db with the rebuild's SQLite file."
    schema = sqlite_schema(Path(db_path))
    for table in tables:
        name = table["name"].lower()
        if name not in schema:
            cat.add(table["name"], 0, "table missing")
            continue
        wanted = [c["name"].lower() for c in table["columns"]]
        found = [c for c in wanted if c in schema[name]]
        missing = [c for c in wanted if c not in schema[name]]
        cat.add(table["name"], len(found) / len(wanted) if wanted else 1,
                f"{len(found)}/{len(wanted)} columns" + (f"; missing {', '.join(missing)}" if missing else ""))
    return cat, f"Compared against {db_path}."


def source_files(root: Path, suffixes: tuple[str, ...]):
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in suffixes and not (set(path.relative_to(root).parts) & SKIP_DIRS):
            yield path


RAW_SQL = re.compile(r"""\.(?:execute|raw|extra)\(\s*(?:f["']|["'][^"']*["']\s*(?:%|\.format\())""")
HASHERS = re.compile(r"make_password|check_password|set_password|bcrypt|argon2|scrypt|pbkdf2|hashlib\.(?:sha256|sha512|blake2)")


def check_safety_and_style(report: dict, source: Path | None, look: Category) -> tuple[Category, str]:
    cat = Category("safety")
    if not source or not Path(source).is_dir():
        for label in ("No legacy PHP left", "CSRF protection on", "Passwords hashed", "No raw SQL string-building"):
            cat.add(label, 0, "source folder not given (--source)")
        look.add("Original stylesheet ported", 0, "source folder not given (--source)")
        return cat, "Safety not checked: pass --source with the rebuild's folder."
    root = Path(source)
    php = list(source_files(root, (".php", ".inc")))
    cat.add("No legacy PHP left", 0 if php else 1, f"{len(php)} PHP files outside legacy-assets/" if php else "no PHP files")

    py = list(source_files(root, (".py",)))
    text = {p: p.read_text("utf-8", "replace") for p in py}
    csrf_on = any("django.middleware.csrf.CsrfViewMiddleware" in t for t in text.values())
    exempt = sum(t.count("csrf_exempt") for t in text.values())
    cat.add("CSRF protection on", 1 if csrf_on and not exempt else (0.5 if csrf_on else 0),
            ("middleware enabled" if csrf_on else "CsrfViewMiddleware not found") + (f"; {exempt} csrf_exempt uses" if exempt else ""))

    hashes = sorted({m.group(0) for t in text.values() for m in HASHERS.finditer(t)})
    cat.add("Passwords hashed", 1 if hashes else 0, ("uses " + ", ".join(hashes[:4])) if hashes else "no password hashing found")

    raw = [f"{p.relative_to(root)}:{t[:m.start()].count(chr(10)) + 1}" for p, t in text.items() for m in RAW_SQL.finditer(t)]
    cat.add("No raw SQL string-building", 0 if raw else 1, ("found at " + ", ".join(raw[:5])) if raw else "none found")

    sheets = [s["path"] for s in (report.get("assets") or {}).get("stylesheets", [])][:3]
    if sheets:
        rebuilt_css = {p.name.lower() for p in source_files(root, (".css",))}
        ported = [s for s in sheets if Path(s).name.lower() in rebuilt_css]
        look.add("Original stylesheet ported", 1 if ported else 0,
                 ("found " + ", ".join(ported)) if ported else f"none of {', '.join(sheets)} found in the rebuild")
    else:
        css = list(source_files(root, (".css",)))
        look.add("Rebuild has its own stylesheet", 1 if css else 0, f"{len(css)} CSS files")
    return cat, f"Scanned {len(py)} Python files in {root}."


def run_check(report: dict, base_url: str, source: str | Path | None = None, db: str | Path | None = None,
              username: str | None = None, password: str | None = None) -> dict:
    """Run every check and return a JSON-serialisable result with an overall score from 0 to 100."""
    client = Client(base_url)
    pages, forms, look, notes, signed_in = check_pages_and_forms(client, report, username, password)
    tables, table_note = check_tables(report, Path(db).expanduser() if db else None)
    safety, safety_note = check_safety_and_style(report, Path(source).expanduser() if source else None, look)
    categories = {c.name: c for c in (pages, forms, tables, safety, look)}
    active = {name: cat for name, cat in categories.items() if cat.items}
    weight = sum(WEIGHTS[n] for n in active) or 1
    overall = round(100 * sum(WEIGHTS[n] * c.score for n, c in active.items()) / weight)
    summary = " · ".join(
        f"{c.passed}/{len(c.items)} {label}" for label, c in
        (("pages", pages), ("forms", forms), ("tables", tables), ("safety checks", safety)) if c.items
    )
    return {
        "version": 1,
        "target": base_url,
        "signed_in": signed_in,
        "score": overall,
        "summary": summary,
        "notes": notes + [table_note, safety_note],
        "categories": {name: cat.as_dict() for name, cat in categories.items()},
    }
