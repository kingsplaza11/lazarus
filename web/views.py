from django.http import JsonResponse
from django.shortcuts import render

from intake.models import Corpse

STEPS = [
    ("Upload", "A legacy PHP app arrives as a zip, a GitHub link, or the demo corpse. Nothing is ever executed."),
    ("Autopsy", "Tree-sitter reads every file: pages, forms, SQL, tables, and the cause of death."),
    ("Spec", "Lazarus writes a Kiro spec: EARS requirements traced to source, Django design, task plan, steering."),
    ("Resurrect", "Open the spec in Kiro and run the tasks. Kiro rebuilds the app on a modern stack."),
    ("Check", "The resurrection check scores the rebuild against the autopsy: pages, forms, tables, safety, look."),
]


def home(request):
    from parity.models import ResurrectionCheck  # local import keeps web free of hard app dependencies

    corpses = list(Corpse.objects.order_by("-created_at", "-pk"))
    scores = {}
    for check in ResurrectionCheck.objects.filter(corpse__in=corpses).order_by("corpse_id", "-created_at", "-pk"):
        scores.setdefault(check.corpse_id, check.score)
    for corpse in corpses:
        corpse.resurrection_score = scores.get(corpse.pk)
    return render(request, "web/home.html", {"corpses": corpses, "steps": STEPS})


def health(request):
    return JsonResponse({"status": "ok"})
