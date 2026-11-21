import io
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from intake import services
from intake.models import Corpse
from lazarus.choices import Status

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


def test_health_returns_ok_json(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_empty_state(client):
    response = client.get("/")
    content = response.content.decode()
    assert response.status_code == 200
    assert "Lazarus" in content
    assert "The graveyard is empty" in content
    assert 'href="/corpses/new/"' in content
    assert "Summon the demo corpse" in content


def test_home_lists_tombstones_newest_first(client):
    Corpse.objects.create(name="Older App", status=Status.DONE, file_count=3)
    Corpse.objects.create(name="Newer App", status=Status.DONE, file_count=5)
    content = client.get("/").content.decode()
    assert content.index("Newer App") < content.index("Older App")


def test_upload_page_renders(client):
    response = client.get("/corpses/new/")
    assert response.status_code == 200
    assert "Upload a corpse" in response.content.decode()


def test_upload_requires_one_input(client):
    response = client.post("/corpses/new/", {"name": "Nothing"})
    assert response.status_code == 200
    assert "Provide a zip file or a GitHub URL." in response.content.decode()


def test_upload_rejects_non_github_url(client):
    response = client.post("/corpses/new/", {"name": "X", "github_url": "https://gitlab.com/o/r"})
    assert "Only public github.com repository URLs are supported." in response.content.decode()


def test_upload_zip_redirects_to_detail(client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("index.php", b"<?php echo 'hi';")
    archive = SimpleUploadedFile("app.zip", buffer.getvalue(), content_type="application/zip")
    response = client.post("/corpses/new/", {"name": "Tiny", "archive": archive})
    corpse = Corpse.objects.get(name="Tiny")
    assert response.status_code == 302
    assert response.url == f"/corpses/{corpse.pk}/"
    detail = client.get(response.url).content.decode()
    assert "index.php" in detail
    assert "Begin autopsy" in detail


def test_detail_warns_when_no_php(client):
    corpse = Corpse.objects.create(name="Not PHP", status=Status.DONE, file_count=1, languages={"Other": 1})
    content = client.get(f"/corpses/{corpse.pk}/").content.decode()
    assert "No PHP files found" in content


def test_detail_404(client):
    assert client.get("/corpses/999999/").status_code == 404


def test_demo_redirects_to_detail(client):
    if not services.demo_source_dir().is_dir():
        pytest.skip("samples/corpse/ not present")
    response = client.post("/corpses/demo/")
    corpse = Corpse.objects.get(is_demo=True)
    assert response.status_code == 302
    assert response.url == f"/corpses/{corpse.pk}/"


def test_demo_rejects_get(client):
    assert client.get("/corpses/demo/").status_code == 405
