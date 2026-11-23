"""Run the resurrection check for a corpse and store the result."""
from __future__ import annotations

import traceback
from pathlib import Path

from autopsy.models import Autopsy
from intake.models import Corpse
from lazarus.choices import Status

from .check import run_check
from .models import Job, ResurrectionCheck


class CheckError(Exception):
    """Raised with a user-facing message."""


def default_db(source: str | None) -> str | None:
    if not source:
        return None
    candidate = Path(source).expanduser() / "db.sqlite3"
    return str(candidate) if candidate.is_file() else None


def run_resurrection_check(corpse: Corpse, url: str, source: str | None = None, db: str | None = None,
                           username: str | None = None, password: str | None = None) -> ResurrectionCheck:
    autopsy = Autopsy.objects.filter(corpse=corpse, status=Status.DONE).first()
    if autopsy is None or not autopsy.report.get("pages"):
        raise CheckError("Run the autopsy before checking the resurrection.")
    job = Job.objects.create(kind="check", corpse=corpse, status=Status.RUNNING)
    try:
        results = run_check(autopsy.report, url, source=source, db=db or default_db(source),
                            username=username, password=password)
    except Exception as exc:
        job.status = Status.FAILED
        job.log = traceback.format_exc()
        job.save()
        raise CheckError(f"The resurrection check failed: {exc}") from exc
    check = ResurrectionCheck.objects.create(
        corpse=corpse, target_url=url, source_path=str(source or ""), score=results["score"], results=results,
    )
    job.status = Status.DONE
    job.log = f"Score {results['score']}%: {results['summary']}\n"
    job.save()
    return check


def latest_check(corpse: Corpse) -> ResurrectionCheck | None:
    return ResurrectionCheck.objects.filter(corpse=corpse).first()
