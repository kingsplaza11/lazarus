import io
import zipfile

import pytest

from autopsy.services import run_autopsy
from intake import services as intake_services
from intake.models import Corpse
from lazarus.choices import Status
from specgen.models import Spec
from specgen.services import SpecError, generate_for_corpse

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def autopsied_demo():
    if not intake_services.demo_source_dir().is_dir():
        pytest.skip("samples/corpse/ not present")
    corpse = intake_services.summon_demo()
    run_autopsy(corpse)
    return corpse


def test_generate_requires_autopsy():
    corpse = Corpse.objects.create(name="Fresh", status=Status.DONE)
    with pytest.raises(SpecError, match="Run the autopsy"):
        generate_for_corpse(corpse)


def test_generate_for_taskfreak(autopsied_demo):
    spec = generate_for_corpse(autopsied_demo)
    assert "Requirement 1:" in spec.requirements_md
    assert "Login page" in spec.requirements_md
    assert "class Member(models.Model):" in spec.design_md
    assert "- [ ] 1." in spec.tasks_md


def test_views_generate_show_and_download(client, autopsied_demo):
    pk = autopsied_demo.pk
    response = client.post(f"/corpses/{pk}/spec/generate/")
    assert response.status_code == 302 and response.url == f"/corpses/{pk}/spec/"

    page = client.get(response.url).content.decode()
    assert "acceptance criteria are valid EARS" in page
    assert "Download .kiro/ folder" in page

    archive = client.get(f"/corpses/{pk}/spec/download/")
    assert archive["Content-Type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(archive.content)).namelist()
    assert ".kiro/steering/product.md" in names
    assert any(n.endswith("/requirements.md") and n.startswith(".kiro/specs/") for n in names)
    assert any(n.startswith("legacy-assets/") and n.endswith(".css") for n in names)
    assert all(n.startswith((".kiro/", "legacy-assets/")) for n in names)
    assert not any(n.endswith(".php") for n in names)

    single = client.get(f"/corpses/{pk}/spec/file/", {"path": "steering/tech.md"})
    assert single.status_code == 200 and b"Django" in single.content
    assert client.get(f"/corpses/{pk}/spec/file/", {"path": "../../etc/passwd"}).status_code == 404


def test_spec_page_without_spec_redirects(client):
    corpse = Corpse.objects.create(name="Fresh", status=Status.DONE)
    assert client.get(f"/corpses/{corpse.pk}/spec/").url == f"/corpses/{corpse.pk}/"


def test_autopsy_report_shows_write_the_spec(client, autopsied_demo):
    page = client.get(f"/corpses/{autopsied_demo.pk}/autopsy/").content.decode()
    assert "Write the spec" in page
    generate_for_corpse(autopsied_demo)
    page = client.get(f"/corpses/{autopsied_demo.pk}/autopsy/").content.decode()
    assert "View the spec" in page
    assert Spec.objects.filter(autopsy__corpse=autopsied_demo).count() == 1
