from django.contrib import admin

from .models import Corpse


@admin.register(Corpse)
class CorpseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "created_at")
