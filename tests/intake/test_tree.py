import tempfile
from pathlib import Path

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from intake.tree import build_tree, count_files, detect_language, language_summary


def test_detect_language():
    assert detect_language("index.php") == "PHP"
    assert detect_language("CONFIG.INC") == "PHP"
    assert detect_language("install/mysql.init.sql") == "SQL"
    assert detect_language("skin/style.css") == "CSS"
    assert detect_language("README.txt") == "Other"


def test_tree_orders_folders_then_files(tmp_path):
    (tmp_path / "b.php").write_text("x")
    (tmp_path / "A.php").write_text("x")
    (tmp_path / "zdir").mkdir()
    (tmp_path / "adir").mkdir()
    (tmp_path / "adir" / "x.sql").write_text("x")
    tree = build_tree(tmp_path)
    names = [c["name"] for c in tree["children"]]
    assert names == ["adir", "zdir", "A.php", "b.php"]
    assert tree["children"][0]["children"][0]["path"] == "adir/x.sql"
    assert count_files(tree) == 3


def test_language_summary(tmp_path):
    for name in ["a.php", "b.php", "c.sql", "d.txt"]:
        (tmp_path / name).write_text("x")
    assert language_summary(tmp_path) == {"PHP": 2, "SQL": 1, "Other": 1}


segment = st.text(alphabet="abcxyz", min_size=1, max_size=4)
ext = st.sampled_from([".php", ".sql", ".css", ".js", ".txt", ".html"])
rel_path = st.builds(lambda parts, e: "/".join(parts) + e, st.lists(segment, min_size=1, max_size=3), ext)


@settings(max_examples=60)
@given(st.sets(rel_path, min_size=1, max_size=25))
def test_prop_tree_counts_match(paths):
    """Every file written appears exactly once in the tree and in the language summary."""
    # A path can't be both a file and a folder.
    file_set = set(paths)
    for p in paths:
        parts = p.split("/")
        for i in range(1, len(parts)):
            assume("/".join(parts[:i]) not in file_set)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for p in paths:
            target = root / p
            if target.parent.exists() and not target.parent.is_dir():
                assume(False)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x")
        tree = build_tree(root)
        assert count_files(tree) == len(paths)
        assert sum(language_summary(root).values()) == len(paths)
