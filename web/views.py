from django.http import JsonResponse
from django.shortcuts import render
from intake.models import Corpse


def home(request):
    corpses = Corpse.objects.order_by("-created_at", "-pk")
    return render(request, "web/home.html", {"corpses": corpses})


def health(request):
    return JsonResponse({"status": "ok"})
