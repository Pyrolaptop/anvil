"""PowerShell command execution with confirmation."""
from __future__ import annotations

import subprocess

from anvil.tools.base import ConfirmationRequest, ToolResult
from anvil.workspace import Workspace, is_destructive


class RunShellTool:
    name = "run_shell"
    description = (
        'Run a PowerShell command in the workspace folder. '
        'Args: {"command": "string"}. Every command prompts for approval.'
    )

    def run(self, args, workspace: Workspace, approve):
        command = args.get("command", "").strip()
        if not command:
            return ToolResult(False, "Missing 'command' argument.")

        destructive = is_destructive(command)
        label = "DESTRUCTIVE COMMAND" if destructive else "Shell command"
        req = ConfirmationRequest(
            prompt=f"Run {label}?",
            detail=f"cwd: {workspace.root}\n\n{command}",
        )
        if not approve(req):
            return ToolResult(False, "User denied shell command.")

        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True,
                text=True,
                cwd=str(workspace.root),
                timeout=300,
            )
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            combined = ""
            if out:
                combined += out
            if err:
                combined += ("\n\n[stderr]\n" + err) if combined else err
            combined = combined or "(no output)"
            ok = result.returncode == 0
            return ToolResult(ok, f"exit {result.returncode}\n\n{combined}")
        except subprocess.TimeoutExpired:
            return ToolResult(False, "Command timed out after 300s.")
        except OSError as e:
            return ToolResult(False, f"Shell error: {e}")
