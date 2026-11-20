"""渐变主视觉卡片。"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..theme import palette


class HeroCard(QWidget):
    """圆角渐变背景容器，子控件通过 left_layout / right_layout 添加。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(196)

        root = QHBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(20)

        self.left = QVBoxLayout()
        self.left.setSpacing(6)
        root.addLayout(self.left, 3)

        self.right = QVBoxLayout()
        self.right.setSpacing(10)
        root.addLayout(self.right, 2)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path.addRoundedRect(rect, 16, 16)
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(p["hero_from"]))
        grad.setColorAt(1.0, QColor(p["hero_to"]))
        painter.fillPath(path, grad)

        # 右上角装饰光斑（浅色主题下用白色柔光）
        glow = QLinearGradient(rect.right() - 240, rect.top(), rect.right(), rect.top() + 200)
        glow.setColorAt(0.0, QColor(255, 255, 255, 0))
        glow.setColorAt(1.0, QColor(255, 255, 255, 60))
        painter.fillPath(path, glow)

        # 描边
        painter.setPen(QColor(p["hero_btn_border"]))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 16, 16)
        painter.end()
