from django.db import models

from lazarus.choices import Status


class Corpse(models.Model):
    name = models.CharField(max_length=200)
    source_url = models.URLField(blank=True)
    storage_path = models.CharField(max_length=500, blank=True)
    file_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
