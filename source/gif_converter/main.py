from __future__ import annotations
import sys
from PyQt5.QtWidgets import QApplication
from .gui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("MP4 to GIF Converter")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
