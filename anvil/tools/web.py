"""Web tools: URL fetch + DuckDuckGo search."""
from __future__ import annotations

import html
import re
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

import requests

from anvil.tools.base import ToolResult


MAX_BYTES = 300_000           # raw HTML budget before stripping
MAX_TEXT_OUT = 20_000         # what we actually return to the model
UA = "Mozilla/5.0 (compatible; Anvil/0.1)"


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
            r = requests.get(url, timeout=15, headers={"User-Agent": UA})
            if r.status_code != 200:
                return ToolResult(False, f"HTTP {r.status_code}")
            content = r.text[:MAX_BYTES]
            is_html = "html" in r.headers.get("content-type", "").lower()
            text = _html_to_text(content) if is_html else content
            if len(text) > MAX_TEXT_OUT:
                text = text[:MAX_TEXT_OUT] + f"\n\n[... truncated, {len(text) - MAX_TEXT_OUT} chars omitted]"
            return ToolResult(True, text)
        except requests.RequestException as e:
            return ToolResult(False, f"Fetch error: {e}")


class WebSearchTool:
    name = "web_search"
    description = (
        'Search the web via DuckDuckGo and return the top results as a list of '
        '{title, url, snippet}. Use this BEFORE fetch_url to find real URLs — '
        'never invent URLs. Args: {"query": "what to search for"}'
    )

    def run(self, args, workspace, approve):
        query = (args.get("query") or "").strip()
        if not query:
            return ToolResult(False, "Missing 'query' argument.")

        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": UA})
            if r.status_code != 200:
                return ToolResult(False, f"HTTP {r.status_code}")
        except requests.RequestException as e:
            return ToolResult(False, f"Search error: {e}")

        results = _parse_ddg(r.text, limit=6)
        if not results:
            return ToolResult(True, "(no results)")
        lines = []
        for i, hit in enumerate(results, 1):
            lines.append(f"{i}. {hit['title']}\n   {hit['url']}\n   {hit['snippet']}")
        return ToolResult(True, "\n\n".join(lines))


def _parse_ddg(html_text: str, limit: int = 6) -> list[dict]:
    # DuckDuckGo HTML result blocks.
    block_re = re.compile(
        r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
        r'[\s\S]*?<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        re.I,
    )
    results = []
    for m in block_re.finditer(html_text):
        href, title_html, snippet_html = m.group(1), m.group(2), m.group(3)
        real_url = _unwrap_ddg(href)
        results.append({
            "title": _strip_tags(title_html),
            "url": real_url,
            "snippet": _strip_tags(snippet_html),
        })
        if len(results) >= limit:
            break
    return results


def _unwrap_ddg(href: str) -> str:
    # DDG wraps redirects like //duckduckgo.com/l/?uddg=<encoded>
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        qs = parse_qs(parsed.query)
        inner = qs.get("uddg", [None])[0]
        if inner:
            return unquote(inner)
    return href


def _strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def _html_to_text(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
