"""Load data from a legacy TaskFreak! 0.6.4 database (tables ``frk_*``)."""
import datetime
import re

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from accounts.hashers import LegacyMD5Hasher
from accounts.models import Member
from core.models import (
    Country, Item, ItemComment, ItemFile, ItemStatus, MemberProject, Project, ProjectStatus,
)

# Dependency order: parents before children.
LOAD_ORDER = [Country, Project, Member, MemberProject, Item, ItemComment, ItemFile, ItemStatus, ProjectStatus]

# Fixed statements, one per legacy table. Table names cannot be bound as query
# parameters, so no SQL is ever assembled from strings at run time (Req 18.2).
SELECT_ALL = {
    "frk_country": "SELECT * FROM frk_country",
    "frk_project": "SELECT * FROM frk_project",
    "frk_member": "SELECT * FROM frk_member",
    "frk_memberproject": "SELECT * FROM frk_memberproject",
    "frk_item": "SELECT * FROM frk_item",
    "frk_itemcomment": "SELECT * FROM frk_itemcomment",
    "frk_itemfile": "SELECT * FROM frk_itemfile",
    "frk_itemstatus": "SELECT * FROM frk_itemstatus",
    "frk_projectstatus": "SELECT * FROM frk_projectstatus",
}
COUNT_ALL = {
    "frk_country": "SELECT COUNT(*) FROM frk_country",
    "frk_project": "SELECT COUNT(*) FROM frk_project",
    "frk_member": "SELECT COUNT(*) FROM frk_member",
    "frk_memberproject": "SELECT COUNT(*) FROM frk_memberproject",
    "frk_item": "SELECT COUNT(*) FROM frk_item",
    "frk_itemcomment": "SELECT COUNT(*) FROM frk_itemcomment",
    "frk_itemfile": "SELECT COUNT(*) FROM frk_itemfile",
    "frk_itemstatus": "SELECT COUNT(*) FROM frk_itemstatus",
    "frk_projectstatus": "SELECT COUNT(*) FROM frk_projectstatus",
}
_ZERO_DATE = re.compile(r"^0000-00-00")
_MD5 = re.compile(r"^[0-9a-fA-F]{32}$")


def _clean(field, value):
    """Convert one legacy value (MySQL-ish) into a value valid for ``field``."""
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    if value is None or (isinstance(value, str) and _ZERO_DATE.match(value)):
        if field.null:
            return None
        return field.get_default()
    if isinstance(value, datetime.datetime) and value.tzinfo is None and field.get_internal_type() == "DateTimeField":
        return timezone.make_aware(value, datetime.timezone.utc)
    value = field.to_python(value)
    if isinstance(value, datetime.datetime) and timezone.is_naive(value):
        value = timezone.make_aware(value, datetime.timezone.utc)
    return value


def convert_password(legacy_hash, salt):
    """Wrap a legacy salted MD5 hash so only a salted one-way hash is stored (Req 18.4)."""
    if legacy_hash and salt and _MD5.match(legacy_hash):
        return LegacyMD5Hasher.wrap(legacy_hash, salt)
    return make_password(None)  # unusable; member must use the password reminder


def _rows(cursor, model):
    cursor.execute(SELECT_ALL[model._meta.db_table])
    cols = [c[0].lower() for c in cursor.description]
    for row in cursor.fetchall():
        yield dict(zip(cols, row))


def load_legacy(connection, stdout=None, tables=None):
    """Copy legacy tables from ``connection`` (a DB-API/Django connection).

    ``tables`` optionally restricts the copy to a set of ``frk_*`` table names
    (each must belong to LOAD_ORDER). Existing rows with the same primary key are
    updated, so the loader can be re-run. Returns ``{table: row_count}``.
    """
    counts = {}
    with transaction.atomic():
        for model in LOAD_ORDER:
            if tables is not None and model._meta.db_table not in tables:
                continue
            meta = model._meta
            fields = [f for f in meta.concrete_fields if f.column]
            cursor = connection.cursor()
            try:
                n = 0
                for row in _rows(cursor, model):
                    values = {}
                    for f in fields:
                        if f.column in row:
                            values[f.attname] = _clean(f, row[f.column])
                    if model is Member:
                        values["password"] = convert_password(str(row.get("password") or ""), str(row.get("salt") or ""))
                        if values.get("country_id") and not Country.objects.filter(pk=values["country_id"]).exists():
                            Country.objects.create(countryid=values["country_id"], name=values["country_id"])
                    if model is MemberProject:
                        key = {"member_id": values.pop("member_id"), "project_id": values.pop("project_id")}
                        model.objects.update_or_create(**key, defaults=values_without_pk(meta, values))
                    else:
                        pk = values.pop(meta.pk.attname)
                        model.objects.update_or_create(**{meta.pk.attname: pk}, defaults=values)
                    n += 1
            finally:
                cursor.close()
            counts[meta.db_table] = n
            if stdout:
                stdout.write("%s: %d rows" % (meta.db_table, n))
    return counts


def values_without_pk(meta, values):
    values.pop(meta.pk.attname, None)
    return values
