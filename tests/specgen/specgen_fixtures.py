"""A small autopsy report shaped like TaskFreak's, for generator tests (no tree-sitter needed)."""


def taskfreak_like_report() -> dict:
    tables = [
        {"name": "frk_member", "columns": [
            {"name": "memberid", "type": "int(10)"}, {"name": "username", "type": "varchar(20)"},
            {"name": "password", "type": "varchar(60)"}, {"name": "email", "type": "varchar(120)"}],
         "primary_key": ["memberid"], "verbs": ["SELECT", "UPDATE"], "used_in": ["login.php"]},
        {"name": "frk_project", "columns": [
            {"name": "projectid", "type": "int(10)"}, {"name": "name", "type": "varchar(120)"},
            {"name": "description", "type": "text"}],
         "primary_key": ["projectid"], "verbs": ["SELECT", "INSERT"], "used_in": ["project_edit.php"]},
        {"name": "frk_item", "columns": [
            {"name": "itemid", "type": "int(10)"}, {"name": "projectid", "type": "int(10)"},
            {"name": "title", "type": "varchar(255)"}, {"name": "deadline", "type": "date"},
            {"name": "showprivate", "type": "tinyint(1)"}],
         "primary_key": ["itemid"], "verbs": ["SELECT"], "used_in": ["index.php"]},
        {"name": "frk_memberproject", "columns": [
            {"name": "memberid", "type": "int(10)"}, {"name": "projectid", "type": "int(10)"},
            {"name": "position", "type": "tinyint(3)"}],
         "primary_key": ["memberid", "projectid"], "verbs": [], "used_in": []},
        {"name": "frk_itemcomment", "columns": [
            {"name": "itemcommentid", "type": "int(10)"}, {"name": "itemid", "type": "int(10)"},
            {"name": "body", "type": "text"}, {"name": "postdate", "type": "datetime"}],
         "primary_key": ["itemcommentid"], "verbs": [], "used_in": []},
    ]
    files = [
        {"path": "login.php", "sql": [{"verb": "SELECT", "tables": ["frk_member"], "text": "SELECT ...", "line": 12}]},
        {"path": "index.php", "sql": [{"verb": "SELECT", "tables": ["frk_item"], "text": "SELECT ...", "line": 40}]},
        {"path": "project_edit.php", "sql": [
            {"verb": "INSERT", "tables": ["frk_project"], "text": "INSERT ...", "line": 88},
            {"verb": "SELECT", "tables": ["frk_project"], "text": "SELECT ...", "line": 20}]},
        {"path": "_common.php", "sql": [{"verb": "UPDATE", "tables": ["frk_member"], "text": "UPDATE ...", "line": 5}]},
        {"path": "logout.php", "sql": []},
        {"path": "rss.php", "sql": []},
    ]
    pages = [
        {"path": "index.php", "includes": ["_common.php"], "reads": {"GET": ["project", "sort", "?"]},
         "forms": [], "tables": ["frk_item", "frk_member"], "redirects": [], "uses_session": True},
        {"path": "login.php", "includes": ["_common.php"], "reads": {"POST": ["username", "password", "remember"]},
         "forms": [{"action": "login.php", "method": "POST", "line": 30, "file": "login.php",
                    "fields": [{"name": "username", "type": "text"}, {"name": "password", "type": "password"},
                               {"name": "{php}", "type": "hidden"}]}],
         "tables": ["frk_member"], "redirects": [{"target": "index.php", "line": 18, "file": "login.php"}], "uses_session": True},
        {"path": "logout.php", "includes": ["_common.php"], "reads": {}, "forms": [], "tables": [],
         "redirects": [{"target": "login.php", "line": 4, "file": "logout.php"}], "uses_session": True},
        {"path": "project_edit.php", "includes": ["_common.php"], "reads": {"GET": ["id"], "POST": ["name"]},
         "forms": [{"action": "", "method": "POST", "line": 60, "file": "project_edit.php",
                    "fields": [{"name": "name", "type": "text"}, {"name": "description", "type": "textarea"}]}],
         "tables": ["frk_project"], "redirects": [], "uses_session": True},
        {"path": "rss.php", "includes": [], "reads": {"GET": ["*"]}, "forms": [], "tables": [], "redirects": [], "uses_session": False},
    ]
    return {
        "version": 1,
        "summary": {"php_files": 6, "lines_of_code": 900, "pages": len(pages), "forms": 2, "sql_statements": 5,
                    "tables": len(tables), "classes": 3, "functions": 10, "unresolved_includes": 0,
                    "files_with_errors": 0, "skipped_translation_files": 12, "libraries": 2},
        "cause_of_death": {
            "summary": "12 calls to 3 functions removed in PHP 7.0, in 2 files.",
            "functions": [{"name": "mysql_query", "count": 8, "why": "removed in PHP 7.0"},
                          {"name": "mysql_connect", "count": 2, "why": "removed in PHP 7.0"},
                          {"name": "ereg", "count": 2, "why": "removed in PHP 7.0"}],
            "files": ["_common.php", "include/classes/tzn_mysql.php"],
        },
        "i18n": {"path": "include/language", "languages": ["de", "en", "fr"], "kept": "en"},
        "assets": {"stylesheets": [{"path": "skins/redfreak/style.css", "bytes": 9000},
                                   {"path": "skins/bluefreak/style.css", "bytes": 8000}],
                   "skins": [{"path": "skins", "names": ["bluefreak", "redfreak"]}]},
        "libraries": [{"path": "jscalendar", "name": "jscalendar", "reason": "well-known library"},
                      {"path": "xajax", "name": "xajax", "reason": "well-known library"}],
        "pages": pages,
        "tables": tables,
        "files": files,
    }
