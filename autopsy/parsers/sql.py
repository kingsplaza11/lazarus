"""Find SQL in PHP strings and read table schemas from .sql files."""
from __future__ import annotations

import re

SQL_START = re.compile(
    r"^\s*\(?\s*(SELECT|INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP|TRUNCATE|SHOW)\b", re.I
)
TABLE_REF = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE(?:\s+IF\s+(?:NOT\s+)?EXISTS)?)\s+[`\"]?([\w?.]+)", re.I
)
CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?(?P<name>[\w]+)[`\"]?\s*\((?P<body>.*?)\)\s*"
    r"(?=ENGINE|TYPE|DEFAULT|AUTO_INCREMENT|COMMENT|CHARSET|COLLATE|;|$)",
    re.I | re.S,
)
NON_COLUMN = {"PRIMARY", "KEY", "INDEX", "UNIQUE", "CONSTRAINT", "FULLTEXT", "FOREIGN", "CHECK", "SPATIAL"}


def clean_table_name(name: str) -> str:
    """Normalise a table reference: drop placeholders, quotes and schema prefixes."""
    name = name.replace("?", "").strip("`\". ")
    if "." in name:
        name = name.split(".")[-1]
    return name.lower()


def detect_sql(text: str) -> dict | None:
    """Return {"verb", "tables", "text"} if `text` looks like an SQL statement, else None."""
    if not text:
        return None
    match = SQL_START.match(text)
    if not match:
        return None
    tables = sorted({t for t in (clean_table_name(r) for r in TABLE_REF.findall(text)) if t})
    return {"verb": match.group(1).upper(), "tables": tables, "text": " ".join(text.split())[:300]}


def split_top_level(body: str) -> list[str]:
    """Split a CREATE TABLE body on commas that are not inside parentheses."""
    parts, depth, current = [], 0, []
    for char in body:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    if "".join(current).strip():
        parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def parse_schema(sql_text: str) -> list[dict]:
    """Return [{"name", "columns": [{"name", "type"}], "primary_key": [...]}] for each CREATE TABLE."""
    tables = []
    for match in CREATE_TABLE.finditer(sql_text):
        columns, primary_key = [], []
        for definition in split_top_level(match["body"]):
            tokens = definition.split()
            if not tokens:
                continue
            first = tokens[0].upper()
            if first in NON_COLUMN:
                if first == "PRIMARY":
                    inside = re.search(r"\((.*?)\)", definition)
                    if inside:
                        primary_key = [c.strip(" `\"").lower() for c in inside.group(1).split(",")]
                continue
            column = {"name": tokens[0].strip("`\"").lower(), "type": tokens[1].lower() if len(tokens) > 1 else ""}
            if "PRIMARY KEY" in definition.upper():
                primary_key = [column["name"]]
            columns.append(column)
        tables.append({"name": match["name"].lower(), "columns": columns, "primary_key": primary_key})
    return tables


def match_table(ref: str, schema_names: list[str]) -> str:
    """Map a reference like "task" to a schema table like "frk_task" when the prefix was dynamic."""
    if ref in schema_names:
        return ref
    for name in schema_names:
        if len(ref) >= 3 and (name.endswith("_" + ref) or name.endswith(ref)):
            return name
    return ref
