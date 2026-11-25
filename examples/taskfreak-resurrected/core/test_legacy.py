import hashlib
import os
import sqlite3
import tempfile
from io import StringIO

from django.contrib.auth.hashers import check_password
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounts.models import Member
from core.models import Country, Item, ItemComment, MemberProject, Project

SCHEMA = """
CREATE TABLE frk_country (countryid TEXT, name TEXT);
CREATE TABLE frk_project (projectid INTEGER, name TEXT, description TEXT);
CREATE TABLE frk_member (memberid INTEGER, email TEXT, username TEXT, password TEXT, salt TEXT,
    countryid TEXT, enabled INTEGER, level INTEGER, creationdate TEXT, expirationdate TEXT);
CREATE TABLE frk_memberproject (memberid INTEGER, projectid INTEGER, position INTEGER);
CREATE TABLE frk_item (itemid INTEGER, projectid INTEGER, title TEXT, deadlinedate TEXT, memberid INTEGER, priority INTEGER);
CREATE TABLE frk_itemcomment (itemcommentid INTEGER, itemid INTEGER, memberid INTEGER, postdate TEXT, body TEXT);
CREATE TABLE frk_itemfile (itemfileid INTEGER, itemid INTEGER, memberid INTEGER, filename TEXT);
CREATE TABLE frk_itemstatus (itemstatusid INTEGER, itemid INTEGER, statusdate TEXT, statuskey INTEGER, memberid INTEGER);
CREATE TABLE frk_projectstatus (projectstatusid INTEGER, projectid INTEGER, statusdate TEXT, statuskey INTEGER, memberid INTEGER);
"""

LEGACY_HASH = hashlib.md5(b"abcd1234" + b"secret").hexdigest()


def build_legacy_db(path):
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    c.executescript(
        f"""
        INSERT INTO frk_country VALUES ('FR','France'),('US','United States');
        INSERT INTO frk_project VALUES (1,'Alpha','first');
        INSERT INTO frk_member VALUES (7,'a@x.org','alice','{LEGACY_HASH}','abcd1234','FR',1,5,'2008-01-02 03:04:05','0000-00-00 00:00:00');
        INSERT INTO frk_member VALUES (8,'b@x.org','bob','nothex','zzzzzzzz','XX',1,1,NULL,NULL);
        INSERT INTO frk_memberproject VALUES (7,1,2);
        INSERT INTO frk_item VALUES (3,1,'Do it','0000-00-00',7,4);
        INSERT INTO frk_item VALUES (4,1,'Later','2009-05-06',7,1);
        INSERT INTO frk_itemcomment VALUES (9,3,7,'2008-02-03 04:05:06','hello');
        """
    )
    c.commit()
    c.close()


class LegacyLoaderTests(TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        self.addCleanup(os.remove, self.path)
        build_legacy_db(self.path)

    def load(self):
        out = StringIO()
        call_command("load_legacy", sqlite=self.path, stdout=out)
        return out.getvalue()

    def test_loads_rows_and_keeps_primary_keys(self):
        self.load()
        self.assertEqual(Country.objects.count(), 3)  # FR, US + placeholder XX
        self.assertEqual(Project.objects.get(pk=1).name, "Alpha")
        self.assertEqual({i.pk for i in Item.objects.all()}, {3, 4})
        self.assertEqual(ItemComment.objects.get(pk=9).body, "hello")
        self.assertEqual(MemberProject.objects.get(member_id=7, project_id=1).position, 2)

    def test_member_country_maps_by_code(self):
        self.load()
        m = Member.objects.get(pk=7)
        self.assertEqual(m.country_id, "FR")
        self.assertEqual(m.country.name, "France")
        self.assertTrue(m.enabled)
        self.assertEqual(Member.objects.get(pk=8).country_id, "XX")

    def test_zero_dates_become_null_and_dates_are_aware(self):
        self.load()
        self.assertIsNone(Item.objects.get(pk=3).deadlinedate)
        self.assertEqual(str(Item.objects.get(pk=4).deadlinedate), "2009-05-06")
        m = Member.objects.get(pk=7)
        self.assertIsNone(m.expirationdate)
        self.assertEqual(m.creationdate.year, 2008)
        self.assertIsNotNone(m.creationdate.tzinfo)

    def test_legacy_password_verifies_without_storing_plaintext_or_raw_md5(self):
        self.load()
        m = Member.objects.get(pk=7)
        self.assertTrue(m.password.startswith("legacy_md5$abcd1234$"))
        self.assertTrue(check_password("secret", m.password))
        self.assertFalse(check_password("wrong", m.password))

    def test_legacy_password_is_upgraded_on_successful_check(self):
        self.load()
        m = Member.objects.get(pk=7)

        def setter(raw):
            m.password = __import__("django.contrib.auth.hashers", fromlist=["x"]).make_password(raw)

        self.assertTrue(check_password("secret", m.password, setter))
        self.assertTrue(m.password.startswith("pbkdf2_sha256$"))

    def test_unrecognised_hash_gives_unusable_password(self):
        self.load()
        self.assertFalse(check_password("anything", Member.objects.get(pk=8).password))

    def test_rerun_is_idempotent(self):
        self.load()
        self.load()
        self.assertEqual(Member.objects.count(), 2)
        self.assertEqual(Item.objects.count(), 2)

    def test_failure_imports_nothing(self):
        c = sqlite3.connect(self.path)
        c.execute("DROP TABLE frk_projectstatus")
        c.commit()
        c.close()
        with self.assertRaises(CommandError):
            self.load()
        self.assertEqual(Country.objects.count(), 0)
