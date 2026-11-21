from django.db import models


class Status(models.TextChoices):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
