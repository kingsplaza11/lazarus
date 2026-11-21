import traceback
from typing import Callable

from lazarus.choices import Status

from .models import Job


def run_job(job_id: int, func: Callable[[Job], None]) -> None:
    """Run func(job), tracking status. Exceptions are logged on the job, never re-raised."""
    job = Job.objects.get(pk=job_id)
    job.status = Status.RUNNING
    job.save(update_fields=["status", "updated_at"])
    try:
        func(job)
    except Exception:
        job.status = Status.FAILED
        job.save(update_fields=["status", "updated_at"])
        job.append_log(traceback.format_exc())
    else:
        job.status = Status.DONE
        job.save(update_fields=["status", "updated_at"])
