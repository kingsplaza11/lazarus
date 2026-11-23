from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from intake.models import Corpse

from .services import latest_check

LABELS = [("pages", "Pages"), ("forms", "Forms"), ("tables", "Tables"), ("safety", "Safety"), ("look", "Look and feel")]


def detail(request, pk: int):
    corpse = get_object_or_404(Corpse, pk=pk)
    check = latest_check(corpse)
    if check is None:
        messages.info(request, "No resurrection check yet. Run: python manage.py resurrection_check "
                               f"{corpse.pk} --url <rebuild url> --source <rebuild folder>")
        return redirect("intake:detail", pk=corpse.pk)
    categories = []
    for key, label in LABELS:
        cat = check.results["categories"].get(key, {})
        if cat.get("total"):
            categories.append({"key": key, "label": label, "percent": round(cat["score"] * 100), **cat})
    return render(request, "parity/check.html", {"corpse": corpse, "check": check, "categories": categories})
