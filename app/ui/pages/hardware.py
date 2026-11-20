"""硬件信息页：CPU / 主板 / 内存 / 显卡 / 硬盘 / 网卡 / 系统。"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    StrongBodyLabel,
)

from ...core.hardware import HwField, HwSection
from ...state import state
from ..theme import palette
from ..widgets.base import Page, SectionCard
from ..widgets.buttons import GradientButton, OutlineButton, SoftButton


class FieldRow(QWidget):
    def __init__(self, label: str, value: str, mono: bool = False, parent=None) -> None:
        super().__init__(parent)
        p = palette()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(10)

        name = CaptionLabel(label, self)
        name.setStyleSheet(f"color:{p['sub']};")
        name.setMinimumWidth(96)
        row.addWidget(name, 0, Qt.AlignTop)

        text = QLabel(value or "-", self)
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        if mono:
            text.setFont(QFont("Consolas", 10))
            text.setStyleSheet(f"color:{p['accent']};")
        else:
            text.setStyleSheet(f"color:{p['text']};")
        row.addWidget(text, 1)

        if mono:
            btn = SoftButton("复制", self)
            btn.setMinimumHeight(26)
            btn.setFixedWidth(56)
            btn.clicked.connect(lambda _=False, v=value: self._copy(v))
            row.addWidget(btn, 0, Qt.AlignTop)
        self.value = value

    def _copy(self, value: str) -> None:
        QApplication.clipboard().setText(value)
        InfoBar.success("已复制", value, parent=self, position=InfoBarPosition.TOP_RIGHT,
                        duration=1800)


class HardwarePage(Page):
    refresh_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("硬件信息", "本机 CPU / 主板 / 内存 / 显卡 / 硬盘 等硬件序列号", parent)
        self.add_widget(self._build_toolbar())
        self.cards_holder = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_holder)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(14)
        self.add_widget(self.cards_holder)
        self.add_stretch()
        self.set_loading()

    def _build_toolbar(self) -> QWidget:
        card = SectionCard("操作", "信息为只读读取，不会对硬件做任何修改", FIF.FINGERPRINT)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.status = CaptionLabel("", card)
        self.status.setStyleSheet(f"color:{palette()['sub']};")
        row.addWidget(self.status)
        row.addStretch(1)
        btn_refresh = OutlineButton("刷新", card)
        btn_refresh.clicked.connect(self.refresh_requested.emit)
        row.addWidget(btn_refresh)
        btn_copy = OutlineButton("复制全部", card)
        btn_copy.clicked.connect(self._copy_all)
        row.addWidget(btn_copy)
        self.btn_export = GradientButton("导出 TXT", card)
        self.btn_export.clicked.connect(self._export)
        row.addWidget(self.btn_export)
        card.content_layout.addLayout(row)
        return card

    # ------------------------------------------------------------------ 渲染
    def _clear(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.hide()
                w.deleteLater()

    def set_loading(self) -> None:
        self._clear()
        if state.hw_loading:
            self.status.setText("正在读取硬件信息…")
        else:
            self.status.setText("等待读取")
        tip = CaptionLabel("首次读取需要 3-5 秒，请稍候…", self.cards_holder)
        tip.setStyleSheet(f"color:{palette()['muted']};")
        self.cards_layout.addWidget(tip)

    def set_data(self, sections: list[HwSection]) -> None:
        self._clear()
        if not sections:
            tip = CaptionLabel("未能读取到硬件信息，可点击「刷新」重试", self.cards_holder)
            tip.setStyleSheet(f"color:{palette()['warning']};")
            self.cards_layout.addWidget(tip)
            self.status.setText(state.hw_error or "无数据")
            return
        self.status.setText(
            f"读取完成　·　{datetime.now().strftime('%H:%M:%S')}　·　数据仅本机可见"
        )
        icon_map = {
            "cpu": FIF.ROBOT, "board": FIF.TILES, "memory": FIF.TAG, "gpu": FIF.PHOTO,
            "disk": FIF.SAVE, "net": FIF.WIFI, "system": FIF.APPLICATION,
        }
        for sec in sections:
            card = SectionCard(
                sec.title,
                "" if sec.entries else "",
                icon_map.get(sec.key, FIF.INFO),
            )
            for f in sec.fields:
                card.content_layout.addWidget(FieldRow(f.label, f.value, f.mono, card))
            for title, fields in sec.entries:
                box = QWidget(card)
                box.setStyleSheet(
                    f"background:{palette()['surface_2']};border-radius:10px;"
                )
                v = QVBoxLayout(box)
                v.setContentsMargins(14, 10, 14, 10)
                v.setSpacing(2)
                head = StrongBodyLabel(title, box)
                head.setStyleSheet(f"color:{palette()['accent']};")
                v.addWidget(head)
                for f in fields:
                    v.addWidget(FieldRow(f.label, f.value, f.mono, box))
                card.content_layout.addWidget(box)
            self.cards_layout.addWidget(card)

    # ------------------------------------------------------------------ 导出
    def _as_text(self) -> str:
        lines = [f"硬件信息　{datetime.now():%Y-%m-%d %H:%M:%S}", "=" * 46]
        for sec in state.hw_sections:
            lines.append("")
            lines.append(f"【{sec.title}】")
            for f in sec.fields:
                lines.append(f"  {f.label}: {f.value}")
            for title, fields in sec.entries:
                lines.append(f"  - {title}")
                for f in fields:
                    lines.append(f"      {f.label}: {f.value}")
        return "\n".join(lines)

    def _copy_all(self) -> None:
        if not state.hw_sections:
            InfoBar.warning("暂无数据", "请先等待硬件信息读取完成", parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=2500)
            return
        QApplication.clipboard().setText(self._as_text())
        InfoBar.success("已复制", "全部硬件信息已复制到剪贴板", parent=self,
                        position=InfoBarPosition.TOP_RIGHT, duration=2500)

    def _export(self) -> None:
        if not state.hw_sections:
            InfoBar.warning("暂无数据", "请先等待硬件信息读取完成", parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=2500)
            return
        default = f"硬件信息_{state.machine}_{datetime.now():%Y%m%d_%H%M%S}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "导出硬件信息", default, "文本文件 (*.txt)")
        if not path:
            return
        with open(path, "w", encoding="utf-8-sig") as fh:
            fh.write(self._as_text())
        InfoBar.success("导出成功", path, parent=self,
                        position=InfoBarPosition.TOP_RIGHT, duration=3000)
