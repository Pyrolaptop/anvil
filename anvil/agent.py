"""Agent loop: stream from Ollama, parse tool calls, execute, continue."""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Callable

from anvil.modes import Mode, get_mode, system_prompt_for
from anvil.ollama_client import stream_chat, OllamaError
from anvil.tools import Tool, ToolResult, ConfirmationRequest, build_registry
from anvil.workspace import Workspace


TOOL_BLOCK_RE = re.compile(
    r'<tool\s+name="([^"]+)"\s*>\s*(\{[\s\S]*?\})\s*</tool>',
    re.IGNORECASE,
)
MAX_AGENT_STEPS = 8


@dataclass
class AgentEvent:
    kind: str  # "token" | "tool_call" | "tool_result" | "mode_routed" | "error" | "done"
    data: str


class Agent:
    def __init__(self, workspace: Workspace, approve: Callable[[ConfirmationRequest], bool]):
        self.workspace = workspace
        self.approve = approve
        self.tools: dict[str, Tool] = build_registry()

    def _tool_descriptions(self) -> dict[str, str]:
        return {name: t.description for name, t in self.tools.items()}

    def route_auto(self, user_message: str) -> str:
        """Use the router model to pick a real mode."""
        router = get_mode("auto")
        messages = [
            {"role": "system", "content": router.system_prompt},
            {"role": "user", "content": user_message},
        ]
        reply = "".join(stream_chat(router.model, messages)).strip().lower()
        for key in ("coding", "ideas", "general"):
            if key in reply:
                return key
        return "general"

    def run(self, mode_key: str, user_message: str, history: list[dict]) -> Iterator[AgentEvent]:
        if mode_key == "auto":
            try:
                target = self.route_auto(user_message)
                yield AgentEvent("mode_routed", target)
                mode_key = target
            except OllamaError as e:
                yield AgentEvent("error", str(e))
                return

        mode = get_mode(mode_key)
        allowed = {name: self.tools[name] for name in mode.tools if name in self.tools}
        tool_descs = {name: t.description for name, t in allowed.items()}
        system = system_prompt_for(mode, tool_descs)

        messages: list[dict] = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        for step in range(MAX_AGENT_STEPS):
            try:
                assistant_text = ""
                for token in stream_chat(mode.model, messages):
                    assistant_text += token
                    yield AgentEvent("token", token)
            except OllamaError as e:
                yield AgentEvent("error", str(e))
                return

            tool_calls = list(TOOL_BLOCK_RE.finditer(assistant_text))
            if not tool_calls:
                yield AgentEvent("done", assistant_text)
                return

            messages.append({"role": "assistant", "content": assistant_text})

            for match in tool_calls:
                name = match.group(1)
                raw_args = match.group(2)
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError as e:
                    result = ToolResult(False, f"Invalid JSON args: {e}")
                else:
                    tool = allowed.get(name)
                    if tool is None:
                        result = ToolResult(
                            False,
                            f"Tool '{name}' not available in {mode.label} mode. Available: {list(allowed)}",
                        )
                    else:
                        yield AgentEvent("tool_call", f"{name} {raw_args[:200]}")
                        try:
                            result = tool.run(args, self.workspace, self.approve)
                        except Exception as e:
                            result = ToolResult(False, f"Tool crashed: {e}")

                status = "OK" if result.ok else "ERROR"
                feedback = f"[tool {name} {status}]\n{result.output}"
                yield AgentEvent("tool_result", feedback)
                messages.append({"role": "user", "content": feedback})

        yield AgentEvent("done", "[max steps reached — stopping]")
