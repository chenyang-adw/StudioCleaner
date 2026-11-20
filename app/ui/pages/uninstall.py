"""应用卸载页：列表 + 批量卸载 + 残留扫描（布局参考 MangoDisk）。"""
from __future__ import annotations

import os
import re
import subprocess

from PySide6.QtCore import QFileInfo, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileIconProvider,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    CheckBox,
    ComboBox,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    MessageBox,
    SegmentedWidget,
    StrongBodyLabel,
)

from ...core.processes import running_image_names
from ...core.sizes import human_size
from ...core.uninstaller import (
    InstalledApp,
    Leftover,
    delete_leftover,
    launch_uninstaller,
    list_installed,
    remove_uninstall_entry,
    scan_leftovers,
)
from ..theme import ACCENT, palette
from ..widgets.base import Badge, Page, SectionCard
from ..widgets.buttons import GradientButton, OutlineButton
from ..worker import FuncWorker


def _open_folder(path: str) -> None:
    if not path:
        return
    if os.path.isdir(path):
        os.startfile(path)  # type: ignore[attr-defined]
    elif os.path.isfile(path):
        subprocess.Popen(["explorer", "/select,", path])
    else:
        parent = os.path.dirname(path)
        if parent and os.path.isdir(parent):
            os.startfile(parent)  # type: ignore[attr-defined]


def _app_icon(app: InstalledApp) -> QIcon:
    for value in (app.display_icon, app.install_location, app.uninstall_string):
        if not value:
            continue
        path = str(value).split(",")[0].strip().strip('"')
        if os.path.isfile(path):
            icon = QFileIconProvider().icon(QFileInfo(path))
            if not icon.isNull():
                return icon
    try:
        return FIF.APPLICATION.icon()
    except Exception:
        return QIcon()


_ALIASES = {
    "microsoft edge": "msedge",
    "微信": "weixin",
    "qq": "qq",
    "抖音": "douyin",
    "豆包": "doubao",
    "chatgpt": "chatgpt",
    "clash verge": "clash-verge",
    "comfy desktop": "comfy",
    "deepseek harness": "deepseek",
    "workbuddy": "workbuddy",
    "夸克": "quark",
    "百度网盘": "baidunetdisk",
}


def _candidate_names(app: InstalledApp) -> set[str]:
    names: set[str] = set()
    for value in (app.name, app.display_icon, app.uninstall_string, app.install_location):
        if not value:
            continue
        path = str(value).split(",")[0].strip().strip('"')
        stem = os.path.splitext(os.path.basename(path))[0].lower()
        if stem:
            names.add(stem)
    norm = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", app.name.lower())
    if norm:
        names.add(norm)
    alias = _ALIASES.get(app.name.strip().lower())
    if alias:
        names.add(alias)
    return names


def _is_running(app: InstalledApp, running: set[str]) -> bool:
    if not running:
        return False
    candidates = _candidate_names(app)
    for proc in running:
        stem = os.path.splitext(proc)[0].lower()
        if stem in candidates:
            return True
        if any(len(c) >= 4 and c in stem for c in candidates):
            return True
    return False


class AppRow(CardWidget):
    toggled = Signal(str, bool)
    activated = Signal(object)
    uninstall_requested = Signal(object)

    def __init__(self, app: InstalledApp, running: bool, parent=None) -> None:
        super().__init__(parent)
        self.app = app
        self.setObjectName("AppRow")
        self.setMinimumHeight(92)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._active = False
        self._apply_style()

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 16, 10)
        row.setSpacing(12)

        self.check = CheckBox(self)
        self.check.stateChanged.connect(
            lambda _s: self.toggled.emit(self.app.key, self.check.isChecked())
        )
        row.addWidget(self.check, 0, Qt.AlignVCenter)

        icon = QLabel(self)
        icon.setFixedSize(42, 42)
        icon.setAlignment(Qt.AlignCenter)
        icon.setPixmap(_app_icon(app).pixmap(32, 32))
        icon.setStyleSheet("background:transparent;")
        row.addWidget(icon, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(3)
        name_row = QHBoxLayout()
        name_row.setSpacing(7)
        name = StrongBodyLabel(app.name, self)
        name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        name_row.addWidget(name)
        if not app.uninstall_string:
            name_row.addWidget(Badge("不可卸载", "muted", self))
        elif running:
            name_row.addWidget(Badge("需关闭应用", "normal", self))
        else:
            name_row.addWidget(Badge("可卸载", "safe", self))
        if app.suspicious()[0]:
            name_row.addWidget(Badge("疑似捆绑", "high", self))
        name_row.addStretch(1)
        col.addLayout(name_row)

        sub = CaptionLabel(
            f"{app.publisher or '未知发布者'} · 版本 {app.version or '-'}", self
        )
        sub.setStyleSheet(f"color:{palette()['sub']};")
        sub.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        col.addWidget(sub)

        path = CaptionLabel(app.install_location or app.uninstall_string or "无安装路径", self)
        path.setStyleSheet(f"color:{palette()['muted']};font-size:11px;")
        path.setMaximumWidth(560)
        path.setMinimumWidth(0)
        path.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        path.setToolTip(app.install_location or app.uninstall_string or "")
        col.addWidget(path)
        row.addLayout(col, 1)

        size = StrongBodyLabel(app.size_text() if app.size_kb else "未知", self)
        size.setFixedWidth(86)
        size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        size.setStyleSheet(f"color:{ACCENT};font-weight:600;")
        row.addWidget(size, 0, Qt.AlignVCenter)

        date = CaptionLabel(app.date_text() if app.install_date else "未知", self)
        date.setFixedWidth(86)
        date.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        date.setStyleSheet(f"color:{palette()['sub']};")
        row.addWidget(date, 0, Qt.AlignVCenter)

        btn = OutlineButton("卸载", self)
        btn.setMinimumHeight(30)
        btn.setFixedWidth(64)
        btn.clicked.connect(lambda: self.uninstall_requested.emit(self.app))
        row.addWidget(btn, 0, Qt.AlignVCenter)

    def _apply_style(self) -> None:
        p = palette()
        border = ACCENT if self._active else p["border"]
        self.setStyleSheet(
            f"CardWidget#AppRow{{background:{p['surface']};border:1px solid {border};"
            "border-radius:12px;}"
            f"CardWidget#AppRow:hover{{border-color:{ACCENT};}}"
        )

    def set_active(self, active: bool) -> None:
        self._active = bool(active)
        self._apply_style()

    def set_checked(self, checked: bool) -> None:
        self.check.blockSignals(True)
        self.check.setChecked(bool(checked))
        self.check.blockSignals(False)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.activated.emit(self.app)
        super().mousePressEvent(event)


class UninstallPage(Page):
    def __init__(self, parent=None) -> None:
        super().__init__("应用卸载", "列出已安装应用，支持批量卸载、打开目录与残留扫描", parent)
        # 页面本身是全窗口宽；给左侧导航留出右侧空间，避免右侧按钮被裁切。
        self.body_layout.setContentsMargins(0, 4, 196, 24)
        self._apps: list[InstalledApp] = []
        self._running: set[str] = set()
        self._rows: dict[str, AppRow] = {}
        self._selected: set[str] = set()
        self._current: InstalledApp | None = None
        self._mode = "all"
        self._leftovers: list[tuple[Leftover, CheckBox]] = []
        self._worker: FuncWorker | None = None

        self.add_widget(self._build_summary())
        self.add_widget(self._build_list())
        self.add_widget(self._build_actions())
        self.leftover_card = self._build_leftovers()
        self.add_widget(self.leftover_card)
        self.leftover_card.setVisible(False)
        self.add_stretch()
        self.reload()

    # ------------------------------------------------------------- 顶部
    def _build_summary(self) -> QWidget:
        card = SectionCard("应用总览", "数据来自系统卸载登记表", FIF.APPLICATION)
        row = QHBoxLayout()
        row.setSpacing(14)
        self.count_label = QLabel("0 个应用", card)
        self.count_label.setStyleSheet(f"color:{palette()['text']};font-size:26px;font-weight:700;")
        row.addWidget(self.count_label)
        self.size_label = QLabel("估算 0 B", card)
        self.size_label.setStyleSheet(f"color:{ACCENT};font-size:18px;font-weight:600;")
        row.addWidget(self.size_label)
        row.addStretch(1)
        btn = GradientButton("重新扫描", card)
        btn.clicked.connect(self.reload)
        row.addWidget(btn)
        card.content_layout.addLayout(row)

        self.state_label = CaptionLabel("正在读取已安装应用…", card)
        self.state_label.setStyleSheet(f"color:{palette()['sub']};")
        card.content_layout.addWidget(self.state_label)

        self.seg = SegmentedWidget()
        for key, text in (
            ("all", "全部"), ("uninstall", "可卸载"),
            ("running", "正在运行"), ("blocked", "不可卸载"),
        ):
            self.seg.addItem(key, text)
        self.seg.setCurrentItem("all")
        self.seg.currentItemChanged.connect(self._on_filter)
        card.content_layout.addWidget(self.seg)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.search = LineEdit()
        self.search.setPlaceholderText("搜索应用、发布者或路径…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _t: self._render_list())
        bar.addWidget(self.search, 1)

        self.sort = ComboBox()
        self.sort.addItem("按名称排序", userData="name")
        self.sort.addItem("按大小排序", userData="size")
        self.sort.addItem("按安装日期排序", userData="date")
        self.sort.currentIndexChanged.connect(lambda _i: self._render_list())
        bar.addWidget(self.sort)

        self.show_system = CheckBox("显示系统项", card)
        self.show_system.setChecked(False)
        self.show_system.setToolTip("当前版本已过滤系统组件；勾选不会改变数据（演示）")
        bar.addWidget(self.show_system)
        card.content_layout.addLayout(bar)
        return card

    # ------------------------------------------------------------- 列表
    def _build_list(self) -> QWidget:
        card = SectionCard("应用列表", "勾选后可批量卸载；点击一行查看操作", FIF.TILES)
        self.list_holder = QWidget(card)
        self.list_layout = QVBoxLayout(self.list_holder)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(7)
        card.content_layout.addWidget(self.list_holder)
        return card

    # ------------------------------------------------------------- 操作
    def _build_actions(self) -> QWidget:
        card = SectionCard("操作", "卸载会调用应用自带卸载程序；残留扫描会先备份注册表", FIF.DELETE)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.sel_label = StrongBodyLabel("已选择 0 个应用 · 0 B", card)
        row.addWidget(self.sel_label)
        row.addStretch(1)
        self.btn_open = OutlineButton("打开安装目录", card)
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self._open_location)
        row.addWidget(self.btn_open)
        self.btn_scan = OutlineButton("扫描卸载残留", card)
        self.btn_scan.setEnabled(False)
        self.btn_scan.clicked.connect(self._scan_leftovers)
        row.addWidget(self.btn_scan)
        self.btn_force = OutlineButton("强制移除记录", card)
        self.btn_force.setEnabled(False)
        self.btn_force.clicked.connect(self._force_remove)
        row.addWidget(self.btn_force)
        self.btn_uninstall = GradientButton("卸载所选应用", card)
        self.btn_uninstall.setEnabled(False)
        self.btn_uninstall.clicked.connect(self._uninstall_selected)
        row.addWidget(self.btn_uninstall)
        card.content_layout.addLayout(row)
        return card

    def _build_leftovers(self) -> QWidget:
        card = SectionCard("卸载残留", "扫描到的残留目录与注册表项，勾选后删除（注册表会先备份）", FIF.DELETE)
        self.leftover_box = QVBoxLayout()
        self.leftover_box.setSpacing(4)
        card.content_layout.addLayout(self.leftover_box)
        row = QHBoxLayout()
        row.addStretch(1)
        btn_all = OutlineButton("全选")
        btn_all.clicked.connect(lambda: [cb.setChecked(True) for _it, cb in self._leftovers])
        row.addWidget(btn_all)
        btn_close = OutlineButton("收起")
        btn_close.clicked.connect(lambda: self.leftover_card.setVisible(False))
        row.addWidget(btn_close)
        self.btn_delete_leftover = GradientButton("删除勾选残留")
        self.btn_delete_leftover.clicked.connect(self._delete_leftovers)
        row.addWidget(self.btn_delete_leftover)
        card.content_layout.addLayout(row)
        return card

    # ------------------------------------------------------------- 数据
    def _load_data(self):
        return list_installed(), running_image_names()

    def reload(self) -> None:
        self.state_label.setText("正在读取已安装应用…")
        if self._worker and self._worker.isRunning():
            return
        self._worker = FuncWorker(self._load_data, parent=self)
        self._worker.done.connect(self._on_loaded)
        self._worker.failed.connect(lambda msg: self.state_label.setText(f"读取失败：{msg}"))
        self._worker.start()

    def _on_loaded(self, data) -> None:
        apps, running = data
        self._apps = apps or []
        self._running = running or set()
        total = sum(a.size_kb * 1024 for a in self._apps if a.size_kb)
        uninstallable = sum(1 for a in self._apps if a.uninstall_string)
        running_count = sum(1 for a in self._apps if _is_running(a, self._running))
        blocked = len(self._apps) - uninstallable
        self.count_label.setText(f"{len(self._apps)} 个应用")
        self.size_label.setText(f"估算 {human_size(total)}")
        self.state_label.setText(
            f"可卸载 {uninstallable}　·　正在运行 {running_count}　·　不可卸载 {blocked}"
        )
        self._render_list()

    def _on_filter(self, key: str) -> None:
        self._mode = key
        self._render_list()

    def _filtered(self) -> list[InstalledApp]:
        text = self.search.text().strip().lower() if hasattr(self, "search") else ""
        rows: list[InstalledApp] = []
        for app in self._apps:
            if text and text not in app.name.lower() and text not in app.publisher.lower() \
                    and text not in (app.install_location or "").lower():
                continue
            running = _is_running(app, self._running)
            if self._mode == "uninstall" and not app.uninstall_string:
                continue
            if self._mode == "running" and not running:
                continue
            if self._mode == "blocked" and app.uninstall_string:
                continue
            rows.append(app)
        mode = self.sort.currentData() if hasattr(self, "sort") else "name"
        if mode == "size":
            rows.sort(key=lambda a: a.size_kb, reverse=True)
        elif mode == "date":
            rows.sort(key=lambda a: a.install_date, reverse=True)
        else:
            rows.sort(key=lambda a: a.name.lower())
        return rows

    def _render_list(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.hide()
                w.deleteLater()
        self._rows.clear()

        for app in self._filtered():
            running = _is_running(app, self._running)
            row = AppRow(app, running, self.list_holder)
            row.toggled.connect(self._on_toggle)
            row.activated.connect(self._on_active)
            row.uninstall_requested.connect(self._uninstall_one)
            row.set_checked(app.key in self._selected)
            row.set_active(self._current is not None and app.key == self._current.key)
            self.list_layout.addWidget(row)
            self._rows[app.key] = row
        self._update_actions()

    # ------------------------------------------------------------- 选择
    def _on_toggle(self, key: str, checked: bool) -> None:
        if checked:
            self._selected.add(key)
        else:
            self._selected.discard(key)
        self._update_actions()

    def _on_active(self, app: InstalledApp) -> None:
        self._current = app
        for key, row in self._rows.items():
            row.set_active(key == app.key)
        self._update_actions()

    def _selected_apps(self) -> list[InstalledApp]:
        return [a for a in self._apps if a.key in self._selected]

    def _update_actions(self) -> None:
        chosen = self._selected_apps()
        total = sum(a.size_kb * 1024 for a in chosen if a.size_kb)
        self.sel_label.setText(f"已选择 {len(chosen)} 个应用 · {human_size(total)}")
        self.btn_uninstall.setEnabled(bool(chosen))
        has_current = self._current is not None
        self.btn_open.setEnabled(has_current)
        self.btn_scan.setEnabled(has_current)
        self.btn_force.setEnabled(has_current)

    # ------------------------------------------------------------- 动作
    def _confirm(self, title: str, text: str, ok_text: str) -> bool:
        box = MessageBox(title, text, self)
        box.yesButton.setText(ok_text)
        box.cancelButton.setText("取消")
        return bool(box.exec())

    def _uninstall_selected(self) -> None:
        chosen = self._selected_apps()
        if not chosen:
            InfoBar.warning("未选择应用", "请先勾选要卸载的应用", parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=2500)
            return
        names = "\n".join(f"· {a.name}" for a in chosen[:8])
        if len(chosen) > 8:
            names += f"\n… 以及另外 {len(chosen) - 8} 个"
        if not self._confirm(
            "确认卸载",
            f"将依次启动以下应用自带的卸载程序：\n\n{names}\n\n"
            "卸载完成后可选中应用并扫描残留。",
            "开始卸载",
        ):
            return
        ok_count = 0
        for app in chosen:
            ok, _msg = launch_uninstaller(app)
            if ok:
                ok_count += 1
        InfoBar.success("已启动卸载程序", f"成功启动 {ok_count}/{len(chosen)} 个", parent=self,
                        position=InfoBarPosition.TOP_RIGHT, duration=3500)

    def _uninstall_one(self, app: InstalledApp) -> None:
        if not self._confirm(
            "确认卸载",
            f"即将启动「{app.name}」自带的卸载程序。\n\n"
            "卸载完成后建议点击「扫描卸载残留」。",
            "启动卸载",
        ):
            return
        ok, msg = launch_uninstaller(app)
        if ok:
            InfoBar.success("已启动卸载程序", msg, parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=3500)
        else:
            InfoBar.error("无法卸载", msg, parent=self,
                          position=InfoBarPosition.TOP_RIGHT, duration=5000)

    def _open_location(self) -> None:
        app = self._current
        if not app:
            return
        target = app.install_location or app.display_icon
        if not target:
            InfoBar.warning("无路径", "该应用没有登记安装目录", parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=2500)
            return
        _open_folder(os.path.expandvars(target.strip('"').split(",")[0]))

    def _force_remove(self) -> None:
        app = self._current
        if not app:
            return
        if not self._confirm(
            "强制移除卸载记录",
            f"仅删除「{app.name}」在系统卸载登记表中的记录，不删除程序文件。\n"
            "删除前会自动备份注册表。",
            "移除记录",
        ):
            return
        ok, msg = remove_uninstall_entry(app)
        if ok:
            InfoBar.success("已移除", msg, parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=3000)
            self.reload()
        else:
            InfoBar.error("移除失败", msg, parent=self,
                          position=InfoBarPosition.TOP_RIGHT, duration=4000)

    def _scan_leftovers(self) -> None:
        app = self._current
        if not app:
            return
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("扫描中…")
        worker = FuncWorker(scan_leftovers, app, parent=self)
        worker.done.connect(lambda items: self._on_leftovers(app, items))
        worker.failed.connect(lambda msg: self._on_leftover_failed(msg))
        worker.start()
        self._scan_worker = worker

    def _on_leftover_failed(self, msg: str) -> None:
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("扫描卸载残留")
        InfoBar.error("扫描失败", msg, parent=self,
                      position=InfoBarPosition.TOP_RIGHT, duration=4000)

    def _on_leftovers(self, app: InstalledApp, items: list[Leftover]) -> None:
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("扫描卸载残留")
        while self.leftover_box.count():
            entry = self.leftover_box.takeAt(0)
            w = entry.widget()
            if w is not None:
                w.setParent(None)
                w.hide()
                w.deleteLater()
        self._leftovers.clear()
        if not items:
            tip = CaptionLabel(f"「{app.name}」没有发现残留", self)
            tip.setStyleSheet(f"color:{palette()['success']};")
            self.leftover_box.addWidget(tip)
            self.leftover_card.setVisible(True)
            return
        total = sum(i.size for i in items if i.kind == "file")
        head = BodyLabel(f"「{app.name}」发现 {len(items)} 项残留，合计约 {human_size(total)}")
        head.setStyleSheet(f"color:{palette()['text']};font-weight:600;")
        self.leftover_box.addWidget(head)
        for item in items:
            cb = CheckBox(f"{item.path}　（{item.detail}，{item.size_text()}）", self)
            cb.setChecked(True)
            cb.setStyleSheet(f"color:{palette()['sub']};")
            self.leftover_box.addWidget(cb)
            self._leftovers.append((item, cb))
        self.leftover_card.setVisible(True)

    def _delete_leftovers(self) -> None:
        chosen = [item for item, cb in self._leftovers if cb.isChecked()]
        if not chosen:
            InfoBar.warning("未勾选", "请先勾选要删除的残留项", parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=2500)
            return
        if not self._confirm(
            "确认删除残留",
            f"将删除 {len(chosen)} 项残留，删除后不可恢复。\n"
            "目录会被递归删除，注册表项会先自动备份。",
            "删除",
        ):
            return
        ok_count = 0
        fails = []
        for item in chosen:
            ok, msg = delete_leftover(item)
            if ok:
                ok_count += 1
            else:
                fails.append(f"{item.path}：{msg}")
        if fails:
            InfoBar.warning("部分删除失败", "\n".join(fails[:3]), parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=6000)
        else:
            InfoBar.success("删除完成", f"已清理 {ok_count} 项残留", parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=3000)
        self.leftover_card.setVisible(False)
        self.reload()
