"""Generate and export the Kiro spec for a corpse."""
from __future__ import annotations

import io
import json
import re
import traceback
import zipfile
from pathlib import Path

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


MAX_ASSET_BYTES = 8 * 1024 * 1024
ASSET_SUFFIXES = {".css", ".png", ".gif", ".jpg", ".jpeg", ".svg", ".ico", ".webp"}


def legacy_assets(spec: Spec) -> list[tuple[str, Path]]:
    """(relative path, file) for the original look: every stylesheet plus images in skin and stylesheet folders.

    These go into the download as legacy-assets/ so Kiro can port the real styling instead of inventing one.
    """
    corpse = spec.autopsy.corpse
    root = Path(corpse.storage_path or "")
    assets = (spec.autopsy.report or {}).get("assets") or {}
    if not root.is_dir() or not assets:
        return []
    folders = {root / skin["path"] for skin in assets.get("skins", [])}
    folders |= {(root / sheet["path"]).parent for sheet in assets.get("stylesheets", [])}
    chosen: dict[str, Path] = {}
    for sheet in assets.get("stylesheets", []):
        path = root / sheet["path"]
        if path.is_file():
            chosen[sheet["path"]] = path
    for folder in sorted(folders):
        if not folder.is_dir() or root.resolve() not in [folder.resolve(), *folder.resolve().parents]:
            continue
        for path in sorted(folder.rglob("*")):
            if path.is_file() and not path.is_symlink() and path.suffix.lower() in ASSET_SUFFIXES:
                chosen.setdefault(path.relative_to(root).as_posix(), path)
    picked, total = [], 0
    for rel, path in sorted(chosen.items(), key=lambda item: (not item[0].endswith(".css"), item[0])):
        size = path.stat().st_size
        if total + size > MAX_ASSET_BYTES:
            continue
        picked.append((rel, path))
        total += size
    return picked


def export_zip(spec: Spec) -> bytes:
    """The .kiro/ folder ready to drop into an empty project, plus legacy-assets/ with the original styling."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(spec_files(spec).items()):
            zf.writestr(f".kiro/{path}", content)
        for rel, path in legacy_assets(spec):
            zf.write(path, f"legacy-assets/{rel}")
    return buffer.getvalue()
