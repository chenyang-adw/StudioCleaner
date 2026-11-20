"""启动项管理：服务、注册表、计划任务、启动文件夹（演示数据）。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    CheckBox,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    SegmentedWidget,
    StrongBodyLabel,
    SwitchButton,
)

from ...demo_data import STARTUP_ITEMS
from ..theme import ACCENT, SUCCESS, WARNING, palette
from ..widgets.base import Badge, Page, SectionCard, StatCard
from ..widgets.buttons import OutlineButton
from ..widgets.icontile import IconTile


class StartupRow(CardWidget):
    toggled = Signal(str, bool)

    def __init__(self, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.data = data
        self.setMinimumHeight(78)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 16, 10)
        row.setSpacing(12)

        color = {"服务": "#0EA5E9", "注册表": "#4C6FFF", "计划任务": "#8B5CF6",
                 "启动文件夹": "#10B981", "残留": "#DC2626"}.get(data["type"], ACCENT)
        row.addWidget(IconTile(FIF.SPEED_HIGH, color, 38, self), 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(3)
        name_row = QHBoxLayout()
        name_row.setSpacing(7)
        name_row.addWidget(StrongBodyLabel(data["name"], self))
        name_row.addWidget(Badge(data["type"], "info", self))
        impact = data["impact"]
        name_row.addWidget(Badge(f"影响 {impact}", "high" if impact == "高" else
                                 ("normal" if impact == "中" else "muted"), self))
        name_row.addStretch(1)
        col.addLayout(name_row)
        desc = CaptionLabel(data["desc"], self)
        desc.setStyleSheet(f"color:{palette()['sub']};")
        col.addWidget(desc)
        path = CaptionLabel(data["path"], self)
        path.setStyleSheet(f"color:{palette()['muted']};font-size:11px;")
        col.addWidget(path)
        row.addLayout(col, 1)

        self.switch = SwitchButton(self)
        self.switch.setOnText("开")
        self.switch.setOffText("关")
        self.switch.setChecked(bool(data["enabled"]))
        self.switch.checkedChanged.connect(self._on_toggle)
        row.addWidget(self.switch, 0, Qt.AlignVCenter)

    def _on_toggle(self, checked: bool) -> None:
        self.data["enabled"] = bool(checked)
        self.toggled.emit(self.data["name"], bool(checked))


class StartupPage(Page):
    def __init__(self, parent=None) -> None:
        super().__init__("启动项", "服务、注册表、计划任务与启动文件夹（演示数据）", parent)
        self.items = [dict(x) for x in STARTUP_ITEMS]
        self._rows: dict[str, StartupRow] = {}
        self._filter = "全部"

        self.add_widget(self._build_stats())
        self.add_widget(self._build_toolbar())
        self.add_widget(self._build_list())
        self.add_stretch()
        self._update_stats()

    def _build_stats(self) -> QWidget:
        host = QWidget(self)
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        self.stat_total = StatCard(FIF.TILES, "启动项", "0", "演示数据", ACCENT, host)
        self.stat_on = StatCard(FIF.PLAY, "已启用", "0", "开机时运行", SUCCESS, host)
        self.stat_off = StatCard(FIF.SPEED_OFF, "已禁用", "0", "不会自动运行", "#6B7280", host)
        self.stat_left = StatCard(FIF.DELETE, "残留项", "0", "指向不存在的程序", WARNING, host)
        for card in (self.stat_total, self.stat_on, self.stat_off, self.stat_left):
            row.addWidget(card)
        return host

    def _build_toolbar(self) -> QWidget:
        card = SectionCard("筛选", "先只读展示，再决定是否禁用；正式版会先备份", FIF.FILTER)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.seg = SegmentedWidget()
        for key in ("全部", "已启用", "已禁用", "残留"):
            self.seg.addItem(key, key)
        self.seg.setCurrentItem("全部")
        self.seg.currentItemChanged.connect(self._on_filter)
        row.addWidget(self.seg, 1)
        self.search = LineEdit()
        self.search.setPlaceholderText("搜索启动项、发布者或路径…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _t: self._apply_filter())
        row.addWidget(self.search)
        self.show_system = CheckBox("显示系统项")
        self.show_system.setChecked(True)
        row.addWidget(self.show_system)
        btn = OutlineButton("刷新")
        btn.clicked.connect(lambda: InfoBar.success("已刷新（演示）", "启动项列表已更新", parent=self,
                                                    position=InfoBarPosition.TOP_RIGHT, duration=2200))
        row.addWidget(btn)
        card.content_layout.addLayout(row)
        return card

    def _build_list(self) -> QWidget:
        card = SectionCard("启动项", "开关只改变演示状态，不会写入注册表或服务", FIF.SPEED_HIGH)
        self.holder = QWidget(card)
        self.holder_layout = QVBoxLayout(self.holder)
        self.holder_layout.setContentsMargins(0, 0, 0, 0)
        self.holder_layout.setSpacing(7)
        for item in self.items:
            row = StartupRow(item, self.holder)
            row.toggled.connect(self._on_toggle)
            self.holder_layout.addWidget(row)
            self._rows[item["name"]] = row
        card.content_layout.addWidget(self.holder)
        return card

    def _on_filter(self, key: str) -> None:
        self._filter = key
        self._apply_filter()

    def _apply_filter(self) -> None:
        text = self.search.text().strip().lower()
        for name, row in self._rows.items():
            item = row.data
            ok = True
            if self._filter == "已启用":
                ok = bool(item["enabled"])
            elif self._filter == "已禁用":
                ok = not item["enabled"]
            elif self._filter == "残留":
                ok = item["type"] == "残留"
            if text and text not in name.lower() and text not in item["desc"].lower():
                ok = False
            row.setVisible(ok)

    def _on_toggle(self, name: str, checked: bool) -> None:
        self._update_stats()
        state = "启用" if checked else "禁用"
        InfoBar.info(f"已{state}（演示）", name, parent=self,
                     position=InfoBarPosition.TOP_RIGHT, duration=1800)

    def _update_stats(self) -> None:
        total = len(self.items)
        on = sum(1 for i in self.items if i["enabled"])
        left = sum(1 for i in self.items if i["type"] == "残留")
        self.stat_total.set_value(str(total), "演示数据")
        self.stat_on.set_value(str(on), "开机时运行")
        self.stat_off.set_value(str(total - on), "不会自动运行")
        self.stat_left.set_value(str(left), "指向不存在的程序")
