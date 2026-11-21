"""Find HTML forms and their fields in PHP/HTML source (regex, PHP blocks masked first)."""
from __future__ import annotations

import re

PHP_BLOCK = re.compile(r"<\?(?:php|=)?.*?(?:\?>|\Z)", re.I | re.S)
FORM = re.compile(r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)(?:</form>|(?=<form\b)|\Z)", re.I | re.S)
FIELD = re.compile(r"<(?P<tag>input|select|textarea|button)\b(?P<attrs>[^>]*)>", re.I | re.S)
ATTR = re.compile(r"([\w:-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.S)

PLACEHOLDER = "{php}"


def mask_php(source: str) -> str:
    """Replace PHP blocks with a placeholder, keeping line breaks so line numbers stay correct."""
    return PHP_BLOCK.sub(lambda m: PLACEHOLDER + "\n" * m.group(0).count("\n"), source)


def parse_attrs(text: str) -> dict[str, str]:
    attrs = {}
    for name, dq, sq, bare in ATTR.findall(text):
        attrs[name.lower()] = dq or sq or bare
    return attrs


def find_forms(source: str) -> list[dict]:
    """Return [{"action", "method", "fields": [{"name", "type"}], "line"}].

    PHP blocks are masked first so `<?php ... ?>` inside attributes can't break parsing.
    If that hides every form (forms echoed from PHP strings), scan the raw source instead.
    """
    forms = _scan(mask_php(source))
    if not forms and "<form" in source.lower():
        forms = _scan(source)
    return forms


def _scan(masked: str) -> list[dict]:
    forms = []
    for match in FORM.finditer(masked):
        attrs = parse_attrs(match["attrs"])
        fields = []
        for field in FIELD.finditer(match["body"]):
            field_attrs = parse_attrs(field["attrs"])
            name = field_attrs.get("name")
            if not name:
                continue
            tag = field["tag"].lower()
            kind = field_attrs.get("type", "text").lower() if tag == "input" else tag
            fields.append({"name": name, "type": kind})
        forms.append({
            "action": attrs.get("action", ""),
            "method": attrs.get("method", "get").upper(),
            "fields": fields,
            "line": masked.count("\n", 0, match.start()) + 1,
        })
    return forms
