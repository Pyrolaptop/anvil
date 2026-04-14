"""File read / write / list, workspace-scoped."""
from __future__ import annotations

from anvil.tools.base import ConfirmationRequest, ToolResult
from anvil.workspace import Workspace


MAX_READ_BYTES = 200_000


class ReadFileTool:
    name = "read_file"
    description = 'Read a text file. Args: {"path": "relative or absolute path"}'

    def run(self, args, workspace: Workspace, approve):
        path = args.get("path")
        if not path:
            return ToolResult(False, "Missing 'path' argument.")
        full = workspace.resolve(path)
        if not full.exists():
            return ToolResult(False, f"File not found: {full}")
        if not full.is_file():
            return ToolResult(False, f"Not a file: {full}")
        try:
            data = full.read_bytes()[:MAX_READ_BYTES]
            text = data.decode("utf-8", errors="replace")
            return ToolResult(True, text)
        except OSError as e:
            return ToolResult(False, f"Read error: {e}")


class WriteFileTool:
    name = "write_file"
    description = 'Write text to a file. Args: {"path": "...", "content": "..."}'

    def run(self, args, workspace: Workspace, approve):
        path = args.get("path")
        content = args.get("content", "")
        if not path:
            return ToolResult(False, "Missing 'path' argument.")
        full = workspace.resolve(path)

        if not workspace.contains(full):
            req = ConfirmationRequest(
                prompt=f"Write file OUTSIDE workspace?",
                detail=f"{full}\n\n{len(content)} chars",
            )
            if not approve(req):
                return ToolResult(False, "User denied write outside workspace.")
        elif full.exists():
            req = ConfirmationRequest(
                prompt=f"Overwrite existing file?",
                detail=f"{full}\n\n{len(content)} chars",
            )
            if not approve(req):
                return ToolResult(False, "User denied overwrite.")

        try:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            return ToolResult(True, f"Wrote {len(content)} chars to {full}")
        except OSError as e:
            return ToolResult(False, f"Write error: {e}")


class ListDirTool:
    name = "list_dir"
    description = 'List files in a directory. Args: {"path": "relative or absolute path"}'

    def run(self, args, workspace: Workspace, approve):
        path = args.get("path", ".")
        full = workspace.resolve(path)
        if not full.exists():
            return ToolResult(False, f"Directory not found: {full}")
        if not full.is_dir():
            return ToolResult(False, f"Not a directory: {full}")
        try:
            entries = []
            for child in sorted(full.iterdir()):
                kind = "DIR" if child.is_dir() else "FILE"
                entries.append(f"[{kind}] {child.name}")
            return ToolResult(True, "\n".join(entries) if entries else "(empty)")
        except OSError as e:
            return ToolResult(False, f"List error: {e}")
