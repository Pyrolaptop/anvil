# Anvil

A local desktop AI assistant for Windows. Chat with your own Ollama models, switch purpose-built modes, and let the assistant actually *do* things on your PC — with a clean summary at the end.

Runs 100% offline. No API keys. No cloud. No subscription.

## What it does

A single desktop window with a mode toggle. Pick a mode, describe what you want, and it works end-to-end:

| Mode    | Purpose                         | Model (default)        | Tools enabled                    |
|---------|---------------------------------|------------------------|----------------------------------|
| Ideas   | Brainstorm, explore, draft      | `phi3:mini`            | None (pure chat)                 |
| Coding  | Write / edit / debug code       | `qwen2.5-coder:3b`     | Files, shell, code-reuse search  |
| General | Everyday Q&A, quick help        | `phi3:mini`            | Web fetch                        |
| Auto    | Routes your first message to the best mode | `gemma3:1b` (router) | Inherits target mode's tools |

Each mode swaps three things: **system prompt**, **Ollama model**, and **which tools are available**.

### Key features

- **Workspace-scoped actions** — pick a folder at session start. Reads and writes inside it run automatically; destructive ops or writes outside the workspace prompt for confirmation.
- **Code-reuse scanner** — when you start a coding task, Anvil searches your existing `LocalProjects` folder (indexed via [MemPalace](https://github.com/MemPalace/mempalace)) for related snippets. You approve, it **copies** matches into the new project (never reads source folders at runtime).
- **Summary-first** — the final message of any task is a clean, stand-alone summary of what was done. Full transcript is still available.
- **Streaming** — tokens appear as the model produces them.

## Requirements

- Windows 10/11
- Python 3.11+
- [Ollama](https://ollama.com) installed and running
- ~5 GB free disk for the recommended model set

## Setup

```powershell
# 1. Clone
git clone https://github.com/Pyrolaptop/anvil.git
cd anvil

# 2. Install Python deps
pip install -r requirements.txt

# 3. Pull default models (once)
ollama pull phi3:mini
ollama pull gemma3:1b
ollama pull qwen2.5-coder:3b

# 4. Optional — install MemPalace for code reuse scanning
pip install mempalace
mempalace init C:\Users\MattL\LocalProjects
mempalace mine C:\Users\MattL\LocalProjects

# 5. Run
python -m anvil
```

## Usage

1. Launch — a single window opens with a mode selector at the top.
2. Pick your workspace folder (defaults to `C:\Users\MattL\LocalProjects`).
3. Pick a mode (or leave on **Auto**).
4. Type your task. Hit **Send**.
5. Watch it work. Approve confirmations when they pop up.
6. Read the summary.

## Project layout

```
anvil/
├── README.md
├── requirements.txt
├── .gitignore
├── build.ps1              # builds a single .exe via PyInstaller
└── anvil/
    ├── __init__.py
    ├── __main__.py        # entry point
    ├── config.py          # settings, paths, defaults
    ├── modes.py           # mode definitions (prompt + model + tools)
    ├── ollama_client.py   # streaming chat via Ollama HTTP API
    ├── agent.py           # agent loop: tool-call parsing + execution
    ├── workspace.py       # workspace scoping + safety checks
    ├── tools/
    │   ├── __init__.py
    │   ├── base.py        # Tool interface
    │   ├── filesystem.py  # read / write / list
    │   ├── shell.py       # PowerShell exec with confirm
    │   ├── web.py         # URL fetch → markdown
    │   └── code_reuse.py  # MemPalace-backed search + copy
    └── ui/
        ├── __init__.py
        ├── main_window.py
        ├── chat_widget.py
        └── confirm_dialog.py
```

## Architecture

```
┌─────────────────────────────────────────────┐
│  PySide6 UI  (chat + mode toggle)           │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  Agent loop                                 │
│  • streams tokens from Ollama               │
│  • parses tool calls from output            │
│  • executes tools (with safety checks)      │
│  • loops until model finishes with summary  │
└──────────────┬──────────────────────────────┘
               │
     ┌─────────┼──────────┬────────────┬───────────────┐
     ▼         ▼          ▼            ▼               ▼
┌─────────┐ ┌──────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│ Ollama  │ │ File │ │ Shell    │ │ Web      │ │ MemPalace    │
│ client  │ │ tool │ │ tool     │ │ fetch    │ │ code search  │
└─────────┘ └──────┘ └──────────┘ └──────────┘ └──────────────┘
```

Tool calls use a simple XML-ish protocol in the model's output so any Ollama model works, regardless of native tool-calling support:

```
<tool name="read_file">
{"path": "src/main.py"}
</tool>
```

The agent intercepts these, runs the tool, feeds the result back, and continues.

## Safety model

| Action                            | Behaviour                       |
|-----------------------------------|---------------------------------|
| Read file inside workspace        | Auto                            |
| List dir inside workspace         | Auto                            |
| Write file inside workspace       | Auto                            |
| Write file outside workspace      | Prompt                          |
| Any shell command                 | Show command, prompt            |
| Destructive command (`rm`, `rmdir`, `del`, `git push -f`, etc.) | Always prompt, even inside workspace |
| Web fetch                         | Auto                            |

## Setup log

- **2026-04-14**
  - Initial scaffold created. Folder initialised, README written up-front per project rules.
  - PySide6 6.11 + `requests` installed via `pip install -r requirements.txt`.
  - Ollama host detected on port **11435** (non-default). `config.py` defaults to that; set `OLLAMA_HOST` env var to override.
  - Models used: `phi3:mini` (ideas + general), `gemma3:1b` (auto router), `qwen2.5-coder:3b` (coding) — last pulled via `ollama pull`.
  - Repo published at https://github.com/Pyrolaptop/anvil (public, main branch).
  - MemPalace 3.2.0 installed via `pip install mempalace`. Initialised with `python -m mempalace init C:\Users\MattL\LocalProjects --yes`. Initial mine running in background.
  - Code-reuse tool uses `python -m mempalace search <query>` as a subprocess (MemPalace has no public Python search API yet); falls back to a grep scan if MemPalace is absent or returns no hits.

## Troubleshooting log

- **Ollama unreachable on port 11434** — this Windows install binds `127.0.0.1:11435` instead. Fixed by defaulting `OLLAMA_HOST` to `http://localhost:11435` in `anvil/config.py`. Override with env var if yours is different.
- **`str.format()` KeyError in tool instructions** — the tool-call template contains literal `{"arg1": "value1"}` JSON, which Python's `.format()` tries to interpret as a named field. Fixed by switching to a simple `__TOOL_LIST__` placeholder + `str.replace()`.
- **`mempalace init` hangs on stdin** — interactive by default; use `--yes` for non-interactive runs. The CLI also fails to print its help on Windows cp1252 due to a Unicode arrow; set `PYTHONIOENCODING=utf-8` when invoking via subprocess.

## Useful commands

```powershell
# Run in dev mode
python -m anvil

# Build single .exe
.\build.ps1

# Update MemPalace index (run after adding new projects)
mempalace mine C:\Users\MattL\LocalProjects

# Check which Ollama models are available
ollama list
```

## Troubleshooting log

*(empty — nothing has gone wrong yet)*

## Notes and decisions

- **PySide6 over Tkinter** — richer widgets, proper async, better chat UX. Single `.exe` via PyInstaller is still practical.
- **Prompt-based tool protocol** — works with any Ollama model (small coding-focused ones don't always support native tool calling). Simple XML-ish parsing.
- **MemPalace for code reuse** — rather than reinventing an index, use the purpose-built local semantic memory tool. Ingesting code needs no LLM (just embeddings), so indexing stays fast and light.
- **Copy, never link** — reused snippets are physically copied into the target project with a provenance comment (`# reused from <source-project>/<file>`), so source projects are never touched at runtime.
- **`qwen2.5-coder:3b`** chosen for coding mode as the sweet spot on CPU-only hardware (Intel Iris Xe, no discrete GPU). 7B is available as an opt-in for heavier work.
