from __future__ import annotations
from typing import Dict, Any
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QGroupBox,
    QFormLayout,
)

from ..config import presets


class SettingsPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._building = False
        self._init_ui()

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)

        # プリセット選択
        row = QHBoxLayout()
        row.addWidget(QLabel("プリセット:"))
        self.preset = QComboBox()
        for key in presets.keys():
            self.preset.addItem(key)
        row.addWidget(self.preset)
        row.addStretch(1)
        root.addLayout(row)

        # 詳細設定（折りたたみ）
        self.advanced = QGroupBox("詳細設定")
        self.advanced.setCheckable(True)
        self.advanced.setChecked(True)
        form = QFormLayout(self.advanced)
        self.fps = QSpinBox()
        self.fps.setRange(1, 60)
        self.width = QSpinBox()
        self.width.setRange(64, 3840)
        self.colors = QSpinBox()
        self.colors.setRange(2, 256)
        form.addRow("FPS", self.fps)
        form.addRow("幅(px)", self.width)
        form.addRow("色数", self.colors)
        root.addWidget(self.advanced)
        root.addStretch(1)

        # イベント
        self.preset.currentTextChanged.connect(self._on_preset_changed)
        self._apply_preset(self.preset.currentText())

    def _on_preset_changed(self, name: str) -> None:
        self._apply_preset(name)

    def _apply_preset(self, name: str) -> None:
        s = presets.get(name)
        if not s:
            return
        self._building = True
        try:
            self.fps.setValue(int(s["fps"]))
            self.width.setValue(int(s["width"]))
            self.colors.setValue(int(s["colors"]))
        finally:
            self._building = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preset": self.preset.currentText(),
            "fps": int(self.fps.value()),
            "width": int(self.width.value()),
            "colors": int(self.colors.value()),
        }

    def apply_dict(self, data: Dict[str, Any]) -> None:
        if not data:
            return
        preset = data.get("preset")
        if preset and preset in presets:
            self.preset.setCurrentText(preset)
        # カスタム値で上書き
        if "fps" in data:
            self.fps.setValue(int(data["fps"]))
        if "width" in data:
            self.width.setValue(int(data["width"]))
        if "colors" in data:
            self.colors.setValue(int(data["colors"]))
