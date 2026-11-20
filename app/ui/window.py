"""主窗口。"""
from __future__ import annotations

import platform

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    Action,
    CaptionLabel,
    FluentIcon as FIF,
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    MessageBox,
    NavigationItemPosition,
    NavigationWidget,
    RoundMenu,
    StrongBodyLabel,
)

from .. import APP_TITLE, APP_VERSION
from ..state import state
from .icon import build_icon
from .pages.clean import CleanPage
from .pages.contact import ContactPage
from .pages.dashboard import DashboardPage
from .pages.hardware import HardwarePage
from .pages.history import HistoryPage
from .pages.maintenance import MaintenancePage
from .pages.media import MediaPage
from .pages.settings import SettingsPage
from .pages.space import SpacePage
from .pages.startup import StartupPage
from .pages.uninstall import UninstallPage
from .theme import ACCENT, apply_theme, palette
from .widgets.icontile import IconTile
from .worker import HardwareWorker



class UserNavButton(NavigationWidget):
    """左下角用户卡：头像 + 名称 + 本机信息。"""

    def __init__(self, name: str, subtitle: str, parent=None) -> None:
        super().__init__(isSelectable=False, parent=parent)
        self.name = name or "本机"
        self.subtitle = subtitle
        self.expand_width = 180
        self.isCompacted = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(self.expand_width, 56)

    def setCompacted(self, isCompacted: bool) -> None:
        self.isCompacted = isCompacted
        self.setFixedSize(40 if isCompacted else self.expand_width, 56)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        bg = QColor(0, 0, 0, 0)
        if self.isPressed:
            bg = QColor(0, 0, 0, 18)
        elif self.isEnter:
            bg = QColor(0, 0, 0, 10)
        if bg.alpha():
            path = QPainterPath()
            path.addRoundedRect(rect, 8, 8)
            painter.fillPath(path, bg)

        size = 32
        x = (self.width() - size) / 2 if self.isCompacted else 8
        y = (self.height() - size) / 2
        avatar = QRectF(x, y, size, size)
        path = QPainterPath()
        path.addRoundedRect(avatar, 8, 8)
        painter.fillPath(path, QColor(ACCENT))
        painter.setPen(QColor("#FFFFFF"))
        f = QFont("Microsoft YaHei UI", 12)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(avatar, Qt.AlignCenter, self.name[:1])

        if not self.isCompacted:
            painter.setPen(QColor(p["text"]))
            f2 = QFont("Microsoft YaHei UI", 10)
            f2.setBold(True)
            painter.setFont(f2)
            painter.drawText(QRectF(50, 10, self.width() - 82, 20),
                             Qt.AlignLeft | Qt.AlignVCenter, self.name)
            painter.setPen(QColor(p["sub"]))
            f3 = QFont("Microsoft YaHei UI", 8)
            painter.setFont(f3)
            painter.drawText(QRectF(50, 29, self.width() - 82, 18),
                             Qt.AlignLeft | Qt.AlignVCenter, self.subtitle)
            painter.setPen(QColor(p["sub"]))
            cx = self.width() - 18
            cy = 28
            painter.drawLine(cx - 4, cy + 3, cx, cy - 1)
            painter.drawLine(cx, cy - 1, cx + 4, cy + 3)
        painter.end()

class MainWindow(FluentWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(build_icon())
        self.resize(1180, 820)
        self.setMinimumSize(1080, 720)
        self._fit_to_screen()
        try:
            self.setMicaEffectEnabled(False)
        except Exception:
            pass

        self.dashboard = DashboardPage(self)
        self.clean = CleanPage(self)
        self.media = MediaPage(self)
        self.space = SpacePage(self)
        self.hardware = HardwarePage(self)
        self.uninstall = UninstallPage(self)
        self.startup = StartupPage(self)
        self.maintenance = MaintenancePage(self)
        self.history = HistoryPage(self)
        self.contact = ContactPage(self)
        self.settings = SettingsPage(self)

        # 联系与设置不再占左侧导航，但仍要加入 StackedWidget 供菜单切换。
        self.stackedWidget.addWidget(self.contact)
        self.stackedWidget.addWidget(self.settings)

        self.addSubInterface(self.dashboard, FIF.HOME, "总览")
        self.addSubInterface(self.clean, FIF.BROOM, "清理")
        self.addSubInterface(self.media, FIF.PHOTO, "照片视频")
        self.addSubInterface(self.space, FIF.TILES, "空间分析")
        self.addSubInterface(self.hardware, FIF.FINGERPRINT, "硬件信息")
        self.addSubInterface(self.uninstall, FIF.APPLICATION, "应用卸载")
        self.addSubInterface(self.startup, FIF.SPEED_HIGH, "启动项")
        self.addSubInterface(self.maintenance, FIF.SYNC, "系统维护")
        self.addSubInterface(self.history, FIF.HISTORY, "记录")

        self.user_btn = UserNavButton(
            state.machine or "本机",
            f"本机 · {platform.system()}",
            self,
        )
        self.navigationInterface.addWidget(
            "user-menu",
            self.user_btn,
            onClick=self._show_user_menu,
            position=NavigationItemPosition.BOTTOM,
            tooltip=f"本机 · {platform.system()}",
        )

        try:
            self.navigationInterface.setExpandWidth(196)
            self.navigationInterface.setCollapsible(True)
            self.navigationInterface.expand(useAni=False)
        except Exception:
            pass

        self.dashboard.scan_requested.connect(self._scan_from_dashboard)
        self.dashboard.clean_requested.connect(self._clean_safe_from_dashboard)
        self.dashboard.goto_history.connect(lambda: self.switchTo(self.history))
        self.dashboard.goto_hardware.connect(self._show_hardware)
        self.dashboard.refresh_hardware.connect(self.load_hardware)
        self.hardware.refresh_requested.connect(self.load_hardware)
        self.clean.finished_clean.connect(self._after_clean)
        self.settings.theme_changed = self._apply_theme
        self.stackedWidget.currentChanged.connect(self._on_page_changed)

        self._hw_worker: HardwareWorker | None = None
        self.switchTo(self.dashboard)
        self.load_hardware()

    def _fit_to_screen(self) -> None:
        """初始窗口按可用桌面收缩并居中，避免底部导航被任务栏挡住。"""
        area = QGuiApplication.primaryScreen().availableGeometry()
        w = min(1180, max(900, area.width() - 40))
        h = min(820, max(600, area.height() - 40))
        self.setMinimumSize(min(1080, w), min(720, h))
        self.resize(w, h)
        self.move(area.left() + (area.width() - w) // 2,
                  area.top() + (area.height() - h) // 2)

    # ------------------------------------------------------------------ 左下角用户菜单
    def _show_user_menu(self) -> None:
        menu = RoundMenu(parent=self)
        header = QWidget(menu)
        h = QHBoxLayout(header)
        h.setContentsMargins(14, 12, 14, 10)
        h.setSpacing(10)
        h.addWidget(IconTile(FIF.HOME, ACCENT, 34, header), 0)
        col = QVBoxLayout()
        col.setSpacing(1)
        col.addWidget(StrongBodyLabel(state.machine or "本机", header))
        sub = CaptionLabel(f"本机 · {platform.system()}", header)
        sub.setStyleSheet(f"color:{palette()['sub']};")
        col.addWidget(sub)
        h.addLayout(col, 1)
        header.setFixedHeight(56)
        menu.addWidget(header, selectable=False)
        menu.addSeparator()

        actions = (
            (FIF.SETTING, "设置", lambda: self.switchTo(self.settings)),
            (FIF.HISTORY, "操作历史", lambda: self.switchTo(self.history)),
            (FIF.CHAT, "帮助与反馈", lambda: self.switchTo(self.contact)),
            (FIF.SYNC, "检查更新", self._check_update),
            (FIF.INFO, f"关于 {APP_TITLE}  v{APP_VERSION}", self._about),
        )
        for icon, text, slot in actions:
            action = Action(icon, text, menu)
            action.triggered.connect(slot)
            menu.addAction(action)

        menu.addSeparator()
        action = Action(FIF.RETURN, "收起侧边栏", menu)
        action.triggered.connect(self._collapse_nav)
        menu.addAction(action)

        menu.adjustSize()
        try:
            menu.view.scrollToTop()
        except Exception:
            pass
        menu.exec(self._user_menu_pos(menu))

    def _user_menu_pos(self, menu: RoundMenu) -> QPoint:
        """把菜单放在用户卡上方；空间不够就放下方，并限制在可用桌面内。"""
        anchor = self.user_btn.mapToGlobal(QPoint(0, 0))
        screen = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        w, h = menu.width(), menu.height()
        gap = 6

        x = max(area.left() + 4, min(anchor.x(), area.right() - w - 3))
        y = anchor.y() - h - gap
        if y < area.top() + 4:
            y = anchor.y() + self.user_btn.height() + gap
        y = max(area.top() + 4, min(y, area.bottom() - h - 3))

        # RoundMenu.exec() 会减掉自身内容边距再定位，这里补回偏移。
        margins = menu.layout().contentsMargins()
        return QPoint(x + margins.left(), y + 4)

    def _check_update(self) -> None:
        InfoBar.info("检查更新", "当前已是最新版本（演示）", parent=self,
                     position=InfoBarPosition.TOP_RIGHT, duration=2600)

    def _about(self) -> None:
        box = MessageBox(
            f"关于 {APP_TITLE}",
            f"{APP_TITLE}  v{APP_VERSION}\n\n"
            "本机维护工具：清理、照片视频、空间分析、硬件信息、应用卸载、启动项、系统维护。",
            self,
        )
        box.cancelButton.hide()
        box.yesButton.setText("知道了")
        box.exec()

    def _collapse_nav(self) -> None:
        try:
            self.navigationInterface.collapse()
        except Exception:
            pass

    # ------------------------------------------------------------------ 硬件信息
    def load_hardware(self) -> None:
        if self._hw_worker and self._hw_worker.isRunning():
            return
        state.hw_loading = True
        self.dashboard.hw_panel.set_loading()
        if not state.hardware_ready():
            self.hardware.set_loading()
        self._hw_worker = HardwareWorker(self)
        self._hw_worker.done.connect(self._on_hardware_ready)
        self._hw_worker.start()

    def _on_hardware_ready(self, _data) -> None:
        self.dashboard.refresh_hw_panel()
        self.hardware.set_data(state.hw_sections)
        self.contact.refresh_info()
        self.settings.refresh_contact()

    def _show_hardware(self) -> None:
        self.switchTo(self.hardware)

    # ------------------------------------------------------------------ 其他槽
    def _scan_from_dashboard(self) -> None:
        self.switchTo(self.clean)
        self.clean.start_scan()

    def _clean_safe_from_dashboard(self) -> None:
        for item in state.items:
            state.selected[item.key] = item.risk != "high" and item.default_selected
        self.switchTo(self.clean)
        self.clean._render_items()
        for key, card in self.clean._cards.items():
            card.set_checked(state.selected.get(key, False))
        self.clean._update_summary()
        self.clean.start_clean()

    def _after_clean(self) -> None:
        self.dashboard.refresh()
        self.history.refresh()

    def _on_page_changed(self, _index: int) -> None:
        widget = self.stackedWidget.currentWidget()
        if widget is self.dashboard:
            self.dashboard.refresh()
        elif widget is self.hardware and not state.hardware_ready() and not state.hw_loading:
            self.load_hardware()

    def _apply_theme(self, mode: str) -> None:
        apply_theme(mode)
        self.setStyleSheet("")
        for page in (self.dashboard, self.clean, self.media, self.space,
                     self.hardware, self.uninstall, self.startup, self.maintenance,
                     self.history, self.contact, self.settings):
            page.update()
        self.dashboard.refresh()
        self.hardware.set_data(state.hw_sections)
