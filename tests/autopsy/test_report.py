from pathlib import Path

import pytest

from autopsy.report import build_report, find_i18n, find_libraries, resolve_include


def write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.fixture
def corpse(tmp_path):
    write(tmp_path, "_common.php", "<?php define('PRJ', './'); session_start(); $db = mysql_connect('h','u','p');")
    write(tmp_path, "index.php", "<?php include '_common.php'; include PRJ.'include/html/header.php';\n"
                                 "$r = mysql_query('SELECT * FROM '.PREFIX.'task WHERE projectId='.$_GET['project']);")
    write(tmp_path, "login.php", "<?php include '_common.php';\nif ($_POST['username']) { header('Location: index.php'); }\n"
                                 "?><form method=\"post\" action=\"login.php\"><input name=\"username\"><input type=\"password\" name=\"password\"></form>")
    write(tmp_path, "include/html/header.php", "<html><head><title>TaskFreak</title></head>")
    write(tmp_path, "include/language/en/common.php", "<?php $lang['hello'] = 'Hello';")
    write(tmp_path, "include/language/fr/common.php", "<?php $lang['hello'] = 'Bonjour';")
    write(tmp_path, "install/mysql.init.sql",
          "CREATE TABLE frk_task (taskId int(10) NOT NULL, title varchar(255), projectId int, PRIMARY KEY (taskId)) TYPE=MyISAM;\n"
          "CREATE TABLE frk_member (memberId int NOT NULL, username varchar(30), PRIMARY KEY (memberId)) TYPE=MyISAM;")
    return tmp_path


def test_pages_exclude_included_files(corpse):
    report = build_report(corpse)
    pages = [p["path"] for p in report["pages"]]
    assert pages == ["index.php", "login.php"]
    assert "_common.php" not in pages
    assert "include/html/header.php" not in pages


def test_page_details(corpse):
    report = build_report(corpse)
    pages = {p["path"]: p for p in report["pages"]}
    index = pages["index.php"]
    assert index["reads"]["GET"] == ["project"]
    assert index["tables"] == ["frk_task"]
    assert index["uses_session"] is True          # via _common.php
    assert "include/html/header.php" in index["includes"]
    login = pages["login.php"]
    assert login["reads"]["POST"] == ["username"]
    assert login["redirects"][0]["target"] == "index.php"
    assert [f["name"] for f in login["forms"][0]["fields"]] == ["username", "password"]


def test_schema_and_usage(corpse):
    report = build_report(corpse)
    tables = {t["name"]: t for t in report["tables"]}
    assert set(tables) == {"frk_task", "frk_member"}
    assert tables["frk_task"]["verbs"] == ["SELECT"]
    assert tables["frk_task"]["used_in"] == ["index.php"]
    assert tables["frk_member"]["verbs"] == []


def test_cause_of_death(corpse):
    cause = build_report(corpse)["cause_of_death"]
    names = {f["name"]: f["count"] for f in cause["functions"]}
    assert names == {"mysql_connect": 1, "mysql_query": 1}
    assert "removed in PHP 7.0" in cause["summary"]
    assert cause["files"] == ["_common.php", "index.php"]


def test_translations_are_skipped_except_one(corpse):
    report = build_report(corpse)
    assert report["i18n"]["languages"] == ["en", "fr"]
    assert report["i18n"]["kept"] == "en"
    assert report["summary"]["skipped_translation_files"] == 1
    paths = [f["path"] for f in report["files"]]
    assert "include/language/en/common.php" in paths
    assert "include/language/fr/common.php" not in paths


def test_report_is_deterministic(corpse):
    assert build_report(corpse) == build_report(corpse)


def test_library_files_outside_root_are_not_pages(tmp_path):
    write(tmp_path, "index.php", "<?php echo 1;")
    write(tmp_path, "include/classes/doc.php", "<?php class Doc { function up() { return $_FILES['f']; } }")
    write(tmp_path, "admin/settings.php", "<?php if ($_POST['save']) { header('Location: ../index.php'); }")
    pages = [p["path"] for p in build_report(tmp_path)["pages"]]
    assert pages == ["admin/settings.php", "index.php"]


def test_bundled_libraries_are_detected_and_not_pages(tmp_path):
    write(tmp_path, "index.php", "<?php echo 1;")
    write(tmp_path, "jscalendar/calendar-setup.php", "<?php echo $_GET['lang'];")
    write(tmp_path, "widgets/editor/LICENSE.txt", "MIT")
    write(tmp_path, "widgets/editor/run.php", "<?php echo $_POST['text'];")
    write(tmp_path, "widgets/editor/sub/x.php", "<?php echo $_GET['y'];")
    report = build_report(tmp_path)
    assert [p["path"] for p in report["pages"]] == ["index.php"]
    assert [lib["path"] for lib in report["libraries"]] == ["jscalendar", "widgets/editor"]
    assert report["summary"]["libraries"] == 2


def test_readme_or_changelog_alone_is_not_a_library(tmp_path):
    write(tmp_path, "index.php", "<?php echo 1;")
    write(tmp_path, "install/CHANGES.txt", "v0.6.4")
    write(tmp_path, "install/index.php", "<?php if ($_POST['go']) { header('Location: ../index.php'); }")
    write(tmp_path, "docs/README", "notes")
    report = build_report(tmp_path)
    assert report["libraries"] == []
    assert "install/index.php" in [p["path"] for p in report["pages"]]


def test_translation_folders_are_never_libraries(tmp_path):
    write(tmp_path, "index.php", "<?php echo 1;")
    write(tmp_path, "include/language/en/common.php", "<?php $l = 1;")
    write(tmp_path, "include/language/sv/common.php", "<?php $l = 1;")
    write(tmp_path, "include/language/sv/LICENSE", "GPL")
    assert build_report(tmp_path)["libraries"] == []


def test_find_libraries_reports_top_most_only(tmp_path):
    write(tmp_path, "xajax/README", "xajax")
    write(tmp_path, "xajax/plugins/README", "plugin")
    write(tmp_path, "app/views/page.php", "<?php")
    assert [lib["path"] for lib in find_libraries(tmp_path)] == ["xajax"]


def test_assets_capture_stylesheets_and_skins(tmp_path):
    write(tmp_path, "index.php", "<?php echo 1;")
    write(tmp_path, "skins/redfreak/style.css", "body { color: red; }" * 10)
    write(tmp_path, "skins/bluefreak/style.css", "body { color: blue; }")
    write(tmp_path, "jscalendar/calendar.css", ".cal {}")
    assets = build_report(tmp_path)["assets"]
    assert [s["path"] for s in assets["stylesheets"]] == ["skins/redfreak/style.css", "skins/bluefreak/style.css"]
    assert assets["skins"] == [{"path": "skins", "names": ["bluefreak", "redfreak"]}]


def test_cause_of_death_wording(tmp_path):
    write(tmp_path, "a.php", "<?php mysql_query('x'); $f = create_function('', '');")
    summary = build_report(tmp_path)["cause_of_death"]["summary"]
    assert summary == "2 calls to 2 functions removed in PHP 7.0 and 8.0, in 1 file."


def test_resolve_include():
    known = {"index.php", "include/html/header.php", "include/classes/tzn_mysql.php"}
    assert resolve_include("?html/header.php", "index.php", known) == "include/html/header.php"
    assert resolve_include("./index.php", "index.php", known) == "index.php"
    assert resolve_include("../../index.php", "include/html/header.php", known) == "index.php"
    assert resolve_include("?", "index.php", known) is None
    assert resolve_include("tzn_mysql.php", "include/classes/x.php", known) == "include/classes/tzn_mysql.php"


def test_find_i18n_none(tmp_path):
    (tmp_path / "lang" / "en").mkdir(parents=True)
    assert find_i18n(tmp_path) is None
