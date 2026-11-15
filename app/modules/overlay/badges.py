# SPDX-License-Identifier: GPL-3.0-only
"""Labeled symbols that share the standard marker projection and clipping."""
from dataclasses import dataclass
from functools import lru_cache
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainterPath, QPen


@dataclass(frozen=True)
class Badge:
    text: str
    scale: float
    selected: bool = False
    provisional: bool = False
    ring: bool = False
    priority: int = 4
    size: float = 10.
    pin_code: bool = False

    @lru_cache(maxsize=512)
    def layout(self, scale):
        radius = max(10.5 if self.pin_code else 3., self.size*self.scale*scale)
        # Pins are registered at the tip; rings are registered at the centre.
        icon = (QRectF(-radius, -radius, 2*radius, 2*radius) if self.ring else
                QRectF(-radius, -2.7*radius, 2*radius, 2.7*radius))
        font = QFont('Segoe UI')
        font.setBold(True)
        font.setPixelSize(max(9, round((10.5 if self.priority >= 3 else 9.5)*self.scale*scale)))
        label = QRectF()
        if self.text and not self.pin_code:
            metrics = QFontMetricsF(font)
            width = math.ceil(metrics.horizontalAdvance(self.text))+8
            label = QRectF(-width/2, icon.bottom()+3, width, math.ceil(metrics.height())+1)
        return icon, label, font

    def bounds(self, scale):
        icon, label, _ = self.layout(scale)
        return icon.united(label).adjusted(-2, -2, 2, 2)

    @lru_cache(maxsize=512)
    def radius(self, scale):
        bounds = self.bounds(scale)
        return math.ceil(max(-bounds.left(), bounds.right(), -bounds.top(), bounds.bottom()))

    def paint(self, painter, color, scale, draw_label=True):
        icon, label, font = self.layout(scale)
        radius = icon.width()/2
        tint = QColor(color)
        edge = QColor('#ffffff' if self.selected else color)
        style = Qt.DashLine if self.provisional else Qt.SolidLine
        painter.setBrush(QColor('#292139' if self.selected else '#171522'))
        painter.setPen(QPen(edge, 2 if self.selected else 1.3, style))
        if self.ring:
            painter.drawEllipse(icon)
            painter.setPen(QPen(tint, 1.15))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(), radius*.39, radius*.39)
        else:
            pin = QPainterPath(QPointF(0, 0))
            pin.cubicTo(-.54*radius, -.70*radius, -radius, -1.35*radius, -radius, -1.70*radius)
            pin.arcTo(QRectF(-radius, -2.70*radius, 2*radius, 2*radius), 180, -180)
            pin.cubicTo(radius, -1.35*radius, .54*radius, -.70*radius, 0, 0)
            pin.closeSubpath()
            painter.drawPath(pin)
            if self.pin_code:
                painter.setPen(edge.lighter(112))
                painter.setFont(font)
                painter.drawText(QRectF(-radius, -2.40*radius, 2*radius, 1.4*radius),
                                 Qt.AlignCenter, self.text)
            else:
                painter.setPen(Qt.NoPen)
                painter.setBrush(tint)
                painter.drawEllipse(QPointF(0, -1.68*radius), radius*.32, radius*.32)
        if draw_label and not label.isEmpty():
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#191724'))
            painter.drawRoundedRect(label, 4, 4)
            painter.setPen(QColor('#ffffff') if self.selected else tint.lighter(112))
            painter.setFont(font)
            painter.drawText(label, Qt.AlignCenter, self.text)


def label_indices(markers, scale, viewport):
    """Reserve icon space and place centred captions by tactical priority."""
    tiles = {}
    tile_size = 32

    def keys(rect):
        for x in range(math.floor(rect.left()/tile_size), math.floor(rect.right()/tile_size)+1):
            for y in range(math.floor(rect.top()/tile_size), math.floor(rect.bottom()/tile_size)+1):
                yield x, y

    def reserve(rect):
        for key in keys(rect):
            tiles.setdefault(key, []).append(rect)

    labels = []
    for index, (x, y, badge) in enumerate(markers):
        icon, label, _ = badge.layout(scale)
        icon = icon.translated(x, y).adjusted(-1, -1, 1, 1)
        if viewport.intersects(icon):
            reserve(icon)
        label = label.translated(x, y)
        if not label.isEmpty() and viewport.contains(label):
            priority = badge.priority + (10 if badge.selected else 0)
            labels.append((-priority, index, label))

    shown = set()
    for _, index, label in sorted(labels, key=lambda entry: entry[:2]):
        if any(label.intersects(other) for key in keys(label) for other in tiles.get(key, ())):
            continue
        shown.add(index)
        reserve(label.adjusted(-1, -1, 1, 1))
    return shown
