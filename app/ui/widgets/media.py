"""照片/视频卡片与预览对话框。"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    StrongBodyLabel,
)

from ...core.sizes import human_size
from ..theme import ACCENT, palette
from .base import Badge
from .buttons import GradientButton, OutlineButton


class ThumbnailWidget(QWidget):
    """用渐变和图形生成缩略图，不依赖外部图片。"""

    view_requested = Signal(object)
    selection_changed = Signal(object, bool)

    def __init__(self, item, width: int = 236, height: int = 132,
                 show_controls: bool = True, parent=None) -> None:
        super().__init__(parent)
        self.item = item
        self.show_controls = show_controls
        self.setFixedSize(width, height)
        self.setCursor(Qt.PointingHandCursor)

        self.check: QPushButton | None = None
        self.view_btn: QPushButton | None = None
        self.size_badge: QLabel | None = None
        self._cleaned = False

        if show_controls:
            self.check = QPushButton(self)
            self.check.setCheckable(True)
            self.check.setFixedSize(24, 24)
            self.check.setCursor(Qt.PointingHandCursor)
            self.check.setStyleSheet(
                "QPushButton{background:rgba(15,23,42,0.55);border:1px solid rgba(255,255,255,0.8);"
                "border-radius:8px;color:#FFFFFF;font-weight:700;font-size:13px;}"
                "QPushButton:checked{background:#4C6FFF;border-color:#4C6FFF;}"
            )
            self.check.toggled.connect(self._on_check)

            self.view_btn = QPushButton("查看", self)
            self.view_btn.setCursor(Qt.PointingHandCursor)
            self.view_btn.setFixedHeight(26)
            self.view_btn.setStyleSheet(
                "QPushButton{background:rgba(15,23,42,0.62);color:#FFFFFF;border:none;"
                "border-radius:8px;padding:0 12px;font-weight:600;font-size:12px;}"
                "QPushButton:hover{background:rgba(76,111,255,0.9);}"
            )
            self.view_btn.clicked.connect(lambda: self.view_requested.emit(self.item))

            self.size_badge = QLabel(human_size(item.size), self)
            self.size_badge.setStyleSheet(
                "QLabel{background:rgba(15,23,42,0.62);color:#FFFFFF;border-radius:7px;"
                "padding:2px 7px;font-size:11px;font-weight:600;}"
            )
            self.size_badge.adjustSize()


    def _on_check(self, checked: bool) -> None:
        self.check.setText("✓" if checked else "")
        self.selection_changed.emit(self.item, checked)

    def set_checked(self, checked: bool) -> None:
        if self.check is None:
            return
        self.check.blockSignals(True)
        self.check.setChecked(checked)
        self.check.setText("✓" if checked else "")
        self.check.blockSignals(False)

    def is_checked(self) -> bool:
        return bool(self.check and self.check.isChecked())

    def mark_cleaned(self) -> None:
        self._cleaned = True
        if self.size_badge is not None:
            self.size_badge.setText("已清理")
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if not self.show_controls:
            return
        if self.check is not None:
            self.check.move(10, 10)
        if self.size_badge is not None:
            self.size_badge.adjustSize()
            self.size_badge.move(self.width() - self.size_badge.width() - 10, 10)
        if self.view_btn is not None:
            self.view_btn.move(self.width() - self.view_btn.width() - 10,
                               self.height() - self.view_btn.height() - 10)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if self.show_controls:
            self.view_requested.emit(self.item)
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        item = self.item
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        painter.setClipPath(path)

        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(item.c1))
        grad.setColorAt(1.0, QColor(item.c2))
        painter.fillRect(rect, grad)

        # 装饰圆
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 26))
        painter.drawEllipse(QPointF(rect.width() * 0.82, rect.height() * 0.18), 52, 52)
        painter.setBrush(QColor(255, 255, 255, 16))
        painter.drawEllipse(QPointF(rect.width() * 0.18, rect.height() * 0.88), 66, 66)

        # 图形
        cx, cy = rect.width() / 2, rect.height() / 2 - 4
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 235))
        if item.kind == "视频":
            painter.drawEllipse(QPointF(cx, cy), 25, 25)
            painter.setBrush(QColor(item.c2))
            tri = QPolygonF([QPointF(cx - 7, cy - 10), QPointF(cx - 7, cy + 10), QPointF(cx + 11, cy)])
            painter.drawPolygon(tri)
        elif item.kind == "截图":
            painter.drawRoundedRect(QRectF(cx - 26, cy - 18, 52, 36), 4, 4)
            painter.setBrush(QColor(item.c2))
            painter.drawRect(QRectF(cx - 18, cy - 10, 36, 20))
        else:
            painter.drawRoundedRect(QRectF(cx - 28, cy - 18, 56, 36), 5, 5)
            painter.setBrush(QColor(item.c2))
            painter.drawEllipse(QPointF(cx, cy), 11, 11)
            painter.setBrush(QColor(255, 255, 255, 235))
            painter.drawEllipse(QPointF(cx, cy), 5, 5)

        if self._cleaned:
            painter.setBrush(QColor(15, 23, 42, 110))
            painter.drawRect(rect)
            painter.setPen(QColor(255, 255, 255, 230))
            f = QFont("Microsoft YaHei UI", 12, QFont.Bold)
            painter.setFont(f)
            painter.drawText(rect, Qt.AlignCenter, "已清理")

        painter.end()


class MediaCard(CardWidget):
    view_requested = Signal(object)
    selection_changed = Signal(object, bool)

    def __init__(self, item, parent=None) -> None:
        super().__init__(parent)
        self.item = item
        self.cleaned = False
        self.setObjectName("MediaCard")
        self.setFixedWidth(236)
        self.setMinimumHeight(238)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._apply_style(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 10)
        root.setSpacing(7)

        self.thumb = ThumbnailWidget(item, 220, 126, True, self)
        self.thumb.view_requested.connect(self.view_requested)
        self.thumb.selection_changed.connect(self._on_selection)
        root.addWidget(self.thumb)

        name = StrongBodyLabel(self)
        metrics = name.fontMetrics()
        name.setText(metrics.elidedText(item.name, Qt.ElideMiddle, 202))
        name.setToolTip(item.name)
        root.addWidget(name)

        meta = CaptionLabel(
            f"{item.duration} · {item.width}×{item.height}" if item.kind == "视频"
            else f"{item.width}×{item.height} · {item.date}"
        )
        meta.setStyleSheet(f"color:{palette()['sub']};")
        root.addWidget(meta)

        tags = QHBoxLayout()
        tags.setSpacing(5)
        tags.addWidget(Badge(item.kind, "info", self))
        if item.duplicate:
            tags.addWidget(Badge("重复", "normal", self))
        elif item.cleanable:
            tags.addWidget(Badge("可清理", "safe", self))
        tags.addStretch(1)
        root.addLayout(tags)

    def _apply_style(self, selected: bool) -> None:
        p = palette()
        border = ACCENT if selected else p["border"]
        bg = p["surface"]
        self.setStyleSheet(
            f"CardWidget#MediaCard{{background:{bg};border:1px solid {border};border-radius:14px;}}"
            f"CardWidget#MediaCard:hover{{border-color:{ACCENT};}}"
        )

    def _on_selection(self, _item, checked: bool) -> None:
        self._apply_style(checked)
        self.selection_changed.emit(self.item, checked)

    def set_selected(self, checked: bool) -> None:
        self.thumb.set_checked(checked)
        self._apply_style(checked)

    def is_selected(self) -> bool:
        return self.thumb.is_checked()

    def mark_cleaned(self) -> None:
        self.cleaned = True
        self.thumb.mark_cleaned()
        self.set_selected(False)


class MediaPreviewDialog(QDialog):
    clean_requested = Signal(object)

    def __init__(self, item, parent=None) -> None:
        super().__init__(parent)
        self.item = item
        self.setWindowTitle(item.name)
        self.setModal(True)
        self.resize(980, 660)
        self.setStyleSheet(f"QDialog{{background:{palette()['page_from']};}}")

        root = QHBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(22)

        preview = ThumbnailWidget(item, 580, 420, False, self)
        root.addWidget(preview, 0, Qt.AlignTop)

        right = QVBoxLayout()
        right.setSpacing(10)
        right.addWidget(Badge(item.kind, "info", self))
        title = BodyLabel(item.name, self)
        title.setWordWrap(True)
        title.setStyleSheet(f"color:{palette()['text']};font-size:18px;font-weight:600;")
        right.addWidget(title)

        rows = [
            ("位置", item.folder),
            ("大小", human_size(item.size)),
            ("尺寸", f"{item.width} × {item.height}" + (f" · {item.duration}" if item.duration else "")),
            ("日期", item.date),
        ]
        for key, value in rows:
            row = QHBoxLayout()
            k = CaptionLabel(key, self)
            k.setMinimumWidth(54)
            k.setStyleSheet(f"color:{palette()['sub']};")
            v = BodyLabel(str(value), self)
            v.setWordWrap(True)
            row.addWidget(k, 0, Qt.AlignTop)
            row.addWidget(v, 1)
            right.addLayout(row)

        if item.cleanable and not item.duplicate:
            right.addWidget(Badge("可清理", "safe", self))
        if item.duplicate:
            right.addWidget(Badge("与其他文件重复", "normal", self))

        right.addStretch(1)
        btn_clean = GradientButton("清理此文件", self)
        btn_clean.clicked.connect(self._on_clean)
        right.addWidget(btn_clean)
        btn_open = OutlineButton("在资源管理器中显示", self)
        btn_open.clicked.connect(
            lambda: InfoBar.info("演示模式", "这里会打开资源管理器并定位文件", parent=self,
                                 position=InfoBarPosition.TOP_RIGHT, duration=2500)
        )
        right.addWidget(btn_open)
        btn_close = OutlineButton("关闭", self)
        btn_close.clicked.connect(self.accept)
        right.addWidget(btn_close)

        root.addLayout(right, 1)

    def _on_clean(self) -> None:
        self.clean_requested.emit(self.item)
        self.accept()
