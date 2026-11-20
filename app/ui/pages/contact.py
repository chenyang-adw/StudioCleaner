"""联系我们页。"""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from qfluentwidgets import CaptionLabel, FluentIcon as FIF, StrongBodyLabel

from ... import APP_TITLE, APP_VERSION
from ..theme import palette
from ..widgets.base import Page, SectionCard
from ..widgets.contact import ISSUES_URL, contact_card

FAQ = [
    ("需要管理员权限吗？",
     "建议右键「以管理员身份运行」。应用卸载、系统临时文件、Windows 更新缓存、"
     "无效启动项等项目需要管理员权限，非管理员运行时这些项目会标注「需管理员」并自动跳过。"),
    ("清理会不会误删我的文件？",
     "只会清理缓存、临时文件、日志这类内容，并且做了三层保护：删除前校验目标在允许的目录内、"
     "不跟随符号链接、文件被占用就跳过。注册表项删除前会自动备份到数据目录。"),
    ("「疑似捆绑」标记准不准？",
     "那是按「无卸载程序 / 无发布者 / 安装目录不存在 / 名称特征」做的启发式提示，"
     "只用于提醒你多看一眼，不代表一定是流氓软件，程序不会自动删除任何东西。"),
    ("断网能用吗？",
     "能。清理、硬件信息、应用卸载全部在本机完成，不需要联网，"
     "也不会把任何文件上传出去。"),
]


class ContactPage(Page):
    def __init__(self, parent=None) -> None:
        super().__init__("帮助与反馈", "遇到问题或有功能建议，欢迎在 GitHub Issues 反馈", parent)
        self.card = contact_card(self)
        self.add_widget(self.card)
        self.add_widget(self._build_faq())
        self.add_stretch()

    def refresh_info(self) -> None:
        from ..widgets.contact import refresh_contact_card
        refresh_contact_card(self.card)

    def _build_faq(self):
        card = SectionCard("常见问题", "先看看这里，也许能直接解决", FIF.QUESTION)
        for question, answer in FAQ:
            box = QVBoxLayout()
            box.setSpacing(3)
            q = StrongBodyLabel(f"· {question}", card)
            q.setStyleSheet(f"color:{palette()['text']};")
            box.addWidget(q)
            a = CaptionLabel(answer, card)
            a.setWordWrap(True)
            a.setStyleSheet(f"color:{palette()['sub']};")
            box.addWidget(a)
            card.content_layout.addLayout(box)
        footer = CaptionLabel(
            f"以上都没解决？到 GitHub Issues 提一条：{ISSUES_URL}", card
        )
        footer.setStyleSheet(f"color:{palette()['accent']};")
        card.content_layout.addWidget(footer)
        return card
