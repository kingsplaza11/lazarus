"""SQL syntax that modern MySQL/MariaDB no longer accepts: part of the cause of death.

Scans raw file text (PHP or .sql), so it also finds statements built across string pieces.
"""
from __future__ import annotations

import re

DEAD_SQL = [
    ("TYPE=", re.compile(r"\bTYPE\s*=\s*(MyISAM|InnoDB|HEAP|MEMORY|MERGE|ISAM|BDB)\b", re.I),
     "table TYPE= option removed in MySQL 5.5 (use ENGINE=)"),
    ("TIMESTAMP(n)", re.compile(r"\bTIMESTAMP\s*\(\s*\d+\s*\)", re.I),
     "TIMESTAMP display width removed in MySQL 5.5"),
    ("SET OPTION", re.compile(r"\bSET\s+OPTION\s+\w+", re.I),
     "SET OPTION syntax removed in MySQL 5.6"),
    ("SHOW TABLE TYPES", re.compile(r"\bSHOW\s+TABLE\s+TYPES\b", re.I),
     "SHOW TABLE TYPES removed in MySQL 5.5 (use SHOW ENGINES)"),
]


def find_dead_sql(text: str) -> list[dict]:
    """Return [{"syntax", "why", "line", "text"}] for every removed construct in `text`."""
    found = []
    for name, pattern, why in DEAD_SQL:
        for match in pattern.finditer(text or ""):
            found.append({
                "syntax": name,
                "why": why,
                "line": text.count("\n", 0, match.start()) + 1,
                "text": " ".join(match.group(0).split())[:60],
            })
    return sorted(found, key=lambda f: (f["line"], f["syntax"]))
