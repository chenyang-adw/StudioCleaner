"""提示横幅（含锁定提示）。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, FluentIcon as FIF, PrimaryPushButton, StrongBodyLabel

from ..theme import palette


class Banner(QWidget):
    """带边框与图标的状态横幅。"""

    action_clicked = Signal()

    def __init__(self, title: str, detail: str = "", kind: str = "warn",
                 action_text: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._kind = kind

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        self.icon = QLabel(self)
        self.icon.setFixedSize(30, 30)
        self.icon.setAlignment(Qt.AlignCenter)
        root.addWidget(self.icon, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(2)
        self.title = StrongBodyLabel(title, self)
        col.addWidget(self.title)
        self.detail = CaptionLabel(detail, self)
        self.detail.setWordWrap(True)
        col.addWidget(self.detail)
        root.addLayout(col, 1)

        self.action_btn = PrimaryPushButton(action_text or "去处理", self)
        self.action_btn.clicked.connect(self.action_clicked.emit)
        if not action_text:
            self.action_btn.hide()
        root.addWidget(self.action_btn, 0, Qt.AlignVCenter)

        self._restyle()

    COLOR = {
        "warn": ("#F59E0B", "FIF.INFO"),
        "lock": ("#EF4444", "FIF.INFO"),
        "ok": ("#22C55E", "FIF.ACCEPT"),
        "info": ("#4C6FFF", "FIF.INFO"),
    }

    def _restyle(self) -> None:
        color, _icon = self.COLOR.get(self._kind, self.COLOR["info"])
        p = palette()
        self.setStyleSheet(
            f"Banner{{background:{p['surface_2']};border:1px solid {color}55;"
            f"border-radius:12px;}}"
        )
        self.icon.setText("!")
        self.icon.setStyleSheet(
            f"QLabel{{color:{color};background:{color}22;border-radius:15px;"
            f"font-size:16px;font-weight:700;}}"
        )
        self.title.setStyleSheet(f"color:{p['text']};")
        self.detail.setStyleSheet(f"color:{p['sub']};")

    def set_action_text(self, text: str) -> None:
        self.action_btn.setText(text)
        self.action_btn.setVisible(bool(text))

    def set_detail(self, text: str) -> None:
        self.detail.setText(text)
