"""Guards for Requirement 18 (modernisation): enforced by scanning the source tree."""
import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import check_password, identify_hasher
from django.test import TestCase

from accounts.models import Member
from core.legacy import COUNT_ALL, SELECT_ALL, LOAD_ORDER, convert_password

ROOT = Path(settings.BASE_DIR)
APP_DIRS = ("core", "accounts", "taskfreak")


def py_sources():
    for d in APP_DIRS:
        for p in (ROOT / d).rglob("*.py"):
            if "migrations" in p.parts or p.name.startswith("test"):
                continue
            yield p


def templates():
    return list((ROOT / "templates").rglob("*.html")) + list((ROOT / "templates").rglob("*.xml"))


# The 17 PHP functions removed between PHP 5 and 8 that TaskFreak used (18.1).
REMOVED_PHP = ["ereg", "eregi", "ereg_replace", "split", "mysql_connect", "mysql_query", "mysql_error",
               "mysql_fetch_array", "mysql_escape_string", "get_magic_quotes_gpc", "set_magic_quotes_runtime",
               "magic_quotes_runtime", "session_register", "mysql_real_escape_string", "mysql_select_db",
               "mysql_num_rows", "mysql_fetch_assoc"]


class RemovedPhpTests(TestCase):
    def test_no_removed_php_functions_in_sources(self):
        # Not preceded by "." so Python methods such as str.split() are not flagged.
        pat = re.compile(r"(?<![\w.])(%s)\s*\(" % "|".join(REMOVED_PHP))
        for p in list(py_sources()) + templates():
            self.assertIsNone(pat.search(p.read_text()), p)


class SqlTests(TestCase):
    def test_no_raw_or_string_built_sql(self):
        raw = re.compile(r"\.(raw|extra)\(|RawSQL\(")
        built = re.compile(r"""\.execute\(\s*(f["']|["'][^"']*["']\s*(%|\.format|\+))""")
        for p in py_sources():
            t = p.read_text()
            self.assertIsNone(raw.search(t), p)
            self.assertIsNone(built.search(t), p)

    def test_execute_only_uses_fixed_statements(self):
        for p in py_sources():
            for m in re.finditer(r"\.execute\(([^)]*)\)", p.read_text()):
                arg = m.group(1).strip()
                self.assertTrue(re.match(r"^(SELECT_ALL|COUNT_ALL)\[[\w.\[\]]+\]$", arg), (p, arg))

    def test_fixed_statements_cover_every_table(self):
        tables = {m._meta.db_table for m in LOAD_ORDER}
        self.assertEqual(set(SELECT_ALL), tables)
        self.assertEqual(set(COUNT_ALL), tables)
        for t in tables:
            self.assertEqual(SELECT_ALL[t], "SELECT * FROM " + t)
            self.assertEqual(COUNT_ALL[t], "SELECT COUNT(*) FROM " + t)


class CsrfTests(TestCase):
    def test_every_post_form_has_csrf_token(self):
        form = re.compile(r"<form\b[^>]*>(.*?)</form>", re.S | re.I)
        opening = re.compile(r"<form\b[^>]*>", re.I)
        checked = 0
        for p in templates():
            text = p.read_text()
            for m in form.finditer(text):
                tag = opening.match(m.group(0)).group(0)
                if re.search(r"method\s*=\s*[\"']post[\"']", tag, re.I) or "hx-post" in tag:
                    checked += 1
                    self.assertIn("{% csrf_token %}", m.group(1) + tag, p)
        self.assertGreater(checked, 5)

    def test_csrf_middleware_enabled(self):
        self.assertIn("django.middleware.csrf.CsrfViewMiddleware", settings.MIDDLEWARE)


class PasswordTests(TestCase):
    def test_hashers_configured(self):
        self.assertIn("accounts.hashers.LegacyMD5Hasher", settings.PASSWORD_HASHERS)
        self.assertNotIn("django.contrib.auth.hashers.MD5PasswordHasher", settings.PASSWORD_HASHERS)
        self.assertNotIn("django.contrib.auth.hashers.UnsaltedMD5PasswordHasher", settings.PASSWORD_HASHERS)

    def test_converted_legacy_hash_is_salted_and_not_raw(self):
        import hashlib
        raw = hashlib.md5(b"abcd1234pw").hexdigest()
        stored = convert_password(raw, "abcd1234")
        self.assertEqual(identify_hasher(stored).algorithm, "legacy_md5")
        self.assertNotEqual(stored, raw)
        self.assertIn("abcd1234", stored)
        self.assertTrue(check_password("pw", stored))
        self.assertFalse(check_password("other", stored))

    def test_unhashable_legacy_value_becomes_unusable(self):
        self.assertFalse(check_password("x", convert_password("plain", "abcd1234")))
        self.assertFalse(check_password("", convert_password("", "")))

    def test_password_column_fits_hash(self):
        self.assertGreaterEqual(Member._meta.get_field("password").max_length, 128)


class LibraryTests(TestCase):
    def test_no_jscalendar_or_xajax_library(self):
        pat = re.compile(r"jscalendar|calendar-setup|calendar\.js|xajax\.js|xajax_|xajax_core|xajaxResponse", re.I)
        for p in list(py_sources()) + templates():
            self.assertIsNone(pat.search(p.read_text()), p)
        for d in ("static/js",):
            for f in (ROOT / d).glob("*"):
                self.assertNotRegex(f.name.lower(), r"jscalendar|calendar|xajax")

    def test_htmx_is_bundled_and_loaded(self):
        self.assertTrue((ROOT / "static/js/htmx.min.js").exists())
        self.assertIn("htmx.min.js", (ROOT / "templates/base.html").read_text())
