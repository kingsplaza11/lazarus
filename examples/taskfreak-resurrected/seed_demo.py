"""Seed demo data for the resurrected TaskFreak.

Run from the project root:  python seed_demo.py   (or: python manage.py shell < seed_demo.py)

Fills required fields automatically by inspecting the models, so it works even though
Kiro chose the exact field names. Prints what it created. Safe to run more than once.
"""
import datetime
import os
import random

if __name__ == "__main__":  # run directly: boot Django first
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "taskfreak.settings")
    import django
    django.setup()

from django.apps import apps
from django.contrib.auth.hashers import make_password
from django.db import models as m
from django.utils import timezone

Member = apps.get_model("accounts", "Member")
DEMO_PASSWORD = "lazarus-demo"




def find(name):
    for model in apps.get_app_config("core").get_models():
        if model.__name__.lower() == name.lower():
            return model
    return None


def related_value(field, given):
    target = field.related_model
    for value in given.values():
        if isinstance(value, target):
            return value
    if target is Member:
        return admin
    existing = target.objects.first()
    if existing is not None:
        return existing
    return None if field.null else make(target)


def make(model, **given):
    values = dict(given)
    for field in model._meta.fields:
        if field.name in values or field.primary_key and field.get_internal_type() in ("AutoField", "BigAutoField"):
            continue
        if field.is_relation:
            value = related_value(field, given)
            if value is not None:
                values[field.name] = value
            continue
        if field.has_default() or field.null or field.blank:
            continue
        kind = field.get_internal_type()
        if kind in ("CharField", "TextField"):
            values[field.name] = field.name[: field.max_length or 20]
        elif kind in ("IntegerField", "PositiveIntegerField", "SmallIntegerField", "PositiveSmallIntegerField", "BigIntegerField"):
            values[field.name] = 0
        elif kind == "BooleanField":
            values[field.name] = False
        elif kind == "DateField":
            values[field.name] = datetime.date.today()
        elif kind == "DateTimeField":
            values[field.name] = timezone.now()
        elif kind in ("DecimalField", "FloatField"):
            values[field.name] = 0
    return model.objects.create(**values)


def set_if(obj, **fields):
    names = {f.name for f in obj._meta.fields}
    for name, value in fields.items():
        if name in names:
            setattr(obj, name, value)
    obj.save()


admin = Member.objects.filter(username="admin").first()
if admin is None:
    admin = make(Member, username="admin")
# Always (re)set the demo password with Django's own hasher. Kiro's accounts app verifies
# through Django's password hashers (legacy TaskFreak MD5 plus the modern default).
if hasattr(admin, "set_password"):
    admin.set_password(DEMO_PASSWORD)
else:
    admin.password = make_password(DEMO_PASSWORD)
set_if(admin, enabled=True, is_active=True, email=admin.email if getattr(admin, "email", "") not in ("", "email") else "admin@example.com",
       first_name="Demo", last_name="Admin")
print(f"Demo login: admin / {DEMO_PASSWORD}")

Project, Item, MemberProject = find("Project"), find("Item"), find("MemberProject")
print("Models found:", Project, Item, MemberProject)

projects = []
for name, description in [
    ("Website relaunch", "Bring the 2009 company site back to life."),
    ("Kiroween 2026", "Ship Lazarus before the deadline."),
]:
    project = Project.objects.filter(name=name).first() if "name" in {f.name for f in Project._meta.fields} else None
    if project is None:
        project = make(Project)
        set_if(project, name=name, description=description)
    projects.append(project)
    if MemberProject is not None:
        link_fields = {f.name: f for f in MemberProject._meta.fields}
        member_field = next(f for f in MemberProject._meta.fields if f.is_relation and f.related_model is Member)
        project_field = next(f for f in MemberProject._meta.fields if f.is_relation and f.related_model is Project)
        link = MemberProject.objects.filter(**{member_field.name: admin, project_field.name: project}).first()
        if link is None:
            link = make(MemberProject, **{member_field.name: admin, project_field.name: project})
        set_if(link, position=5)

tasks = {
    "Website relaunch": ["Audit dead links", "Replace mysql_* calls", "Write migration plan", "Test on PHP 8"],
    "Kiroween 2026": ["Record the demo video", "Write the Kiro write-up", "Publish blog post", "Submit on Devpost"],
}
project_field = next((f for f in Item._meta.fields if f.is_relation and f.related_model is Project), None)
for project in projects:
    for i, title in enumerate(tasks.get(getattr(project, "name", ""), ["Sample task"]), start=1):
        lookup = {project_field.name: project} if project_field else {}
        if "title" in {f.name for f in Item._meta.fields} and Item.objects.filter(title=title, **lookup).exists():
            continue
        item = make(Item, **lookup)
        set_if(item, title=title, priority=random.choice([1, 2, 3]),
               deadline=datetime.date.today() + datetime.timedelta(days=i * 3),
               description=f"Demo task {i} for {getattr(project, 'name', 'project')}.")

print("Projects:", Project.objects.count(), "| Tasks:", Item.objects.count(),
      "| Memberships:", MemberProject.objects.count() if MemberProject else "n/a")
