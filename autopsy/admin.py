from django.contrib import admin

from .models import Autopsy


@admin.register(Autopsy)
class AutopsyAdmin(admin.ModelAdmin):
    list_display = ("id", "corpse", "status", "created_at")
