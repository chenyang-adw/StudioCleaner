"""通用表单控件：文件选择、目录选择、带标签的输入行。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import CaptionLabel, LineEdit

from ..theme import palette
from .buttons import OutlineButton, SoftButton


class LabeledRow(QWidget):
    """左侧标签 + 右侧控件的表单行。"""

    def __init__(self, label: str, widget: QWidget, hint: str = "", parent=None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        row = QHBoxLayout()
        row.setSpacing(10)
        name = CaptionLabel(label, self)
        name.setStyleSheet(f"color:{palette()['sub']};")
        name.setMinimumWidth(84)
        row.addWidget(name, 0, Qt.AlignTop)
        row.addWidget(widget, 1)
        outer.addLayout(row)
        self.widget = widget
        if hint:
            tip = CaptionLabel(hint, self)
            tip.setWordWrap(True)
            tip.setStyleSheet(f"color:{palette()['muted']};font-size:11px;")
            outer.addWidget(tip)


class FilePicker(QWidget):
    """单文件选择。"""

    changed = Signal(str)

    def __init__(self, caption: str = "选择文件", filters: str = "所有文件 (*.*)",
                 save: bool = False, parent=None, validator=None,
                 validate_hint: str = "") -> None:
        super().__init__(parent)
        self._caption = caption
        self._filters = filters
        self._save = save
        self._validator = validator
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.edit = LineEdit(self)
        self.edit.setPlaceholderText("点击右侧按钮选择文件…" if not save else "点击右侧按钮选择保存位置…")
        self.edit.textChanged.connect(self._on_text)
        row.addWidget(self.edit, 1)
        btn = OutlineButton("浏览…", self)
        btn.setMinimumHeight(32)
        btn.clicked.connect(self._browse)
        row.addWidget(btn)
        col.addLayout(row)
        self.warning = CaptionLabel("", self)
        self.warning.setWordWrap(True)
        self.warning.setStyleSheet("color:#DC2626;font-size:11px;")
        self.warning.setVisible(False)
        col.addWidget(self.warning)
        self._validate_hint = validate_hint

    def _on_text(self, text: str) -> None:
        self._validate(text)
        self.changed.emit(text)

    def _validate(self, text: str) -> None:
        if not self._validator:
            return
        message = self._validator(text) if text.strip() else ""
        self.warning.setText(message)
        self.warning.setVisible(bool(message))

    def validate_now(self) -> str:
        if not self._validator or self._save:
            return ""
        message = self._validator(self.path())
        self.warning.setText(message)
        self.warning.setVisible(bool(message))
        return message

    def set_readonly(self, value: bool) -> None:
        self.edit.setReadOnly(value)

    def _browse(self) -> None:
        if self._save:
            path, _ = QFileDialog.getSaveFileName(self, self._caption, self.edit.text(),
                                                  self._filters)
        else:
            path, _ = QFileDialog.getOpenFileName(self, self._caption, self.edit.text(),
                                                  self._filters)
        if path:
            self.edit.setText(path)

    def path(self) -> str:
        return self.edit.text().strip()

    def set_path(self, value: str) -> None:
        self.edit.setText(value)


class DirPicker(QWidget):
    """目录选择。"""

    changed = Signal(str)

    def __init__(self, caption: str = "选择文件夹", parent=None) -> None:
        super().__init__(parent)
        self._caption = caption
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.edit = LineEdit(self)
        self.edit.setPlaceholderText("点击右侧按钮选择文件夹…")
        self.edit.textChanged.connect(self.changed.emit)
        row.addWidget(self.edit, 1)
        btn = OutlineButton("浏览…", self)
        btn.setMinimumHeight(32)
        btn.clicked.connect(self._browse)
        row.addWidget(btn)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, self._caption, self.edit.text())
        if path:
            self.edit.setText(path)

    def path(self) -> str:
        return self.edit.text().strip()

    def set_path(self, value: str) -> None:
        self.edit.setText(value)


class FileListPicker(QWidget):
    """多文件列表，支持增删与排序（用于合并、图片转 PDF）。"""

    changed = Signal()

    def __init__(self, filters: str = "PDF 文件 (*.pdf)", caption: str = "选择文件",
                 parent=None, validator=None) -> None:
        super().__init__(parent)
        self._filters = filters
        self._caption = caption
        self._validator = validator
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)

        self.list = QListWidget(self)
        self.list.setMinimumHeight(132)
        self.list.setSelectionMode(QListWidget.ExtendedSelection)
        self.list.setStyleSheet(
            f"QListWidget{{background:{palette()['surface_2']};"
            f"border:1px solid {palette()['border']};border-radius:10px;padding:4px;}}"
        )
        col.addWidget(self.list)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        for text, slot in (("添加文件", self._add), ("移除选中", self._remove),
                           ("上移", lambda: self._move(-1)), ("下移", lambda: self._move(1)),
                           ("清空", self._clear)):
            btn = SoftButton(text, self)
            btn.setMinimumHeight(30)
            btn.clicked.connect(slot)
            bar.addWidget(btn)
        bar.addStretch(1)
        col.addLayout(bar)

        self.warning = CaptionLabel("", self)
        self.warning.setWordWrap(True)
        self.warning.setStyleSheet("color:#DC2626;font-size:11px;")
        self.warning.setVisible(False)
        col.addWidget(self.warning)

    def _validate(self) -> None:
        if not self._validator:
            return
        message = self._validator(self.paths()) if self.paths() else ""
        self.warning.setText(message)
        self.warning.setVisible(bool(message))

    def validate_now(self) -> str:
        self._validate()
        return self.warning.text() if self.warning.isVisible() else ""

    def _add(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, self._caption, "", self._filters)
        for p in paths:
            QListWidgetItem(p, self.list)
        if paths:
            self._validate()
            self.changed.emit()

    def _remove(self) -> None:
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))
        self._validate()
        self.changed.emit()

    def _clear(self) -> None:
        self.list.clear()
        self._validate()
        self.changed.emit()

    def _move(self, delta: int) -> None:
        row = self.list.currentRow()
        if row < 0:
            return
        item = self.list.takeItem(row)
        self.list.insertItem(max(0, min(self.list.count(), row + delta)), item)
        self.list.setCurrentRow(row + delta)
        self.changed.emit()

    def paths(self) -> list[str]:
        return [self.list.item(i).text() for i in range(self.list.count())]

    def set_paths(self, paths: list[str]) -> None:
        self.list.clear()
        for p in paths:
            QListWidgetItem(p, self.list)
        self._validate()
        self.changed.emit()


def guess_output(src: str, suffix: str, same_dir: bool = True) -> str:
    """根据源文件猜一个输出路径。"""
    if not src:
        return ""
    p = Path(src)
    return str(p.with_name(f"{p.stem}{suffix}"))
