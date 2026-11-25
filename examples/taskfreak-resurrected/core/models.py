from django.db import models


class Country(models.Model):
    # Legacy countryid is the 2-letter code; it is the primary key so that
    # frk_member.countryid keeps referencing it unchanged.
    countryid = models.CharField(max_length=2, primary_key=True)
    name = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "frk_country"


class Project(models.Model):
    projectid = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "frk_project"


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


class ItemComment(models.Model):
    itemcommentid = models.BigAutoField(primary_key=True)
    item = models.ForeignKey("core.Item", on_delete=models.CASCADE, db_column="itemid")
    member = models.ForeignKey("accounts.Member", on_delete=models.CASCADE, db_column="memberid")
    postdate = models.DateTimeField(null=True, blank=True)
    body = models.TextField(blank=True)
    lastchangedate = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "frk_itemcomment"


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


class ItemStatus(models.Model):
    itemstatusid = models.BigAutoField(primary_key=True)
    item = models.ForeignKey("core.Item", on_delete=models.CASCADE, db_column="itemid")
    statusdate = models.DateTimeField(null=True, blank=True)
    statuskey = models.IntegerField(default=0)
    member = models.ForeignKey("accounts.Member", on_delete=models.CASCADE, db_column="memberid")

    class Meta:
        db_table = "frk_itemstatus"


class MemberProject(models.Model):
    member = models.ForeignKey("accounts.Member", on_delete=models.CASCADE, db_column="memberid")
    project = models.ForeignKey("core.Project", on_delete=models.CASCADE, db_column="projectid")
    position = models.IntegerField(default=0)

    class Meta:
        db_table = "frk_memberproject"
        constraints = [models.UniqueConstraint(fields=["member", "project"], name="frk_memberproject_pk")]


class ProjectStatus(models.Model):
    projectstatusid = models.AutoField(primary_key=True)
    project = models.ForeignKey("core.Project", on_delete=models.CASCADE, db_column="projectid")
    statusdate = models.DateTimeField(null=True, blank=True)
    statuskey = models.IntegerField(default=0)
    member = models.ForeignKey("accounts.Member", on_delete=models.CASCADE, db_column="memberid")

    class Meta:
        db_table = "frk_projectstatus"
