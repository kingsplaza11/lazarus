"""File tree and language summary for a stored corpse."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterator

LANGUAGES = {
    ".php": "PHP", ".php3": "PHP", ".php4": "PHP", ".php5": "PHP", ".inc": "PHP",
    ".sql": "SQL",
    ".html": "HTML", ".htm": "HTML", ".tpl": "HTML",
    ".css": "CSS",
    ".js": "JavaScript",
}


def detect_language(path: str) -> str:
    """Return the language for a file path, based on its extension."""
    return LANGUAGES.get(Path(path).suffix.lower(), "Other")


def iter_files(root: Path) -> Iterator[Path]:
    """Yield every regular (non-symlink) file under root, sorted."""
    for path in sorted(Path(root).rglob("*")):
        if path.is_file() and not path.is_symlink():
            yield path


def build_tree(root: Path) -> dict:
    """Return a nested tree: folders first, then files, both alphabetical."""
    root = Path(root)

    def walk(folder: Path) -> dict:
        entries = [c for c in folder.iterdir() if not c.is_symlink()]
        dirs = sorted((c for c in entries if c.is_dir()), key=lambda c: c.name.lower())
        files = sorted((c for c in entries if c.is_file()), key=lambda c: c.name.lower())
        children = [walk(d) for d in dirs]
        children += [
            {
                "name": f.name,
                "type": "file",
                "path": f.relative_to(root).as_posix(),
                "size": f.stat().st_size,
                "language": detect_language(f.name),
            }
            for f in files
        ]
        return {
            "name": folder.name,
            "type": "dir",
            "path": "" if folder == root else folder.relative_to(root).as_posix(),
            "children": children,
        }

    return walk(root)


def count_files(tree: dict) -> int:
    """Count file nodes in a tree from build_tree."""
    if tree.get("type") == "file":
        return 1
    return sum(count_files(child) for child in tree.get("children", []))


def language_summary(root: Path) -> dict[str, int]:
    """Count files per language, most common first."""
    counts = Counter(detect_language(p.name) for p in iter_files(root))
    return dict(counts.most_common())
