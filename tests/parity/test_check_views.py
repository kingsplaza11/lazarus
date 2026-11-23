import pytest
from django.core.management import CommandError, call_command

from autopsy.models import Autopsy
from intake.models import Corpse
from lazarus.choices import Status
from parity import services
from parity.models import ResurrectionCheck

pytestmark = pytest.mark.django_db

FAKE_RESULT = {
    "version": 1, "target": "http://127.0.0.1:8001", "signed_in": True, "score": 91,
    "summary": "15/16 pages · 8/9 forms · 9/9 tables · 4/4 safety checks",
    "notes": ["Signed in as admin via /login/."],
    "categories": {
        "pages": {"score": 0.94, "passed": 15, "total": 16, "items": [
            {"label": "index.php", "score": 1, "detail": "/: 200"},
            {"label": "rss.php", "score": 0, "detail": "/rss/: server error 500"}]},
        "forms": {"score": 0.9, "passed": 8, "total": 9, "items": [{"label": "login.php:30", "score": 1, "detail": "2/2 fields"}]},
        "tables": {"score": 1, "passed": 9, "total": 9, "items": [{"label": "frk_item", "score": 1, "detail": "14/14 columns"}]},
        "safety": {"score": 1, "passed": 4, "total": 4, "items": [{"label": "Passwords hashed", "score": 1, "detail": "uses make_password"}]},
        "look": {"score": 1, "passed": 2, "total": 2, "items": [{"label": "Original stylesheet ported", "score": 1, "detail": "found"}]},
    },
}


@pytest.fixture
def corpse():
    corpse = Corpse.objects.create(name="TaskFreak! 0.6.4", status=Status.DONE)
    Autopsy.objects.create(corpse=corpse, status=Status.DONE, report={"pages": [{"path": "index.php"}], "summary": {}})
    return corpse


@pytest.fixture
def fake_check(monkeypatch):
    calls = []

    def fake(report, url, source=None, db=None, username=None, password=None):
        calls.append({"url": url, "source": source, "db": db, "username": username})
        return FAKE_RESULT

    monkeypatch.setattr(services, "run_check", fake)
    return calls


def test_check_requires_autopsy():
    corpse = Corpse.objects.create(name="Fresh", status=Status.DONE)
    with pytest.raises(services.CheckError, match="Run the autopsy"):
        services.run_resurrection_check(corpse, "http://127.0.0.1:8001")


def test_service_saves_result(corpse, fake_check, tmp_path):
    (tmp_path / "db.sqlite3").write_bytes(b"")
    check = services.run_resurrection_check(corpse, "http://127.0.0.1:8001", source=str(tmp_path), username="admin")
    assert check.score == 91 and check.results["summary"].startswith("15/16 pages")
    assert fake_check[0]["db"] == str(tmp_path / "db.sqlite3")  # defaults to <source>/db.sqlite3
    assert services.latest_check(corpse) == check


def test_command_prints_score(corpse, fake_check, capsys):
    call_command("resurrection_check", str(corpse.pk), "--url", "http://127.0.0.1:8001", "--username", "admin", "--password", "x")
    out = capsys.readouterr().out
    assert "Resurrection score: 91%" in out
    assert "✗ rss.php: /rss/: server error 500" in out
    assert "✓ index.php" not in out  # passes are hidden unless --details
    assert ResurrectionCheck.objects.count() == 1


def test_command_unknown_corpse():
    with pytest.raises(CommandError, match="No corpse"):
        call_command("resurrection_check", "999999")


def test_check_page_and_links(client, corpse, fake_check):
    assert client.get(f"/corpses/{corpse.pk}/check/").status_code == 302  # nothing yet
    services.run_resurrection_check(corpse, "http://127.0.0.1:8001")
    page = client.get(f"/corpses/{corpse.pk}/check/").content.decode()
    assert "91%" in page and "15/16 pages" in page and "server error 500" in page
    detail = client.get(f"/corpses/{corpse.pk}/").content.decode()
    assert "Resurrection check:" in detail and "91%" in detail
