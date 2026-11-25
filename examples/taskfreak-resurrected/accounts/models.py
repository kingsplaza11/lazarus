from django.db import models


# The legacy repo never defines what Member.level values mean. We therefore treat
# the single value ADMIN_LEVEL (and anything above it) as "administrator". Only
# administrators may edit other members or change a member's 'enabled'/'level'
# (see accounts.views.user_edit). Levels are clamped to 0..ADMIN_LEVEL.
ADMIN_LEVEL = 5


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
