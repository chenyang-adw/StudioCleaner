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

QQ_NUMBER = "1773323815"


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


def open_qq_chat(parent=None) -> None:
    """尝试用 tencent:// 协议直接打开与 QQ 的对话。"""
    url = QUrl(f"tencent://AddContact/?fromId=45&fromSubId=1&subcmd=all&uin={QQ_NUMBER}")
    ok = QDesktopServices.openUrl(url)
    if not ok and parent is not None:
        InfoBar.warning(
            "未找到 QQ",
            f"没能唤起 QQ，请手动搜索 QQ 号 {QQ_NUMBER}",
            parent=parent, position=InfoBarPosition.TOP_RIGHT, duration=4000,
        )


def contact_card(parent, compact: bool = False) -> QWidget:
    """联系方式卡片：QQ 号 + 复制 + 加好友按钮 + 复制诊断信息。"""
    card = SectionCard(
        "联系我们",
        "使用中有任何问题，或者想加新功能，都可以直接找我" if not compact else "有问题可咨询",
        FIF.CHAT,
    )

    row = QHBoxLayout()
    row.setSpacing(10)
    label = CaptionLabel("QQ", card)
    label.setStyleSheet(f"color:{palette()['sub']};")
    row.addWidget(label, 0, Qt.AlignVCenter)

    number = QLabel(QQ_NUMBER, card)
    f = QFont("Consolas", 15)
    f.setBold(True)
    number.setFont(f)
    number.setStyleSheet(f"color:{palette()['accent']};")
    number.setTextInteractionFlags(Qt.TextSelectableByMouse)
    row.addWidget(number, 0, Qt.AlignVCenter)

    btn_copy = OutlineButton("复制 QQ 号", card)
    btn_copy.setMinimumHeight(32)
    btn_copy.clicked.connect(
        lambda: copy_text(card, QQ_NUMBER, f"QQ 号 {QQ_NUMBER} 已复制")
    )
    row.addWidget(btn_copy)

    btn_chat = GradientButton("在 QQ 中找我", card)
    btn_chat.setMinimumHeight(32)
    btn_chat.clicked.connect(lambda: open_qq_chat(card))
    row.addWidget(btn_chat)
    row.addStretch(1)
    card.content_layout.addLayout(row)

    tip = CaptionLabel("有问题可咨询　·　欢迎反馈你希望增加的功能", card)
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
