from django.conf import settings
from django.core import signing
from django.http import HttpResponseRedirect
from django.db import transaction
from django.db.models import Max, OuterRef, Q, Subquery
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST
from urllib.parse import quote

import re

from accounts.models import Member
from accounts.views import current_member

from .legacy import COUNT_ALL, LOAD_ORDER, load_legacy
from .forms import PROJECT_STATUS_CHOICES, InviteForm, ProjectForm
from .models import Item, ItemStatus, MemberProject, Project, ProjectStatus

# Latest ItemStatus.statuskey at or above this value counts as finished.
DONE_STATUS = 5
SORTS = {
    "priority": "priority",
    "title": "title",
    "deadline": "deadlinedate",
    "project": "project__name",
}
SHOWS = ("my", "all", "done")


def build_task_list(request, member):
    """Apply the header form fields (sProject, id, mode, sort, dir, show) and return the template context.

    Shared by the home and print_list views.
    """
    params = request.POST if request.method == "POST" else request.GET
    project_ids = list(
        MemberProject.objects.filter(member=member).order_by("position").values_list("project_id", flat=True)
    )
    projects = list(
        MemberProject.objects.filter(member=member).select_related("project").order_by("position", "project__name")
    )

    sproject = params.get("sProject", "")
    selected = int(sproject) if sproject.isdigit() and int(sproject) in project_ids else None
    sort = params.get("sort", "")
    if sort not in SORTS:
        sort = "priority"
    direction = "desc" if params.get("dir") == "desc" else "asc"
    show = params.get("show", "")
    if show not in SHOWS:
        show = "my"
    item_id = params.get("id", "")
    item_id = int(item_id) if item_id.isdigit() else None

    latest = (
        ItemStatus.objects.filter(item=OuterRef("pk")).order_by("-statusdate", "-itemstatusid").values("statuskey")[:1]
    )
    items = (
        Item.objects.filter(project_id__in=[selected] if selected else project_ids)
        .select_related("project", "member")
        .annotate(status=Subquery(latest))
    )
    # Private items are only visible to their assignee.
    items = items.filter(Q(showprivate=False) | Q(member=member))
    if show == "done":
        items = items.filter(status__gte=DONE_STATUS)
    else:
        items = items.filter(Q(status__isnull=True) | Q(status__lt=DONE_STATUS))
        if show == "my":
            items = items.filter(member=member)
    order = SORTS[sort]
    items = items.order_by(("-" if direction == "desc" else "") + order, "itemid")

    ctx = {
        "projects": projects,
        "items": items,
        "sProject": selected,
        "sort": sort,
        "dir": direction,
        "show": show,
        "item_id": item_id,
        "mode": params.get("mode", "")[:20],
        "sorts": list(SORTS),
        "shows": SHOWS,
    }
    return ctx


@require_http_methods(["GET", "POST"])
def home(request):
    """Task list for the signed-in member's projects.

    Accepts the header form fields sProject, id, mode, sort, dir, show via GET or POST.
    HTMX requests receive only the list fragment.
    """
    member = current_member(request)
    if member is None:
        return redirect("/login/?next=" + quote(request.get_full_path(), safe="/"))
    ctx = build_task_list(request, member)
    if request.headers.get("HX-Request"):
        return render(request, "core/_task_list.html", ctx)
    return render(request, "core/home.html", ctx)


@require_http_methods(["GET", "POST"])
def print_list(request):
    """Printable version of the home task list (same filters and sorting)."""
    member = current_member(request)
    if member is None:
        return redirect("/login/?next=" + quote(request.get_full_path(), safe="/"))
    ctx = build_task_list(request, member)
    params = request.POST if request.method == "POST" else request.GET
    ctx["xajax"] = params.get("xajax", "")[:200]
    ctx["xajaxargs"] = params.get("xajaxargs", "")[:1000]
    ctx["member"] = member
    ctx["selected_project"] = next((mp.project for mp in ctx["projects"] if mp.project_id == ctx["sProject"]), None)
    return render(request, "core/print_list.html", ctx)


@require_http_methods(["GET", "POST"])
def project_list(request):
    """List the signed-in member's projects with their latest status and an edit link.

    Accepts the header form fields (sProject, id, mode, sort, dir, show) and the
    xajax/xajaxargs values, and carries them through in hidden inputs.
    """
    member = current_member(request)
    if member is None:
        return redirect("/login/?next=" + quote(request.get_full_path(), safe="/"))
    ctx = build_task_list(request, member)
    params = request.POST if request.method == "POST" else request.GET
    labels = dict(PROJECT_STATUS_CHOICES)
    rows = []
    for mp in ctx["projects"]:
        last = ProjectStatus.objects.filter(project=mp.project).order_by("-statusdate", "-projectstatusid").first()
        key = last.statuskey if last else None
        rows.append({"project": mp.project, "status_key": key, "status": labels.get(key, "") if key else ""})
    ctx["rows"] = rows
    ctx["carried"] = {
        "xajax": params.get("xajax", "")[:200],
        "xajaxargs": params.get("xajaxargs", "")[:1000],
    }
    return render(request, "core/project_list.html", ctx)


def error(request):
    """Display the message passed in ?tznMessage= (auto-escaped by the template)."""
    return render(request, "core/error.html", {"message": request.GET.get("tznMessage", "")})


INSTALL_TABLES = tuple(m._meta.db_table for m in LOAD_ORDER)
_HOST_RE = re.compile(r"^[A-Za-z0-9._-]{1,255}$")
_MYSQL_NAME_RE = re.compile(r"^[A-Za-z0-9_$]{1,64}$")


def open_source_connection(host, port, user, password, database):
    """Open a DB-API connection to the legacy MySQL database (needs PyMySQL or mysqlclient)."""
    try:
        import pymysql as driver
        kwargs = {"database": database}
    except ImportError:
        try:
            import MySQLdb as driver
            kwargs = {"db": database}
        except ImportError:
            raise RuntimeError("No MySQL driver installed (install PyMySQL).")
    return driver.connect(host=host, port=port, user=user, password=password, connect_timeout=10, **kwargs)


def _install_form(data):
    """Validate the install form; return (cleaned, errors)."""
    errors = {}
    action = data.get("action", "")
    if action not in ("test", "copy"):
        errors["action"] = "Unknown action."
    host = data.get("src_host", "").strip() or "localhost"
    if not _HOST_RE.match(host):
        errors["src_host"] = "Invalid host name."
    port = data.get("src_port", "").strip() or "3306"
    if not (port.isdigit() and 0 < int(port) < 65536):
        errors["src_port"] = "Invalid port."
    user = data.get("src_user", "")
    if not user or len(user) > 80:
        errors["src_user"] = "A user name is required."
    base = data.get("src_base", "").strip()
    if not _MYSQL_NAME_RE.match(base):
        errors["src_base"] = "Invalid database name."
    table = data.get("src_table", "").strip() or "all"
    if table != "all" and table not in INSTALL_TABLES:
        errors["src_table"] = "Unknown table."
    cleaned = {
        "action": action, "src_host": host, "src_port": port, "src_user": user,
        "src_pass": data.get("src_pass", ""), "src_base": base, "src_table": table,
    }
    return cleaned, errors


@require_http_methods(["GET", "POST"])
def install(request):
    """Copy data from a legacy TaskFreak! MySQL database.

    Only available while no Member exists (fresh install); afterwards it answers 403.
    The source password is never echoed, logged or put in an error message.
    """
    if Member.objects.exists():
        return render(
            request, "core/error.html",
            {"message": "Installation is disabled: this site already has members."}, status=403,
        )
    ctx = {"values": {}, "errors": {}, "tables": INSTALL_TABLES, "result": None, "fail": ""}
    if request.method == "POST":
        cleaned, errors = _install_form(request.POST)
        ctx["values"] = {k: v for k, v in cleaned.items() if k != "src_pass"}
        ctx["errors"] = errors
        if not errors:
            wanted = INSTALL_TABLES if cleaned["src_table"] == "all" else (cleaned["src_table"],)
            conn = None
            try:
                conn = open_source_connection(
                    cleaned["src_host"], int(cleaned["src_port"]), cleaned["src_user"],
                    cleaned["src_pass"], cleaned["src_base"],
                )
                if cleaned["action"] == "test":
                    counts = {}
                    for name in wanted:  # names come from the allowlist, never from input
                        cur = conn.cursor()
                        cur.execute(COUNT_ALL[name])
                        counts[name] = cur.fetchone()[0]
                        cur.close()
                    ctx["result"] = {"title": "Connection OK", "counts": counts}
                else:
                    counts = load_legacy(conn, tables=set(wanted))
                    ctx["result"] = {"title": "Data copied", "counts": counts}
            except Exception as e:
                # Do not include str(e): driver messages can contain credentials.
                ctx["fail"] = "Could not read the source database (%s)." % type(e).__name__
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
    return render(request, "core/install.html", ctx)


@require_POST
def set_skin(request):
    """Remember the user's skin choice (redfreak or bluefreak) in a cookie."""
    chosen = request.POST.get("skin")
    nxt = request.POST.get("next", "/")
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = "/"
    response = HttpResponseRedirect(nxt)
    if chosen in settings.SKINS:
        response.set_cookie("skin", chosen, max_age=365 * 24 * 3600, samesite="Lax")
    return response


@require_http_methods(["GET", "POST"])
def project_edit(request):
    """Create or edit a project (name, description, status) and invite members.

    ?id= (GET or POST) selects an existing project; the signed-in member must belong to it.
    POST 'submit' saves; POST 'invite' adds a member by username or email.
    """
    member = current_member(request)
    if member is None:
        return redirect("/login/?next=" + quote(request.get_full_path(), safe="/"))
    params = request.POST if request.method == "POST" else request.GET
    pid = params.get("id", "")
    project = None
    if pid:
        if not pid.isdigit():
            raise Http404
        project = get_object_or_404(Project, pk=int(pid))
        if not MemberProject.objects.filter(member=member, project=project).exists():
            return HttpResponseForbidden("You are not a member of this project.")

    def current_status(p):
        if p is None:
            return 1
        last = ProjectStatus.objects.filter(project=p).order_by("-statusdate", "-projectstatusid").first()
        return last.statuskey if last else 1

    carried = {
        "xajax": params.get("xajax", "")[:200],
        "xajaxargs": params.get("xajaxargs", "")[:1000],
    }
    ctx = {"project": project, "carried": carried, "invite_error": "", "invite_ok": "", "saved": False}
    form = ProjectForm(instance=project, initial={"status": current_status(project)})
    invite_form = InviteForm()

    if request.method == "POST":
        if "invite" in request.POST and project is not None:
            invite_form = InviteForm(request.POST)
            if invite_form.is_valid():
                who = invite_form.cleaned_data["invitee"].strip()
                target = (
                    Member.objects.filter(enabled=True)
                    .filter(Q(username__iexact=who) | Q(email__iexact=who))
                    .order_by("memberid")
                    .first()
                )
                if target is None:
                    ctx["invite_error"] = "No active member matches that username or email."
                else:
                    with transaction.atomic():
                        top = MemberProject.objects.filter(project=project).aggregate(m=Max("position"))["m"] or 0
                        _, created = MemberProject.objects.get_or_create(
                            member=target, project=project, defaults={"position": top + 1}
                        )
                    ctx["invite_ok"] = (
                        "%s was added to the project." % target.username if created
                        else "%s is already a member." % target.username
                    )
                    invite_form = InviteForm()
            else:
                ctx["invite_error"] = "Enter a username or email."
        elif "submit" in request.POST:
            form = ProjectForm(request.POST, instance=project)
            if form.is_valid():
                with transaction.atomic():
                    saved = form.save()
                    if project is None:
                        top = MemberProject.objects.filter(member=member).aggregate(m=Max("position"))["m"] or 0
                        MemberProject.objects.create(member=member, project=saved, position=top + 1)
                    status = form.cleaned_data["status"]
                    if project is None or status != current_status(project):
                        ProjectStatus.objects.create(
                            project=saved, statuskey=status, member=member, statusdate=timezone.now()
                        )
                return redirect("/project/edit/?id=%d&saved=1" % saved.pk)
    ctx["saved"] = request.method == "GET" and params.get("saved") == "1"
    if project is not None:
        ctx["public_url"] = "/public/?token=" + quote(public_token(project), safe="")
    ctx["form"] = form
    ctx["invite_form"] = invite_form
    ctx["members"] = (
        MemberProject.objects.filter(project=project).select_related("member").order_by("position")
        if project else []
    )
    return render(request, "core/project_edit.html", ctx)
PUBLIC_SALT = "taskfreak.public"
def public_token(project):
    """Unguessable, signed token that grants read-only access to a project's non-private open tasks."""
    return signing.dumps(project.pk, salt=PUBLIC_SALT)
def _project_from_token(token):
    try:
        pid = signing.loads(token, salt=PUBLIC_SALT)
    except signing.BadSignature:
        return None
    return Project.objects.filter(pk=pid).first() if isinstance(pid, int) else None
def _public_error(message):
    return redirect("/error/?tznMessage=" + quote(message, safe=""))
@require_http_methods(["GET"])
def public(request):
    """Read-only task list for one project, no sign-in. Requires ?token= from project_public_token.
    Private items, assignee names and completed items are never shown.
    """
    project = _project_from_token(request.GET.get("token", ""))
    if project is None:
        return _public_error("This public page is not available.")
    return render(request, "core/public.html", {"project": project, "items": _public_open_items(project)})
def _public_open_items(project):
    latest = (
        ItemStatus.objects.filter(item=OuterRef("pk")).order_by("-statusdate", "-itemstatusid").values("statuskey")[:1]
    )
    return (
        Item.objects.filter(project=project, showprivate=False)
        .annotate(status=Subquery(latest))
        .filter(Q(status__isnull=True) | Q(status__lt=DONE_STATUS))
        .order_by("priority", "itemid")
    )
@require_http_methods(["GET"])
def rss(request):
    """RSS 2.0 feed of a project's open, non-private items. Same ?token= authorisation as public()."""
    token = request.GET.get("token", "")
    project = _project_from_token(token)
    if project is None:
        return _public_error("This feed is not available.")
    link = request.build_absolute_uri("/public/?token=" + quote(token, safe=""))
    return render(
        request,
        "core/rss.xml",
        {"project": project, "items": _public_open_items(project), "link": link},
        content_type="application/rss+xml; charset=utf-8",
    )


def _latest_status(item):
    last = ItemStatus.objects.filter(item=item).order_by("-statusdate", "-itemstatusid").first()
    return last.statuskey if last else None


def _task_context(request, member, params, item, form=None, comment_form=None, mode="view", **extra):
    from .forms import TASK_STATUS_CHOICES, CommentForm

    status = _latest_status(item) if item else None
    ctx = {
        "item": item,
        "mode": mode,
        "form": form,
        "comment_form": comment_form or CommentForm(),
        "status": status,
        "is_done": status is not None and status >= DONE_STATUS,
        "status_choices": TASK_STATUS_CHOICES,
        "comments": item.itemcomment_set.select_related("member").order_by("postdate", "itemcommentid") if item else [],
        "carried": {
            "xajax": params.get("xajax", "")[:200],
            "xajaxargs": params.get("xajaxargs", "")[:1000],
        },
    }
    ctx.update(extra)
    return ctx


def _task_response(request, ctx):
    if request.headers.get("HX-Request"):
        partial = "core/_task_form.html" if ctx["mode"] == "edit" else "core/_task_detail.html"
        return render(request, partial, ctx)
    return render(request, "core/task.html", ctx)


@require_http_methods(["GET", "POST"])
def task(request):
    """Task view, create/edit, status change, comments and delete (replaces xajax.task.php).

    GET  ?id=N                 show a task
    GET  ?action=edit[&id=N]   edit form (new task when no id)
    POST action=save|status|comment|delete  (CSRF-protected, atomic)
    The signed-in member must belong to the item's project; private items are
    only available to their assignee. HTMX requests receive partials.
    """
    from .forms import TASK_STATUS_CHOICES, CommentForm, TaskForm

    member = current_member(request)
    if member is None:
        return redirect("/login/?next=" + quote(request.get_full_path(), safe="/"))
    params = request.POST if request.method == "POST" else request.GET
    action = params.get("action", "")
    posting = request.method == "POST"
    if posting and action not in ("save", "status", "comment", "delete"):
        return HttpResponseBadRequest("Unknown action.")
    if not posting and action not in ("", "view", "edit"):
        return HttpResponseBadRequest("Unknown action.")

    my_projects = Project.objects.filter(memberproject__member=member).distinct()
    item = None
    raw_id = params.get("id", "")
    if raw_id:
        if not raw_id.isdigit():
            raise Http404
        item = get_object_or_404(Item.objects.select_related("project", "member"), pk=int(raw_id))
        if not MemberProject.objects.filter(member=member, project_id=item.project_id).exists():
            return HttpResponseForbidden("You are not a member of this project.")
        if item.showprivate and item.member_id != member.pk:
            raise Http404
    elif action != "save" and posting:
        return HttpResponseBadRequest("A task id is required.")

    if not posting:
        if action == "edit" or item is None:
            initial = {}
            if item is None:
                initial = {"member": member.pk, "priority": 5}
                sp = params.get("sProject", "")
                if sp.isdigit() and my_projects.filter(pk=int(sp)).exists():
                    initial["project"] = int(sp)
                form = TaskForm(projects=my_projects, initial=initial)
            else:
                form = TaskForm(projects=my_projects, initial={
                    "title": item.title, "description": item.description, "priority": item.priority,
                    "deadlinedate": item.deadlinedate, "project": item.project_id,
                    "member": item.member_id, "showprivate": item.showprivate,
                })
            return _task_response(request, _task_context(request, member, params, item, form=form, mode="edit"))
        return _task_response(request, _task_context(request, member, params, item))

    if action == "save":
        form = TaskForm(request.POST, projects=my_projects)
        if not form.is_valid():
            return _task_response(request, _task_context(request, member, params, item, form=form, mode="edit"))
        d = form.cleaned_data
        with transaction.atomic():
            if item is None:
                item = Item(authorid=member.pk)
            item.project, item.member = d["project"], d["member"]
            item.title, item.description = d["title"], d["description"]
            item.priority, item.deadlinedate = d["priority"], d["deadlinedate"]
            item.showprivate = d["showprivate"]
            item.save()
    elif action == "status":
        try:
            key = int(request.POST.get("status", ""))
        except ValueError:
            return HttpResponseBadRequest("Invalid status.")
        if key not in dict(TASK_STATUS_CHOICES):
            return HttpResponseBadRequest("Invalid status.")
        with transaction.atomic():
            ItemStatus.objects.create(item=item, statuskey=key, member=member, statusdate=timezone.now())
    elif action == "comment":
        cform = CommentForm(request.POST)
        if not cform.is_valid():
            return _task_response(request, _task_context(request, member, params, item, comment_form=cform))
        with transaction.atomic():
            now = timezone.now()
            item.itemcomment_set.create(member=member, body=cform.cleaned_data["body"], postdate=now, lastchangedate=now)
    elif action == "delete":
        with transaction.atomic():
            item.delete()
        if request.headers.get("HX-Request"):
            return render(request, "core/_task_deleted.html")
        return redirect("/")

    if request.headers.get("HX-Request"):
        item = Item.objects.select_related("project", "member").get(pk=item.pk)
        return _task_response(request, _task_context(request, member, params, item))
    return redirect("/task/?id=%d" % item.pk)
