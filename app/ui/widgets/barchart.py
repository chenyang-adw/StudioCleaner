"""横向条形图：展示占用最大的若干清理项。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, StrongBodyLabel

from ..theme import category_color, palette


class BarRow(QWidget):
    def __init__(self, name: str, value_text: str, ratio: float, color: str, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 4)
        root.setSpacing(5)

        head = QHBoxLayout()
        head.setSpacing(8)
        dot = QLabel(self)
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background:{color};border-radius:4px;")
        head.addWidget(dot)
        head.addWidget(StrongBodyLabel(name, self))
        head.addStretch(1)
        val = CaptionLabel(value_text, self)
        val.setStyleSheet(f"color:{palette()['sub']};")
        head.addWidget(val)
        root.addLayout(head)

        bar = QProgressBar(self)
        bar.setRange(0, 1000)
        bar.setValue(int(max(0.0, min(1.0, ratio)) * 1000))
        bar.setTextVisible(False)
        bar.setFixedHeight(7)
        bar.setStyleSheet(
            "QProgressBar{background:transparent;border:none;}"
            f"QProgressBar::chunk{{background:{color};border-radius:3px;}}"
        )
        root.addWidget(bar)


class BarChart(QWidget):
    """根据 (名称, 字节, 分类) 列表渲染条形图。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(6)

    def set_data(self, rows: list[tuple[str, int, str, str]], empty_text: str = "暂无数据") -> None:
        while self._root.count():
            item = self._root.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.hide()
                w.deleteLater()
        if not rows:
            tip = CaptionLabel(empty_text, self)
            tip.setStyleSheet(f"color:{palette()['sub']};")
            self._root.addWidget(tip)
            return
        top = max(r[1] for r in rows) or 1
        for name, size, category, value_text in rows:
            self._root.addWidget(BarRow(name, value_text, size / top, category_color(category), self))
