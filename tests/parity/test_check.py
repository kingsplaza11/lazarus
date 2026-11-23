"""Resurrection check against a real local HTTP server that imitates a rebuilt app."""
import http.server
import sqlite3
import threading
import urllib.parse

import pytest

from parity.check import (
    candidate_urls, check_tables, expected_url, legacy_fields, parse_page, run_check,
)

LOGIN_FORM = (
    '<form method="post" action="/login/"><input type="hidden" name="csrfmiddlewaretoken" value="tok123">'
    '<input name="username"><input type="password" name="password"><button>Login</button></form>'
)


class FakeRebuild(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def signed_in(self):
        return "session=ok" in (self.headers.get("Cookie") or "")

    def reply(self, status, body="", headers=None):
        self.send_response(status)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/login/":
            if self.signed_in():  # like TaskFreak: signed-in users are sent away from the sign-in page
                return self.reply(302, headers={"Location": "/"})
            return self.reply(200, f"<html><body>{LOGIN_FORM}</body></html>", {"Set-Cookie": "csrftoken=tok123; Path=/"})
        if path == "/rss/":
            return self.reply(500, "boom")
        if path == "/install/":
            return self.reply(200, "<html><body><p>Run python manage.py migrate.</p></body></html>")
        if path == "/logout/":
            return self.reply(302, headers={"Location": "/login/", "Set-Cookie": "session=; Path=/"})
        if path in ("/", "/project/edit/"):
            if not self.signed_in():
                return self.reply(302, headers={"Location": "/login/"})
            fields = '<input name="name"><textarea name="description"></textarea>' if path != "/" else '<select name="project"></select>'
            return self.reply(200, f'<html><head><link rel="stylesheet" href="/static/core/style.css"></head>'
                                   f'<body><form method="post">{fields}</form></body></html>')
        return self.reply(404, "not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = urllib.parse.parse_qs(self.rfile.read(length).decode())
        ok = (data.get("csrfmiddlewaretoken") == ["tok123"] and data.get("username") == ["admin"]
              and data.get("password") == ["lazarus-demo"] and "csrftoken=tok123" in (self.headers.get("Cookie") or ""))
        if ok:
            return self.reply(302, headers={"Location": "/", "Set-Cookie": "session=ok; Path=/"})
        return self.reply(200, f"<html><body><p>Invalid</p>{LOGIN_FORM}</body></html>")


@pytest.fixture(scope="module")
def server():
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeRebuild)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def report() -> dict:
    return {
        "pages": [
            {"path": "logout.php", "forms": []},
            {"path": "index.php", "forms": []},
            {"path": "login.php", "forms": [{"file": "login.php", "line": 30, "fields": [
                {"name": "username", "type": "text"}, {"name": "password", "type": "password"},
                {"name": "{php}", "type": "hidden"}, {"name": "go", "type": "submit"}]}]},
            {"path": "project_edit.php", "forms": [{"file": "project_edit.php", "line": 60, "fields": [
                {"name": "name", "type": "text"}, {"name": "description", "type": "textarea"},
                {"name": "priority", "type": "select"}]}]},
            {"path": "rss.php", "forms": []},
            {"path": "install/index.php", "forms": [{"file": "install/mysql.copy.php", "line": 84, "fields": [
                {"name": "src_host", "type": "text"}, {"name": "src_user", "type": "text"},
                {"name": "src_pass", "type": "password"}, {"name": "src_base", "type": "text"},
                {"name": "user_mode", "type": "select"}]}]},
            {"path": "user_list.php", "forms": []},
        ],
        "tables": [
            {"name": "frk_member", "columns": [{"name": "memberid"}, {"name": "username"}, {"name": "password"}]},
            {"name": "frk_project", "columns": [{"name": "projectid"}, {"name": "name"}, {"name": "description"}]},
            {"name": "frk_item", "columns": [{"name": "itemid"}]},
        ],
        "assets": {"stylesheets": [{"path": "skins/redfreak/style.css", "bytes": 9000}], "skins": []},
    }


@pytest.fixture
def rebuild(tmp_path):
    db = tmp_path / "db.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE frk_member (memberid INTEGER, username TEXT, password TEXT)')
        conn.execute('CREATE TABLE frk_project (projectid INTEGER, name TEXT)')
    src = tmp_path / "src"
    (src / "taskfreak").mkdir(parents=True)
    (src / "taskfreak" / "settings.py").write_text('MIDDLEWARE = ["django.middleware.csrf.CsrfViewMiddleware"]\n')
    (src / "accounts").mkdir()
    (src / "accounts" / "views.py").write_text("from django.contrib.auth.hashers import make_password\n")
    (src / "core").mkdir()
    (src / "core" / "reports.py").write_text('def run(c, q):\n    c.execute(f"SELECT * FROM frk_item WHERE title = {q}")\n')
    (src / "core" / "static" / "core").mkdir(parents=True)
    (src / "core" / "static" / "core" / "style.css").write_text("body{}")
    (src / "legacy-assets" / "skins").mkdir(parents=True)
    (src / "legacy-assets" / "skins" / "old.php").write_text("<?php")  # ignored: legacy-assets is not the rebuild
    (src / ".venv" / "lib").mkdir(parents=True)
    (src / ".venv" / "lib" / "x.php").write_text("<?php")  # ignored: virtualenv
    return src, db


def test_full_check_signed_in(server, rebuild):
    src, db = rebuild
    result = run_check(report(), server, source=src, db=db, username="admin", password="lazarus-demo")
    cats = result["categories"]
    assert result["signed_in"] is True

    pages = {i["label"]: i for i in cats["pages"]["items"]}
    assert pages["index.php"]["score"] == 1 and pages["login.php"]["score"] == 1
    assert pages["project_edit.php"]["score"] == 1 and pages["logout.php"]["score"] == 1
    assert pages["rss.php"]["score"] == 0 and "server error 500" in pages["rss.php"]["detail"]
    assert pages["user_list.php"]["score"] == 0 and "404" in pages["user_list.php"]["detail"]
    assert cats["pages"]["passed"] == 5 and cats["pages"]["total"] == 7

    forms = {i["label"]: i for i in cats["forms"]["items"]}
    assert forms["login.php:30"]["score"] == 1  # read signed out, although /login/ redirects once signed in
    assert "install/mysql.copy.php:84" not in forms
    assert any("database credentials" in n for n in result["notes"])
    assert forms["project_edit.php:60"]["score"] == pytest.approx(2 / 3, abs=0.001)
    assert "missing priority" in forms["project_edit.php:60"]["detail"]

    tables = {i["label"]: i for i in cats["tables"]["items"]}
    assert tables["frk_member"]["score"] == 1
    assert tables["frk_project"]["score"] == pytest.approx(2 / 3, abs=0.001)
    assert tables["frk_item"]["score"] == 0

    safety = {i["label"]: i for i in cats["safety"]["items"]}
    assert safety["No legacy PHP left"]["score"] == 1
    assert safety["CSRF protection on"]["score"] == 1
    assert safety["Passwords hashed"]["score"] == 1
    assert safety["No raw SQL string-building"]["score"] == 0
    assert "core/reports.py:2" in safety["No raw SQL string-building"]["detail"]

    look = {i["label"]: i for i in cats["look"]["items"]}
    assert look["Original stylesheet ported"]["score"] == 1
    assert look["Pages load a stylesheet"]["detail"] == "3/4 pages link a stylesheet"

    assert 0 < result["score"] < 100
    assert result["summary"] == "5/7 pages · 1/2 forms · 1/3 tables · 3/4 safety checks"


def test_wrong_password_checks_signed_out(server, rebuild):
    src, db = rebuild
    result = run_check(report(), server, source=src, db=db, username="admin", password="nope")
    assert result["signed_in"] is False
    assert any("did not succeed" in n for n in result["notes"])
    pages = {i["label"]: i for i in result["categories"]["pages"]["items"]}
    assert pages["index.php"]["score"] == 1  # redirect to sign-in still counts as restored


def test_unreachable_app_scores_zero_pages(rebuild):
    src, db = rebuild
    result = run_check(report(), "http://127.0.0.1:9", source=src, db=db)
    assert result["categories"]["pages"]["passed"] == 0
    assert all("no response" in i["detail"] for i in result["categories"]["pages"]["items"])


def test_missing_db_and_source_are_reported(server):
    result = run_check(report(), server)
    assert any("--db" in n for n in result["notes"])
    assert any("--source" in n for n in result["notes"])
    assert result["categories"]["tables"]["passed"] == 0


def test_no_schema_means_no_table_items(tmp_path):
    cat, note = check_tables({"tables": []}, None)
    assert cat.items == [] and "no CREATE TABLE" in note


def test_database_form_detection():
    from parity.check import is_database_form
    assert is_database_form(["dst_host", "dst_user", "dst_pass", "dst_base", "user_mode"])
    assert not is_database_form(["title", "deadline", "priority", "project"])
    assert not is_database_form(["username", "password"])  # a sign-in form is not an installer


def test_helpers():
    assert expected_url("project_edit.php") == "/project/edit/"
    assert expected_url("index.php") == "/"
    assert expected_url("xajax.task.php") == "/task/"
    assert candidate_urls("login.php") == ["/login/", "/login", "/login.php"]
    assert legacy_fields({"fields": [{"name": "Tags[]", "type": "text"}, {"name": "x", "type": "hidden"},
                                     {"name": "{php}", "type": "text"}, {"name": "go", "type": "submit"}]}) == ["tags"]
    page = parse_page('<link rel="stylesheet" href="a.css"><form><input name="q"></form><input name="loose">')
    assert page.stylesheets == ["a.css"] and set(page.fields) == {"q", "loose"} and len(page.forms) == 1
    assert parse_page("<form><input name=").fields == {}
