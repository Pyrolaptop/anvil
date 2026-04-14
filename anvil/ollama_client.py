"""Ollama HTTP client with streaming."""
from __future__ import annotations

import json
import threading
from collections.abc import Iterator

import requests

from anvil.config import OLLAMA_HOST


class OllamaError(RuntimeError):
    pass


def stream_chat(
    model: str,
    messages: list[dict],
    *,
    host: str = OLLAMA_HOST,
    options: dict | None = None,
    stop_event: threading.Event | None = None,
) -> Iterator[str]:
    """Yield response chunks from Ollama /api/chat. Aborts promptly if stop_event is set."""
    url = f"{host}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": options or {},
    }
    try:
        # (connect_timeout, read_timeout) — read timeout is per-chunk, not total.
        # Streaming tokens from Ollama resets the timer each chunk, so 120 s
        # between chunks is plenty even on slow CPU inference.
        with requests.post(url, json=payload, stream=True, timeout=(10, 120)) as r:
            if r.status_code != 200:
                raise OllamaError(f"HTTP {r.status_code}: {r.text[:400]}")
            for raw in r.iter_lines(decode_unicode=True):
                if stop_event is not None and stop_event.is_set():
                    r.close()
                    return
                if not raw:
                    continue
                try:
                    chunk = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]
                if chunk.get("done"):
                    break
    except requests.ConnectionError as e:
        raise OllamaError(
            f"Could not reach Ollama at {host}. Is the Ollama service running?"
        ) from e


def list_models(host: str = OLLAMA_HOST) -> list[str]:
    try:
        r = requests.get(f"{host}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except requests.RequestException:
        return []


def model_available(name: str, host: str = OLLAMA_HOST) -> bool:
    available = list_models(host)
    return any(m == name or m.startswith(f"{name}:") or name == m.split(":")[0] for m in available)
