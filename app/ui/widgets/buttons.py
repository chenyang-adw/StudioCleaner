"""统一风格按钮：描边 / 渐变 / 柔和。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from ..theme import gradient_button_qss, outline_button_qss, soft_button_qss


class _Base(QPushButton):
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(36)
        self.refresh_style()

    def refresh_style(self) -> None:
        raise NotImplementedError


class OutlineButton(_Base):
    """白底 + 描边，用于次要操作。"""

    def refresh_style(self) -> None:
        self.setStyleSheet(outline_button_qss())


class GradientButton(_Base):
    """渐变填充，用于主操作。"""

    def refresh_style(self) -> None:
        self.setStyleSheet(gradient_button_qss())


class SoftButton(_Base):
    """浅底强调色文字，用于轻量操作。"""

    def refresh_style(self) -> None:
        self.setStyleSheet(soft_button_qss())


def restyle_all(widget) -> None:
    for cls in (OutlineButton, GradientButton, SoftButton):
        for btn in widget.findChildren(cls):
            btn.refresh_style()
