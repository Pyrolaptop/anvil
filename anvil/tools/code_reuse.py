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
    try:
        import mempalace  # type: ignore
    except ImportError:
        return None

    # MemPalace Python API is still evolving; try common entry points.
    for candidate in ("search", "query", "recall"):
        fn = getattr(mempalace, candidate, None)
        if callable(fn):
            try:
                res = fn(query, limit=MAX_MATCHES)
                return _format_mempalace(res)
            except TypeError:
                try:
                    res = fn(query)
                    return _format_mempalace(res)
                except Exception:
                    continue
            except Exception:
                continue
    return None


def _format_mempalace(res) -> str:
    if not res:
        return "(MemPalace returned no matches)"
    lines = ["[MemPalace index]"]
    items = res if isinstance(res, list) else [res]
    for item in items[:MAX_MATCHES]:
        if isinstance(item, dict):
            src = item.get("path") or item.get("source") or "?"
            snippet = (item.get("text") or item.get("content") or "").strip()[:MAX_SNIPPET]
            lines.append(f"\n--- {src} ---\n{snippet}")
        else:
            lines.append(str(item)[:MAX_SNIPPET])
    return "\n".join(lines)


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
