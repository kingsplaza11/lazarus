import pytest

from lazarus.choices import Status
from parity.jobs import run_job
from parity.models import Job


@pytest.mark.django_db
def test_run_job_marks_done_on_success():
    job = Job.objects.create(kind="ok")
    run_job(job.pk, lambda j: j.append_log("hello"))
    job.refresh_from_db()
    assert job.status == Status.DONE
    assert "hello" in job.log


@pytest.mark.django_db
def test_run_job_marks_failed_and_logs_traceback_without_reraising():
    job = Job.objects.create(kind="bad")

    def boom(j):
        raise ValueError("kaboom")

    run_job(job.pk, boom)  # must not raise
    job.refresh_from_db()
    assert job.status == Status.FAILED
    assert "Traceback" in job.log
    assert "ValueError: kaboom" in job.log
