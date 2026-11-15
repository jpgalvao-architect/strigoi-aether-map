# SPDX-License-Identifier: GPL-3.0-only
"""Labeled symbols that share the standard marker projection and clipping."""
from dataclasses import dataclass
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPen


@dataclass(frozen=True)
class Badge:
    text: str
    scale: float
    selected: bool = False
    provisional: bool = False

    def radius(self, scale):
        return math.ceil(10 * self.scale * scale + 2)

    def paint(self, painter, color, scale):
        radius = self.radius(scale) - 2
        edge = QColor('#ffffff' if self.selected else color)
        style = Qt.DashLine if self.provisional else Qt.SolidLine
        painter.setPen(QPen(edge, 2 if self.selected else 1.3, style))
        painter.setBrush(QColor('#292139' if self.selected else '#171522'))
        painter.drawEllipse(QPointF(), radius, radius)
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(max(6, round(radius * min(1.2, 2.8/len(self.text)))))
        painter.setFont(font)
        painter.drawText(QRectF(-radius, -radius, 2*radius, 2*radius), Qt.AlignCenter, self.text)
