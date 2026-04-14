"""Modal confirmation dialog for destructive or out-of-scope actions."""
from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from anvil.tools.base import ConfirmationRequest


def ask_user(parent: QWidget, request: ConfirmationRequest) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("Anvil — confirm action")
    box.setText(request.prompt)
    if request.detail:
        box.setInformativeText(request.detail)
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.setDefaultButton(QMessageBox.No)
    return box.exec() == QMessageBox.Yes
