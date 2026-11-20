"""清理项卡片。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QVBoxLayout
from qfluentwidgets import CaptionLabel, CardWidget, CheckBox, StrongBodyLabel

from ...core.items import RISK_LABEL
from ...core.sizes import human_size
from ..theme import category_color, palette
from .base import Badge


class CleanItemCard(CardWidget):
    toggled = Signal(str, bool)

    def __init__(self, item, parent=None) -> None:
        super().__init__(parent)
        self.item = item
        self.setMinimumHeight(78)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 18, 12)
        root.setSpacing(14)

        strip = QFrame(self)
        strip.setFixedWidth(4)
        strip.setStyleSheet(
            f"background:{category_color(item.category)};border-radius:2px;"
        )
        root.addWidget(strip)

        self.checkbox = CheckBox(self)
        self.checkbox.setChecked(item.default_selected)
        self.checkbox.stateChanged.connect(
            lambda _s: self.toggled.emit(self.item.key, self.checkbox.isChecked())
        )
        root.addWidget(self.checkbox, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(4)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        label = StrongBodyLabel(item.label, self)
        name_row.addWidget(label)
        kind = {"safe": "safe", "normal": "normal", "high": "high"}[item.risk]
        name_row.addWidget(Badge(RISK_LABEL[item.risk], kind, self))
        if item.requires_admin:
            name_row.addWidget(Badge("需管理员", "info", self))
        blocked = getattr(item, "blocked_by", ())
        if blocked:
            text = "需关闭 " + "、".join(blocked[:2]) + ("…" if len(blocked) > 2 else "")
            badge = Badge(text, "normal", self)
            badge.setToolTip("、".join(blocked))
            name_row.addWidget(badge)
        name_row.addStretch(1)
        col.addLayout(name_row)

        desc = CaptionLabel(item.desc, self)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{palette()['sub']};")
        col.addWidget(desc)

        root.addLayout(col, 1)

        self.size_label = StrongBodyLabel("未统计", self)
        self.size_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.size_label.setMinimumWidth(104)
        root.addWidget(self.size_label, 0, Qt.AlignVCenter)

    def set_size_text(self, text: str, is_error: bool = False) -> None:
        self.size_label.setText(text)
        self.size_label.setStyleSheet(
            f"color:{palette()['danger'] if is_error else palette()['accent']};"
            "font-weight:600;"
        )

    def set_checked(self, value: bool) -> None:
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(bool(value))
        self.checkbox.blockSignals(False)

    def set_locked(self, locked: bool) -> None:
        """未激活时禁止勾选。"""
        self.checkbox.setEnabled(not locked)
        if locked:
            self.set_checked(False)
