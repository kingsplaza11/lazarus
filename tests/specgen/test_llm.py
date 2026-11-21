import io
import json
import urllib.error

import pytest

from specgen import llm

ORIGINAL = "TaskFreak is a legacy app with 16 pages, 9 tables and 67 dead calls."


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def groq_reply(text):
    return FakeResponse(json.dumps({"choices": [{"message": {"content": text}}]}).encode())


def gemini_reply(text):
    return FakeResponse(json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode())


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    llm._cache.clear()
    for var in ("LAZARUS_AI_POLISH", "GROQ_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def test_disabled_returns_original():
    assert llm.polish(ORIGINAL) == (ORIGINAL, "templates")


def test_groq_success(monkeypatch):
    monkeypatch.setenv("LAZARUS_AI_POLISH", "true")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    better = "TaskFreak is an old app: 16 pages, 9 tables, 67 dead calls."
    assert llm.polish(ORIGINAL, opener=lambda req, timeout: groq_reply(better)) == (better, "groq")


def test_answer_that_changes_numbers_is_rejected(monkeypatch):
    monkeypatch.setenv("LAZARUS_AI_POLISH", "true")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    wrong = "TaskFreak is an old app with 20 pages and 9 tables and 67 dead calls."
    assert llm.polish(ORIGINAL, opener=lambda req, timeout: groq_reply(wrong)) == (ORIGINAL, "templates")


def test_falls_back_to_gemini_when_groq_fails(monkeypatch):
    monkeypatch.setenv("LAZARUS_AI_POLISH", "true")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    better = "An old app: 16 pages, 9 tables, 67 dead calls."

    def opener(req, timeout):
        if "groq" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)
        return gemini_reply(better)

    assert llm.polish(ORIGINAL, opener=opener) == (better, "gemini")


def test_everything_failing_returns_original(monkeypatch):
    monkeypatch.setenv("LAZARUS_AI_POLISH", "true")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("GEMINI_API_KEY", "g")

    def opener(req, timeout):
        raise TimeoutError()

    assert llm.polish(ORIGINAL, opener=opener) == (ORIGINAL, "templates")


def test_acceptable():
    assert llm.acceptable("3 pages", "three... 3 pages")
    assert not llm.acceptable("3 pages", "4 pages")
    assert not llm.acceptable("3 pages", "")
