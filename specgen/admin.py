from django.contrib import admin

from .models import Spec


@admin.register(Spec)
class SpecAdmin(admin.ModelAdmin):
    list_display = ("id", "autopsy", "created_at")
