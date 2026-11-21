"""Turn a zip upload, a GitHub URL or the demo into a stored Corpse."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django.conf import settings

from intake.models import Corpse
from lazarus.choices import Status
from parity.models import Job

from .github import GitHubError, fetch_zip
from .safety import SKIP_DIRS, UnsafeArchive, safe_extract
from .tree import build_tree, count_files, language_summary

DEMO_NAME = "TaskFreak! 0.6.4"
DEMO_SOURCE_URL = "https://sourceforge.net/projects/taskfreak2016/"


class IntakeError(Exception):
    """Raised with a user-facing message when intake fails."""


def corpse_dir(corpse: Corpse) -> Path:
    return Path(settings.MEDIA_ROOT) / "corpses" / str(corpse.pk)


def demo_source_dir() -> Path:
    return Path(settings.BASE_DIR) / "samples" / "corpse"


def _start(name: str, **fields) -> tuple[Corpse, Job]:
    corpse = Corpse.objects.create(name=name, status=Status.RUNNING, **fields)
    job = Job.objects.create(kind="intake", corpse=corpse, status=Status.RUNNING)
    return corpse, job


def _log(job: Job, line: str) -> None:
    job.log = f"{job.log}{line}\n" if job.log else f"{line}\n"


def _finish(corpse: Corpse, job: Job, root: Path) -> Corpse:
    corpse.file_tree = build_tree(root)
    corpse.languages = language_summary(root)
    corpse.file_count = count_files(corpse.file_tree)
    corpse.storage_path = str(root)
    corpse.status = Status.DONE
    corpse.error = ""
    corpse.save()
    _log(job, f"Stored {corpse.file_count} files.")
    job.status = Status.DONE
    job.save()
    return corpse


def _fail(corpse: Corpse, job: Job, root: Path, message: str) -> None:
    shutil.rmtree(root, ignore_errors=True)
    corpse.status = Status.FAILED
    corpse.error = message
    corpse.save()
    _log(job, message)
    job.status = Status.FAILED
    job.save()
    raise IntakeError(message)


def _extract(corpse: Corpse, job: Job, zip_path: Path) -> Corpse:
    root = corpse_dir(corpse)
    try:
        safe_extract(zip_path, root)
    except UnsafeArchive as exc:
        _fail(corpse, job, root, str(exc))
    return _finish(corpse, job, root)


def create_from_zip(name: str, uploaded_file) -> Corpse:
    """Create a Corpse from an uploaded .zip (a Django UploadedFile)."""
    corpse, job = _start(name)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
    tmp_path = Path(tmp.name)
    try:
        return _extract(corpse, job, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def create_from_github(name: str, url: str) -> Corpse:
    """Create a Corpse by downloading a public GitHub repository."""
    corpse, job = _start(name, source_url=url)
    tmp_path = Path(tempfile.mkstemp(suffix=".zip")[1])
    try:
        try:
            fetch_zip(url, tmp_path)
        except GitHubError as exc:
            _fail(corpse, job, corpse_dir(corpse), str(exc))
        return _extract(corpse, job, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def summon_demo() -> Corpse:
    """Create (or return) the TaskFreak demo corpse from samples/corpse/ without modifying it."""
    existing = Corpse.objects.filter(is_demo=True).first()
    if existing and existing.status == Status.DONE:
        return existing
    source = demo_source_dir()
    if not source.is_dir():
        raise IntakeError("The demo corpse is missing from samples/corpse/.")
    if existing:
        corpse = existing
        corpse.status = Status.RUNNING
        corpse.save()
        job = Job.objects.create(kind="intake", corpse=corpse, status=Status.RUNNING)
    else:
        corpse, job = _start(DEMO_NAME, is_demo=True, source_url=DEMO_SOURCE_URL)
    root = corpse_dir(corpse)
    shutil.rmtree(root, ignore_errors=True)
    shutil.copytree(source, root, ignore=shutil.ignore_patterns(*SKIP_DIRS))
    return _finish(corpse, job, root)
