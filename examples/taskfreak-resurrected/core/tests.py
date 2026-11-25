from django.test import TestCase


class BaseTemplateTests(TestCase):
    def test_home_uses_shared_stylesheet_and_htmx(self):
        r = self.client.get("/login/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "skins/redfreak/css/freak.css")
        self.assertContains(r, "js/htmx.min.js")

    def test_skin_choice_switches_stylesheet(self):
        r = self.client.post("/skin/", {"skin": "bluefreak", "next": "/login/"}, follow=True)
        self.assertContains(r, "skins/bluefreak/css/freak.css")

    def test_invalid_skin_ignored(self):
        r = self.client.post("/skin/", {"skin": "../evil", "next": "/login/"}, follow=True)
        self.assertContains(r, "skins/redfreak/css/freak.css")

    def test_navigation_only_when_signed_in(self):
        from accounts.models import Member
        from core.models import Country
        self.assertNotContains(self.client.get("/login/"), 'id="menu"')
        Country.objects.create(countryid="US")
        m = Member.objects.create(username="bob", country_id="US", enabled=True)
        session = self.client.session
        session["memberid"] = m.pk
        session.save()
        r = self.client.get("/")
        self.assertContains(r, 'id="menu"')
        self.assertContains(r, "bob")


class ErrorViewTests(TestCase):
    def test_error_shows_message(self):
        r = self.client.get("/error/", {"tznMessage": "Something broke"})
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "core/error.html")
        self.assertContains(r, "Something broke")

    def test_error_without_message(self):
        r = self.client.get("/error/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "An error occurred.")

    def test_error_message_is_escaped(self):
        r = self.client.get("/error/", {"tznMessage": "<script>alert(1)</script>"})
        self.assertNotContains(r, "<script>alert(1)</script>")
        self.assertContains(r, "&lt;script&gt;alert(1)&lt;/script&gt;")


class HomeViewTests(TestCase):
    def setUp(self):
        from accounts.models import Member
        from core.models import Country, Item, ItemStatus, MemberProject, Project
        Country.objects.create(countryid="US")
        self.me = Member.objects.create(username="me", country_id="US", enabled=True)
        self.other = Member.objects.create(username="other", country_id="US", enabled=True)
        self.p1 = Project.objects.create(name="Alpha")
        self.p2 = Project.objects.create(name="Beta")
        self.p3 = Project.objects.create(name="Hidden")
        MemberProject.objects.create(member=self.me, project=self.p1, position=1)
        MemberProject.objects.create(member=self.me, project=self.p2, position=2)
        self.a = Item.objects.create(project=self.p1, member=self.me, title="Mine A", priority=2)
        self.b = Item.objects.create(project=self.p2, member=self.me, title="Mine B", priority=1)
        self.c = Item.objects.create(project=self.p1, member=self.other, title="Theirs C", priority=3)
        self.d = Item.objects.create(project=self.p3, member=self.me, title="Not my project")
        self.e = Item.objects.create(project=self.p1, member=self.other, title="Private E", showprivate=True)
        self.done = Item.objects.create(project=self.p1, member=self.me, title="Finished")
        ItemStatus.objects.create(item=self.done, statuskey=9, member=self.me)
        s = self.client.session
        s["memberid"] = self.me.pk
        s.save()

    def test_anonymous_redirected_to_login_with_next(self):
        self.client.session.flush()
        c = self.client_class()
        r = c.get("/", {"sort": "title"})
        self.assertRedirects(r, "/login/?next=/%3Fsort%3Dtitle", fetch_redirect_response=False)

    def test_default_shows_my_open_items_in_my_projects(self):
        r = self.client.get("/")
        self.assertTemplateUsed(r, "core/home.html")
        titles = [i.title for i in r.context["items"]]
        self.assertEqual(titles, ["Mine B", "Mine A"])
        for name in ("sProject", "id", "mode", "sort", "dir", "show"):
            self.assertContains(r, f'name="{name}"')

    def test_show_all_excludes_private_of_others_and_foreign_projects(self):
        titles = [i.title for i in self.client.get("/", {"show": "all"}).context["items"]]
        self.assertEqual(sorted(titles), ["Mine A", "Mine B", "Theirs C"])

    def test_show_done(self):
        titles = [i.title for i in self.client.get("/", {"show": "done"}).context["items"]]
        self.assertEqual(titles, ["Finished"])

    def test_project_filter_sort_and_dir_via_post(self):
        r = self.client.post("/", {"sProject": self.p1.pk, "show": "all", "sort": "title", "dir": "desc"})
        self.assertEqual([i.title for i in r.context["items"]], ["Theirs C", "Mine A"])

    def test_foreign_project_and_bad_values_ignored(self):
        r = self.client.get("/", {"sProject": self.p3.pk, "sort": "x;drop", "dir": "zz", "show": "bogus"})
        self.assertIsNone(r.context["sProject"])
        self.assertEqual((r.context["sort"], r.context["dir"], r.context["show"]), ("priority", "asc", "my"))
        self.assertEqual(len(r.context["items"]), 2)

    def test_htmx_returns_partial_only(self):
        r = self.client.get("/", HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(r, "core/_task_list.html")
        self.assertTemplateNotUsed(r, "base.html")
        self.assertContains(r, "Mine A")


class PrintListViewTests(HomeViewTests):
    """Reuses the home fixtures; the print view must filter and sort identically."""

    def test_anonymous_redirected_to_login_with_next(self):
        c = self.client_class()
        r = c.get("/print/list/", {"sort": "title"})
        self.assertRedirects(r, "/login/?next=/print/list/%3Fsort%3Dtitle", fetch_redirect_response=False)

    def test_print_list_is_standalone_and_matches_home_items(self):
        for params in ({}, {"show": "all"}, {"show": "done"}, {"sProject": self.p1.pk, "show": "all", "sort": "title", "dir": "desc"}):
            home = [i.pk for i in self.client.get("/", params).context["items"]]
            r = self.client.get("/print/list/", params)
            self.assertTemplateUsed(r, "core/print_list.html")
            self.assertTemplateNotUsed(r, "base.html")
            self.assertEqual([i.pk for i in r.context["items"]], home)

    def test_post_and_xajax_params_carried_through(self):
        r = self.client.post("/print/list/", {"show": "all", "xajax": "foo", "xajaxargs": "b\"ar"})
        self.assertContains(r, 'name="xajax" value="foo"')
        self.assertContains(r, 'name="xajaxargs" value="b&quot;ar"')
        self.assertContains(r, "Theirs C")


class ProjectEditViewTests(TestCase):
    def setUp(self):
        from accounts.models import Member
        from core.models import Country, MemberProject, Project
        Country.objects.create(countryid="US")
        self.me = Member.objects.create(username="me", email="me@x.org", country_id="US", enabled=True)
        self.bob = Member.objects.create(username="bob", email="bob@x.org", country_id="US", enabled=True)
        self.off = Member.objects.create(username="off", email="off@x.org", country_id="US", enabled=False)
        self.p = Project.objects.create(name="Mine")
        self.q = Project.objects.create(name="Theirs")
        MemberProject.objects.create(member=self.me, project=self.p, position=1)
        MemberProject.objects.create(member=self.bob, project=self.q, position=1)
        s = self.client.session
        s["memberid"] = self.me.pk
        s.save()

    def test_anonymous_redirected(self):
        r = self.client_class().get("/project/edit/")
        self.assertRedirects(r, "/login/?next=/project/edit/", fetch_redirect_response=False)

    def test_new_form_and_create(self):
        from core.models import MemberProject, Project, ProjectStatus
        r = self.client.get("/project/edit/")
        self.assertTemplateUsed(r, "core/project_edit.html")
        r = self.client.post("/project/edit/", {"submit": "1", "name": "New", "description": "d", "status": "2"})
        p = Project.objects.get(name="New")
        self.assertRedirects(r, f"/project/edit/?id={p.pk}&saved=1", fetch_redirect_response=False)
        self.assertTrue(MemberProject.objects.filter(member=self.me, project=p).exists())
        self.assertEqual(ProjectStatus.objects.get(project=p).statuskey, 2)

    def test_invalid_post_rerenders_without_saving(self):
        from core.models import Project
        r = self.client.post("/project/edit/", {"submit": "1", "name": "  ", "status": "9"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors)
        self.assertEqual(Project.objects.count(), 2)

    def test_edit_existing_and_forbidden_for_non_member(self):
        self.client.post("/project/edit/", {"submit": "1", "id": self.p.pk, "name": "Renamed", "status": "1"})
        self.p.refresh_from_db()
        self.assertEqual(self.p.name, "Renamed")
        self.assertEqual(self.client.get("/project/edit/", {"id": self.q.pk}).status_code, 403)
        self.assertEqual(self.client.post("/project/edit/", {"submit": "1", "id": self.q.pk, "name": "x", "status": "1"}).status_code, 403)
        self.assertEqual(self.client.get("/project/edit/", {"id": 9999}).status_code, 404)
        self.assertEqual(self.client.get("/project/edit/", {"id": "abc"}).status_code, 404)

    def test_invite_by_username_email_and_failures(self):
        from core.models import MemberProject
        url = "/project/edit/"
        r = self.client.post(url, {"invite": "1", "id": self.p.pk, "invitee": "BOB"})
        self.assertContains(r, "bob was added")
        self.assertTrue(MemberProject.objects.filter(member=self.bob, project=self.p).exists())
        r = self.client.post(url, {"invite": "1", "id": self.p.pk, "invitee": "bob@x.org"})
        self.assertContains(r, "already a member")
        self.assertEqual(MemberProject.objects.filter(member=self.bob, project=self.p).count(), 1)
        r = self.client.post(url, {"invite": "1", "id": self.p.pk, "invitee": "off"})
        self.assertContains(r, "No active member")

    def test_csrf_enforced_and_xajax_carried(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        s = c.session
        s["memberid"] = self.me.pk
        s.save()
        c.cookies[settings_session_cookie()] = s.session_key
        self.assertEqual(c.post("/project/edit/", {"submit": "1", "name": "x", "status": "1"}).status_code, 403)
        r = self.client.get("/project/edit/", {"xajax": "foo", "xajaxargs": 'b"ar'})
        self.assertContains(r, 'name="xajax" value="foo"')
        self.assertContains(r, 'name="xajaxargs" value="b&quot;ar"')


class ProjectListViewTests(TestCase):
    def setUp(self):
        from accounts.models import Member
        from core.models import Country, MemberProject, Project, ProjectStatus
        from django.utils import timezone
        import datetime
        Country.objects.create(countryid="US")
        self.me = Member.objects.create(username="me", email="me@x.org", country_id="US", enabled=True)
        self.bob = Member.objects.create(username="bob", email="bob@x.org", country_id="US", enabled=True)
        self.p = Project.objects.create(name="Mine")
        self.q = Project.objects.create(name="Theirs")
        MemberProject.objects.create(member=self.me, project=self.p, position=1)
        MemberProject.objects.create(member=self.bob, project=self.q, position=1)
        now = timezone.now()
        ProjectStatus.objects.create(project=self.p, statuskey=1, member=self.me, statusdate=now - datetime.timedelta(days=1))
        ProjectStatus.objects.create(project=self.p, statuskey=3, member=self.me, statusdate=now)
        s = self.client.session
        s["memberid"] = self.me.pk
        s.save()

    def test_anonymous_redirected(self):
        r = self.client_class().get("/project/list/")
        self.assertRedirects(r, "/login/?next=/project/list/", fetch_redirect_response=False)

    def test_lists_only_own_projects_with_latest_status_and_edit_link(self):
        r = self.client.get("/project/list/")
        self.assertTemplateUsed(r, "core/project_list.html")
        self.assertContains(r, "Mine")
        self.assertNotContains(r, "Theirs")
        self.assertContains(r, "Completed")
        self.assertContains(r, f'href="/project/edit/?id={self.p.pk}"')

    def test_header_fields_and_xajax_carried_on_post(self):
        r = self.client.post("/project/list/", {"sort": "title", "dir": "desc", "show": "all", "xajax": "foo", "xajaxargs": 'b"ar'})
        self.assertContains(r, 'name="sort" value="title"')
        self.assertContains(r, 'name="show" value="all"')
        self.assertContains(r, 'name="xajax" value="foo"')
        self.assertContains(r, 'name="xajaxargs" value="b&quot;ar"')


def settings_session_cookie():
    from django.conf import settings
    return settings.SESSION_COOKIE_NAME
class PublicViewTests(TestCase):
    def setUp(self):
        from accounts.models import Member
        from core.models import Country, Item, ItemStatus, MemberProject, Project
        from core.views import public_token
        from django.utils import timezone
        Country.objects.create(countryid="US")
        self.me = Member.objects.create(username="me", email="me@x.org", country_id="US", enabled=True)
        self.p = Project.objects.create(name="Mine")
        self.q = Project.objects.create(name="Other")
        MemberProject.objects.create(member=self.me, project=self.p, position=1)
        Item.objects.create(project=self.p, member=self.me, title="Open one")
        Item.objects.create(project=self.p, member=self.me, title="Secret one", showprivate=True)
        Item.objects.create(project=self.q, member=self.me, title="Other project task")
        done = Item.objects.create(project=self.p, member=self.me, title="Finished one")
        ItemStatus.objects.create(item=done, statuskey=5, member=self.me, statusdate=timezone.now())
        self.token = public_token(self.p)
    def test_valid_token_shows_only_public_open_items_without_login(self):
        r = self.client.get("/public/", {"token": self.token})
        self.assertTemplateUsed(r, "core/public.html")
        self.assertContains(r, "Open one")
        for hidden in ("Secret one", "Other project task", "Finished one", "me@x.org"):
            self.assertNotContains(r, hidden)
    def test_missing_or_bad_token_redirects_to_error(self):
        for params in ({}, {"token": "garbage"}, {"token": self.token + "x"}, {"token": "1"}):
            r = self.client.get("/public/", params)
            self.assertEqual(r.status_code, 302)
            self.assertTrue(r["Location"].startswith("/error/?tznMessage="))
    def test_token_for_other_purpose_rejected(self):
        from django.core import signing
        r = self.client.get("/public/", {"token": signing.dumps(self.p.pk, salt="other")})
        self.assertEqual(r.status_code, 302)
    def test_rss_valid_token_lists_only_public_open_items(self):
        from xml.etree import ElementTree
        r = self.client.get("/rss/", {"token": self.token})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r["Content-Type"].startswith("application/rss+xml"))
        root = ElementTree.fromstring(r.content)
        titles = [t.text for t in root.findall("./channel/item/title")]
        self.assertEqual(titles, ["Open one"])
    def test_rss_escapes_markup(self):
        from xml.etree import ElementTree
        from core.models import Item
        Item.objects.create(project=self.p, member=self.me, title="A <b>&</b>")
        r = self.client.get("/rss/", {"token": self.token})
        titles = [t.text for t in ElementTree.fromstring(r.content).findall("./channel/item/title")]
        self.assertIn("A <b>&</b>", titles)
    def test_rss_bad_token_redirects_to_error(self):
        for params in ({}, {"token": "garbage"}, {"token": self.token + "x"}):
            r = self.client.get("/rss/", params)
            self.assertEqual(r.status_code, 302)
            self.assertTrue(r["Location"].startswith("/error/?tznMessage="))
    def test_project_edit_shows_public_link_to_member(self):
        s = self.client.session
        s["memberid"] = self.me.pk
        s.save()
        r = self.client.get("/project/edit/", {"id": self.p.pk})
        self.assertContains(r, 'id="public-link"')
        r2 = self.client.get(r.context["public_url"])
        self.assertContains(r2, "Open one")


class LookAndFeelTests(TestCase):
    """Requirement 19: one shared skin stylesheet, nav + user everywhere, phone-ready."""

    def setUp(self):
        from accounts.models import Member
        from core.models import Country
        Country.objects.create(countryid="US")
        self.m = Member.objects.create(username="bob", country_id="US", enabled=True)
        s = self.client.session
        s["memberid"] = self.m.pk
        s.save()

    def test_pages_share_skin_stylesheet_viewport_nav_and_user(self):
        for url in ["/", "/project/list/", "/user/list/", "/user/details/", "/user/edit/",
                    "/user/password/", "/print/list/"]:
            r = self.client.get(url, follow=True)
            self.assertEqual(r.status_code, 200, url)
            self.assertContains(r, "skins/redfreak/css/freak.css", msg_prefix=url)
            self.assertContains(r, 'name="viewport"', msg_prefix=url)
            self.assertNotContains(r, "css/app.css", msg_prefix=url)
            if url != "/print/list/":
                self.assertContains(r, 'id="menu"', msg_prefix=url)
                self.assertContains(r, "bob", msg_prefix=url)

    def test_print_list_follows_chosen_skin(self):
        self.client.cookies["skin"] = "bluefreak"
        r = self.client.get("/print/list/")
        self.assertContains(r, "skins/bluefreak/css/freak.css")

    def test_skin_stylesheets_exist_with_responsive_rules(self):
        from django.contrib.staticfiles import finders
        for skin in ("redfreak", "bluefreak"):
            path = finders.find(f"skins/{skin}/css/freak.css")
            self.assertTrue(path)
            self.assertIn("@media (max-width: 600px)", open(path).read())
