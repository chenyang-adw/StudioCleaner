"""圆角着色图标块。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel
from qfluentwidgets import FluentIconBase, IconWidget


class IconTile(QLabel):
    """带底色圆角方块的图标，用于统计卡片与列表。"""

    def __init__(self, icon, color: str = "#4C6FFF", size: int = 42, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = color
        self._apply_bg()
        inner = IconWidget(icon, self)
        inner.setFixedSize(int(size * 0.52), int(size * 0.52))
        inner.move((size - inner.width()) // 2, (size - inner.height()) // 2)

    def _apply_bg(self) -> None:
        c = QColor(self._color)
        self.setStyleSheet(
            f"QLabel{{background:rgba({c.red()},{c.green()},{c.blue()},38);"
            f"border-radius:{self.width() // 3}px;}}"
        )
        for child in self.findChildren(IconWidget):
            child.setStyleSheet(f"background:transparent;color:{self._color};")

    def set_color(self, color: str) -> None:
        self._color = color
        self._apply_bg()
