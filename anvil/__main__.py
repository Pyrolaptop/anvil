"""Entry point: `python -m anvil`."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from anvil.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Anvil")
    app.setOrganizationName("MysticLab")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
