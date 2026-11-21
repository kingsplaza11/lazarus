from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from intake.models import Corpse
from lazarus.choices import Status

from .models import Autopsy
from .services import AutopsyError, run_autopsy


@require_POST
def run(request, pk: int):
    corpse = get_object_or_404(Corpse, pk=pk)
    try:
        run_autopsy(corpse)
    except AutopsyError as exc:
        messages.error(request, str(exc))
        return redirect("intake:detail", pk=corpse.pk)
    return redirect("autopsy:report", pk=corpse.pk)


def report(request, pk: int):
    corpse = get_object_or_404(Corpse, pk=pk)
    autopsy = Autopsy.objects.filter(corpse=corpse).first()
    if autopsy is None or autopsy.status != Status.DONE:
        messages.info(request, "No autopsy yet. Begin one below.")
        return redirect("intake:detail", pk=corpse.pk)
    return render(request, "autopsy/report.html", {"corpse": corpse, "autopsy": autopsy, "report": autopsy.report})
