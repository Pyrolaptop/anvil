"""URL fetch → plain-text."""
from __future__ import annotations

import re

import requests

from anvil.tools.base import ToolResult


MAX_BYTES = 300_000


class FetchUrlTool:
    name = "fetch_url"
    description = 'Fetch a URL and return its text content. Args: {"url": "https://..."}'

    def run(self, args, workspace, approve):
        url = args.get("url", "").strip()
        if not url:
            return ToolResult(False, "Missing 'url' argument.")
        if not url.startswith(("http://", "https://")):
            return ToolResult(False, "URL must start with http:// or https://")

        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Anvil/0.1"})
            if r.status_code != 200:
                return ToolResult(False, f"HTTP {r.status_code}")
            content = r.text[:MAX_BYTES]
            text = _html_to_text(content) if "html" in r.headers.get("content-type", "").lower() else content
            return ToolResult(True, text)
        except requests.RequestException as e:
            return ToolResult(False, f"Fetch error: {e}")


def _html_to_text(html: str) -> str:
    # Strip scripts, styles, tags — keep text.
    html = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", "", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()
