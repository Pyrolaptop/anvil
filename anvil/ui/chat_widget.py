"""Chat transcript widget — scrollable, supports streaming into the last block."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit


class ChatView(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAcceptRichText(True)
        self._streaming_anchor: int | None = None
        self.document().setDefaultStyleSheet(
            "p { margin: 4px 0; }"
            ".user { color: #a3e635; }"
            ".assistant { color: #e5e7eb; }"
            ".sys { color: #64748b; font-style: italic; }"
            ".tool { color: #60a5fa; font-family: Consolas, monospace; font-size: 0.9em; }"
            ".result { color: #a78bfa; font-family: Consolas, monospace; font-size: 0.9em; }"
            ".error { color: #f87171; }"
            "pre { background: #1f2937; padding: 6px; border-radius: 4px; }"
        )

    def _append_html(self, html: str) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(html)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def add_user(self, text: str) -> None:
        self._append_html(f'<p class="user"><b>You:</b> {_escape(text)}</p>')

    def add_system(self, text: str) -> None:
        self._append_html(f'<p class="sys">{_escape(text)}</p>')

    def add_tool_call(self, text: str) -> None:
        self._append_html(f'<p class="tool">→ {_escape(text)}</p>')

    def add_tool_result(self, text: str) -> None:
        snippet = text if len(text) < 600 else text[:600] + " …"
        self._append_html(f'<pre class="result">{_escape(snippet)}</pre>')

    def add_error(self, text: str) -> None:
        self._append_html(f'<p class="error"><b>Error:</b> {_escape(text)}</p>')

    def begin_assistant(self) -> None:
        self._append_html('<p class="assistant"><b>Anvil:</b> </p>')
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._streaming_anchor = cursor.position()

    def stream_assistant_token(self, token: str) -> None:
        if self._streaming_anchor is None:
            self.begin_assistant()
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(token)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def end_assistant(self) -> None:
        self._streaming_anchor = None
        self._append_html("")


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )
