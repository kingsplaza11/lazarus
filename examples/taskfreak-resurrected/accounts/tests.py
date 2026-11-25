from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.utils import timezone

from core.models import Country

from .hashers import LegacyMD5Hasher
from .models import Member


def make_member(password="secret", legacy=False, **kw):
    Country.objects.get_or_create(countryid="US")
    if legacy:
        import hashlib
        stored = LegacyMD5Hasher.wrap(hashlib.md5(("abcd1234" + password).encode()).hexdigest(), "abcd1234")
    else:
        stored = make_password(password)
    defaults = dict(username="alice", password=stored, country_id="US", enabled=True)
    defaults.update(kw)
    return Member.objects.create(**defaults)


class LoginTests(TestCase):
    def test_get_shows_form_posting_to_login(self):
        r = self.client.get("/login/")
        self.assertContains(r, 'action="/login/"')
        self.assertContains(r, 'name="username"')
        self.assertContains(r, 'name="password"')
        self.assertContains(r, 'name="remember"')
        self.assertContains(r, "csrfmiddlewaretoken")

    def test_success_starts_session_and_updates_member(self):
        m = make_member()
        r = self.client.post("/login/", {"username": "alice", "password": "secret"})
        self.assertRedirects(r, "/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["memberid"], m.pk)
        m.refresh_from_db()
        self.assertEqual(m.visits, 1)
        self.assertIsNotNone(m.lastlogindate)
        self.assertContains(self.client.get("/"), 'id="menu"')

    def test_legacy_md5_hash_is_upgraded(self):
        m = make_member(legacy=True)
        self.assertTrue(m.password.startswith("legacy_md5$"))
        self.client.post("/login/", {"username": "alice", "password": "secret"})
        m.refresh_from_db()
        self.assertTrue(m.password.startswith("pbkdf2_"))
        self.assertEqual(self.client.session["memberid"], m.pk)

    def test_wrong_password_rejected_and_counted(self):
        m = make_member()
        r = self.client.post("/login/", {"username": "alice", "password": "nope"})
        self.assertContains(r, "Invalid username or password")
        self.assertNotIn("memberid", self.client.session)
        m.refresh_from_db()
        self.assertEqual(m.badaccess, 1)

    def test_unknown_user_and_unusable_password_rejected(self):
        make_member(password=None, username="ghost")
        Member.objects.filter(username="ghost").update(password=make_password(None))
        for u in ("nobody", "ghost"):
            r = self.client.post("/login/", {"username": u, "password": "x"})
            self.assertContains(r, "Invalid username or password")

    def test_disabled_and_expired_redirect_to_error(self):
        make_member(username="off", enabled=False)
        r = self.client.post("/login/", {"username": "off", "password": "secret"})
        self.assertTrue(r["Location"].startswith("/error/?tznMessage="))
        make_member(username="old", expirationdate=timezone.now() - timezone.timedelta(days=1))
        r = self.client.post("/login/", {"username": "old", "password": "secret"})
        self.assertTrue(r["Location"].startswith("/error/?tznMessage="))
        self.assertNotIn("memberid", self.client.session)

    def test_remember_sets_long_expiry(self):
        make_member()
        self.client.post("/login/", {"username": "alice", "password": "secret", "remember": "1"})
        self.assertGreater(self.client.session.get_expiry_age(), 24 * 3600)
        self.assertTrue(Member.objects.get(username="alice").autologin)

    def test_next_is_followed_only_if_safe(self):
        make_member()
        r = self.client.post("/login/", {"username": "alice", "password": "secret", "next": "/project/list/"})
        self.assertEqual(r["Location"], "/project/list/")
        self.client.logout()
        r = self.client.post("/login/", {"username": "alice", "password": "secret", "next": "https://evil.com/"})
        self.assertEqual(r["Location"], "/")

    def test_xajax_params_carried_through_form(self):
        r = self.client.get("/login/?xajax=foo&xajaxargs=bar&next=/task/")
        self.assertContains(r, 'name="xajax" value="foo"')
        self.assertContains(r, 'name="xajaxargs" value="bar"')
        self.assertContains(r, 'name="next" value="/task/"')

    def test_signed_in_member_is_redirected_away(self):
        make_member()
        self.client.post("/login/", {"username": "alice", "password": "secret"})
        self.assertRedirects(self.client.get("/login/"), "/", fetch_redirect_response=False)

    def test_csrf_enforced(self):
        from django.test import Client
        make_member()
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post("/login/", {"username": "alice", "password": "secret"}).status_code, 403)


class LogoutTests(TestCase):
    def test_get_ends_session_and_shows_screen(self):
        m = make_member(autologin=True)
        self.client.post("/login/", {"username": "alice", "password": "secret"})
        r = self.client.get("/logout/")
        self.assertContains(r, "logged out")
        self.assertNotIn("memberid", self.client.session)
        m.refresh_from_db()
        self.assertFalse(m.autologin)
        self.assertNotContains(self.client.get("/login/"), 'id="logout-form"')

    def test_post_from_header_form_ends_session(self):
        make_member()
        self.client.post("/login/", {"username": "alice", "password": "secret"})
        r = self.client.post("/logout/")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("memberid", self.client.session)

    def test_anonymous_logout_is_ok(self):
        self.assertEqual(self.client.get("/logout/").status_code, 200)


class UserPasswordTests(TestCase):
    def test_get_shows_reminder_form(self):
        r = self.client.get("/user/password/")
        self.assertContains(r, 'action="/user/password/"')
        self.assertContains(r, 'name="email"')
        self.assertContains(r, 'name="reminder"')

    def test_reminder_emails_reset_link_not_password(self):
        from django.core import mail
        m = make_member(email="a@example.com")
        r = self.client.post("/user/password/", {"reminder": "1", "email": "a@example.com"})
        self.assertContains(r, "reminder-sent")
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("/user/password/?token=", body)
        self.assertNotIn("secret", body)
        self.assertNotIn(m.password, body)

    def test_unknown_email_gives_same_response_no_mail(self):
        from django.core import mail
        r = self.client.post("/user/password/", {"reminder": "1", "email": "x@example.com"})
        self.assertContains(r, "reminder-sent")
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_email_rejected(self):
        r = self.client.post("/user/password/", {"reminder": "1", "email": "nope"})
        self.assertContains(r, "valid email")

    def test_reset_flow_changes_hashed_password_once(self):
        from django.contrib.auth.hashers import check_password
        from .views import _reset_token
        m = make_member(email="a@example.com")
        tok = _reset_token(m)
        self.assertContains(self.client.get("/user/password/", {"token": tok}), "password-reset-form")
        r = self.client.post("/user/password/", {"token": tok, "password": "newpass1", "password2": "newpass2"})
        self.assertContains(r, "do not match")
        r = self.client.post("/user/password/", {"token": tok, "password": "newpass1", "password2": "newpass1"})
        self.assertContains(r, "password-done")
        m.refresh_from_db()
        self.assertNotEqual(m.password, "newpass1")
        self.assertTrue(check_password("newpass1", m.password))
        self.assertContains(self.client.get("/user/password/", {"token": tok}), "invalid or has expired")

    def test_bad_token_rejected(self):
        self.assertContains(self.client.get("/user/password/", {"token": "junk"}), "invalid or has expired")


class UserRegisterTests(TestCase):
    DATA = {
        "submit": "1", "username": "bob", "email": "bob@example.com",
        "password1": "secret1", "password2": "secret1",
    }

    def test_get_shows_form_posting_to_register(self):
        r = self.client.get("/user/register/")
        self.assertContains(r, 'action="/user/register/"')
        for name in ("username", "email", "password1", "password2", "submit"):
            self.assertContains(r, 'name="%s"' % name)
        self.assertContains(r, "csrfmiddlewaretoken")

    def test_xajax_params_carried_through_form(self):
        r = self.client.get("/user/register/?xajax=foo&xajaxargs=bar")
        self.assertContains(r, 'name="xajax" value="foo"')
        self.assertContains(r, 'name="xajaxargs" value="bar"')

    def test_register_creates_disabled_hashed_member_and_emails_link(self):
        from django.core import mail
        from django.contrib.auth.hashers import check_password
        r = self.client.post("/user/register/", self.DATA)
        self.assertContains(r, "register-done")
        m = Member.objects.get(username="bob")
        self.assertFalse(m.enabled)
        self.assertNotEqual(m.password, "secret1")
        self.assertTrue(check_password("secret1", m.password))
        self.assertEqual(len(m.activation), 16)
        self.assertIn("/user/register/?activate=" + m.activation, mail.outbox[0].body)
        self.assertNotIn("secret1", mail.outbox[0].body)

    def test_activation_enables_member_once(self):
        self.client.post("/user/register/", self.DATA)
        code = Member.objects.get(username="bob").activation
        self.assertContains(self.client.get("/user/register/", {"activate": code}), "register-activated")
        self.assertTrue(Member.objects.get(username="bob").enabled)
        self.assertContains(self.client.get("/user/register/", {"activate": code}), "invalid or has already")

    def test_validation_errors(self):
        make_member(username="alice", email="a@example.com")
        cases = [
            ({"password2": "different"}, "do not match"),
            ({"password1": "abc", "password2": "abc"}, "at least"),
            ({"username": "ALICE"}, "already taken"),
            ({"email": "a@example.com"}, "already registered"),
            ({"email": "nope"}, "valid email"),
            ({"username": ""}, "Username is required"),
            ({"country": "ZZ"}, "valid country"),
        ]
        for override, msg in cases:
            r = self.client.post("/user/register/", {**self.DATA, **override})
            self.assertContains(r, msg)
        self.assertFalse(Member.objects.filter(username="bob").exists())

    def test_signed_in_member_is_redirected_away(self):
        make_member()
        self.client.post("/login/", {"username": "alice", "password": "secret"})
        self.assertRedirects(self.client.get("/user/register/"), "/", fetch_redirect_response=False)

    def test_csrf_enforced(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post("/user/register/", self.DATA).status_code, 403)

    def test_password_column_fits_django_hash(self):
        self.assertEqual(Member._meta.get_field("password").max_length, 128)
        self.assertLessEqual(len(make_password("x")), 128)


class UserDetailsTests(TestCase):
    def setUp(self):
        from core.models import MemberProject, Project

        self.alice = make_member(username="alice", activation="SECRETACT1234567", salt="SALT1234")
        self.bob = make_member(username="bob", email="bob@example.com")
        self.carol = make_member(username="carol")
        shared = Project.objects.create(name="Shared")
        MemberProject.objects.create(member=self.alice, project=shared)
        MemberProject.objects.create(member=self.bob, project=shared)

    def login(self, name="alice"):
        self.client.post("/login/", {"username": name, "password": "secret"})

    def test_requires_sign_in(self):
        r = self.client.get("/user/details/")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].startswith("/login/?next="))

    def test_defaults_to_self_and_hides_secrets(self):
        self.login()
        r = self.client.get("/user/details/")
        self.assertContains(r, "alice")
        self.assertContains(r, 'action="/user/details/"')
        for secret in (self.alice.password, "SECRETACT1234567", "SALT1234"):
            self.assertNotContains(r, secret)

    def test_shared_project_member_visible(self):
        self.login()
        r = self.client.get("/user/details/", {"id": self.bob.pk})
        self.assertContains(r, "bob@example.com")

    def test_unrelated_member_forbidden(self):
        self.login()
        self.assertEqual(self.client.get("/user/details/", {"id": self.carol.pk}).status_code, 403)

    def test_unknown_or_bad_id(self):
        self.login()
        self.assertEqual(self.client.get("/user/details/", {"id": "abc"}).status_code, 404)

    def test_xajax_carried(self):
        self.login()
        r = self.client.get("/user/details/", {"xajax": "foo", "xajaxargs": "bar"})
        self.assertContains(r, 'name="xajax" value="foo"')
        self.assertContains(r, 'name="xajaxargs" value="bar"')


class UserEditTests(TestCase):
    def setUp(self):
        from .models import ADMIN_LEVEL

        self.admin = make_member(username="admin", email="admin@example.com", level=ADMIN_LEVEL)
        self.alice = make_member(username="alice", email="alice@example.com")
        self.bob = make_member(username="bob", email="bob@example.com")

    def login(self, name="alice"):
        self.client.post("/login/", {"username": name, "password": "secret"})

    def post(self, member, **extra):
        data = {"id": member.pk, "submit": "1", "email": member.email, "country": "US"}
        data.update(extra)
        return self.client.post("/user/edit/", data)

    def test_requires_sign_in(self):
        r = self.client.get("/user/edit/")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].startswith("/login/?next="))

    def test_form_posts_to_edit_and_carries_xajax(self):
        self.login()
        r = self.client.get("/user/edit/", {"xajax": "foo", "xajaxargs": "bar"})
        self.assertContains(r, 'action="/user/edit/"')
        self.assertContains(r, "csrfmiddlewaretoken")
        self.assertContains(r, 'name="xajax" value="foo"')
        self.assertContains(r, 'name="xajaxargs" value="bar"')
        self.assertNotContains(r, 'name="level"')
        self.assertNotContains(r, 'name="enabled"')

    def test_self_edit_saves_and_redirects(self):
        self.login()
        r = self.post(self.alice, firstname="Alicia", xajax="foo")
        self.assertRedirects(r, "/user/details/?id=%d&xajax=foo" % self.alice.pk, fetch_redirect_response=False)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.firstname, "Alicia")

    def test_non_admin_cannot_change_own_level_or_enabled(self):
        self.login()
        self.post(self.alice, level="5", enabled="")
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.level, 0)
        self.assertTrue(self.alice.enabled)

    def test_non_admin_cannot_edit_others(self):
        self.login()
        self.assertEqual(self.client.get("/user/edit/", {"id": self.bob.pk}).status_code, 403)
        self.assertEqual(self.post(self.bob, firstname="X").status_code, 403)

    def test_admin_changes_other_level_and_enabled(self):
        self.login("admin")
        self.post(self.bob, level="3")
        self.bob.refresh_from_db()
        self.assertEqual((self.bob.level, self.bob.enabled), (3, False))

    def test_admin_cannot_change_own_level_or_enabled(self):
        from .models import ADMIN_LEVEL

        self.login("admin")
        self.post(self.admin, level="0")
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.level, ADMIN_LEVEL)
        self.assertTrue(self.admin.enabled)

    def test_invalid_level_rejected(self):
        self.login("admin")
        self.post(self.bob, level="99")
        self.bob.refresh_from_db()
        self.assertEqual(self.bob.level, 0)

    def test_password_change_hashed(self):
        from django.contrib.auth.hashers import check_password

        self.login()
        self.post(self.alice, password1="newsecret", password2="newsecret")
        self.alice.refresh_from_db()
        self.assertTrue(check_password("newsecret", self.alice.password))

    def test_password_too_short_or_mismatch(self):
        self.login()
        old = self.alice.password
        r = self.post(self.alice, password1="abc", password2="abc")
        self.assertContains(r, "at least 6")
        r = self.post(self.alice, password1="abcdef", password2="abcdeg")
        self.assertContains(r, "do not match")
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.password, old)

    def test_duplicate_email_rejected(self):
        self.login()
        r = self.post(self.alice, email="bob@example.com")
        self.assertContains(r, "already registered")

    def test_csrf_enforced(self):
        from django.test import Client

        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post("/user/edit/", {"submit": "1"}).status_code, 403)


class UserListTests(TestCase):
    def setUp(self):
        from core.models import MemberProject, Project
        from .models import ADMIN_LEVEL

        self.alice = make_member(username="alice", activation="SECRETACT1234567", salt="SALT1234")
        self.bob = make_member(username="bob", email="bob@example.com")
        self.carol = make_member(username="carol", email="carol@example.com")
        self.admin = make_member(username="root", level=ADMIN_LEVEL)
        shared = Project.objects.create(name="Shared")
        MemberProject.objects.create(member=self.alice, project=shared)
        MemberProject.objects.create(member=self.bob, project=shared)

    def login(self, name="alice"):
        self.client.post("/login/", {"username": name, "password": "secret"})

    def test_requires_sign_in(self):
        r = self.client.get("/user/list/")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].startswith("/login/?next="))

    def test_non_admin_sees_only_project_peers_with_links_and_no_secrets(self):
        self.login()
        r = self.client.get("/user/list/")
        self.assertContains(r, '/user/details/?id=%d"' % self.bob.pk)
        self.assertNotContains(r, "carol")
        self.assertNotContains(r, "root")
        for secret in (self.alice.password, "SECRETACT1234567", "SALT1234"):
            self.assertNotContains(r, secret)

    def test_admin_sees_everyone(self):
        self.login("root")
        r = self.client.get("/user/list/")
        for m in (self.alice, self.bob, self.carol, self.admin):
            self.assertContains(r, '/user/details/?id=%d"' % m.pk)

    def test_header_fields_and_xajax_carried(self):
        self.login()
        r = self.client.post("/user/list/", {
            "sProject": "3", "id": "4", "mode": "m", "sort": "title", "dir": "desc",
            "show": "my", "xajax": "foo", "xajaxargs": "bar",
        })
        self.assertContains(r, 'action="/user/list/"')
        for name, value in (("sProject", "3"), ("sort", "title"), ("dir", "desc"), ("show", "my"),
                            ("xajax", "foo"), ("xajaxargs", "bar")):
            self.assertContains(r, 'name="%s" value="%s"' % (name, value))
