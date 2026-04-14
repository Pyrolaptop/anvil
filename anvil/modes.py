"""Mode definitions: system prompt + model + enabled tools per mode."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mode:
    key: str
    label: str
    model: str
    tools: tuple[str, ...]
    system_prompt: str


TOOL_INSTRUCTIONS_TEMPLATE = """
You can use tools to take actions on the user's PC. To call a tool, output a single block in this exact format:

<tool name="TOOL_NAME">
{"REAL_ARG_NAME": "value"}
</tool>

RULES FOR TOOL CALLS — READ CAREFULLY:
1. Use the EXACT argument names shown in each tool's description below. Do NOT invent names like "arg1", "arg2", "input" — those are placeholders, not real keys.
2. After emitting the <tool>...</tool> block, STOP generating. Do not write a Summary yet. The system will run the tool and send you the result in the next turn.
3. If a previous tool call ERRORED with "Missing X argument", your JSON was missing that exact key. Re-read the tool description below and use the correct key name.
4. Do NOT repeat the same failing tool call. If a call errors, fix the argument names or give up and answer without the tool.

Concrete example (for a tool whose description says 'Args: {"url": "..."}'):
<tool name="fetch_url">
{"url": "https://example.com"}
</tool>

When you are fully done, reply with a short, clear SUMMARY of what you did. Do not include tool call blocks in the summary.

Available tools for this mode (use these exact argument keys):
__TOOL_LIST__
""".strip()


IDEAS = Mode(
    key="ideas",
    label="Ideas",
    model="phi3:mini",
    tools=(),
    system_prompt=(
        "You are Anvil in IDEAS mode — a creative brainstorming partner. "
        "The user wants expansive, imaginative thinking. Offer multiple angles, "
        "challenge assumptions, suggest unconventional directions. Be bold. "
        "Do NOT write code. Do NOT take actions on the PC. Talk ideas only. "
        "Keep each response focused and under ~300 words unless the user asks for depth."
    ),
)

CODING = Mode(
    key="coding",
    label="Coding",
    model="qwen2.5-coder:3b",
    tools=("read_file", "write_file", "list_dir", "run_shell", "search_code"),
    system_prompt=(
        "You are Anvil in CODING mode — a focused engineering assistant. "
        "The user's workspace is scoped; use tools to read, write, and execute. "
        "Before editing, read the relevant files. Before creating new code, use "
        "search_code to check if similar logic exists in the user's existing "
        "LocalProjects — if it does, copy it into the new project with attribution "
        "(`# reused from <project>/<file>`). Prefer small, incremental changes. "
        "Write concise code without over-commenting. End with a brief SUMMARY of "
        "what you changed and why."
    ),
)

GENERAL = Mode(
    key="general",
    label="General",
    model="phi3:mini",
    tools=("fetch_url",),
    system_prompt=(
        "You are Anvil in GENERAL mode — an everyday helpful assistant. Answer "
        "questions clearly and concisely. Use the fetch_url tool when the user "
        "needs current information from the web. End with a short SUMMARY if the "
        "task involved multiple steps."
    ),
)

AUTO = Mode(
    key="auto",
    label="Auto",
    model="gemma3:1b",
    tools=(),
    system_prompt=(
        "You route user requests to one of three modes. Reply with ONLY one "
        "lowercase word: coding, ideas, or general.\n\n"
        "coding  = writing, editing, debugging, running, or explaining code; "
        "anything about scripts, APIs, functions, files, terminals, or repos.\n"
        "ideas   = open-ended brainstorming, creative exploration, naming, "
        "strategy, 'what if', 'help me think through'.\n"
        "general = everyday questions, facts, definitions, math, summarising, "
        "anything not clearly coding or brainstorming.\n\n"
        "Examples:\n"
        "User: write me a python function to reverse a string  -> coding\n"
        "User: fix the bug in main.py                           -> coding\n"
        "User: brainstorm names for my new app                  -> ideas\n"
        "User: what could I do with a spare Raspberry Pi?       -> ideas\n"
        "User: what is 2+2?                                     -> general\n"
        "User: explain photosynthesis                           -> general\n\n"
        "Reply with ONE WORD only."
    ),
)


MODES: dict[str, Mode] = {m.key: m for m in (IDEAS, CODING, GENERAL, AUTO)}


def get_mode(key: str) -> Mode:
    return MODES[key]


def system_prompt_for(mode: Mode, tool_descriptions: dict[str, str]) -> str:
    if not mode.tools:
        return mode.system_prompt
    lines = [f"- {name}: {tool_descriptions.get(name, '')}" for name in mode.tools]
    tool_block = TOOL_INSTRUCTIONS_TEMPLATE.replace("__TOOL_LIST__", "\n".join(lines))
    return f"{mode.system_prompt}\n\n{tool_block}"
