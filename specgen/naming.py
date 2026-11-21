"""Turn legacy names (tables, columns, PHP files) into readable and Django-friendly names."""
from __future__ import annotations

import os
import re

COMMON_WORDS = {
    "comment", "status", "file", "project", "member", "user", "item", "country", "group", "role", "task",
    "category", "tag", "log", "history", "note", "attachment", "setting", "message", "order", "product",
    "customer", "invoice", "payment", "page", "post", "type", "event", "account", "address", "contact",
    "session", "permission", "team", "list", "entry", "level", "priority", "context", "time",
}
AUTH_WORDS = {"login", "logout", "register", "password", "signin", "signup", "signout", "auth"}
SKIP_URL_TOKENS = {"index", "xajax", "ajax", "inc", "php"}


def common_prefix(names: list[str]) -> str:
    """Return a shared table prefix like "frk_" when every name has it (and it ends with "_")."""
    if len(names) < 2:
        return ""
    prefix = os.path.commonprefix(names)
    if "_" not in prefix:
        return ""
    return prefix[: prefix.rfind("_") + 1]


def split_words(word: str, known: set[str]) -> list[str]:
    """Split a run-together lowercase word using known words, e.g. "itemcomment" -> ["item", "comment"]."""
    word = word.lower()
    vocabulary = known | COMMON_WORDS
    if not word or word in vocabulary:
        return [word] if word else []
    for cut in range(len(word) - 1, 1, -1):
        head, tail = word[:cut], word[cut:]
        if head in vocabulary:
            rest = split_words(tail, known)
            if all(part in vocabulary for part in rest):
                return [head] + rest
    return [word]


def table_base(table: str, prefix: str) -> str:
    return table[len(prefix):] if prefix and table.startswith(prefix) else table


def model_name(table: str, prefix: str, known_bases: set[str]) -> str:
    """frk_itemcomment -> ItemComment; frk_member -> Member."""
    base = table_base(table, prefix)
    others = known_bases - {base}  # a table's own name must not stop it being split
    words = []
    for chunk in re.split(r"[_\W]+", base):
        words.extend(split_words(chunk, others))
    name = "".join(w.capitalize() for w in words if w) or "Record"
    return name if name[0].isalpha() else f"T{name}"


def human(name: str) -> str:
    """ItemComment -> "item comment"."""
    return re.sub(r"(?<!^)(?=[A-Z])", " ", name).lower()


def field_name(column: str) -> str:
    name = re.sub(r"\W+", "_", column).strip("_").lower() or "field"
    return name if name[0].isalpha() else f"f_{name}"


def page_tokens(path: str) -> list[str]:
    stem = path[:-4] if path.lower().endswith(".php") else path
    return [t for t in re.split(r"[/_.\-]+", stem.lower()) if t]


def page_title(path: str) -> str:
    tokens = [t for t in page_tokens(path) if t not in {"xajax", "inc"}]
    if not tokens:
        return "Home"
    if tokens == ["index"]:
        return "Home"
    if tokens[-1] == "index" and len(tokens) > 1:
        tokens = tokens[:-1]
    return " ".join(t.upper() if t in {"rss", "api"} else t.capitalize() for t in tokens)


def page_group(path: str) -> str:
    tokens = page_tokens(path)
    if any(t in AUTH_WORDS for t in tokens):
        return "Authentication"
    title = page_title(path)
    return title.split()[0] if title else "Home"


def page_url(path: str) -> str:
    tokens = [t for t in page_tokens(path) if t not in SKIP_URL_TOKENS]
    return "/" + "/".join(tokens) + "/" if tokens else "/"


def view_name(path: str) -> str:
    tokens = [t for t in page_tokens(path) if t not in SKIP_URL_TOKENS]
    return "_".join(tokens) or "home"


def app_for_group(group: str) -> str:
    return "accounts" if group in {"Authentication", "User"} else "core"
