"""设置页。"""
from __future__ import annotations

import os
import subprocess

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    SpinBox,
    SwitchButton,
)

from ... import APP_TITLE, APP_VERSION
from ...core.paths import APP_DIR, ensure_app_dirs
from ...state import state
from ..theme import palette
from ..widgets.base import Page, SectionCard
from ..widgets.buttons import OutlineButton
from ..widgets.contact import contact_card, refresh_contact_card


class SettingsPage(Page):
    theme_changed = None  # 由窗口注入

    def __init__(self, parent=None) -> None:
        super().__init__("设置", "外观、清理策略与数据位置", parent)
        # 左列：设置项；右列：联系我们（打开设置就能看到）
        columns = QHBoxLayout()
        columns.setSpacing(14)

        left = QVBoxLayout()
        left.setSpacing(14)
        left.addWidget(self._build_appearance())
        left.addWidget(self._build_cleaning())
        left.addWidget(self._build_about())
        left.addStretch(1)
        columns.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(14)
        self.contact = contact_card(self, compact=True)
        right.addWidget(self.contact)
        right.addStretch(1)
        columns.addLayout(right, 2)

        self.add_layout(columns)
        self.add_stretch()

    def refresh_contact(self) -> None:
        refresh_contact_card(self.contact)

    def _build_appearance(self):
        card = SectionCard("外观", "", FIF.VIEW)
        row = QHBoxLayout()
        row.addWidget(BodyLabel("主题模式", card))
        hint = CaptionLabel("默认浅色渐变，可切换为深色或跟随系统")
        hint.setStyleSheet(f"color:{palette()['sub']};")
        row.addWidget(hint)
        row.addStretch(1)
        self.combo_theme = ComboBox()
        self.combo_theme.addItem("浅色（默认）", userData="light")
        self.combo_theme.addItem("深色", userData="dark")
        self.combo_theme.addItem("跟随系统", userData="auto")
        self.combo_theme.setMinimumWidth(150)
        self.combo_theme.setCurrentIndex({"light": 0, "dark": 1, "auto": 2}.get(state.theme_mode, 0))
        self.combo_theme.currentIndexChanged.connect(self._on_theme)
        row.addWidget(self.combo_theme)
        card.content_layout.addLayout(row)
        return card

    def _on_theme(self, _index: int) -> None:
        mode = self.combo_theme.currentData()
        state.theme_mode = mode
        state.save_setting("theme", mode)
        if callable(self.theme_changed):
            self.theme_changed(mode)

    def _build_cleaning(self):
        card = SectionCard("清理策略", "", FIF.BROOM)

        row = QHBoxLayout()
        row.addWidget(BodyLabel("修改注册表前自动备份", card))
        hint = CaptionLabel("备份文件保存在数据目录的 registry_backups 中")
        hint.setStyleSheet(f"color:{palette()['sub']};")
        row.addWidget(hint)
        row.addStretch(1)
        self.switch_backup = SwitchButton()
        self.switch_backup.setChecked(state.auto_backup)
        self.switch_backup.setOnText("开")
        self.switch_backup.setOffText("关")
        self.switch_backup.checkedChanged.connect(self._on_backup)
        row.addWidget(self.switch_backup)
        card.content_layout.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(BodyLabel("历史记录保留条数", card))
        row2.addStretch(1)
        self.spin_keep = SpinBox()
        self.spin_keep.setRange(100, 20000)
        self.spin_keep.setSingleStep(100)
        self.spin_keep.setValue(state.history_keep)
        self.spin_keep.valueChanged.connect(self._on_keep)
        row2.addWidget(self.spin_keep)
        card.content_layout.addLayout(row2)
        return card

    def _on_backup(self, checked: bool) -> None:
        state.auto_backup = bool(checked)
        state.save_setting("auto_backup", "1" if checked else "0")

    def _on_keep(self, value: int) -> None:
        state.history_keep = int(value)
        state.save_setting("history_keep", str(int(value)))

    def _build_about(self):
        card = SectionCard("关于", "", FIF.INFO)
        card.content_layout.addWidget(BodyLabel(f"{APP_TITLE}  v{APP_VERSION}", card))
        path_label = CaptionLabel(f"数据目录：{APP_DIR}")
        path_label.setStyleSheet(f"color:{palette()['sub']};")
        card.content_layout.addWidget(path_label)
        row = QHBoxLayout()
        row.addStretch(1)
        btn_open = OutlineButton("打开数据目录", card)
        btn_open.clicked.connect(self._open_dir)
        row.addWidget(btn_open)
        card.content_layout.addLayout(row)
        return card

    def _open_dir(self) -> None:
        ensure_app_dirs()
        try:
            os.startfile(APP_DIR)  # type: ignore[attr-defined]
        except Exception:
            subprocess.Popen(["explorer", str(APP_DIR)])
