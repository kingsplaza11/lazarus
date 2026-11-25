"""Download a public GitHub repository as a zip (standard library only)."""
from __future__ import annotations

import logging
import os
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


log = logging.getLogger(__name__)


class GitHubError(Exception):
    """Raised with a user-facing message."""


def parse_github_url(url: str) -> tuple[str, str, str | None]:
    """Return (owner, repo, branch or None) or raise GitHubError."""
    match = GITHUB_RE.match((url or "").strip())
    if not match:
        raise GitHubError(MSG_BAD_URL)
    return match["owner"], match["repo"], match["branch"]


def archive_url(owner: str, repo: str, branch: str | None) -> str:
    """github.com archive link. Redirects to codeload, which has no API rate limit.

    HEAD resolves to the repository's default branch, whatever it is called.
    """
    ref = f"refs/heads/{quote(branch, safe='')}" if branch else "HEAD"
    return f"https://github.com/{owner}/{repo}/archive/{ref}.zip"


def zipball_url(owner: str, repo: str, branch: str | None) -> str:
    base = f"https://api.github.com/repos/{owner}/{repo}/zipball"
    return f"{base}/{quote(branch, safe='')}" if branch else base


def _requests(owner: str, repo: str, branch: str | None) -> list[urllib.request.Request]:
    """Archive link first; the REST API as a fallback (authenticated when GITHUB_TOKEN is set).

    Shared hosts such as Render share outbound IPs, so the API's 60-requests-an-hour
    anonymous limit is often already spent. The archive link avoids that limit.
    """
    agent = {"User-Agent": "Lazarus/1.0"}
    api_headers = {**agent, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        api_headers["Authorization"] = f"Bearer {token}"
    return [
        urllib.request.Request(archive_url(owner, repo, branch), headers=agent),
        urllib.request.Request(zipball_url(owner, repo, branch), headers=api_headers),
    ]


def _download(request, dest_file: Path, timeout: int, opener) -> None:
    deadline = time.monotonic() + timeout
    with opener(request, timeout=timeout) as response, open(dest_file, "wb") as out:
        total = 0
        while chunk := response.read(64 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise GitHubError(MSG_TOO_BIG)
            if time.monotonic() > deadline:
                raise TimeoutError("download took too long")
            out.write(chunk)


def fetch_zip(url: str, dest_file: Path, timeout: int = 30, opener=urllib.request.urlopen) -> None:
    """Stream the repo zip to dest_file. Aborts past 20 MB or `timeout` seconds per attempt."""
    owner, repo, branch = parse_github_url(url)
    last_error: Exception | None = None
    for request in _requests(owner, repo, branch):
        try:
            _download(request, dest_file, timeout, opener)
            return
        except GitHubError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            log.warning("GitHub fetch failed for %s: %r", request.full_url, exc)
            last_error = exc
    raise GitHubError(MSG_FETCH) from last_error
