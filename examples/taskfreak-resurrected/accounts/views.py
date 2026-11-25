from urllib.parse import quote

from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from core.models import Country

from .models import Member

SESSION_KEY = "memberid"
REMEMBER_SECONDS = 30 * 24 * 3600
PASSTHROUGH = ("next", "xajax", "xajaxargs")


def current_member(request):
    """Return the signed-in Member for this session, or None."""
    memberid = request.session.get(SESSION_KEY)
    if not memberid:
        return None
    return Member.objects.filter(pk=memberid, enabled=True).first()


def _safe_next(request, value):
    if value and url_has_allowed_host_and_scheme(value, allowed_hosts={request.get_host()}):
        return value
    return "/"


def _error_redirect(message):
    return HttpResponseRedirect("/error/?tznMessage=" + quote(message))


def _client_ip(request):
    return request.META.get("REMOTE_ADDR", "")[:60]


@require_http_methods(["GET", "POST"])
def login(request):
    params = request.POST if request.method == "POST" else request.GET
    carried = {k: params.get(k, "") for k in PASSTHROUGH if params.get(k)}
    next_url = _safe_next(request, carried.get("next"))

    if current_member(request):
        return redirect(next_url)

    ctx = {"carried": carried, "username": "", "remember": False, "error": ""}
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        remember = bool(request.POST.get("remember"))
        ctx.update(username=username, remember=remember)

        member = Member.objects.filter(username=username).first() if username and password else None
        if member is None or not member.password:
            ctx["error"] = "Invalid username or password."
            return render(request, "accounts/login.html", ctx)

        def upgrade(raw):
            from django.contrib.auth.hashers import make_password
            member.password = make_password(raw)
            member.save(update_fields=["password"])

        if not check_password(password, member.password, setter=upgrade):
            Member.objects.filter(pk=member.pk).update(badaccess=member.badaccess + 1)
            ctx["error"] = "Invalid username or password."
            return render(request, "accounts/login.html", ctx)

        if not member.enabled:
            return _error_redirect("Your account is not activated.")
        if member.expirationdate and member.expirationdate < timezone.now():
            return _error_redirect("Your account has expired.")

        request.session.cycle_key()
        request.session[SESSION_KEY] = member.pk
        request.session.set_expiry(REMEMBER_SECONDS if remember else 0)
        Member.objects.filter(pk=member.pk).update(
            lastlogindate=timezone.now(),
            lastloginaddress=_client_ip(request),
            visits=member.visits + 1,
            badaccess=0,
            autologin=remember,
        )
        return redirect(next_url)

    return render(request, "accounts/login.html", ctx)


@require_http_methods(["GET", "POST"])
def logout(request):
    """End the session (GET or POST) and show the Logout screen."""
    member = current_member(request)
    if member:
        Member.objects.filter(pk=member.pk).update(autologin=False)
    request.session.flush()
    params = request.POST if request.method == "POST" else request.GET
    carried = {k: params.get(k, "") for k in PASSTHROUGH if params.get(k) and k != "next"}
    return render(request, "accounts/logout.html", {"carried": carried})


RESET_SALT = "accounts.user_password"
RESET_MAX_AGE = 24 * 3600
MIN_PASSWORD_LENGTH = 6


def _reset_token(member):
    # Binds to the current hash, so the link stops working once the password changes.
    return signing.dumps({"id": member.pk, "h": member.password[-12:]}, salt=RESET_SALT)


def _member_from_token(token):
    try:
        data = signing.loads(token, salt=RESET_SALT, max_age=RESET_MAX_AGE)
    except signing.BadSignature:
        return None
    member = Member.objects.filter(pk=data.get("id"), enabled=True).first()
    if member is None or member.password[-12:] != data.get("h"):
        return None
    return member


@require_http_methods(["GET", "POST"])
def user_password(request):
    """Password reminder: email a time-limited reset link, then let the user set a new password."""
    params = request.POST if request.method == "POST" else request.GET
    carried = {k: params.get(k, "") for k in PASSTHROUGH if params.get(k) and k != "next"}
    token = params.get("token", "")
    ctx = {"carried": carried, "email": "", "error": "", "sent": False, "done": False, "token": ""}

    if token:
        member = _member_from_token(token)
        if member is None:
            ctx["error"] = "This password reset link is invalid or has expired."
            return render(request, "accounts/user_password.html", ctx)
        ctx["token"] = token
        if request.method == "POST":
            p1, p2 = request.POST.get("password", ""), request.POST.get("password2", "")
            if len(p1) < MIN_PASSWORD_LENGTH:
                ctx["error"] = "Password must be at least %d characters." % MIN_PASSWORD_LENGTH
            elif p1 != p2:
                ctx["error"] = "Passwords do not match."
            else:
                member.password = make_password(p1)
                member.badaccess = 0
                member.save(update_fields=["password", "badaccess"])
                ctx.update(done=True, token="")
        return render(request, "accounts/user_password.html", ctx)

    if request.method == "POST" and "reminder" in request.POST:
        email = request.POST.get("email", "").strip()
        ctx["email"] = email
        if not email or "@" not in email:
            ctx["error"] = "Please enter a valid email address."
            return render(request, "accounts/user_password.html", ctx)
        # Same response whether or not the address matches, to avoid revealing accounts.
        for member in Member.objects.filter(email__iexact=email, enabled=True):
            link = request.build_absolute_uri("/user/password/?token=" + quote(_reset_token(member)))
            send_mail(
                "TaskFreak! password reset",
                "Hello %s,\n\nUse this link within 24 hours to choose a new password:\n%s\n\n"
                "If you did not request this, ignore this message." % (member.username, link),
                None,
                [member.email],
                fail_silently=True,
            )
        ctx["sent"] = True
    return render(request, "accounts/user_password.html", ctx)


@require_http_methods(["GET"])
def user_details(request):
    """Read-only profile of a member. Defaults to the signed-in member.

    Visible to the member themself and to members sharing at least one project.
    Never exposes password, salt or activation.
    """
    from core.models import MemberProject

    viewer = current_member(request)
    if viewer is None:
        return redirect("/login/?next=" + quote(request.get_full_path(), safe="/"))

    raw_id = request.GET.get("id", "").strip()
    if not raw_id:
        target_id = viewer.pk
    elif raw_id.isdigit():
        target_id = int(raw_id)
    else:
        return HttpResponseNotFound("Unknown member.")

    if target_id != viewer.pk:
        shared = MemberProject.objects.filter(
            member_id=target_id,
            project_id__in=MemberProject.objects.filter(member=viewer).values("project_id"),
        ).exists()
        if not shared:
            return HttpResponseForbidden("You may not view this member.")

    member = Member.objects.select_related("country").filter(pk=target_id).first()
    if member is None:
        return HttpResponseNotFound("Unknown member.")

    ctx = {
        "member": member,
        "is_self": member.pk == viewer.pk,
        "xajax": request.GET.get("xajax", "")[:200],
        "xajaxargs": request.GET.get("xajaxargs", "")[:1000],
        "projects": [
            mp.project
            for mp in MemberProject.objects.filter(member=member).select_related("project").order_by("position")
        ],
    }
    return render(request, "accounts/user_details.html", ctx)


HEADER_FIELDS = ("sProject", "id", "mode", "sort", "dir", "show")


@require_http_methods(["GET", "POST"])
def user_list(request):
    """List members. Administrators see everyone; others see members sharing a project.

    Each row links to /user/details/?id=N. Only public profile columns are read.
    """
    from core.models import MemberProject

    from .models import ADMIN_LEVEL

    viewer = current_member(request)
    if viewer is None:
        return redirect("/login/?next=" + quote(request.get_full_path(), safe="/"))

    if viewer.level >= ADMIN_LEVEL:
        members = Member.objects.all()
    else:
        mine = MemberProject.objects.filter(member=viewer).values("project_id")
        peers = MemberProject.objects.filter(project_id__in=mine).values("member_id")
        members = Member.objects.filter(Q(pk__in=peers) | Q(pk=viewer.pk))
    members = members.only("memberid", "username", "title", "firstname", "middlename", "lastname", "email", "enabled", "level").order_by("lastname", "firstname", "username", "memberid")

    params = request.POST if request.method == "POST" else request.GET
    ctx = {
        "members": members,
        "header": {f: params.get(f, "")[:100] for f in HEADER_FIELDS},
        "xajax": params.get("xajax", "")[:200],
        "xajaxargs": params.get("xajaxargs", "")[:1000],
    }
    return render(request, "accounts/user_list.html", ctx)


EDIT_FIELDS = (
    ("email", 120), ("title", 20), ("firstname", 50), ("middlename", 50), ("lastname", 50),
    ("zipcode", 20), ("city", 60), ("statecode", 2), ("phone", 30), ("mobile", 30), ("fax", 30),
)


@require_http_methods(["GET", "POST"])
def user_edit(request):
    """Edit a member's profile.

    Members edit only themselves; administrators (level >= ADMIN_LEVEL) may edit anyone.
    'enabled' and 'level' are changeable only by an administrator on ANOTHER member, so
    nobody can escalate their own privileges or lock themselves out.
    """
    from .models import ADMIN_LEVEL

    editor = current_member(request)
    if editor is None:
        return redirect("/login/?next=" + quote(request.get_full_path(), safe="/"))
    is_admin = editor.level >= ADMIN_LEVEL

    params = request.POST if request.method == "POST" else request.GET
    raw_id = params.get("id", "").strip()
    if not raw_id:
        target_id = editor.pk
    elif raw_id.isdigit():
        target_id = int(raw_id)
    else:
        return HttpResponseNotFound("Unknown member.")
    if target_id != editor.pk and not is_admin:
        return HttpResponseForbidden("You may not edit this member.")
    member = Member.objects.select_related("country").filter(pk=target_id).first()
    if member is None:
        return HttpResponseNotFound("Unknown member.")

    can_admin_fields = is_admin and member.pk != editor.pk
    xajax = params.get("xajax", "")[:200]
    xajaxargs = params.get("xajaxargs", "")[:1000]
    values = {f: getattr(member, f) for f, _ in EDIT_FIELDS}
    values["country"] = member.country_id
    values["enabled"] = member.enabled
    values["level"] = member.level
    errors = []

    if request.method == "POST" and "submit" in request.POST:
        post = request.POST
        for f, _ in EDIT_FIELDS:
            values[f] = post.get(f, "").strip()
        values["country"] = post.get("country", "").strip() or member.country_id
        for f, maxlen in EDIT_FIELDS:
            if len(values[f]) > maxlen:
                errors.append("%s must be at most %d characters." % (f.capitalize(), maxlen))
        if not values["email"] or "@" not in values["email"]:
            errors.append("Please enter a valid email address.")
        elif Member.objects.filter(email__iexact=values["email"]).exclude(pk=member.pk).exists():
            errors.append("This email address is already registered.")
        country = Country.objects.filter(pk=values["country"]).first()
        if country is None:
            errors.append("Please choose a valid country.")

        p1, p2 = post.get("password1", ""), post.get("password2", "")
        if p1 or p2:
            if len(p1) < MIN_PASSWORD_LENGTH:
                errors.append("Password must be at least %d characters." % MIN_PASSWORD_LENGTH)
            elif p1 != p2:
                errors.append("Passwords do not match.")

        new_level, new_enabled = member.level, member.enabled
        if can_admin_fields:  # silently ignored for everyone else
            raw_level = post.get("level", str(member.level)).strip()
            if raw_level.isdigit() and 0 <= int(raw_level) <= ADMIN_LEVEL:
                new_level = int(raw_level)
            else:
                errors.append("Level must be a number from 0 to %d." % ADMIN_LEVEL)
            new_enabled = bool(post.get("enabled"))
            values["level"], values["enabled"] = raw_level, new_enabled

        if not errors:
            for f, _ in EDIT_FIELDS:
                setattr(member, f, values[f])
            member.country = country
            member.level, member.enabled = new_level, new_enabled
            if p1:
                member.password = make_password(p1)
                member.badaccess = 0
            member.lastchangedate = timezone.now()
            member.save()
            url = "/user/details/?id=%d" % member.pk
            for k, v in (("xajax", xajax), ("xajaxargs", xajaxargs)):
                if v:
                    url += "&%s=%s" % (k, quote(v))
            return HttpResponseRedirect(url)

    ctx = {
        "member": member,
        "values": values,
        "errors": errors,
        "can_admin_fields": can_admin_fields,
        "admin_level": ADMIN_LEVEL,
        "xajax": xajax,
        "xajaxargs": xajaxargs,
        "countries": Country.objects.order_by("name"),
    }
    return render(request, "accounts/user_edit.html", ctx)


REGISTER_FIELDS = ("username", "email", "firstname", "lastname", "country")
UNKNOWN_COUNTRY = "--"


@require_http_methods(["GET", "POST"])
def user_register(request):
    """Self-registration. Accounts start disabled and are enabled by an emailed activation link."""
    params = request.POST if request.method == "POST" else request.GET
    carried = {k: params.get(k, "") for k in PASSTHROUGH if params.get(k) and k != "next"}
    ctx = {
        "carried": carried,
        "values": {f: "" for f in REGISTER_FIELDS},
        "errors": [],
        "done": False,
        "activated": False,
        "countries": Country.objects.exclude(countryid=UNKNOWN_COUNTRY).order_by("name"),
    }

    code = request.GET.get("activate", "")
    if request.method == "GET" and code:
        member = Member.objects.filter(activation=code, enabled=False).first() if len(code) == 16 else None
        if member is None:
            ctx["errors"] = ["This activation link is invalid or has already been used."]
        else:
            member.enabled = True
            member.activation = ""
            member.save(update_fields=["enabled", "activation"])
            ctx["activated"] = True
        return render(request, "accounts/user_register.html", ctx)

    if current_member(request):
        return redirect("/")

    if request.method == "POST" and "submit" in request.POST:
        v = {f: request.POST.get(f, "").strip() for f in REGISTER_FIELDS}
        ctx["values"] = v
        p1, p2 = request.POST.get("password1", ""), request.POST.get("password2", "")
        errors = ctx["errors"]
        if not v["username"]:
            errors.append("Username is required.")
        elif len(v["username"]) > 20:
            errors.append("Username must be at most 20 characters.")
        elif Member.objects.filter(username__iexact=v["username"]).exists():
            errors.append("This username is already taken.")
        if not v["email"] or "@" not in v["email"] or len(v["email"]) > 120:
            errors.append("Please enter a valid email address.")
        elif Member.objects.filter(email__iexact=v["email"]).exists():
            errors.append("This email address is already registered.")
        if len(p1) < MIN_PASSWORD_LENGTH:
            errors.append("Password must be at least %d characters." % MIN_PASSWORD_LENGTH)
        elif p1 != p2:
            errors.append("Passwords do not match.")
        if len(v["firstname"]) > 50 or len(v["lastname"]) > 50:
            errors.append("Names must be at most 50 characters.")
        country = Country.objects.filter(pk=v["country"]).first() if v["country"] else None
        if v["country"] and country is None:
            errors.append("Please choose a valid country.")

        if not errors:
            if country is None:
                country, _ = Country.objects.get_or_create(countryid=UNKNOWN_COUNTRY)
            now = timezone.now()
            activation = get_random_string(16)
            member = Member.objects.create(
                username=v["username"],
                email=v["email"],
                firstname=v["firstname"],
                lastname=v["lastname"],
                country=country,
                password=make_password(p1),
                activation=activation,
                enabled=False,
                creationdate=now,
                lastchangedate=now,
            )
            link = request.build_absolute_uri("/user/register/?activate=" + activation)
            send_mail(
                "TaskFreak! account activation",
                "Hello %s,\n\nOpen this link to activate your account:\n%s\n" % (member.username, link),
                None,
                [member.email],
                fail_silently=True,
            )
            ctx["done"] = True
    return render(request, "accounts/user_register.html", ctx)
