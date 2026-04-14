"""Workspace scoping + safety checks."""
from __future__ import annotations

import re
from pathlib import Path

DESTRUCTIVE_PATTERNS = [
    re.compile(r"\brm\s+-rf\b", re.I),
    re.compile(r"\brm\s+.*\*", re.I),
    re.compile(r"\bremove-item\b.*-recurse", re.I),
    re.compile(r"\brmdir\b", re.I),
    re.compile(r"\bdel\s+/[sq]", re.I),
    re.compile(r"\bformat\s+[a-z]:", re.I),
    re.compile(r"\bgit\s+push\s+.*--force\b", re.I),
    re.compile(r"\bgit\s+push\s+.*-f\b", re.I),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
    re.compile(r"\bgit\s+clean\s+-[a-z]*f", re.I),
    re.compile(r"\bdrop\s+table\b", re.I),
    re.compile(r"\bdrop\s+database\b", re.I),
    re.compile(r"\bshutdown\b", re.I),
]


class Workspace:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        if not self.root.exists():
            raise ValueError(f"Workspace does not exist: {self.root}")

    def contains(self, path: str | Path) -> bool:
        try:
            p = Path(path).resolve()
            p.relative_to(self.root)
            return True
        except (ValueError, OSError):
            return False

    def resolve(self, path: str | Path) -> Path:
        """Resolve a path; if relative, anchor to workspace root."""
        p = Path(path)
        if not p.is_absolute():
            p = self.root / p
        return p.resolve()


def is_destructive(command: str) -> bool:
    return any(p.search(command) for p in DESTRUCTIVE_PATTERNS)
