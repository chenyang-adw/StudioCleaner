"""运行时生成应用图标（无需外部资源文件）。"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)


def build_pixmap(size: int = 256) -> QPixmap:
    """圆角渐变底 + 磁盘环 + 对勾 + 闪光。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = size / 2048.0

    grad = QLinearGradient(40 * s, 40 * s, 2008 * s, 2008 * s)
    grad.setColorAt(0.0, QColor("#5B7BFF"))
    grad.setColorAt(1.0, QColor("#2D4BD8"))
    p.setBrush(grad)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(40 * s, 40 * s, 1968 * s, 1968 * s), 440 * s, 440 * s)

    sheen = QLinearGradient(60 * s, 60 * s, size * 0.62, size * 0.62)
    sheen.setColorAt(0.0, QColor(255, 255, 255, 38))
    sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setBrush(sheen)
    p.drawRoundedRect(QRectF(40 * s, 40 * s, 1968 * s, 1968 * s), 440 * s, 440 * s)

    cx = cy = size / 2.0
    radius = 590 * s
    ring = QPainterPath()
    for i in range(281):
        a = math.radians(20 + i)
        pt = QPointF(cx + radius * math.cos(a), cy + radius * math.sin(a))
        if i == 0:
            ring.moveTo(pt)
        else:
            ring.lineTo(pt)
    p.setPen(QPen(QColor(255, 255, 255, 250), 150 * s,
                  Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPath(ring)

    check = QPainterPath(QPointF(cx - 245 * s, cy + 20 * s))
    check.lineTo(cx - 55 * s, cy + 205 * s)
    check.lineTo(cx + 285 * s, cy - 190 * s)
    p.setPen(QPen(QColor(255, 255, 255), 128 * s,
                  Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPath(check)

    star = QPolygonF()
    for i in range(8):
        a = math.radians(i * 45 - 90)
        r = (120 if i % 2 == 0 else 41) * s
        star.append(QPointF(cx + 430 * s + r * math.cos(a),
                            cy - 430 * s + r * math.sin(a)))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 245))
    p.drawPolygon(star)
    p.drawEllipse(QPointF(cx + 575 * s, cy - 300 * s), 30 * s, 30 * s)

    p.end()
    return pm


def build_icon() -> QIcon:
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(build_pixmap(s))
    return icon


def write_ico(path: str) -> bool:
    return bool(build_pixmap(256).save(path, "ICO"))