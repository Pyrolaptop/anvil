"""Code-reuse scanner — MemPalace-backed with a grep fallback."""
from __future__ import annotations

from pathlib import Path

from anvil.config import DEFAULT_WORKSPACE
from anvil.tools.base import ToolResult


CODE_EXTS = {".py", ".ps1", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".cs", ".java", ".cpp", ".c", ".h", ".hpp", ".md", ".html", ".css", ".sh"}
MAX_MATCHES = 20
MAX_SNIPPET = 400


class SearchCodeTool:
    name = "search_code"
    description = (
        'Search existing LocalProjects for code related to a description. '
        'Returns file paths and snippets. Args: {"query": "what to look for"}'
    )

    def run(self, args, workspace, approve):
        query = args.get("query", "").strip()
        if not query:
            return ToolResult(False, "Missing 'query' argument.")

        # Try MemPalace first
        mp_result = _mempalace_search(query)
        if mp_result is not None:
            return ToolResult(True, mp_result)

        # Fallback: simple substring search over LocalProjects
        return ToolResult(True, _grep_search(query))


def _mempalace_search(query: str) -> str | None:
    """Invoke `python -m mempalace search` and capture the output.

    Returns None if MemPalace isn't installed/configured, so we fall back to grep.
    """
    try:
        import mempalace  # noqa: F401
    except ImportError:
        return None

    import os
    import sys
    import subprocess

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mempalace", "search", query,
             "--results", str(MAX_MATCHES)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            env=env,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    if not out and "No results" in err:
        return "(MemPalace returned no matches)"
    if result.returncode != 0 and not out:
        return None  # fall back to grep
    if not out:
        return "(MemPalace returned no matches)"
    return f"[MemPalace index]\n{out[:8000]}"


def _grep_search(query: str) -> str:
    root = Path(DEFAULT_WORKSPACE)
    needles = [w.lower() for w in query.split() if len(w) > 2]
    if not needles:
        return "(query too short to search)"

    matches = []
    for path in root.rglob("*"):
        if len(matches) >= MAX_MATCHES:
            break
        if not path.is_file() or path.suffix.lower() not in CODE_EXTS:
            continue
        if any(part in {"__pycache__", "node_modules", ".git", "venv", ".venv", "dist", "build"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lower = text.lower()
        hits = sum(1 for n in needles if n in lower)
        if hits >= max(1, len(needles) // 2):
            idx = min((lower.find(n) for n in needles if n in lower), default=0)
            start = max(0, idx - 80)
            snippet = text[start:start + MAX_SNIPPET]
            rel = path.relative_to(root)
            matches.append((hits, rel, snippet))

    if not matches:
        return "(no matches — MemPalace is not installed; used grep fallback)"

    matches.sort(key=lambda m: -m[0])
    lines = ["[grep fallback — install mempalace for semantic search]"]
    for _, rel, snippet in matches[:MAX_MATCHES]:
        lines.append(f"\n--- {rel} ---\n{snippet}")
    return "\n".join(lines)
