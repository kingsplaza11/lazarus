import re

from django.test import Client


def test_home_returns_200_with_title_and_disabled_button():
    response = Client().get("/")
    assert response.status_code == 200
    html = response.content.decode()
    assert "Lazarus" in html
    assert re.search(r"<button[^>]*\bdisabled\b[^>]*>\s*Upload a corpse\s*</button>", html)


def test_health_returns_ok_json():
    response = Client().get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
