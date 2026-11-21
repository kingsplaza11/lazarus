"""Run an autopsy on a stored corpse and save the report."""
from __future__ import annotations

import traceback
from pathlib import Path

from autopsy.models import Autopsy
from intake.models import Corpse
from lazarus.choices import Status
from parity.models import Job

from .report import build_report


class AutopsyError(Exception):
    """Raised with a user-facing message."""


def run_autopsy(corpse: Corpse) -> Autopsy:
    """Analyse the corpse's files and store the report on its Autopsy (created if needed)."""
    if corpse.status != Status.DONE or not corpse.storage_path or not Path(corpse.storage_path).is_dir():
        raise AutopsyError("This corpse isn't ready for an autopsy.")

    autopsy, _ = Autopsy.objects.get_or_create(corpse=corpse)
    autopsy.status = Status.RUNNING
    autopsy.save()
    job = Job.objects.create(kind="autopsy", corpse=corpse, status=Status.RUNNING)

    try:
        report = build_report(Path(corpse.storage_path))
    except Exception as exc:  # the report must never take the site down
        autopsy.status = Status.FAILED
        autopsy.report = {"error": str(exc)}
        autopsy.save()
        job.status = Status.FAILED
        job.log = traceback.format_exc()
        job.save()
        raise AutopsyError(f"The autopsy failed: {exc}") from exc

    autopsy.report = report
    autopsy.status = Status.DONE
    autopsy.save()
    summary = report["summary"]
    job.status = Status.DONE
    job.log = (
        f"Analysed {summary['php_files']} PHP files: {summary['pages']} pages, "
        f"{summary['tables']} tables, {summary['sql_statements']} SQL statements.\n"
    )
    job.save()
    return autopsy
