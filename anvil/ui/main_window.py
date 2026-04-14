"""Main Anvil window."""
from __future__ import annotations

from pathlib import Path

import threading

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from anvil.agent import Agent, AgentEvent
from anvil.config import Settings
from anvil.modes import MODES
from anvil.tools.base import ConfirmationRequest
from anvil.ui.chat_widget import ChatView
from anvil.ui.confirm_dialog import ask_user
from anvil.workspace import Workspace


class AgentWorker(QObject):
    event = Signal(object)          # AgentEvent
    confirm_needed = Signal(object) # ConfirmationRequest
    finished = Signal()

    def __init__(self, agent_factory, mode_key: str, message: str, history: list[dict]):
        super().__init__()
        self.agent_factory = agent_factory
        self.mode_key = mode_key
        self.message = message
        self.history = history
        self._confirm_event = threading.Event()
        self._confirm_result = False

    def approve(self, request: ConfirmationRequest) -> bool:
        self._confirm_event.clear()
        self._confirm_result = False
        self.confirm_needed.emit(request)
        self._confirm_event.wait()
        return self._confirm_result

    @Slot(bool)
    def receive_confirmation(self, result: bool):
        self._confirm_result = result
        self._confirm_event.set()

    @Slot()
    def run(self):
        try:
            agent = self.agent_factory(self.approve)
            for ev in agent.run(self.mode_key, self.message, self.history):
                self.event.emit(ev)
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings.load()
        self.setWindowTitle("Anvil")
        self.resize(960, 720)
        self.setStyleSheet("background: #0f172a; color: #e5e7eb;")

        self.history: list[dict] = []
        self._thread: QThread | None = None
        self._worker: AgentWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top bar
        top = QHBoxLayout()
        top.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        for key, mode in MODES.items():
            self.mode_combo.addItem(mode.label, key)
        idx = self.mode_combo.findData(self.settings.default_mode)
        self.mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        top.addWidget(self.mode_combo)

        top.addSpacing(16)
        top.addWidget(QLabel("Workspace:"))
        self.workspace_label = QLabel(self.settings.workspace)
        self.workspace_label.setStyleSheet("color: #94a3b8;")
        top.addWidget(self.workspace_label, 1)
        self.pick_btn = QPushButton("Change…")
        self.pick_btn.clicked.connect(self.pick_workspace)
        top.addWidget(self.pick_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_chat)
        top.addWidget(self.clear_btn)
        layout.addLayout(top)

        # Chat
        self.chat = ChatView()
        self.chat.setStyleSheet("background: #0b1220; border: 1px solid #1e293b; border-radius: 6px; padding: 8px;")
        layout.addWidget(self.chat, 1)

        # Input
        bottom = QHBoxLayout()
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("Describe the task… (Ctrl+Enter to send)")
        self.input.setFixedHeight(90)
        self.input.setStyleSheet("background: #0b1220; border: 1px solid #1e293b; border-radius: 6px; padding: 6px;")
        bottom.addWidget(self.input, 1)
        self.send_btn = QPushButton("Send")
        self.send_btn.setFixedWidth(90)
        self.send_btn.setStyleSheet("background: #2563eb; color: white; padding: 8px; border-radius: 4px;")
        self.send_btn.clicked.connect(self.send)
        bottom.addWidget(self.send_btn)
        layout.addLayout(bottom)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        # Ctrl+Enter to send
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self.send)

        self.chat.add_system(
            "Anvil v0.1 — local AI assistant. Pick a mode, describe a task, press Ctrl+Enter."
        )

    def pick_workspace(self):
        folder = QFileDialog.getExistingDirectory(self, "Pick workspace", self.settings.workspace)
        if folder:
            self.settings.workspace = folder
            self.settings.save()
            self.workspace_label.setText(folder)

    def clear_chat(self):
        self.history.clear()
        self.chat.clear()
        self.chat.add_system("Chat cleared.")

    def send(self):
        message = self.input.toPlainText().strip()
        if not message:
            return
        if self._thread is not None and self._thread.isRunning():
            return

        try:
            workspace = Workspace(self.settings.workspace)
        except ValueError as e:
            self.chat.add_error(str(e))
            return

        mode_key = self.mode_combo.currentData()
        self.settings.default_mode = mode_key
        self.settings.save()

        self.input.clear()
        self.chat.add_user(message)
        self.send_btn.setEnabled(False)
        self.statusBar().showMessage(f"Running in {MODES[mode_key].label} mode…")

        def agent_factory(approve):
            return Agent(workspace, approve=approve)

        self._thread = QThread()
        self._worker = AgentWorker(agent_factory, mode_key, message, list(self.history))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.event.connect(self.on_event)
        self._worker.confirm_needed.connect(self.on_confirm_needed)
        self._worker.finished.connect(self.on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._pending_user_msg = message
        self._assistant_accumulator = ""
        self.chat.begin_assistant()
        self._thread.start()

    @Slot(object)
    def on_confirm_needed(self, request: ConfirmationRequest):
        result = ask_user(self, request)
        if self._worker is not None:
            self._worker.receive_confirmation(result)

    @Slot(object)
    def on_event(self, ev: AgentEvent):
        if ev.kind == "token":
            self._assistant_accumulator += ev.data
            self.chat.stream_assistant_token(ev.data)
        elif ev.kind == "mode_routed":
            self.chat.end_assistant()
            self.chat.add_system(f"Auto → routed to {ev.data.upper()} mode")
            self.chat.begin_assistant()
            self._assistant_accumulator = ""
        elif ev.kind == "tool_call":
            self.chat.end_assistant()
            self.chat.add_tool_call(ev.data)
        elif ev.kind == "tool_result":
            self.chat.add_tool_result(ev.data)
            self.chat.begin_assistant()
            self._assistant_accumulator = ""
        elif ev.kind == "error":
            self.chat.end_assistant()
            self.chat.add_error(ev.data)
        elif ev.kind == "done":
            self.chat.end_assistant()

    @Slot()
    def on_finished(self):
        self.send_btn.setEnabled(True)
        self.statusBar().showMessage("Ready")
        # Only store the last user + final assistant text in history (keeps context small)
        if hasattr(self, "_pending_user_msg") and self._assistant_accumulator.strip():
            self.history.append({"role": "user", "content": self._pending_user_msg})
            self.history.append({"role": "assistant", "content": self._assistant_accumulator})
            # Cap history to last 12 messages
            if len(self.history) > 12:
                self.history = self.history[-12:]
        self._thread = None
        self._worker = None
