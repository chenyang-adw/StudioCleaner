"""左侧硬件信息面板（紧凑版，总览页常驻）。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, CardWidget, FluentIcon as FIF, IconWidget, StrongBodyLabel

from ...core.hardware import fmt_bytes
from ..theme import palette
from .buttons import OutlineButton, SoftButton


def _clean(value) -> str:
    text = str(value or "").strip()
    return text if text else "-"


class HwPanel(CardWidget):
    goto_detail = Signal()
    refresh_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(8)
        icon = IconWidget(FIF.FINGERPRINT, self)
        icon.setFixedSize(18, 18)
        head.addWidget(icon)
        title = StrongBodyLabel("硬件信息", self)
        head.addWidget(title)
        head.addStretch(1)
        self.btn_refresh = SoftButton("刷新", self)
        self.btn_refresh.setMinimumHeight(30)
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        head.addWidget(self.btn_refresh)
        root.addLayout(head)

        self.hint = CaptionLabel("本机硬件序列号一览", self)
        self.hint.setStyleSheet(f"color:{palette()['sub']};")
        root.addWidget(self.hint)

        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        root.addLayout(self.body)
        root.addStretch(1)

        self.btn_detail = OutlineButton("查看完整硬件信息", self)
        self.btn_detail.clicked.connect(self.goto_detail.emit)
        root.addWidget(self.btn_detail)

        self.set_loading()

    # ------------------------------------------------------------------ 渲染
    def _clear(self) -> None:
        while self.body.count():
            item = self.body.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.hide()
                w.deleteLater()
            lay = item.layout()
            if lay is not None:
                while lay.count():
                    sub = lay.takeAt(0)
                    sw = sub.widget()
                    if sw is not None:
                        sw.setParent(None)
                        sw.hide()
                        sw.deleteLater()

    def _row(self, label: str, value: str, mono: bool = False) -> QWidget:
        p = palette()
        row = QWidget(self)
        lay = QVBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        name = CaptionLabel(label, row)
        name.setStyleSheet(f"color:{p['sub']};")
        lay.addWidget(name)

        text = StrongBodyLabel(value, row)
        text.setWordWrap(True)
        style = f"color:{p['text']};"
        if mono:
            f = QFont("Consolas", 10)
            text.setFont(f)
            style = f"color:{p['accent']};"
        text.setStyleSheet(style)
        lay.addWidget(text)
        return row

    def set_loading(self) -> None:
        self._clear()
        self.hint.setText("正在读取硬件信息…")
        tip = CaptionLabel("首次读取约需 3-5 秒", self)
        tip.setStyleSheet(f"color:{palette()['muted']};")
        self.body.addWidget(tip)

    def set_error(self, message: str) -> None:
        self._clear()
        self.hint.setText("硬件信息读取受限")
        tip = CaptionLabel(message, self)
        tip.setWordWrap(True)
        tip.setStyleSheet(f"color:{palette()['warning']};")
        self.body.addWidget(tip)

    def set_data(self, sections) -> None:
        """sections 来自 app.core.hardware.build_sections。"""
        self._clear()
        if not sections:
            self.set_error("未能读取硬件信息")
            return

        def field(section_key: str, label: str) -> str:
            for sec in sections:
                if sec.key != section_key:
                    continue
                for f in sec.fields:
                    if f.label == label:
                        return f.value
            return ""

        def first_entry(section_key: str):
            for sec in sections:
                if sec.key == section_key and sec.entries:
                    return sec.entries[0]
            return None, []

        def entry_field(section_key: str, label: str, fallback: str = "") -> str:
            title, fields = first_entry(section_key)
            for f in fields:
                if f.label == label:
                    return f.value
            return fallback

        sys_name = field("system", "计算机名")
        sys_os = field("system", "操作系统")
        self.hint.setText(f"{_clean(sys_name)}　·　{_clean(sys_os)}")

        self.body.addWidget(self._row("处理器", field("cpu", "型号") or "-"))
        self.body.addWidget(self._row("主板", field("board", "主板型号") or "-"))
        self.body.addWidget(self._row("产品名称", field("system", "产品名称") or "-"))
        self.body.addWidget(self._row("主板序列号", field("board", "主板序列号") or "-", mono=True))

        mem_text = field("memory", "总容量")
        count = field("memory", "内存条数量")
        if mem_text and count and count != "-":
            mem_text = f"{mem_text}　{count}"
        self.body.addWidget(self._row("内存", mem_text or "-"))

        gpu_name, gpu_fields = first_entry("gpu")
        if gpu_name:
            vram = next((f.value for f in gpu_fields if f.label == "显存"), "")
            text = f"{gpu_name}　{vram}".strip("　")
            self.body.addWidget(self._row("显卡", text))

        disk_name, disk_fields = first_entry("disk")
        if disk_name:
            size = next((f.value for f in disk_fields if f.label == "容量"), "")
            serial = next((f.value for f in disk_fields if f.label == "序列号"), "-")
            self.body.addWidget(self._row("硬盘", f"{disk_name}　{size}".strip()))
            self.body.addWidget(self._row("硬盘序列号", serial, mono=True))

        bios_ver = field("board", "BIOS 版本")
        if bios_ver:
            self.body.addWidget(self._row("BIOS", bios_ver))

    def refresh_styles(self) -> None:
        self.hint.setStyleSheet(f"color:{palette()['sub']};")
