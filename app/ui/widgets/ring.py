"""环形占比图。"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..theme import palette


class RingChart(QWidget):
    """磁盘占用环形图。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(170, 170)
        self._ratio = 0.0
        self._center_text = "-"
        self._sub_text = ""

    def set_ratio(self, ratio: float, center: str, sub: str = "") -> None:
        self._ratio = max(0.0, min(1.0, float(ratio)))
        self._center_text = center
        self._sub_text = sub
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height()) - 18
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        thickness = max(10, int(side * 0.085))

        pen = QPen(QColor(p["ring_track"]), thickness)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect.adjusted(thickness / 2, thickness / 2, -thickness / 2, -thickness / 2),
                        0, 360 * 16)

        if self._ratio > 0:
            color = QColor(p["accent"])
            if self._ratio >= 0.9:
                color = QColor(p["danger"])
            elif self._ratio >= 0.75:
                color = QColor(p["warning"])
            pen.setColor(color)
            painter.setPen(pen)
            span = int(-360 * 16 * self._ratio)
            painter.drawArc(rect.adjusted(thickness / 2, thickness / 2, -thickness / 2, -thickness / 2),
                            90 * 16, span)

        f = QFont()
        f.setPointSize(max(12, int(side * 0.13)))
        f.setBold(True)
        painter.setFont(f)
        painter.setPen(QColor(p["text"]))
        painter.drawText(rect, Qt.AlignCenter, self._center_text)

        if self._sub_text:
            f2 = QFont()
            f2.setPointSize(max(8, int(side * 0.065)))
            painter.setFont(f2)
            painter.setPen(QColor(p["sub"]))
            painter.drawText(rect.adjusted(0, side * 0.26, 0, 0), Qt.AlignHCenter | Qt.AlignTop,
                             self._sub_text)
        painter.end()
