import pytest

from autopsy.models import Autopsy
from intake.models import Corpse
from parity.models import Job
from specgen.models import Spec


@pytest.fixture
def corpse():
    return Corpse.objects.create(name="oldapp")


@pytest.mark.django_db
def test_corpse_str(corpse):
    assert str(corpse) == "oldapp"


@pytest.mark.django_db
def test_autopsy_str_and_relation(corpse):
    autopsy = Autopsy.objects.create(corpse=corpse)
    assert str(autopsy) == "Autopsy of oldapp"
    assert corpse.autopsy == autopsy


@pytest.mark.django_db
def test_spec_str_and_related_name(corpse):
    autopsy = Autopsy.objects.create(corpse=corpse)
    spec = Spec.objects.create(autopsy=autopsy)
    assert str(spec) == "Spec for Autopsy of oldapp"
    assert list(autopsy.specs.all()) == [spec]


@pytest.mark.django_db
def test_job_str_and_related_name(corpse):
    job = Job.objects.create(kind="analyze", corpse=corpse)
    assert str(job) == f"Job {job.pk} (analyze, pending)"
    assert list(corpse.jobs.all()) == [job]
