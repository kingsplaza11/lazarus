from django.db import models

from intake.models import Corpse
from lazarus.choices import Status


class Job(models.Model):
    kind = models.CharField(max_length=50)
    corpse = models.ForeignKey(
        Corpse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    log = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Job {self.pk} ({self.kind}, {self.status})"

    def append_log(self, line: str) -> None:
        self.log += line + "\n"
        self.save(update_fields=["log", "updated_at"])

class ResurrectionCheck(models.Model):
    """How faithfully a rebuilt app matches the legacy app's autopsy (see parity/check.py)."""

    corpse = models.ForeignKey("intake.Corpse", on_delete=models.CASCADE, related_name="checks")
    target_url = models.CharField(max_length=300)
    source_path = models.CharField(max_length=500, blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    results = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.corpse} – {self.score}%"
