"""Optional AI polish for prose (never for EARS criteria). Groq → Gemini → unchanged.

Off unless LAZARUS_AI_POLISH=true. Any failure, timeout, rate limit or suspicious answer
returns the original text, so AI can never break or falsify a spec.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
PROMPT = (
    "Rewrite this introduction for a software requirements document in clear, plain English. "
    "Keep every fact, name and number exactly. Do not add facts. Return only the rewritten paragraph.\n\n"
)
_cache: dict[str, tuple[str, str]] = {}


def enabled() -> bool:
    return os.environ.get("LAZARUS_AI_POLISH", "").lower() == "true"


def numbers(text: str) -> list[str]:
    return sorted(re.findall(r"\d+(?:\.\d+)?", text))


def acceptable(original: str, candidate: str | None) -> bool:
    """Reject empty, runaway or fact-changing answers (every number must survive)."""
    if not candidate or not candidate.strip():
        return False
    if len(candidate) > 3 * len(original) + 200:
        return False
    return numbers(candidate) == numbers(original)


def _post_json(url: str, payload: dict, headers: dict, timeout: int, opener) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers}
    )
    with opener(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def ask_groq(text: str, timeout: int, opener) -> str | None:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    data = _post_json(
        GROQ_URL,
        {"model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
         "messages": [{"role": "user", "content": PROMPT + text}], "temperature": 0.2},
        {"Authorization": f"Bearer {key}"},
        timeout, opener,
    )
    return data["choices"][0]["message"]["content"].strip()


def ask_gemini(text: str, timeout: int, opener) -> str | None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    data = _post_json(
        GEMINI_URL.format(model=model),
        {"contents": [{"parts": [{"text": PROMPT + text}]}]},
        {"x-goog-api-key": key},
        timeout, opener,
    )
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def polish(text: str, timeout: int = 20, opener=urllib.request.urlopen) -> tuple[str, str]:
    """Return (text, provider). Provider is "groq", "gemini" or "templates" (unchanged)."""
    if not enabled() or not text.strip():
        return text, "templates"
    key = hashlib.sha256(text.encode()).hexdigest()
    if key in _cache:
        return _cache[key]
    for provider, ask in (("groq", ask_groq), ("gemini", ask_gemini)):
        try:
            candidate = ask(text, timeout, opener)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError):
            continue
        if acceptable(text, candidate):
            _cache[key] = (candidate, provider)
            return candidate, provider
    return text, "templates"
