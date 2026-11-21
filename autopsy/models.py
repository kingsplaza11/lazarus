from django.db import models

from intake.models import Corpse
from lazarus.choices import Status


class Autopsy(models.Model):
    corpse = models.OneToOneField(
        Corpse, on_delete=models.CASCADE, related_name="autopsy"
    )
    report = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Autopsy of {self.corpse.name}"
