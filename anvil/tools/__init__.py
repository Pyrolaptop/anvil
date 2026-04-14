"""Tool registry."""
from __future__ import annotations

from anvil.tools.base import Tool, ToolResult, ConfirmationRequest
from anvil.tools.filesystem import ReadFileTool, WriteFileTool, ListDirTool
from anvil.tools.shell import RunShellTool
from anvil.tools.web import FetchUrlTool
from anvil.tools.code_reuse import SearchCodeTool


def build_registry() -> dict[str, Tool]:
    tools: list[Tool] = [
        ReadFileTool(),
        WriteFileTool(),
        ListDirTool(),
        RunShellTool(),
        FetchUrlTool(),
        SearchCodeTool(),
    ]
    return {t.name: t for t in tools}


__all__ = [
    "Tool",
    "ToolResult",
    "ConfirmationRequest",
    "build_registry",
]
