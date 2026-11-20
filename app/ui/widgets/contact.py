"""联系方式与诊断信息（设置页 / 联系我们页 / 其他工具页共用）。"""
from __future__ import annotations

import platform

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    StrongBodyLabel,
    TextEdit,
)

from ... import APP_TITLE, APP_VERSION
from ...state import state
from ..theme import palette
from .base import SectionCard
from .buttons import GradientButton, OutlineButton

ISSUES_URL = "https://github.com/chenyang-adw/StudioCleaner/issues"


def _hw_field(name: str, label: str) -> str:
    for sec in state.hw_sections or []:
        if sec.key == name:
            for f in sec.fields:
                if f.label == label:
                    return f.value
    return ""


def diagnostics_text() -> str:
    """拼一段可以直接发给客服的诊断信息。"""
    lines = [
        f"【{APP_TITLE} 反馈】",
        f"软件版本：v{APP_VERSION}",
        f"操作系统：{platform.system()} {platform.release()}（{platform.version()}）",
        f"计算机名：{state.machine}",
        f"机器码：{state.hwid}",
    ]
    cpu = _hw_field("cpu", "型号")
    board = _hw_field("board", "主板型号")
    mem = _hw_field("memory", "总容量")
    if cpu:
        lines.append(f"处理器：{cpu}")
    if board:
        lines.append(f"主板：{board}")
    if mem:
        lines.append(f"内存：{mem}")
    if not state.hardware_ready():
        lines.append("（硬件信息尚未读取完成，可稍后重新复制）")
    return "\n".join(lines)


def copy_text(parent, text: str, tip: str = "已复制到剪贴板") -> None:
    QApplication.clipboard().setText(text)
    InfoBar.success("已复制", tip, parent=parent,
                    position=InfoBarPosition.TOP_RIGHT, duration=2200)


def open_issues(parent=None) -> None:
    """在浏览器中打开 GitHub Issues。"""
    ok = QDesktopServices.openUrl(QUrl(ISSUES_URL))
    if not ok and parent is not None:
        InfoBar.warning(
            "未能打开浏览器",
            f"请手动访问 {ISSUES_URL}",
            parent=parent, position=InfoBarPosition.TOP_RIGHT, duration=4000,
        )


def contact_card(parent, compact: bool = False) -> QWidget:
    """反馈卡片：Issue 地址 + 复制 + 打开按钮 + 复制诊断信息。"""
    card = SectionCard(
        "帮助与反馈",
        "遇到问题或有功能建议，欢迎在 GitHub Issues 反馈" if not compact else "欢迎反馈问题与建议",
        FIF.CHAT,
    )

    row = QHBoxLayout()
    row.setSpacing(10)
    label = CaptionLabel("GitHub", card)
    label.setStyleSheet(f"color:{palette()['sub']};")
    row.addWidget(label, 0, Qt.AlignVCenter)

    number = QLabel("提交 Issue", card)
    f = QFont("Microsoft YaHei UI", 13)
    f.setBold(True)
    number.setFont(f)
    number.setStyleSheet(f"color:{palette()['accent']};")
    number.setTextInteractionFlags(Qt.TextSelectableByMouse)
    row.addWidget(number, 0, Qt.AlignVCenter)

    btn_copy = OutlineButton("复制 Issue 地址", card)
    btn_copy.setMinimumHeight(32)
    btn_copy.clicked.connect(
        lambda: copy_text(card, ISSUES_URL, "Issue 地址已复制")
    )
    row.addWidget(btn_copy)

    btn_chat = GradientButton("在浏览器中打开", card)
    btn_chat.setMinimumHeight(32)
    btn_chat.clicked.connect(lambda: open_issues(card))
    row.addWidget(btn_chat)
    row.addStretch(1)
    card.content_layout.addLayout(row)

    tip = CaptionLabel("反馈时请附上下面的诊断信息（手动粘贴，不会自动上传）", card)
    tip.setStyleSheet(f"color:{palette()['sub']};")
    card.content_layout.addWidget(tip)

    card.content_layout.addWidget(BodyLabel("反馈时建议附上下面的诊断信息", card))
    preview = TextEdit(card)
    preview.setReadOnly(True)
    preview.setMinimumHeight(132 if not compact else 118)
    preview.setPlainText(diagnostics_text())
    card.content_layout.addWidget(preview)

    actions = QHBoxLayout()
    actions.addStretch(1)
    btn_diag = GradientButton("一键复制诊断信息", card)
    btn_diag.clicked.connect(
        lambda: copy_text(card, diagnostics_text(), "诊断信息已复制，粘贴发给客服即可")
    )
    actions.addWidget(btn_diag)
    card.content_layout.addLayout(actions)
    card.diag_preview = preview  # type: ignore[attr-defined]
    return card


def refresh_contact_card(card) -> None:
    preview = getattr(card, "diag_preview", None)
    if preview is not None:
        preview.setPlainText(diagnostics_text())
