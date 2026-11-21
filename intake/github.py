"""Download a public GitHub repository as a zip (standard library only)."""
from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

from .safety import MAX_UPLOAD_BYTES

GITHUB_RE = re.compile(
    r"^https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?"
    r"(?:/tree/(?P<branch>[^/?#]+))?/?$"
)

MSG_BAD_URL = "Only public github.com repository URLs are supported."
MSG_FETCH = "Couldn't fetch that repository. Is it public?"
MSG_TOO_BIG = "Corpses must be 20 MB or smaller."


class GitHubError(Exception):
    """Raised with a user-facing message."""


def parse_github_url(url: str) -> tuple[str, str, str | None]:
    """Return (owner, repo, branch or None) or raise GitHubError."""
    match = GITHUB_RE.match((url or "").strip())
    if not match:
        raise GitHubError(MSG_BAD_URL)
    return match["owner"], match["repo"], match["branch"]


def zipball_url(owner: str, repo: str, branch: str | None) -> str:
    base = f"https://api.github.com/repos/{owner}/{repo}/zipball"
    return f"{base}/{quote(branch, safe='')}" if branch else base


def fetch_zip(url: str, dest_file: Path, timeout: int = 30, opener=urllib.request.urlopen) -> None:
    """Stream the repo zip to dest_file. Aborts past 20 MB or `timeout` seconds total."""
    owner, repo, branch = parse_github_url(url)
    request = urllib.request.Request(
        zipball_url(owner, repo, branch),
        headers={"User-Agent": "Lazarus/1.0", "Accept": "application/vnd.github+json"},
    )
    deadline = time.monotonic() + timeout
    try:
        with opener(request, timeout=timeout) as response, open(dest_file, "wb") as out:
            total = 0
            while chunk := response.read(64 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise GitHubError(MSG_TOO_BIG)
                if time.monotonic() > deadline:
                    raise GitHubError(MSG_FETCH)
                out.write(chunk)
    except GitHubError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise GitHubError(MSG_FETCH) from exc
