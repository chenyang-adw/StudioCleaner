"""基础组件：页面骨架、徽标、统计卡片、分区卡片。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    IconWidget,
    ScrollArea,
    StrongBodyLabel,
    SubtitleLabel,
    setFont,
)

from ..theme import ACCENT, palette
from .icontile import IconTile


class Badge(QLabel):
    """圆角小徽标。"""

    COLORS = {
        "safe": ("#16A34A", "#E7F8EE"),
        "normal": ("#D97706", "#FDF3E3"),
        "high": ("#DC2626", "#FDECEC"),
        "info": ("#4C6FFF", "#E9EEFF"),
        "muted": ("#6B7280", "#EEF1F6"),
    }

    def __init__(self, text: str, kind: str = "muted", parent=None) -> None:
        super().__init__(text, parent)
        fg, bg = self.COLORS.get(kind, self.COLORS["muted"])
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            f"QLabel{{color:{fg};background:{bg};border-radius:9px;"
            f"padding:2px 9px;font-size:11px;font-weight:600;}}"
        )
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)


class StatCard(CardWidget):
    """图标块 + 标题 + 大数值 + 说明。"""

    def __init__(self, icon, title: str, value: str = "-", hint: str = "",
                 color: str = ACCENT, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(112)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        self.tile = IconTile(icon, color, 44, self)
        root.addWidget(self.tile, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(3)
        self.title_label = CaptionLabel(title, self)
        col.addWidget(self.title_label)
        self.value_label = QLabel(value, self)
        f = QFont()
        f.setPointSize(21)
        f.setBold(True)
        self.value_label.setFont(f)
        col.addWidget(self.value_label)
        self.hint_label = CaptionLabel(hint, self)
        self.hint_label.setWordWrap(True)
        self.hint_label.setMinimumWidth(0)
        col.addWidget(self.hint_label)
        root.addLayout(col, 1)

        self._apply()

    def _apply(self) -> None:
        p = palette()
        self.value_label.setStyleSheet(f"color:{p['text']};")
        self.title_label.setStyleSheet(f"color:{p['sub']};")
        self.hint_label.setStyleSheet(f"color:{p['sub']};")

    def set_value(self, value: str, hint: str = "") -> None:
        self.value_label.setText(value)
        if hint:
            self.hint_label.setText(hint)
        self._apply()


class SectionCard(CardWidget):
    """带标题的分区卡片，内部提供 content 布局。"""

    def __init__(self, title: str, subtitle: str = "", icon=None, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(8)
        if icon is not None:
            iw = IconWidget(icon, self)
            iw.setFixedSize(18, 18)
            head.addWidget(iw)
        head.addWidget(StrongBodyLabel(title, self))
        head.addStretch(1)
        self.header_extra = QWidget(self)
        self.header_extra_layout = QHBoxLayout(self.header_extra)
        self.header_extra_layout.setContentsMargins(0, 0, 0, 0)
        self.header_extra_layout.setSpacing(8)
        head.addWidget(self.header_extra)
        outer.addLayout(head)

        if subtitle:
            sub = CaptionLabel(subtitle, self)
            sub.setWordWrap(True)
            outer.addWidget(sub)

        self.content = QWidget(self)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        outer.addWidget(self.content)


class Page(QWidget):
    """统一页面骨架：浅色渐变背景 + 标题 + 可滚动内容区。"""

    def __init__(self, title: str, subtitle: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(f"page_{abs(hash(title))}")
        self.setAttribute(Qt.WA_StyledBackground, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        head = QVBoxLayout()
        head.setSpacing(2)
        self.title_label = SubtitleLabel(title, self)
        setFont(self.title_label, 22, QFont.DemiBold)
        self.title_label.setStyleSheet(f"color:{palette()['text']};")
        head.addWidget(self.title_label)
        if subtitle:
            sub = BodyLabel(subtitle, self)
            sub.setStyleSheet(f"color:{palette()['sub']};")
            head.addWidget(sub)
        root.addLayout(head)

        self.scroll = ScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.enableTransparentBackground()
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 4, 8, 24)
        self.body_layout.setSpacing(14)
        self.scroll.setWidget(self.body)
        root.addWidget(self.scroll, 1)

    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        self.body_layout.addWidget(widget, stretch)

    def add_layout(self, layout) -> None:
        self.body_layout.addLayout(layout)

    def add_stretch(self) -> None:
        self.body_layout.addStretch(1)

    def refresh_theme(self) -> None:
        for child in self.findChildren(Badge):
            child.style().unpolish(child)
            child.style().polish(child)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 0, max(1, self.height()))
        grad.setColorAt(0.0, QColor(p["page_from"]))
        grad.setColorAt(1.0, QColor(p["page_to"]))
        painter.fillRect(self.rect(), grad)
        painter.end()
        super().paintEvent(event)
