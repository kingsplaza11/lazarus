import pytest

from autopsy.models import Autopsy
from intake.models import Corpse
from lazarus.choices import Status
from parity.models import ResurrectionCheck

pytestmark = pytest.mark.django_db


def make_check(corpse, score):
    return ResurrectionCheck.objects.create(
        corpse=corpse, target_url="http://127.0.0.1:8001", source_path="", score=score,
        results={"score": score, "summary": "", "categories": {}},
    )


def test_home_shows_how_it_works(client):
    content = client.get("/").content.decode()
    for step in ("Upload", "Autopsy", "Spec", "Resurrect", "Check"):
        assert step in content
    assert 'class="steps"' in content


def test_tombstone_shows_latest_score(client):
    corpse = Corpse.objects.create(name="TaskFreak", status=Status.DONE)
    make_check(corpse, 80)
    make_check(corpse, 100)
    content = client.get("/").content.decode()
    assert "Resurrected · 100%" in content
    assert "Resurrected · 80%" not in content
    assert "score-good" in content


def test_tombstone_without_check_has_no_badge(client):
    Corpse.objects.create(name="Fresh", status=Status.DONE)
    assert "Resurrected ·" not in client.get("/").content.decode()


def test_detail_tracker_before_autopsy(client):
    corpse = Corpse.objects.create(name="Fresh", status=Status.DONE)
    content = client.get(f"/corpses/{corpse.pk}/").content.decode()
    assert 'class="tracker"' in content
    assert f'href="/corpses/{corpse.pk}/autopsy/"' not in content


def test_detail_tracker_links_finished_stages(client):
    corpse = Corpse.objects.create(name="TaskFreak", status=Status.DONE)
    Autopsy.objects.create(corpse=corpse, status=Status.DONE, report={"pages": [], "summary": {}})
    make_check(corpse, 100)
    content = client.get(f"/corpses/{corpse.pk}/").content.decode()
    assert f'href="/corpses/{corpse.pk}/autopsy/">Autopsy</a>' in content
    assert f'href="/corpses/{corpse.pk}/check/">Check · 100%</a>' in content
