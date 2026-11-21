from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from intake.models import Corpse

from .generator import validate_ears
from .services import SpecError, export_filename, export_zip, generate_for_corpse, latest_spec, requirements_text, spec_files


@require_POST
def generate(request, pk: int):
    corpse = get_object_or_404(Corpse, pk=pk)
    try:
        generate_for_corpse(corpse)
    except SpecError as exc:
        messages.error(request, str(exc))
        return redirect("intake:detail", pk=corpse.pk)
    return redirect("specgen:detail", pk=corpse.pk)


def detail(request, pk: int):
    corpse = get_object_or_404(Corpse, pk=pk)
    spec = latest_spec(corpse)
    if spec is None:
        messages.info(request, "No spec yet. Run the autopsy, then write the spec.")
        return redirect("intake:detail", pk=corpse.pk)
    files = spec_files(spec)
    total, invalid = validate_ears(requirements_text(files))
    order = {"requirements.md": 0, "design.md": 1, "tasks.md": 2}
    ordered = sorted(files.items(), key=lambda item: (
        not item[0].startswith("specs/"), order.get(item[0].rsplit("/", 1)[-1], 9), item[0]))
    return render(request, "specgen/detail.html", {
        "corpse": corpse,
        "spec": spec,
        "files": [{"path": path, "content": content, "index": i} for i, (path, content) in enumerate(ordered)],
        "criteria_total": total,
        "criteria_invalid": invalid,
    })


def download(request, pk: int):
    corpse = get_object_or_404(Corpse, pk=pk)
    spec = latest_spec(corpse)
    if spec is None:
        raise Http404("No spec yet.")
    response = HttpResponse(export_zip(spec), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{export_filename(corpse)}"'
    return response


def download_file(request, pk: int):
    corpse = get_object_or_404(Corpse, pk=pk)
    spec = latest_spec(corpse)
    path = request.GET.get("path", "")
    files = spec_files(spec) if spec else {}
    if path not in files:
        raise Http404("No such file.")
    response = HttpResponse(files[path], content_type="text/markdown; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{path.rsplit("/", 1)[-1]}"'
    return response
