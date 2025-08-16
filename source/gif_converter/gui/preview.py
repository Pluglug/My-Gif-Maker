from __future__ import annotations
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtGui import QMovie

from PIL import Image
from PIL import ImageQt as PilImageQt


class PreviewWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        row = QHBoxLayout()
        self.label_src = QLabel("元動画プレビュー")
        self.label_src.setAlignment(Qt.AlignCenter)
        self.label_dst = QLabel("GIFプレビュー")
        self.label_dst.setAlignment(Qt.AlignCenter)
        self.label_dst.setMinimumWidth(200)
        row.addWidget(self.label_src, 1)
        row.addWidget(self.label_dst, 1)
        root.addLayout(row)

        self._movie: Optional[QMovie] = None

    def show_source_png(self, png_path: Path) -> None:
        if not png_path.exists():
            self.label_src.setText("プレビュー画像がありません")
            return
        try:
            im = Image.open(str(png_path))
            qim = PilImageQt.ImageQt(im.convert("RGBA"))
            pix = QPixmap.fromImage(qim)
            self.label_src.setPixmap(pix.scaled(
                self.label_src.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        except Exception:
            self.label_src.setText("プレビュー読み込み失敗")

    def resizeEvent(self, e) -> None:  # type: ignore[override]
        # サイズが変わったらリスケール
        if pix := self.label_src.pixmap():
            self.label_src.setPixmap(pix.scaled(
                self.label_src.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        super().resizeEvent(e)

    def show_gif(self, gif_path: Path) -> None:
        if self._movie:
            self._movie.stop()
            self._movie.deleteLater()
            self._movie = None
        if not gif_path.exists():
            self.label_dst.setText("GIFがありません")
            return
        self._movie = QMovie(str(gif_path))
        self.label_dst.setMovie(self._movie)
        self._movie.start()
