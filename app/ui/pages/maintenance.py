"""系统维护：常见修复动作（演示数据）。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    ProgressBar,
    SegmentedWidget,
    StrongBodyLabel,
)

from ...demo_data import MAINTENANCE_ACTIONS
from ..theme import ACCENT, SUCCESS, WARNING, palette
from ..widgets.base import Badge, Page, SectionCard
from ..widgets.buttons import GradientButton, OutlineButton
from ..widgets.icontile import IconTile


class MaintenanceCard(CardWidget):
    run_requested = Signal(str)

    def __init__(self, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.data = data
        self.setMinimumHeight(132)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(12)

        icon = getattr(FIF, data.get("icon", "SYNC"), FIF.SYNC)
        row.addWidget(IconTile(icon, ACCENT if data["category"] == "系统修复" else "#0891B2",
                               40, self), 0, Qt.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(7)
        head.addWidget(StrongBodyLabel(data["title"], self))
        if data.get("admin"):
            head.addWidget(Badge("需管理员", "info", self))
        head.addStretch(1)
        col.addLayout(head)

        desc = CaptionLabel(data["desc"], self)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{palette()['sub']};")
        col.addWidget(desc)

        meta = CaptionLabel(f"{data['category']} · 预计 {data['time']}", self)
        meta.setStyleSheet(f"color:{palette()['muted']};font-size:11px;")
        col.addWidget(meta)
        row.addLayout(col, 1)

        btn = OutlineButton("执行", self)
        btn.setMinimumHeight(32)
        btn.clicked.connect(lambda: self.run_requested.emit(data["title"]))
        row.addWidget(btn, 0, Qt.AlignVCenter)


class MaintenancePage(Page):
    def __init__(self, parent=None) -> None:
        super().__init__("系统维护", "修复、重建与网络重置（演示数据）", parent)
        self._filter = "全部"
        self._cards: list[MaintenanceCard] = []
        self.add_widget(self._build_health())
        self.add_widget(self._build_toolbar())
        self.add_widget(self._build_grid())
        self.add_stretch()

    def _build_health(self) -> QWidget:
        card = SectionCard("系统健康", "演示评分：按启动项、缓存、系统文件与网络状态估算", FIF.INFO)
        row = QHBoxLayout()
        row.setSpacing(18)
        score = QLabel("92", card)
        score.setStyleSheet(f"color:{ACCENT};font-size:44px;font-weight:700;")
        row.addWidget(score, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(6)
        col.addWidget(StrongBodyLabel("整体状态良好", card))
        tip = CaptionLabel("2 项建议处理：Windows 更新缓存偏大、搜索索引较旧", card)
        tip.setStyleSheet(f"color:{palette()['sub']};")
        col.addWidget(tip)
        bar = ProgressBar(card)
        bar.setValue(92)
        bar.setFixedHeight(8)
        col.addWidget(bar)
        row.addLayout(col, 1)

        btn = GradientButton("一键修复建议项", card)
        btn.clicked.connect(lambda: InfoBar.success("演示模式", "正式版会依次执行 SFC / 搜索索引 / 缓存重建",
                                                    parent=self, position=InfoBarPosition.TOP_RIGHT,
                                                    duration=3000))
        row.addWidget(btn, 0, Qt.AlignVCenter)
        card.content_layout.addLayout(row)
        return card

    def _build_toolbar(self) -> QWidget:
        card = SectionCard("维护动作", "11 项常用修复；执行前会提示管理员权限与预计耗时", FIF.SYNC)
        self.seg = SegmentedWidget()
        for key in ("全部", "系统修复", "搜索与界面", "网络连接"):
            self.seg.addItem(key, key)
        self.seg.setCurrentItem("全部")
        self.seg.currentItemChanged.connect(self._on_filter)
        card.content_layout.addWidget(self.seg)
        return card

    def _build_grid(self) -> QWidget:
        card = SectionCard("可执行动作", "每项可单独执行；正式版会显示进度与日志", FIF.SYNC)
        host = QWidget(card)
        self.grid = QGridLayout(host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(10)
        for index, data in enumerate(MAINTENANCE_ACTIONS):
            widget = MaintenanceCard(data, host)
            widget.run_requested.connect(self._run)
            self.grid.addWidget(widget, index // 2, index % 2)
            self._cards.append(widget)
        card.content_layout.addWidget(host)
        return card

    def _on_filter(self, key: str) -> None:
        self._filter = key
        for card in self._cards:
            card.setVisible(key == "全部" or card.data["category"] == key)

    def _run(self, title: str) -> None:
        InfoBar.info("已加入队列（演示）", f"{title}：正式版会显示进度与日志", parent=self,
                     position=InfoBarPosition.TOP_RIGHT, duration=2800)
