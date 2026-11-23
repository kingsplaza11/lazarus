"""Read one PHP file with tree-sitter and pull out what it does.

Targets py-tree-sitter >= 0.25 and tree-sitter-php >= 0.23. Walks the syntax tree by
node type (no queries), so small grammar changes degrade gracefully instead of crashing.
"""
from __future__ import annotations

from functools import lru_cache

import tree_sitter_php
from tree_sitter import Language, Parser

from .sql import detect_sql

SUPERGLOBALS = {
    "$_GET": "GET", "$_POST": "POST", "$_REQUEST": "REQUEST", "$_SESSION": "SESSION",
    "$_COOKIE": "COOKIE", "$_FILES": "FILES", "$_SERVER": "SERVER",
    "$HTTP_GET_VARS": "GET", "$HTTP_POST_VARS": "POST", "$HTTP_SESSION_VARS": "SESSION",
    "$HTTP_COOKIE_VARS": "COOKIE", "$HTTP_POST_FILES": "FILES", "$HTTP_SERVER_VARS": "SERVER",
}
INCLUDE_TYPES = {
    "include_expression": "include", "include_once_expression": "include_once",
    "require_expression": "require", "require_once_expression": "require_once",
}
STRING_TYPES = {"string", "encapsulated_string", "heredoc", "nowdoc"}

# Functions that no longer exist in modern PHP: the "cause of death".
REMOVED_IN_PHP54 = {
    "session_register", "session_unregister", "session_is_registered", "define_syslog_variables",
    "import_request_variables", "mysqli_bind_param", "mysqli_bind_result", "mysqli_client_encoding",
    "mysqli_fetch", "mysqli_param_count", "mysqli_get_metadata", "mysqli_send_long_data",
}
REMOVED_IN_PHP7 = {
    "mysql_affected_rows", "mysql_client_encoding", "mysql_close", "mysql_connect", "mysql_create_db",
    "mysql_data_seek", "mysql_db_name", "mysql_db_query", "mysql_drop_db", "mysql_errno", "mysql_error",
    "mysql_escape_string", "mysql_fetch_array", "mysql_fetch_assoc", "mysql_fetch_field",
    "mysql_fetch_lengths", "mysql_fetch_object", "mysql_fetch_row", "mysql_field_flags", "mysql_field_len",
    "mysql_field_name", "mysql_field_seek", "mysql_field_table", "mysql_field_type", "mysql_free_result",
    "mysql_get_client_info", "mysql_get_host_info", "mysql_get_proto_info", "mysql_get_server_info",
    "mysql_info", "mysql_insert_id", "mysql_list_dbs", "mysql_list_fields", "mysql_list_processes",
    "mysql_list_tables", "mysql_num_fields", "mysql_num_rows", "mysql_pconnect", "mysql_ping",
    "mysql_query", "mysql_real_escape_string", "mysql_result", "mysql_select_db", "mysql_set_charset",
    "mysql_stat", "mysql_tablename", "mysql_thread_id", "mysql_unbuffered_query",
    "ereg", "eregi", "ereg_replace", "eregi_replace", "split", "spliti", "sql_regcase",
    "set_magic_quotes_runtime", "magic_quotes_runtime", "call_user_method", "call_user_method_array",
    "set_socket_blocking", "datefmt_set_timezone_id", "mcrypt_generic_end",
}
REMOVED_IN_PHP8 = {
    "each", "create_function", "get_magic_quotes_gpc", "get_magic_quotes_runtime", "money_format",
    "__autoload", "convert_cyr_string", "hebrevc", "restore_include_path", "ezmlm_hash", "fgetss",
    "image2wbmp", "png2wbmp", "jpeg2wbmp", "read_exif_data", "gmp_random", "ldap_sort",
}


def death_reason(name: str) -> str | None:
    if name in REMOVED_IN_PHP54:
        return "removed in PHP 5.4"
    if name in REMOVED_IN_PHP7:
        return "removed in PHP 7.0"
    if name in REMOVED_IN_PHP8:
        return "removed in PHP 8.0"
    return None


@lru_cache(maxsize=1)
def get_parser() -> Parser:
    return Parser(Language(tree_sitter_php.language_php()))


def _text(node) -> str:
    return node.text.decode("utf-8", "replace") if node is not None and node.text is not None else ""


def _line(node) -> int:
    return node.start_point[0] + 1


def _strip_binary_prefix(text: str) -> str:
    return text[1:] if text[:1] in ("b", "B") and len(text) > 1 and text[1] in "'\"" else text


def is_string_node(node) -> bool:
    """True for string literal nodes, whatever this grammar version calls them.

    Grammar versions name double-quoted strings differently (encapsulated_string, string, ...),
    so besides the known names we accept any node with "string" in its type whose text is
    wrapped in matching quotes. Content-only child nodes (no quotes) are excluded.
    """
    if node is None:
        return False
    if node.type in ("heredoc", "nowdoc"):
        return True
    if node.type not in STRING_TYPES and "string" not in node.type:
        return False
    text = _strip_binary_prefix(_text(node))
    return len(text) >= 2 and text[0] in "'\"" and text[-1] == text[0]


def literal_value(node) -> str | None:
    """Return the value of a string literal node, or None if it isn't one."""
    if not is_string_node(node):
        return None
    text = _text(node)
    if node.type in ("heredoc", "nowdoc"):
        lines = text.split("\n")
        return "\n".join(lines[1:-1])
    if text[:1] in ("b", "B") and len(text) > 1 and text[1] in "'\"":
        text = text[1:]
    if len(text) >= 2 and text[0] in "'\"" and text[-1] == text[0]:
        return text[1:-1]
    return text


def is_concat(node) -> bool:
    if node is None or node.type != "binary_expression":
        return False
    operator = node.child_by_field_name("operator")
    if operator is not None:
        return _text(operator) == "."
    return any(not child.is_named and _text(child) == "." for child in node.children)


def flatten(node) -> str:
    """Join a string concatenation into one string; non-literal parts become "?"."""
    if node is None:
        return "?"
    if node.type == "parenthesized_expression" and node.named_children:
        return flatten(node.named_children[0])
    if is_concat(node):
        left = node.child_by_field_name("left") or (node.named_children[0] if node.named_children else None)
        right = node.child_by_field_name("right") or (node.named_children[-1] if node.named_children else None)
        return flatten(left) + flatten(right)
    value = literal_value(node)
    return value if value is not None else "?"


def call_name(node) -> str:
    function = node.child_by_field_name("function")
    return _text(function).lstrip("\\").lower() if function is not None else ""


def call_args(node) -> list:
    arguments = node.child_by_field_name("arguments")
    if arguments is None:
        return []
    values = []
    for arg in arguments.named_children:
        if arg.type == "argument" and arg.named_children:
            values.append(arg.named_children[-1])
        elif arg.type != "comment":
            values.append(arg)
    return values


def _new_result() -> dict:
    return {
        "functions": [], "classes": [], "includes": [], "superglobals": {},
        "dead_calls": [], "sql": [], "redirects": [], "uses_session": False, "has_errors": False,
    }


def _add_key(result: dict, kind: str, key: str) -> None:
    keys = result["superglobals"].setdefault(kind, [])
    if key not in keys:
        keys.append(key)


def parse_php(source: bytes) -> dict:
    """Analyse one PHP file. Never raises on malformed input."""
    result = _new_result()
    tree = get_parser().parse(source)
    result["has_errors"] = bool(tree.root_node.has_error)
    seen_sql_lines: set[tuple[int, str]] = set()

    def record_sql(text: str, node) -> None:
        found = detect_sql(text)
        if found:
            key = (_line(node), found["text"])
            if key not in seen_sql_lines:
                seen_sql_lines.add(key)
                found["line"] = _line(node)
                result["sql"].append(found)

    def visit(node, current_class: dict | None, in_concat: bool) -> None:
        kind = node.type

        if kind == "function_definition":
            result["functions"].append({"name": _text(node.child_by_field_name("name")), "line": _line(node)})
        elif kind == "class_declaration":
            base = next((c for c in node.children if c.type == "base_clause"), None)
            parents = [_text(n) for n in base.named_children] if base is not None else []
            current_class = {
                "name": _text(node.child_by_field_name("name")),
                "extends": parents[0] if parents else "",
                "methods": [],
                "line": _line(node),
            }
            result["classes"].append(current_class)
        elif kind == "method_declaration" and current_class is not None:
            current_class["methods"].append(_text(node.child_by_field_name("name")))
        elif kind in INCLUDE_TYPES:
            target_node = node.named_children[-1] if node.named_children else None
            result["includes"].append({"kind": INCLUDE_TYPES[kind], "target": flatten(target_node), "line": _line(node)})
        elif kind == "function_call_expression":
            name = call_name(node)
            reason = death_reason(name)
            if reason:
                result["dead_calls"].append({"name": name, "line": _line(node), "why": reason})
            if name == "session_start":
                result["uses_session"] = True
            if name == "header":
                args = call_args(node)
                value = flatten(args[0]) if args else ""
                if value.lower().lstrip().startswith("location:"):
                    result["redirects"].append({"target": value.split(":", 1)[1].strip(), "line": _line(node)})
        elif kind == "subscript_expression" and node.named_children:
            obj = node.named_children[0]
            if obj.type == "variable_name" and _text(obj) in SUPERGLOBALS:
                sg = SUPERGLOBALS[_text(obj)]
                index = node.named_children[1] if len(node.named_children) > 1 else None
                value = literal_value(index)
                _add_key(result, sg, value if value is not None else "?")
                if sg == "SESSION":
                    result["uses_session"] = True
        elif kind == "variable_name" and _text(node) in SUPERGLOBALS:
            parent = node.parent
            if parent is None or parent.type != "subscript_expression":
                _add_key(result, SUPERGLOBALS[_text(node)], "*")
            if SUPERGLOBALS[_text(node)] == "SESSION":
                result["uses_session"] = True

        if is_concat(node) and not in_concat:
            record_sql(flatten(node), node)
            for child in node.children:
                visit(child, current_class, True)
            return
        if is_string_node(node):
            if not in_concat:
                value = literal_value(node)
                if value:
                    record_sql(value, node)
            # Children of a string are its content pieces; don't treat them as separate strings.
            for child in node.children:
                visit(child, current_class, True)
            return

        for child in node.children:
            visit(child, current_class, in_concat)

    _walk(tree.root_node, visit)
    return result


def _walk(root, visit) -> None:
    """Run the recursive visitor with a raised recursion limit for deeply nested files."""
    import sys

    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, 20000))
    try:
        visit(root, None, False)
    finally:
        sys.setrecursionlimit(limit)


def debug_tree(source: bytes) -> str:
    """Return the S-expression of a file's syntax tree (for the management command)."""
    return str(get_parser().parse(source).root_node)
