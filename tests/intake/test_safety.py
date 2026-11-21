import io
import stat
import tempfile
import zipfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from intake import safety
from intake.safety import UnsafeArchive, is_safe_member, safe_extract


def make_zip(path: Path, entries: dict[str, bytes], symlinks: dict[str, str] | None = None) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
        for name, target in (symlinks or {}).items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(info, target)
    return path


def test_extracts_normal_archive(tmp_path):
    archive = make_zip(tmp_path / "a.zip", {"index.php": b"<?php echo 1;", "inc/db.php": b"<?php"})
    dest = tmp_path / "out"
    assert safe_extract(archive, dest) == 2
    assert (dest / "index.php").read_bytes() == b"<?php echo 1;"
    assert (dest / "inc" / "db.php").exists()


def test_flattens_single_top_level_folder(tmp_path):
    archive = make_zip(tmp_path / "a.zip", {"owner-repo-abc123/index.php": b"x", "owner-repo-abc123/a/b.php": b"y"})
    dest = tmp_path / "out"
    safe_extract(archive, dest)
    assert (dest / "index.php").exists()
    assert (dest / "a" / "b.php").exists()


def test_does_not_flatten_when_root_has_files(tmp_path):
    archive = make_zip(tmp_path / "a.zip", {"index.php": b"x", "lib/a.php": b"y"})
    dest = tmp_path / "out"
    safe_extract(archive, dest)
    assert (dest / "lib" / "a.php").exists()


@pytest.mark.parametrize("bad_name", ["../evil.php", "a/../../evil.php", "/etc/passwd", "C:/evil.php", "..\\evil.php"])
def test_rejects_unsafe_paths_and_cleans_up(tmp_path, bad_name):
    archive = make_zip(tmp_path / "a.zip", {"ok.php": b"x", bad_name: b"boom"})
    dest = tmp_path / "out"
    with pytest.raises(UnsafeArchive, match="unsafe paths"):
        safe_extract(archive, dest)
    assert not dest.exists()
    assert not (tmp_path / "evil.php").exists()


def test_skips_symlinks(tmp_path):
    archive = make_zip(tmp_path / "a.zip", {"index.php": b"x"}, symlinks={"link.php": "/etc/passwd"})
    dest = tmp_path / "out"
    assert safe_extract(archive, dest) == 1
    assert not (dest / "link.php").exists()


def test_skips_ignored_dirs(tmp_path):
    archive = make_zip(tmp_path / "a.zip", {
        "index.php": b"x", ".git/config": b"x", "node_modules/a.js": b"x",
        "vendor/lib.php": b"x", "__MACOSX/._index.php": b"x",
    })
    dest = tmp_path / "out"
    assert safe_extract(archive, dest) == 1


def test_rejects_too_many_files(tmp_path):
    entries = {f"f{i}.php": b"x" for i in range(safety.MAX_FILES + 1)}
    archive = make_zip(tmp_path / "a.zip", entries)
    with pytest.raises(UnsafeArchive, match="at most 500 files"):
        safe_extract(archive, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_rejects_large_expanded_size(tmp_path, monkeypatch):
    monkeypatch.setattr(safety, "MAX_UNCOMPRESSED_BYTES", 1000)
    archive = make_zip(tmp_path / "a.zip", {"big.sql": b"0" * 2000})
    with pytest.raises(UnsafeArchive, match="more than 100 MB"):
        safe_extract(archive, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_rejects_invalid_zip(tmp_path):
    fake = tmp_path / "fake.zip"
    fake.write_bytes(b"this is not a zip")
    with pytest.raises(UnsafeArchive, match="valid zip"):
        safe_extract(fake, tmp_path / "out")


def test_is_safe_member_basic(tmp_path):
    assert is_safe_member("a/b.php", tmp_path)
    assert not is_safe_member("../a.php", tmp_path)
    assert not is_safe_member("", tmp_path)
    assert not is_safe_member("a\x00b", tmp_path)


_ROOT = Path(tempfile.mkdtemp(prefix="lazarus-prop-")).resolve()


@settings(max_examples=300)
@given(st.text(alphabet=st.sampled_from(list("ab./\\:~ ")), max_size=24))
def test_prop_safe_member_never_escapes(name):
    """If is_safe_member says yes, the resolved path is always inside the root."""
    if is_safe_member(name, _ROOT):
        target = (_ROOT / name.replace("\\", "/")).resolve()
        assert target == _ROOT or _ROOT in target.parents
