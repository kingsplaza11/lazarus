import pytest

from autopsy.models import Autopsy
from autopsy.services import AutopsyError, run_autopsy
from intake import services as intake_services
from intake.models import Corpse
from lazarus.choices import Status

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def demo():
    if not intake_services.demo_source_dir().is_dir():
        pytest.skip("samples/corpse/ not present")
    return intake_services.summon_demo()


def test_autopsy_on_taskfreak_finds_cause_of_death(demo):
    autopsy = run_autopsy(demo)
    report = autopsy.report
    assert autopsy.status == Status.DONE
    dead = {f["name"] for f in report["cause_of_death"]["functions"]}
    assert {"mysql_connect", "mysql_query"} <= dead
    pages = {p["path"] for p in report["pages"]}
    assert "login.php" in pages
    assert report["summary"]["php_files"] > 30
    assert report["i18n"] is not None and report["i18n"]["kept"] == "en"


def test_not_ready_corpse_raises():
    corpse = Corpse.objects.create(name="Empty", status=Status.PENDING)
    with pytest.raises(AutopsyError, match="isn't ready"):
        run_autopsy(corpse)


def test_run_view_redirects_to_report(client, demo):
    response = client.post(f"/corpses/{demo.pk}/autopsy/run/")
    assert response.status_code == 302
    assert response.url == f"/corpses/{demo.pk}/autopsy/"
    page = client.get(response.url).content.decode()
    assert "Cause of death" in page
    assert "mysql_query()" in page
    assert "index.php" in page


def test_report_without_autopsy_redirects_to_detail(client):
    corpse = Corpse.objects.create(name="Fresh", status=Status.DONE)
    response = client.get(f"/corpses/{corpse.pk}/autopsy/")
    assert response.status_code == 302
    assert response.url == f"/corpses/{corpse.pk}/"


def test_run_view_rejects_get(client):
    corpse = Corpse.objects.create(name="X", status=Status.DONE)
    assert client.get(f"/corpses/{corpse.pk}/autopsy/run/").status_code == 405


def test_detail_shows_view_report_after_autopsy(client, demo):
    run_autopsy(demo)
    page = client.get(f"/corpses/{demo.pk}/").content.decode()
    assert "View autopsy report" in page
    assert Autopsy.objects.filter(corpse=demo).count() == 1
