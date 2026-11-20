"""总览页：左侧常驻硬件信息面板。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from qfluentwidgets import CaptionLabel, FluentIcon as FIF, StrongBodyLabel

from ...core.sizes import disk_usage, human_size
from ...state import state
from ..theme import ACCENT, ACCENT_2, DANGER, INFO, SUCCESS, WARNING, palette
from ..widgets.barchart import BarChart
from ..widgets.base import Page, SectionCard, StatCard
from ..widgets.hero import HeroCard
from ..widgets.hwpanel import HwPanel
from ..widgets.ring import RingChart


class DashboardPage(Page):
    scan_requested = Signal()
    clean_requested = Signal()
    goto_history = Signal()
    goto_hardware = Signal()
    refresh_hardware = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("总览", "本机维护状态与硬件信息", parent)

        self.add_widget(self._build_hero())

        columns = QHBoxLayout()
        columns.setSpacing(14)

        # ---------- 左：硬件信息（打开即可见） ----------
        self.hw_panel = HwPanel(self)
        self.hw_panel.goto_detail.connect(self.goto_hardware.emit)
        self.hw_panel.refresh_requested.connect(self.refresh_hardware.emit)
        columns.addWidget(self.hw_panel, 1)

        # ---------- 右：统计 + 图表 ----------
        right = QVBoxLayout()
        right.setSpacing(14)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.card_scan = StatCard(FIF.PIE_SINGLE, "待清理空间", "尚未统计", "点击「扫描」开始", ACCENT)
        self.card_freed = StatCard(FIF.BROOM, "累计释放", "0 B", "本机历史累计", SUCCESS)
        self.card_items = StatCard(FIF.TILES, "累计清理项", "0", "本机历史累计", INFO)
        grid.addWidget(self.card_scan, 0, 0)
        grid.addWidget(self.card_freed, 0, 1)
        grid.addWidget(self.card_items, 0, 2)
        right.addLayout(grid)

        mid = QHBoxLayout()
        mid.setSpacing(14)
        self.disk_card = SectionCard("磁盘占用", "系统盘 C:", FIF.SAVE)
        ring_row = QHBoxLayout()
        ring_row.setSpacing(16)
        self.ring = RingChart()
        ring_row.addWidget(self.ring, 0, Qt.AlignVCenter)
        legend = QVBoxLayout()
        legend.setSpacing(9)
        self.lbl_total = self._legend_row(legend, "总容量", "-")
        self.lbl_used = self._legend_row(legend, "已使用", "-")
        self.lbl_free = self._legend_row(legend, "可用", "-")
        legend.addStretch(1)
        ring_row.addLayout(legend, 1)
        self.disk_card.content_layout.addLayout(ring_row)
        mid.addWidget(self.disk_card, 1)

        self.top_card = SectionCard("可清理空间 Top 6", "扫描后按占用排序", FIF.PIE_SINGLE)
        self.bar_chart = BarChart()
        self.top_card.content_layout.addWidget(self.bar_chart)
        mid.addWidget(self.top_card, 1)
        right.addLayout(mid)

        self.recent_card = SectionCard("最近清理", "最近 8 次清理结果", FIF.HISTORY)
        self.recent_box = QVBoxLayout()
        self.recent_box.setSpacing(6)
        self.recent_card.content_layout.addLayout(self.recent_box)
        right.addWidget(self.recent_card)

        columns.addLayout(right, 2)
        self.add_layout(columns)
        self.add_stretch()
        self.refresh()

    # ------------------------------------------------------------- hero
    def _build_hero(self) -> HeroCard:
        hero = HeroCard(self)
        p = palette()

        title = QLabel("本机维护状态", hero)
        f = QFont()
        f.setPointSize(11)
        title.setFont(f)
        title.setStyleSheet(f"color:{p['hero_sub']};")
        hero.left.addWidget(title)

        self.hero_value = QLabel("-", hero)
        f2 = QFont()
        f2.setPointSize(30)
        f2.setBold(True)
        self.hero_value.setFont(f2)
        self.hero_value.setStyleSheet(f"color:{p['hero_text']};")
        hero.left.addWidget(self.hero_value)

        self.hero_sub = QLabel("", hero)
        self.hero_sub.setStyleSheet(f"color:{p['hero_sub']};")
        hero.left.addWidget(self.hero_sub)
        hero.left.addSpacing(8)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        self.hero_chip_state = QLabel("就绪", hero)
        self.hero_chip_machine = QLabel(f"计算机名  {state.machine}", hero)
        for chip in (self.hero_chip_state, self.hero_chip_machine):
            chip.setStyleSheet(
                f"QLabel{{color:{p['hero_chip_fg']};background:{p['hero_chip_bg']};"
                f"border:1px solid {p['hero_btn_border']};"
                "border-radius:11px;padding:4px 12px;font-size:12px;}"
            )
            chips.addWidget(chip)
        chips.addStretch(1)
        hero.left.addLayout(chips)
        hero.left.addStretch(1)

        hero.right.addStretch(1)
        self.hero_btn_scan = self._hero_button("立即扫描", hero, primary=True)
        self.hero_btn_scan.clicked.connect(self.scan_requested.emit)
        hero.right.addWidget(self.hero_btn_scan)
        self.hero_btn_clean = self._hero_button("一键清理", hero)
        self.hero_btn_clean.clicked.connect(self.clean_requested.emit)
        hero.right.addWidget(self.hero_btn_clean)
        self.hero_btn_hw = self._hero_button("硬件信息", hero)
        self.hero_btn_hw.clicked.connect(self.goto_hardware.emit)
        hero.right.addWidget(self.hero_btn_hw)
        hero.right.addStretch(1)
        return hero

    def _hero_button(self, text: str, parent, primary: bool = False) -> QPushButton:
        p = palette()
        btn = QPushButton(text, parent)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(38)
        if primary:
            btn.setStyleSheet(
                "QPushButton{"
                f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                f"stop:0 {ACCENT},stop:1 {ACCENT_2});"
                "color:#FFFFFF;border:none;border-radius:10px;padding:9px 20px;font-weight:600;}"
                "QPushButton:hover{opacity:0.9;}"
            )
        else:
            btn.setStyleSheet(
                "QPushButton{"
                f"background:{p['hero_btn']};color:{p['hero_btn_fg']};"
                f"border:1px solid {p['hero_btn_border']};border-radius:10px;"
                "padding:9px 20px;font-weight:600;}"
                f"QPushButton:hover{{background:{p['btn_hover']};}}"
            )
        return btn

    # ------------------------------------------------------------- helpers
    def _legend_row(self, layout: QVBoxLayout, name: str, value: str) -> QLabel:
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(CaptionLabel(name, self))
        v = StrongBodyLabel(value, self)
        v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addStretch(1)
        row.addWidget(v)
        layout.addLayout(row)
        return v

    def _clear(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.hide()
                w.deleteLater()

    # ------------------------------------------------------------- refresh
    def refresh(self) -> None:
        total, used, free = disk_usage("C:\\")
        ratio = (used / total) if total else 0.0
        self.ring.set_ratio(ratio, f"{ratio * 100:.0f}%", "已使用")
        self.lbl_total.setText(human_size(total))
        self.lbl_used.setText(human_size(used))
        self.lbl_free.setText(human_size(free))

        self.hero_value.setText(f"{human_size(free)} 可用")
        self.hero_sub.setText(
            f"系统盘共 {human_size(total)}，已用 {human_size(used)}（{ratio * 100:.0f}%）"
        )
        self.hero_chip_state.setText("可直接使用　·　全部功能已开放")

        scanned = state.total_scanned_size()
        if state.last_scan:
            self.card_scan.set_value(human_size(scanned), f"已统计 {len(state.last_scan)} 个清理项")
            rows = sorted(
                ((o.label, o.size, o.category) for o in state.last_scan.values() if o.size > 0),
                key=lambda r: r[1], reverse=True,
            )[:6]
            self.bar_chart.set_data([(n, s, c, human_size(s)) for n, s, c in rows],
                                    empty_text="扫描后这里会显示占用最大的项目")
        else:
            self.card_scan.set_value("尚未统计", "点击「扫描」开始")
            self.bar_chart.set_data([], empty_text="扫描后这里会显示占用最大的项目")

        stats = state.db.history_stats()
        self.card_freed.set_value(human_size(stats["freed"]), "本机历史累计")
        self.card_items.set_value(f"{stats['removed']:,}", f"共执行 {stats['runs']} 次清理")
        self.refresh_recent()
        self.refresh_hw_panel()

    def refresh_hw_panel(self) -> None:
        if state.hw_sections:
            self.hw_panel.set_data(state.hw_sections)
        elif state.hw_error:
            self.hw_panel.set_error(state.hw_error)
        else:
            self.hw_panel.set_loading()

    def refresh_recent(self) -> None:
        self._clear(self.recent_box)
        rows = state.db.sessions(8)
        if not rows:
            self.recent_box.addWidget(CaptionLabel("暂无清理记录", self.recent_card))
            return
        for r in rows:
            row = QHBoxLayout()
            row.setSpacing(10)
            dot = QLabel(self.recent_card)
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background:{SUCCESS};border-radius:4px;")
            row.addWidget(dot, 0, Qt.AlignVCenter)
            ts = CaptionLabel(str(r["ts"])[5:16], self.recent_card)
            ts.setMinimumWidth(88)
            row.addWidget(ts)
            row.addWidget(StrongBodyLabel(
                f"成功 {r['success_items']}/{r['total_items']} 项", self.recent_card))
            row.addStretch(1)
            row.addWidget(CaptionLabel(f"{r['removed_count']} 项", self.recent_card))
            row.addWidget(StrongBodyLabel(human_size(r["freed_bytes"]), self.recent_card))
            self.recent_box.addLayout(row)
