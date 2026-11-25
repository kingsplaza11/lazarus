import os
import sqlite3
import tempfile
from unittest import mock

from django.test import TestCase

from accounts.models import Member
from core.models import Country, Item, Project
from core.test_legacy import build_legacy_db

SECRET = "s3cr3t-PASSWORD-xyz"


def form(**over):
    data = {
        "action": "copy", "src_host": "db.example.org", "src_port": "3306", "src_user": "tf",
        "src_pass": SECRET, "src_base": "taskfreak", "src_table": "all",
    }
    data.update(over)
    return data


class InstallTests(TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        self.addCleanup(os.remove, self.path)
        build_legacy_db(self.path)
        self.calls = []

        def fake_open(host, port, user, password, database):
            self.calls.append((host, port, user, password, database))
            return sqlite3.connect(self.path)

        p = mock.patch("core.views.open_source_connection", fake_open)
        p.start()
        self.addCleanup(p.stop)

    def test_get_shows_form_without_prefilled_password(self):
        r = self.client.get("/install/")
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "core/install.html")
        for name in ("action", "src_host", "src_user", "src_pass", "src_base", "src_table"):
            self.assertContains(r, f'name="{name}"')
        self.assertContains(r, 'name="csrfmiddlewaretoken"')

    def test_copy_all_loads_data(self):
        r = self.client.post("/install/", form())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Data copied")
        self.assertEqual(self.calls[0][3], SECRET)
        self.assertEqual(Project.objects.get(pk=1).name, "Alpha")
        self.assertEqual(Item.objects.count(), 2)

    def test_copy_single_table_only(self):
        self.client.post("/install/", form(src_table="frk_project"))
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(Item.objects.count(), 0)
        self.assertEqual(Member.objects.count(), 0)

    def test_test_action_counts_without_copying(self):
        r = self.client.post("/install/", form(action="test"))
        self.assertContains(r, "Connection OK")
        self.assertContains(r, "frk_item: 2 rows")
        self.assertEqual(Item.objects.count(), 0)

    def test_table_name_must_be_in_allowlist(self):
        for bad in ("frk_item; DROP TABLE frk_item", "auth_user", "../x"):
            r = self.client.post("/install/", form(src_table=bad))
            self.assertContains(r, "Unknown table.")
        self.assertEqual(self.calls, [])

    def test_invalid_fields_rejected_before_connecting(self):
        r = self.client.post("/install/", form(action="drop", src_host="a b;", src_base="x;y", src_port="99999", src_user=""))
        for msg in ("Unknown action.", "Invalid host name.", "Invalid database name.", "Invalid port.", "A user name is required."):
            self.assertContains(r, msg)
        self.assertEqual(self.calls, [])

    def test_password_never_echoed_on_validation_error(self):
        r = self.client.post("/install/", form(src_base="bad;name"))
        self.assertNotContains(r, SECRET)

    def test_password_never_echoed_or_logged_on_connection_failure(self):
        def boom(*a, **k):
            raise RuntimeError("Access denied for password " + SECRET)

        with mock.patch("core.views.open_source_connection", boom), self.assertNoLogs(level="DEBUG"):
            r = self.client.post("/install/", form())
        self.assertContains(r, "Could not read the source database (RuntimeError).")
        self.assertNotContains(r, SECRET)

    def test_forbidden_once_a_member_exists(self):
        Country.objects.create(countryid="US")
        Member.objects.create(username="bob", country_id="US", enabled=True)
        self.assertEqual(self.client.get("/install/").status_code, 403)
        r = self.client.post("/install/", form())
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.calls, [])
        self.assertEqual(Project.objects.count(), 0)

    def test_post_requires_csrf_token(self):
        from django.test import Client
        r = Client(enforce_csrf_checks=True).post("/install/", form())
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.calls, [])

    def test_delete_not_allowed(self):
        self.assertEqual(self.client.delete("/install/").status_code, 405)
