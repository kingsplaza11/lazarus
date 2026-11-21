from hypothesis import given, settings
from hypothesis import strategies as st

from autopsy.parsers.forms import find_forms, mask_php
from autopsy.parsers.sql import clean_table_name, detect_sql, match_table, parse_schema, split_top_level

SCHEMA = """
CREATE TABLE frk_task (
  taskId int(10) unsigned NOT NULL auto_increment,
  title varchar(255) NOT NULL default '',
  deadline date default NULL,
  PRIMARY KEY  (taskId),
  KEY projectId (projectId)
) TYPE=MyISAM;
CREATE TABLE IF NOT EXISTS `frk_project` (`projectId` int(10) NOT NULL, `name` varchar(120), PRIMARY KEY (`projectId`)) ENGINE=MyISAM DEFAULT CHARSET=utf8;
"""


def test_detect_sql_basic():
    found = detect_sql("SELECT * FROM frk_task WHERE taskId = 1")
    assert found["verb"] == "SELECT"
    assert found["tables"] == ["frk_task"]


def test_detect_sql_with_dynamic_prefix_and_join():
    found = detect_sql("SELECT t.* FROM ?task t LEFT JOIN ?project p ON p.id = t.projectId")
    assert found["tables"] == ["project", "task"]


def test_detect_sql_ignores_plain_text():
    assert detect_sql("Hello, select your project") is None
    assert detect_sql("") is None


def test_clean_table_name():
    assert clean_table_name("`frk_user`") == "frk_user"
    assert clean_table_name("db.frk_user") == "frk_user"
    assert clean_table_name("?") == ""


def test_parse_schema_reads_tables_columns_and_keys():
    tables = {t["name"]: t for t in parse_schema(SCHEMA)}
    assert set(tables) == {"frk_task", "frk_project"}
    assert [c["name"] for c in tables["frk_task"]["columns"]] == ["taskid", "title", "deadline"]
    assert tables["frk_task"]["primary_key"] == ["taskid"]
    assert tables["frk_project"]["columns"][1] == {"name": "name", "type": "varchar(120)"}


def test_split_top_level_respects_parentheses():
    assert split_top_level("a int(10), b decimal(5,2), c text") == ["a int(10)", "b decimal(5,2)", "c text"]


def test_match_table_handles_prefix():
    assert match_table("task", ["frk_task", "frk_project"]) == "frk_task"
    assert match_table("frk_task", ["frk_task"]) == "frk_task"
    assert match_table("unknown", ["frk_task"]) == "unknown"


FORM_SOURCE = """<html>
<form action="login.php" method="post" name="<?php echo $x; ?>">
 <input type="text" name="username" value="<?php echo $u ?>">
 <input type="password" name="password">
 <select name="lang"><option>en</option></select>
 <textarea name="note"></textarea>
 <input type="submit" value="Go">
</form>
<form action=search.php><input name=q></form>
"""


def test_find_forms_fields_methods_and_lines():
    forms = find_forms(FORM_SOURCE)
    assert len(forms) == 2
    login, search = forms
    assert login["action"] == "login.php"
    assert login["method"] == "POST"
    assert login["line"] == 2
    assert [f["name"] for f in login["fields"]] == ["username", "password", "lang", "note"]
    assert login["fields"][1]["type"] == "password"
    assert search["method"] == "GET"
    assert search["fields"] == [{"name": "q", "type": "text"}]


def test_find_forms_echoed_from_php():
    source = "<?php echo '<form method=\"post\" action=\"save.php\"><input name=\"title\"></form>'; ?>"
    forms = find_forms(source)
    assert forms and forms[0]["action"] == "save.php"


def test_mask_php_keeps_line_count():
    source = "a\n<?php\n echo 1;\n?>\nb"
    assert mask_php(source).count("\n") == source.count("\n")


@settings(max_examples=200)
@given(st.text(max_size=200))
def test_prop_detect_sql_never_crashes_and_tables_are_clean(text):
    found = detect_sql(text)
    if found is not None:
        for table in found["tables"]:
            assert table and table == table.lower()
            assert "?" not in table and "`" not in table


@settings(max_examples=200)
@given(st.text(max_size=300))
def test_prop_find_forms_never_crashes(text):
    for form in find_forms(text):
        assert form["line"] >= 1
        assert form["method"] == form["method"].upper()
