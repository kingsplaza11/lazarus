"""Generate and export the Kiro spec for a corpse."""
from __future__ import annotations

import io
import json
import re
import traceback
import zipfile

from autopsy.models import Autopsy
from intake.models import Corpse
from lazarus.choices import Status
from parity.models import Job

from .generator import default_intro, generate_spec, validate_ears
from .llm import polish
from .models import Spec


class SpecError(Exception):
    """Raised with a user-facing message."""


def spec_files(spec: Spec) -> dict[str, str]:
    """All generated files as {path inside .kiro/: content}."""
    try:
        files = json.loads(spec.steering_md or "{}")
    except json.JSONDecodeError:
        files = {}
    return files if isinstance(files, dict) else {}


def requirements_text(files: dict[str, str]) -> str:
    return next((v for k, v in files.items() if k.endswith("/requirements.md")), "")


def generate_for_corpse(corpse: Corpse) -> Spec:
    autopsy = Autopsy.objects.filter(corpse=corpse, status=Status.DONE).first()
    if autopsy is None or not autopsy.report.get("summary"):
        raise SpecError("Run the autopsy before writing the spec.")
    job = Job.objects.create(kind="spec", corpse=corpse, status=Status.RUNNING)
    try:
        intro, provider = polish(default_intro(corpse.name, autopsy.report))
        files = generate_spec(autopsy.report, corpse.name, intro)
        total, invalid = validate_ears(requirements_text(files))
        spec = Spec.objects.create(
            autopsy=autopsy,
            requirements_md=requirements_text(files),
            design_md=next((v for k, v in files.items() if k.endswith("/design.md")), ""),
            tasks_md=next((v for k, v in files.items() if k.endswith("/tasks.md")), ""),
            steering_md=json.dumps(files),
        )
    except Exception as exc:
        job.status = Status.FAILED
        job.log = traceback.format_exc()
        job.save()
        raise SpecError(f"Writing the spec failed: {exc}") from exc
    job.status = Status.DONE
    job.log = f"{len(files)} files, {total} acceptance criteria, {len(invalid)} not EARS. Introduction by {provider}.\n"
    job.save()
    return spec


def latest_spec(corpse: Corpse) -> Spec | None:
    return Spec.objects.filter(autopsy__corpse=corpse).order_by("-created_at", "-pk").first()


def export_filename(corpse: Corpse) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", corpse.name.lower()).strip("-") or "corpse"
    return f"{slug}-kiro.zip"


def export_zip(spec: Spec) -> bytes:
    """A zip whose single top-level folder is .kiro/, ready to drop into an empty project."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(spec_files(spec).items()):
            zf.writestr(f".kiro/{path}", content)
    return buffer.getvalue()
