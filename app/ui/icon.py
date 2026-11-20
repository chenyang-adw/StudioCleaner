"""运行时生成应用图标（无需外部资源文件）。"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap

from .theme import ACCENT


def build_pixmap(size: int = 256) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#5B7BFF"))
    grad.setColorAt(1.0, QColor("#2D4BD8"))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    radius = size * 0.22
    p.drawRoundedRect(QRectF(size * 0.04, size * 0.04, size * 0.92, size * 0.92), radius, radius)

    f = QFont("Segoe UI", int(size * 0.38))
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("#FFFFFF"))
    p.drawText(QRectF(0, -size * 0.02, size, size), Qt.AlignCenter, "SC")
    p.end()
    return pm


def build_icon() -> QIcon:
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(build_pixmap(s))
    return icon


def write_ico(path: str) -> bool:
    return bool(build_pixmap(256).save(path, "ICO"))
