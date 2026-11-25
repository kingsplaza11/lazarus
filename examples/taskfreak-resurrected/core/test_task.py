from django.test import Client, TestCase

from accounts.models import Member
from core.models import Country, Item, ItemComment, ItemStatus, MemberProject, Project
from core.views import DONE_STATUS


class TaskViewTests(TestCase):
    def setUp(self):
        Country.objects.create(countryid="US")
        self.me = Member.objects.create(username="me", country_id="US", enabled=True)
        self.other = Member.objects.create(username="other", country_id="US", enabled=True)
        self.outsider = Member.objects.create(username="out", country_id="US", enabled=True)
        self.p1 = Project.objects.create(name="Alpha")
        self.p2 = Project.objects.create(name="Beta")
        MemberProject.objects.create(member=self.me, project=self.p1, position=1)
        MemberProject.objects.create(member=self.other, project=self.p1, position=1)
        MemberProject.objects.create(member=self.outsider, project=self.p2, position=1)
        self.item = Item.objects.create(project=self.p1, member=self.me, title="Do it", description="Body")
        self.private = Item.objects.create(project=self.p1, member=self.other, title="Secret", showprivate=True)
        self.foreign = Item.objects.create(project=self.p2, member=self.outsider, title="Foreign")
        self._login(self.client, self.me)

    def _login(self, client, member):
        s = client.session
        s["memberid"] = member.pk
        s.save()

    def _payload(self, **kw):
        data = {
            "action": "save", "title": "New one", "description": "d", "priority": "3",
            "deadlinedate": "2030-01-31", "project": self.p1.pk, "member": self.other.pk,
        }
        data.update(kw)
        return data

    def test_anonymous_redirected_to_login(self):
        r = Client().get("/task/", {"id": self.item.pk})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].startswith("/login/?next="))

    def test_view_task(self):
        r = self.client.get("/task/", {"id": self.item.pk})
        self.assertContains(r, "Do it")
        self.assertTemplateUsed(r, "core/task.html")

    def test_htmx_returns_partial(self):
        r = self.client.get("/task/", {"id": self.item.pk}, HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(r, "core/_task_detail.html")
        self.assertTemplateNotUsed(r, "base.html")

    def test_non_member_forbidden(self):
        self.assertEqual(self.client.get("/task/", {"id": self.foreign.pk}).status_code, 403)
        self.assertEqual(self.client.post("/task/", {"action": "delete", "id": self.foreign.pk}).status_code, 403)
        self.assertTrue(Item.objects.filter(pk=self.foreign.pk).exists())

    def test_private_item_hidden_from_non_assignee(self):
        self.assertEqual(self.client.get("/task/", {"id": self.private.pk}).status_code, 404)
        c = Client()
        self._login(c, self.other)
        self.assertEqual(c.get("/task/", {"id": self.private.pk}).status_code, 200)

    def test_bad_id_404(self):
        self.assertEqual(self.client.get("/task/", {"id": "abc"}).status_code, 404)
        self.assertEqual(self.client.get("/task/", {"id": 99999}).status_code, 404)

    def test_create_task(self):
        r = self.client.post("/task/", self._payload())
        item = Item.objects.get(title="New one")
        self.assertRedirects(r, "/task/?id=%d" % item.pk, fetch_redirect_response=False)
        self.assertEqual((item.priority, str(item.deadlinedate), item.member_id, item.authorid),
                         (3, "2030-01-31", self.other.pk, self.me.pk))

    def test_create_rejects_foreign_project_and_nonmember_assignee(self):
        r = self.client.post("/task/", self._payload(project=self.p2.pk))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Item.objects.filter(title="New one").exists())
        r = self.client.post("/task/", self._payload(member=self.outsider.pk))
        self.assertFalse(Item.objects.filter(title="New one").exists())

    def test_edit_task(self):
        self.client.post("/task/", self._payload(id=self.item.pk, title="Renamed"))
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, "Renamed")

    def test_edit_form_prefilled_with_date_input(self):
        self.item.deadlinedate = "2030-05-06"
        self.item.save()
        r = self.client.get("/task/", {"action": "edit", "id": self.item.pk})
        self.assertContains(r, 'type="date"')
        self.assertContains(r, 'value="2030-05-06"')

    def test_change_status(self):
        self.client.post("/task/", {"action": "status", "id": self.item.pk, "status": DONE_STATUS})
        self.assertEqual(ItemStatus.objects.get(item=self.item).statuskey, DONE_STATUS)
        r = self.client.post("/task/", {"action": "status", "id": self.item.pk, "status": "77"})
        self.assertEqual(r.status_code, 400)

    def test_add_comment(self):
        r = self.client.post("/task/", {"action": "comment", "id": self.item.pk, "body": "Hello"},
                             HTTP_HX_REQUEST="true")
        self.assertContains(r, "Hello")
        self.assertEqual(ItemComment.objects.get(item=self.item).member_id, self.me.pk)
        self.client.post("/task/", {"action": "comment", "id": self.item.pk, "body": "  "})
        self.assertEqual(ItemComment.objects.count(), 1)

    def test_delete(self):
        r = self.client.post("/task/", {"action": "delete", "id": self.item.pk})
        self.assertRedirects(r, "/", fetch_redirect_response=False)
        self.assertFalse(Item.objects.filter(pk=self.item.pk).exists())

    def test_get_cannot_mutate(self):
        self.assertEqual(self.client.get("/task/", {"action": "delete", "id": self.item.pk}).status_code, 400)
        self.assertTrue(Item.objects.filter(pk=self.item.pk).exists())

    def test_xajax_values_carried(self):
        r = self.client.get("/task/", {"id": self.item.pk, "xajax": "a", "xajaxargs": "b"})
        self.assertContains(r, 'name="xajax" value="a"')
        self.assertContains(r, 'name="xajaxargs" value="b"')


class TaskCsrfTests(TestCase):
    def test_post_without_token_rejected(self):
        Country.objects.create(countryid="US")
        m = Member.objects.create(username="me", country_id="US", enabled=True)
        c = Client(enforce_csrf_checks=True)
        s = c.session
        s["memberid"] = m.pk
        s.save()
        self.assertEqual(c.post("/task/", {"action": "save", "title": "x"}).status_code, 403)
