"""Tool interface."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from anvil.workspace import Workspace


@dataclass
class ToolResult:
    ok: bool
    output: str


@dataclass
class ConfirmationRequest:
    """Raised by a tool when the user must approve the action."""

    prompt: str
    detail: str = ""


class Tool(Protocol):
    name: str
    description: str

    def run(
        self,
        args: dict,
        workspace: Workspace,
        approve: "callable[[ConfirmationRequest], bool]",
    ) -> ToolResult: ...
