"""清理记录页。"""
from __future__ import annotations

import csv
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QGridLayout, QHBoxLayout
from qfluentwidgets import (
    CaptionLabel,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    PushButton,
    TableWidget,
)

from ...core.sizes import human_size
from ...state import state
from ..widgets.base import Page, SectionCard, StatCard


class HistoryPage(Page):
    def __init__(self, parent=None) -> None:
        super().__init__("清理记录", "每一次清理都会留下可追溯的记录", parent)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.card_freed = StatCard(FIF.SAVE, "累计释放", "0 B")
        self.card_items = StatCard(FIF.TILES, "累计清理项", "0")
        self.card_runs = StatCard(FIF.HISTORY, "执行次数", "0")
        grid.addWidget(self.card_freed, 0, 0)
        grid.addWidget(self.card_items, 0, 1)
        grid.addWidget(self.card_runs, 0, 2)
        self.add_layout(grid)

        card = SectionCard("历史明细", "最多显示最近 500 条记录", FIF.HISTORY)
        bar = QHBoxLayout()
        bar.addStretch(1)
        btn_refresh = PushButton(FIF.SYNC, "刷新")
        btn_refresh.clicked.connect(self.refresh)
        bar.addWidget(btn_refresh)
        btn_export = PushButton(FIF.SAVE, "导出 CSV")
        btn_export.clicked.connect(self.export_csv)
        bar.addWidget(btn_export)
        btn_clear = PushButton(FIF.DELETE, "清空记录")
        btn_clear.clicked.connect(self.clear_all)
        bar.addWidget(btn_clear)
        card.content_layout.addLayout(bar)

        self.table = TableWidget()
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["时间", "清理项", "分类", "结果", "清理数", "释放空间", "备注"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(420)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        card.content_layout.addWidget(self.table)
        self.add_widget(card)
        self.add_stretch()
        self.refresh()

    def refresh(self) -> None:
        stats = state.db.history_stats()
        self.card_freed.set_value(human_size(stats["freed"]))
        self.card_items.set_value(f"{stats['removed']:,}")
        self.card_runs.set_value(str(stats["runs"]))

        rows = state.db.recent_history(500)
        from PySide6.QtWidgets import QTableWidgetItem
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            ok = bool(row["success"])
            note = row["note"] or ""
            values = [
                str(row["ts"]),
                row["item_label"],
                row["category"],
                "成功" if ok else "失败",
                str(row["removed_count"]),
                human_size(row["freed_bytes"]),
                note,
            ]
            for c, v in enumerate(values):
                cell = QTableWidgetItem(v)
                if c in (4, 5):
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r, c, cell)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

    def export_csv(self) -> None:
        rows = state.db.recent_history(5000)
        if not rows:
            InfoBar.warning("没有记录", "暂无可导出的清理记录", parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=2500)
            return
        default = f"清理记录_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "导出清理记录", default, "CSV 文件 (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(["时间", "清理项", "分类", "结果", "清理数", "释放字节", "跳过", "备注"])
            for row in rows:
                writer.writerow([
                    row["ts"], row["item_label"], row["category"],
                    "成功" if row["success"] else "失败",
                    row["removed_count"], row["freed_bytes"], row["skipped_count"], row["note"],
                ])
        InfoBar.success("导出成功", f"已导出 {len(rows)} 条记录", parent=self,
                        position=InfoBarPosition.TOP_RIGHT, duration=3000)

    def clear_all(self) -> None:
        from qfluentwidgets import MessageBox
        box = MessageBox("清空记录", "确定清空所有清理历史吗？此操作不可撤销。", self)
        box.yesButton.setText("清空")
        box.cancelButton.setText("取消")
        if box.exec():
            state.db.clear_history()
            self.refresh()
            InfoBar.success("已清空", "清理记录已清空", parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=2500)
