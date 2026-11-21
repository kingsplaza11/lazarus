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
