import io
import zipfile
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from intake import services
from intake.github import MSG_FETCH, GitHubError
from intake.models import Corpse
from lazarus.choices import Status
from parity.models import Job

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    return Path(settings.MEDIA_ROOT)


def zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buffer.getvalue()


def upload(entries: dict[str, bytes], name: str = "app.zip") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, zip_bytes(entries), content_type="application/zip")


def test_create_from_zip_success(media):
    corpse = services.create_from_zip("My app", upload({"index.php": b"<?php", "db.sql": b"CREATE TABLE t (id int);"}))
    corpse.refresh_from_db()
    assert corpse.status == Status.DONE
    assert corpse.file_count == 2
    assert corpse.languages == {"PHP": 1, "SQL": 1}
    assert (media / "corpses" / str(corpse.pk) / "index.php").exists()
    assert Job.objects.get(corpse=corpse).status == Status.DONE


def test_create_from_zip_unsafe_marks_failed(media):
    with pytest.raises(services.IntakeError, match="unsafe paths"):
        services.create_from_zip("Evil", upload({"ok.php": b"x", "../evil.php": b"x"}))
    corpse = Corpse.objects.get(name="Evil")
    assert corpse.status == Status.FAILED
    assert "unsafe" in corpse.error
    assert not (media / "corpses" / str(corpse.pk)).exists()
    assert Job.objects.get(corpse=corpse).status == Status.FAILED


def test_create_from_github_success(monkeypatch):
    def fake_fetch(url, dest):
        Path(dest).write_bytes(zip_bytes({"owner-repo-abc/index.php": b"<?php"}))

    monkeypatch.setattr(services, "fetch_zip", fake_fetch)
    corpse = services.create_from_github("Repo", "https://github.com/owner/repo")
    assert corpse.status == Status.DONE
    assert corpse.source_url == "https://github.com/owner/repo"
    assert corpse.file_count == 1


def test_create_from_github_fetch_error(monkeypatch):
    def fake_fetch(url, dest):
        raise GitHubError(MSG_FETCH)

    monkeypatch.setattr(services, "fetch_zip", fake_fetch)
    with pytest.raises(services.IntakeError, match="Is it public"):
        services.create_from_github("Missing", "https://github.com/owner/missing")
    assert Corpse.objects.get(name="Missing").status == Status.FAILED


def test_summon_demo_once_and_source_untouched():
    source = services.demo_source_dir()
    if not source.is_dir():
        pytest.skip("samples/corpse/ not present")
    before = sorted(str(p.relative_to(source)) for p in source.rglob("*"))

    first = services.summon_demo()
    second = services.summon_demo()

    assert first.pk == second.pk
    assert Corpse.objects.filter(is_demo=True).count() == 1
    assert first.name == services.DEMO_NAME
    assert first.languages.get("PHP", 0) > 100
    assert sorted(str(p.relative_to(source)) for p in source.rglob("*")) == before
