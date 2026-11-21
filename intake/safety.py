"""Safe extraction of uploaded archives.

Nothing extracted here is ever executed. Every archive is validated in full
before a single byte is written, and any failure removes what was written.
"""
from __future__ import annotations

import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_FILES = 500
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
SKIP_DIRS = {".git", "node_modules", "vendor", "__MACOSX"}

MSG_INVALID = "That file isn't a valid zip archive."
MSG_UNSAFE = "This archive contains unsafe paths."
MSG_TOO_MANY = "Corpses can contain at most 500 files."
MSG_TOO_BIG = "This archive expands to more than 100 MB."
MSG_UNSUPPORTED = "This archive can't be opened (it may be encrypted)."


class UnsafeArchive(Exception):
    """Raised with a user-facing message when an archive is rejected."""


def is_safe_member(name: str, root: Path) -> bool:
    """Return True if archive entry `name` would land inside `root`."""
    if not name or "\x00" in name:
        return False
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or (len(normalized) > 1 and normalized[1] == ":"):
        return False
    if any(part == ".." for part in PurePosixPath(normalized).parts):
        return False
    root_resolved = Path(root).resolve()
    target = (root_resolved / normalized).resolve()
    return target == root_resolved or root_resolved in target.parents


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK(info.external_attr >> 16)


def _plan(zf: zipfile.ZipFile, dest: Path) -> list[tuple[zipfile.ZipInfo, tuple[str, ...]]]:
    """Validate every entry and return (info, relative parts) for files to write."""
    files: list[tuple[zipfile.ZipInfo, tuple[str, ...]]] = []
    total = 0
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if not is_safe_member(name, dest):
            raise UnsafeArchive(MSG_UNSAFE)
        if info.is_dir() or _is_symlink(info):
            continue
        parts = tuple(p for p in PurePosixPath(name).parts if p not in ("", "."))
        if not parts or any(p in SKIP_DIRS for p in parts):
            continue
        files.append((info, parts))
        total += info.file_size
    if len(files) > MAX_FILES:
        raise UnsafeArchive(MSG_TOO_MANY)
    if total > MAX_UNCOMPRESSED_BYTES:
        raise UnsafeArchive(MSG_TOO_BIG)
    # Flatten a single top-level folder (e.g. GitHub's "owner-repo-sha/").
    if files:
        firsts = {parts[0] for _, parts in files}
        if len(firsts) == 1 and all(len(parts) > 1 for _, parts in files):
            files = [(info, parts[1:]) for info, parts in files]
    return files


def safe_extract(zip_path: Path, dest: Path) -> int:
    """Extract `zip_path` into `dest` safely. Returns the number of files written.

    Raises UnsafeArchive with a user-facing message. On any failure `dest` is removed.
    """
    dest = Path(dest)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            plan = _plan(zf, dest)
            dest.mkdir(parents=True, exist_ok=True)
            written = 0
            for info, parts in plan:
                if not is_safe_member("/".join(parts), dest):
                    raise UnsafeArchive(MSG_UNSAFE)
                target = dest.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as out:
                    while chunk := src.read(64 * 1024):
                        written += len(chunk)
                        if written > MAX_UNCOMPRESSED_BYTES:  # guards lying headers
                            raise UnsafeArchive(MSG_TOO_BIG)
                        out.write(chunk)
            return len(plan)
    except zipfile.BadZipFile:
        shutil.rmtree(dest, ignore_errors=True)
        raise UnsafeArchive(MSG_INVALID)
    except (NotImplementedError, RuntimeError):
        shutil.rmtree(dest, ignore_errors=True)
        raise UnsafeArchive(MSG_UNSUPPORTED)
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise
