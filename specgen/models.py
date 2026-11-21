from django.db import models

from autopsy.models import Autopsy


class Spec(models.Model):
    autopsy = models.ForeignKey(
        Autopsy, on_delete=models.CASCADE, related_name="specs"
    )
    requirements_md = models.TextField(blank=True)
    design_md = models.TextField(blank=True)
    tasks_md = models.TextField(blank=True)
    steering_md = models.TextField(blank=True)
    export_path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Spec for {self.autopsy}"
