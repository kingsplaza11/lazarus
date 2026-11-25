import io
import urllib.error

import pytest

from intake import github
from intake.github import GitHubError, archive_url, fetch_zip, parse_github_url, zipball_url


@pytest.mark.parametrize("url,expected", [
    ("https://github.com/owner/repo", ("owner", "repo", None)),
    ("https://github.com/owner/repo/", ("owner", "repo", None)),
    ("https://github.com/owner/repo.git", ("owner", "repo", None)),
    ("https://github.com/my-org/my.repo/tree/dev", ("my-org", "my.repo", "dev")),
])
def test_parse_valid_urls(url, expected):
    assert parse_github_url(url) == expected


@pytest.mark.parametrize("url", [
    "", "http://github.com/owner/repo", "https://gitlab.com/owner/repo",
    "https://github.com/owner", "https://github.com.evil.com/owner/repo", "github.com/owner/repo",
])
def test_parse_rejects_bad_urls(url):
    with pytest.raises(GitHubError, match="github.com"):
        parse_github_url(url)


def test_zipball_url():
    assert zipball_url("o", "r", None) == "https://api.github.com/repos/o/r/zipball"
    assert zipball_url("o", "r", "dev") == "https://api.github.com/repos/o/r/zipball/dev"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def test_fetch_success(tmp_path):
    dest = tmp_path / "repo.zip"
    fetch_zip("https://github.com/o/r", dest, opener=lambda req, timeout: FakeResponse(b"zipdata"))
    assert dest.read_bytes() == b"zipdata"


def test_fetch_http_error(tmp_path):
    def opener(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    with pytest.raises(GitHubError, match="Is it public"):
        fetch_zip("https://github.com/o/missing", tmp_path / "x.zip", opener=opener)


def test_fetch_timeout(tmp_path):
    def opener(req, timeout):
        raise TimeoutError()

    with pytest.raises(GitHubError, match="Is it public"):
        fetch_zip("https://github.com/o/r", tmp_path / "x.zip", opener=opener)


def test_fetch_too_big(tmp_path, monkeypatch):
    monkeypatch.setattr(github, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(GitHubError, match="20 MB"):
        fetch_zip("https://github.com/o/r", tmp_path / "x.zip", opener=lambda req, timeout: FakeResponse(b"x" * 100))


def test_archive_url():
    assert archive_url("o", "r", None) == "https://github.com/o/r/archive/HEAD.zip"
    assert archive_url("o", "r", "dev") == "https://github.com/o/r/archive/refs/heads/dev.zip"


def test_fetch_tries_archive_first(tmp_path):
    seen = []

    def opener(req, timeout):
        seen.append(req.full_url)
        return FakeResponse(b"zipdata")

    fetch_zip("https://github.com/o/r.git", tmp_path / "x.zip", opener=opener)
    assert seen == ["https://github.com/o/r/archive/HEAD.zip"]


def test_fetch_falls_back_to_api_with_token(tmp_path, monkeypatch):
    import urllib.error
    monkeypatch.setenv("GITHUB_TOKEN", "abc")
    seen = []

    def opener(req, timeout):
        seen.append((req.full_url, req.get_header("Authorization")))
        if "archive" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)
        return FakeResponse(b"zipdata")

    fetch_zip("https://github.com/o/r", tmp_path / "x.zip", opener=opener)
    assert seen[1] == ("https://api.github.com/repos/o/r/zipball", "Bearer abc")
    assert (tmp_path / "x.zip").read_bytes() == b"zipdata"
