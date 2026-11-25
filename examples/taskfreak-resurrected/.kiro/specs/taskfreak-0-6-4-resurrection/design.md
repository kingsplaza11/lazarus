# Design Document: TaskFreak! 0.6.4 (resurrected)

## Overview

A Django 6 rebuild of TaskFreak! 0.6.4. Two apps: `accounts` (sign-in, registration, user management) and `core` (everything else). Server-rendered templates, HTMX for in-page updates, the Django ORM for all data access.

## Architecture

```
Browser ──► Django URLs ──► views (accounts, core) ──► templates (+ HTMX partials)
                                   │
                                   └──► Django ORM ──► database (same tables as the original)
```

## URL map

| Legacy page | New URL | App | View |
|---|---|---|---|
| `error.php` | `/error/` | core | `error` |
| `index.php` | `/` | core | `home` |
| `install/index.php` | `/install/` | core | `install` |
| `login.php` | `/login/` | accounts | `login` |
| `logout.php` | `/logout/` | accounts | `logout` |
| `print_list.php` | `/print/list/` | core | `print_list` |
| `project_edit.php` | `/project/edit/` | core | `project_edit` |
| `project_list.php` | `/project/list/` | core | `project_list` |
| `public.php` | `/public/` | core | `public` |
| `rss.php` | `/rss/` | core | `rss` |
| `user_details.php` | `/user/details/` | accounts | `user_details` |
| `user_edit.php` | `/user/edit/` | accounts | `user_edit` |
| `user_list.php` | `/user/list/` | accounts | `user_list` |
| `user_password.php` | `/user/password/` | accounts | `user_password` |
| `user_register.php` | `/user/register/` | accounts | `user_register` |
| `xajax.task.php` | `/task/` | core | `task` |

## Data Models

Field names follow the legacy columns; `db_table` and `db_column` keep the original schema so existing data loads directly.

### Country (`core` app)

```python
class Country(models.Model):
    # 2-letter code is the primary key so frk_member.countryid keeps referencing it
    countryid = models.CharField(max_length=2, primary_key=True)
    name = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "frk_country"
```

### Item (`core` app)

```python
class Item(models.Model):
    itemid = models.AutoField(primary_key=True)
    project = models.ForeignKey("core.Project", on_delete=models.CASCADE, db_column="projectid")
    itemparentid = models.IntegerField(default=0)
    priority = models.IntegerField(default=0)
    context = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    deadlinedate = models.DateField(null=True, blank=True)
    expectedduration = models.IntegerField(default=0)
    showincalendar = models.BooleanField(default=False)
    showprivate = models.BooleanField(default=False)
    member = models.ForeignKey("accounts.Member", on_delete=models.CASCADE, db_column="memberid")
    authorid = models.IntegerField(default=0)

    class Meta:
        db_table = "frk_item"
```

### ItemComment (`core` app)

```python
class ItemComment(models.Model):
    itemcommentid = models.BigAutoField(primary_key=True)
    item = models.ForeignKey("core.Item", on_delete=models.CASCADE, db_column="itemid")
    member = models.ForeignKey("accounts.Member", on_delete=models.CASCADE, db_column="memberid")
    postdate = models.DateTimeField(null=True, blank=True)
    body = models.TextField(blank=True)
    lastchangedate = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "frk_itemcomment"
```

### ItemFile (`core` app)

```python
class ItemFile(models.Model):
    itemfileid = models.BigAutoField(primary_key=True)
    item = models.ForeignKey("core.Item", on_delete=models.CASCADE, db_column="itemid")
    member = models.ForeignKey("accounts.Member", on_delete=models.CASCADE, db_column="memberid")
    filetitle = models.CharField(max_length=200, blank=True)
    filename = models.CharField(max_length=127, blank=True)
    filetype = models.CharField(max_length=30, blank=True)
    filesize = models.IntegerField(default=0)
    postdate = models.DateTimeField(null=True, blank=True)
    lastchangedate = models.DateTimeField(null=True, blank=True)
    filetags = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "frk_itemfile"
```

### ItemStatus (`core` app)

```python
class ItemStatus(models.Model):
    itemstatusid = models.BigAutoField(primary_key=True)
    item = models.ForeignKey("core.Item", on_delete=models.CASCADE, db_column="itemid")
    statusdate = models.DateTimeField(null=True, blank=True)
    statuskey = models.IntegerField(default=0)
    member = models.ForeignKey("accounts.Member", on_delete=models.CASCADE, db_column="memberid")

    class Meta:
        db_table = "frk_itemstatus"
```

### Member (`accounts` app)

```python
class Member(models.Model):
    memberid = models.AutoField(primary_key=True)
    email = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=20, blank=True)
    firstname = models.CharField(max_length=50, blank=True)
    middlename = models.CharField(max_length=50, blank=True)
    lastname = models.CharField(max_length=50, blank=True)
    zipcode = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=60, blank=True)
    statecode = models.CharField(max_length=2, blank=True)
    country = models.ForeignKey("core.Country", on_delete=models.CASCADE, db_column="countryid")
    phone = models.CharField(max_length=30, blank=True)
    mobile = models.CharField(max_length=30, blank=True)
    fax = models.CharField(max_length=30, blank=True)
    username = models.CharField(max_length=20, blank=True)
    # holds a salted hash string (PBKDF2 or wrapped legacy MD5), hence 128
    password = models.CharField(max_length=128, blank=True)
    salt = models.CharField(max_length=8, blank=True)
    autologin = models.BooleanField(default=False)
    timezone = models.IntegerField(default=0)
    expirationdate = models.DateTimeField(null=True, blank=True)
    lastlogindate = models.DateTimeField(null=True, blank=True)
    lastloginaddress = models.CharField(max_length=60, blank=True)
    creationdate = models.DateTimeField(null=True, blank=True)
    lastchangedate = models.DateTimeField(null=True, blank=True)
    visits = models.IntegerField(default=0)
    badaccess = models.IntegerField(default=0)
    level = models.IntegerField(default=0)
    activation = models.CharField(max_length=16, blank=True)
    authorid = models.IntegerField(default=0)
    enabled = models.BooleanField(default=False)

    class Meta:
        db_table = "frk_member"
```

### MemberProject (`core` app)

```python
class MemberProject(models.Model):
    member = models.ForeignKey("accounts.Member", on_delete=models.CASCADE, db_column="memberid")
    project = models.ForeignKey("core.Project", on_delete=models.CASCADE, db_column="projectid")
    position = models.IntegerField(default=0)

    class Meta:
        db_table = "frk_memberproject"
        constraints = [models.UniqueConstraint(fields=["member", "project"], name="frk_memberproject_pk")]
```

### Project (`core` app)

```python
class Project(models.Model):
    projectid = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "frk_project"
```

### ProjectStatus (`core` app)

```python
class ProjectStatus(models.Model):
    projectstatusid = models.AutoField(primary_key=True)
    project = models.ForeignKey("core.Project", on_delete=models.CASCADE, db_column="projectid")
    statusdate = models.DateTimeField(null=True, blank=True)
    statuskey = models.IntegerField(default=0)
    member = models.ForeignKey("accounts.Member", on_delete=models.CASCADE, db_column="memberid")

    class Meta:
        db_table = "frk_projectstatus"
```

## Replacing what killed it

| Legacy | Replacement |
|---|---|
| `mysql_*` functions | Django ORM querysets (parameterised by default) |
| `ereg*` / `split` | Python `re` module |
| Hand-built sessions | `django.contrib.auth` and sessions |
| bundled `jscalendar` | native HTML date inputs |
| bundled `xajax` | HTMX partial requests |

## Error Handling

- Missing records return 404; forms re-render with field errors; every write is in a transaction.
- Legacy error page behaviour maps to Django's 404/500 templates.

## Testing Strategy

- One view test per legacy page: status code, key content, and form submission where a form exists.
- Model tests for each table, including uniqueness of composite keys.
- Parity check: replay recorded requests against the legacy app and the rebuild with `lazarus parity`.
