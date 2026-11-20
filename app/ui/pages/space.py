"""空间分析：treemap、30 天变化、重复文件（演示数据）。"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    ComboBox,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    SegmentedWidget,
    StrongBodyLabel,
)

from ...core.sizes import human_size
from ...demo_data import DUPLICATE_GROUPS, SPACE_HISTORY, SPACE_TREE
from ..theme import ACCENT, INFO, SUCCESS, WARNING, palette
from ..widgets.base import Badge, Page, SectionCard, StatCard
from ..widgets.buttons import GradientButton, OutlineButton, SoftButton


class TreemapWidget(QWidget):
    """简化的 slice-and-dice treemap，两级目录。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.items = SPACE_TREE
        self.setMinimumHeight(430)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(palette()["surface_2"]))
        painter.drawRoundedRect(rect, 12, 12)
        self._draw_items(painter, self.items, rect.adjusted(6, 6, -6, -6), True)
        painter.end()

    def _draw_items(self, painter: QPainter, items: list[dict], rect: QRectF,
                    horizontal: bool) -> None:
        total = sum(max(0, int(i.get("size", 0))) for i in items)
        if total <= 0 or rect.width() < 8 or rect.height() < 8:
            return
        offset = 0.0
        for item in items:
            frac = max(0, int(item.get("size", 0))) / total
            if horizontal:
                r = QRectF(rect.x(), rect.y() + offset, rect.width(), rect.height() * frac)
            else:
                r = QRectF(rect.x() + offset, rect.y(), rect.width() * frac, rect.height())
            offset += (rect.height() if horizontal else rect.width()) * frac
            inner = r.adjusted(3, 3, -3, -3)
            if inner.width() < 8 or inner.height() < 8:
                continue

            color = QColor(item.get("color", "#4C6FFF"))
            path = QPainterPath()
            path.addRoundedRect(inner, 6, 6)
            painter.setPen(QPen(color.lighter(135), 1))
            fill = QColor(color)
            fill.setAlpha(170)
            painter.setBrush(fill)
            painter.drawPath(path)

            if inner.width() > 56 and inner.height() > 22:
                painter.setPen(QColor("#FFFFFF"))
                font = QFont("Microsoft YaHei UI", 9, QFont.DemiBold)
                painter.setFont(font)
                text = str(item.get("name", ""))
                painter.drawText(inner.adjusted(7, 4, -7, 0),
                                 Qt.AlignLeft | Qt.AlignTop, text)
            if inner.width() > 72 and inner.height() > 42:
                painter.setPen(QColor(255, 255, 255, 210))
                font = QFont("Microsoft YaHei UI", 8)
                painter.setFont(font)
                painter.drawText(inner.adjusted(7, 0, -7, -5),
                                 Qt.AlignLeft | Qt.AlignBottom,
                                 human_size(item.get("size", 0)))

            children = item.get("children") or []
            if children:
                self._draw_items(painter, children, inner.adjusted(4, 20, -4, -4), not horizontal)


class SpaceChangeChart(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.data = SPACE_HISTORY
        self.setMinimumHeight(320)

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self.data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        p = palette()
        rect = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(p["surface_2"]))
        painter.drawRoundedRect(rect, 12, 12)

        plot = rect.adjusted(52, 26, -22, -36)
        values = [v for _l, v in self.data]
        lo, hi = min(values) - 1, max(values) + 1
        span = max(1.0, hi - lo)

        # 网格
        painter.setPen(QPen(QColor(p["border"]), 1))
        for i in range(5):
            y = plot.bottom() - plot.height() * i / 4
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(QColor(p["muted"]))
            painter.setFont(QFont("Microsoft YaHei UI", 8))
            painter.drawText(QRectF(4, y - 9, 42, 18), Qt.AlignRight | Qt.AlignVCenter,
                             f"{lo + span * i / 4:.0f}")
            painter.setPen(QPen(QColor(p["border"]), 1))

        # 面积 + 折线
        path = QPainterPath()
        points = []
        for i, (_label, value) in enumerate(self.data):
            x = plot.left() + plot.width() * i / max(1, len(self.data) - 1)
            y = plot.bottom() - plot.height() * (value - lo) / span
            points.append(QPointF(x, y))
        path.moveTo(points[0].x(), plot.bottom())
        for pt in points:
            path.lineTo(pt)
        path.lineTo(points[-1].x(), plot.bottom())
        path.closeSubpath()
        fill = QColor(ACCENT)
        fill.setAlpha(34)
        painter.setBrush(fill)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

        painter.setPen(QPen(QColor(ACCENT), 2.2))
        for i in range(1, len(points)):
            painter.drawLine(points[i - 1], points[i])
        painter.setBrush(QColor(ACCENT))
        for i, pt in enumerate(points):
            if i % 5 == 0 or i == len(points) - 1:
                painter.drawEllipse(pt, 3.2, 3.2)

        # x 标签
        painter.setPen(QColor(p["muted"]))
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        for i, (label, _v) in enumerate(self.data):
            if i % 5 == 0 or i == len(self.data) - 1:
                x = plot.left() + plot.width() * i / max(1, len(self.data) - 1)
                painter.drawText(QRectF(x - 30, plot.bottom() + 8, 60, 18),
                                 Qt.AlignHCenter | Qt.AlignTop, label)

        # 最新值
        painter.setPen(QColor(p["text"]))
        painter.setFont(QFont("Microsoft YaHei UI", 11, QFont.DemiBold))
        painter.drawText(QRectF(plot.left(), 2, 220, 22), Qt.AlignLeft | Qt.AlignVCenter,
                         f"已用 {values[-1]:.1f} GB")
        painter.end()


class DuplicatePanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        total = sum(g["size"] * (len(g["copies"]) - 1) for g in DUPLICATE_GROUPS)
        head = QHBoxLayout()
        tip = CaptionLabel(f"{len(DUPLICATE_GROUPS)} 组重复 · 可回收约 {human_size(total)}", self)
        tip.setStyleSheet(f"color:{palette()['sub']};")
        head.addWidget(tip)
        head.addStretch(1)
        btn = SoftButton("只看照片/视频", self)
        btn.clicked.connect(lambda: InfoBar.info("演示", "这里会按媒体类型筛选重复组", parent=self,
                                                 position=InfoBarPosition.TOP_RIGHT, duration=2200))
        head.addWidget(btn)
        root.addLayout(head)

        for group in DUPLICATE_GROUPS:
            root.addWidget(self._build_group(group))

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        btn_clean = GradientButton("清理选中副本", self)
        btn_clean.clicked.connect(lambda: InfoBar.success("演示模式", "正式版会保留一份并清理其余副本",
                                                         parent=self, position=InfoBarPosition.TOP_RIGHT,
                                                         duration=2600))
        bottom.addWidget(btn_clean)
        root.addLayout(bottom)

    def _build_group(self, group: dict) -> QWidget:
        card = CardWidget(self)
        card.setMinimumHeight(96)
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)

        for idx in range(min(3, len(group["copies"]))):
            mini = QLabel(card)
            mini.setFixedSize(64, 46)
            mini.setStyleSheet(
                f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {group['c1']},stop:1 {group['c2']});"
                "border-radius:7px;color:#FFFFFF;font-size:11px;font-weight:600;"
            )
            mini.setAlignment(Qt.AlignCenter)
            mini.setText(group["kind"])
            row.addWidget(mini)

        col = QVBoxLayout()
        col.setSpacing(3)
        name = StrongBodyLabel(group["name"], card)
        col.addWidget(name)
        meta = CaptionLabel(
            f"{len(group['copies'])} 个副本 · 每个 {human_size(group['size'])} · "
            f"可回收 {human_size(group['size'] * (len(group['copies']) - 1))}",
            card,
        )
        meta.setStyleSheet(f"color:{palette()['sub']};")
        col.addWidget(meta)
        path = CaptionLabel(group["copies"][0][0], card)
        path.setStyleSheet(f"color:{palette()['muted']};font-size:11px;")
        col.addWidget(path)
        row.addLayout(col, 1)

        row.addWidget(Badge("重复", "normal", card))
        btn = OutlineButton("查看", card)
        btn.setMinimumHeight(30)
        btn.clicked.connect(lambda: InfoBar.info("演示", group["name"], parent=self,
                                                 position=InfoBarPosition.TOP_RIGHT, duration=2200))
        row.addWidget(btn)
        return card


class SpacePage(Page):
    def __init__(self, parent=None) -> None:
        super().__init__("空间分析", "空间分布、30 天变化与重复文件（演示数据）", parent)
        self.add_widget(self._build_toolbar())
        self.add_widget(self._build_tabs())
        self.add_stretch()

    def _build_toolbar(self) -> QWidget:
        card = SectionCard("磁盘", "切换磁盘后重新分析；演示数据不会真正扫描", FIF.SAVE)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.disk = ComboBox()
        self.disk.addItem("本地磁盘 (C:)")
        self.disk.addItem("软件 (D:)")
        row.addWidget(self.disk)
        row.addStretch(1)
        btn_snapshot = OutlineButton("保存快照")
        btn_snapshot.clicked.connect(lambda: InfoBar.success("已保存快照（演示）", "差异会出现在「空间变化」",
                                                             parent=self, position=InfoBarPosition.TOP_RIGHT,
                                                             duration=2400))
        row.addWidget(btn_snapshot)
        btn = GradientButton("重新分析")
        btn.clicked.connect(lambda: InfoBar.info("演示模式", "正式版会后台扫描并绘制 treemap",
                                                 parent=self, position=InfoBarPosition.TOP_RIGHT,
                                                 duration=2400))
        row.addWidget(btn)
        card.content_layout.addLayout(row)
        return card

    def _build_tabs(self) -> QWidget:
        card = SectionCard("分析结果", "", FIF.PIE_SINGLE)
        self.seg = SegmentedWidget()
        self.seg.addItem("map", "空间分布")
        self.seg.addItem("history", "空间变化")
        self.seg.addItem("dupes", "重复文件")
        self.seg.setCurrentItem("map")
        self.seg.currentItemChanged.connect(self._on_tab)
        card.content_layout.addWidget(self.seg)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_map())
        self.stack.addWidget(self._build_history())
        self.stack.addWidget(self._build_dupes())
        card.content_layout.addWidget(self.stack)
        return card

    def _on_tab(self, key: str) -> None:
        self.stack.setCurrentIndex({"map": 0, "history": 1, "dupes": 2}.get(key, 0))

    def _build_map(self) -> QWidget:
        host = QWidget()
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        row.addWidget(TreemapWidget(host), 3)

        legend = QVBoxLayout()
        legend.setSpacing(8)
        legend.addWidget(StrongBodyLabel("占用最大的目录", host))
        for item in SPACE_TREE[:5]:
            line = QHBoxLayout()
            dot = QLabel(host)
            dot.setFixedSize(9, 9)
            dot.setStyleSheet(f"background:{item['color']};border-radius:4px;")
            line.addWidget(dot)
            line.addWidget(BodyLabel(item["name"], host))
            line.addStretch(1)
            val = CaptionLabel(human_size(item["size"]), host)
            val.setStyleSheet(f"color:{palette()['sub']};")
            line.addWidget(val)
            legend.addLayout(line)
        legend.addStretch(1)
        row.addLayout(legend, 1)
        return host

    def _build_history(self) -> QWidget:
        host = QWidget()
        col = QVBoxLayout(host)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(10)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        stats.addWidget(StatCard(FIF.SAVE, "当前已用", "131.6 GB", "C: 总容量 190.9 GB", ACCENT, host))
        stats.addWidget(StatCard(FIF.SYNC, "本周增长", "+3.2 GB", "视频与截图", WARNING, host))
        stats.addWidget(StatCard(FIF.BROOM, "可回收", "8.4 GB", "重复 / 缓存 / 旧安装", SUCCESS, host))
        col.addLayout(stats)
        col.addWidget(SpaceChangeChart(host))
        return host

    def _build_dupes(self) -> QWidget:
        host = QWidget()
        col = QVBoxLayout(host)
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(DuplicatePanel(host))
        return host
