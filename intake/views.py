from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CorpseUploadForm
from .models import Corpse
from .services import IntakeError, create_from_github, create_from_zip, summon_demo


def upload(request):
    if request.method == "POST":
        form = CorpseUploadForm(request.POST, request.FILES)
        if form.is_valid():
            name = form.cleaned_data["name"]
            try:
                if form.cleaned_data.get("archive"):
                    corpse = create_from_zip(name, form.cleaned_data["archive"])
                else:
                    corpse = create_from_github(name, form.cleaned_data["github_url"])
            except IntakeError as exc:
                form.add_error(None, str(exc))
            else:
                return redirect("intake:detail", pk=corpse.pk)
    else:
        form = CorpseUploadForm()
    return render(request, "intake/upload.html", {"form": form})


@require_POST
def demo(request):
    try:
        corpse = summon_demo()
    except IntakeError as exc:
        messages.error(request, str(exc))
        return redirect("web:home")
    return redirect("intake:detail", pk=corpse.pk)


def detail(request, pk: int):
    from autopsy.models import Autopsy  # local imports keep intake usable on its own
    from parity.services import latest_check
    from specgen.services import latest_spec

    corpse = get_object_or_404(Corpse, pk=pk)
    languages = corpse.languages or {}
    return render(
        request,
        "intake/detail.html",
        {
            "corpse": corpse,
            "languages": languages,
            "has_php": languages.get("PHP", 0) > 0,
            "autopsy": Autopsy.objects.filter(corpse=corpse).first(),
            "check": latest_check(corpse),
            "spec": latest_spec(corpse),
        },
    )
