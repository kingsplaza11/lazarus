from hypothesis import given, settings
from hypothesis import strategies as st

from autopsy.parsers.php import death_reason, parse_php


def php(code: str) -> dict:
    return parse_php(code.encode())


def test_includes_with_constant_prefix():
    result = php("<?php include_once PRJ_INCLUDE_PATH.'html/header.php'; require 'config.php';")
    targets = [(i["kind"], i["target"]) for i in result["includes"]]
    assert ("include_once", "?html/header.php") in targets
    assert ("require", "config.php") in targets


def test_superglobal_keys():
    result = php("<?php $id = $_GET['id']; $t = $_POST[\"title\"]; $u = $_SESSION['user']; foreach ($_REQUEST as $k) {}")
    assert result["superglobals"]["GET"] == ["id"]
    assert result["superglobals"]["POST"] == ["title"]
    assert result["superglobals"]["SESSION"] == ["user"]
    assert result["superglobals"]["REQUEST"] == ["*"]
    assert result["uses_session"] is True


def test_dead_calls_are_found_with_reason():
    result = php("<?php $l = mysql_connect($h, $u, $p); mysql_select_db('x'); $r = mysql_query($q); if (ereg('a', $b)) {}")
    names = [c["name"] for c in result["dead_calls"]]
    assert names == ["mysql_connect", "mysql_select_db", "mysql_query", "ereg"]
    assert result["dead_calls"][0]["why"] == "removed in PHP 7.0"
    assert result["dead_calls"][0]["line"] == 1


def test_sql_in_concatenation():
    result = php("<?php $sql = 'SELECT * FROM '.TZN_DB_PREFIX.'task WHERE taskId='.$id;")
    assert len(result["sql"]) == 1
    statement = result["sql"][0]
    assert statement["verb"] == "SELECT"
    assert statement["tables"] == ["task"]


def test_sql_in_plain_string_argument():
    result = php("<?php mysql_query(\"UPDATE frk_task SET status=1\");")
    assert result["sql"][0]["verb"] == "UPDATE"
    assert result["sql"][0]["tables"] == ["frk_task"]


def test_redirect_and_session_start():
    result = php("<?php session_start(); header('Location: index.php'); exit;")
    assert result["uses_session"] is True
    assert result["redirects"] == [{"target": "index.php", "line": 1}]


def test_classes_methods_and_functions():
    code = "<?php\nclass Task extends TznDb {\n function load() {}\n function save() {}\n}\nfunction helper() {}\n"
    result = php(code)
    assert result["classes"][0]["name"] == "Task"
    assert result["classes"][0]["extends"] == "TznDb"
    assert result["classes"][0]["methods"] == ["load", "save"]
    assert result["functions"][0]["name"] == "helper"


def test_mixed_html_and_php():
    result = php("<html><body><?php echo $_GET['q']; ?></body></html>")
    assert result["superglobals"]["GET"] == ["q"]


def test_death_reason():
    assert death_reason("mysql_query") == "removed in PHP 7.0"
    assert death_reason("each") == "removed in PHP 8.0"
    assert death_reason("mysqli_query") is None


@settings(max_examples=150, deadline=None)
@given(st.binary(max_size=400))
def test_prop_parse_php_never_crashes(data):
    """Any bytes at all: the parser returns a well-formed result instead of raising."""
    result = parse_php(b"<?php " + data)
    assert set(result) >= {"functions", "classes", "includes", "superglobals", "dead_calls", "sql", "redirects"}
    for call in result["dead_calls"]:
        assert call["line"] >= 1
