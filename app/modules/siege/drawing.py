# SPDX-License-Identifier: GPL-3.0-only
"""Project the same map drawings for the editor and the transparent overlay."""
from dataclasses import dataclass
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainterPath, QPen, QPolygonF, QTransform

from app.modules.siege.models import COLORS


def drawing_color(drawing, preset):
    return drawing.color or preset.colors.get('TacticalShapes', COLORS['TacticalShapes'])


def visible_drawings(preset):
    return tuple((drawing, drawing_color(drawing, preset)) for drawing in preset.drawings
                 if drawing.visible and 'TacticalShapes' in preset.layers)


def registration_transform(registration, ratio):
    a, b = registration.matrix / ratio
    return QTransform(a[0], b[0], a[1], b[1], a[2], b[2])


@dataclass
class ProjectedDrawing:
    path: QPainterPath
    head: QPainterPath
    start: QPointF
    end: QPointF
    label_box: QRectF
    font: QFont
    width: float
    color: str
    opacity: float
    dashed: bool
    label: str

    def bounds(self):
        bounds = self.path.boundingRect()
        if not self.head.isEmpty():
            bounds = bounds.united(self.head.boundingRect())
        if not self.label_box.isEmpty():
            bounds = bounds.united(self.label_box)
        margin = self.width/2 + 3
        return bounds.adjusted(-margin, -margin, margin, margin)

    def paint(self, painter):
        painter.save()
        painter.setOpacity(self.opacity*painter.opacity())
        color = QColor(self.color)
        pen = QPen(color, self.width, Qt.DashLine if self.dashed else Qt.SolidLine,
                   Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path)
        if not self.head.isEmpty():
            painter.fillPath(self.head, color)
        if not self.label_box.isEmpty():
            painter.setFont(self.font)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#171721'))
            painter.drawRoundedRect(self.label_box, 4, 4)
            painter.setPen(color)
            painter.drawText(self.label_box, Qt.AlignCenter, self.label)
        painter.restore()

    def stencil(self, ratio):
        def polygons(path):
            return [[(round(point.x()*ratio), round(point.y()*ratio)) for point in poly]
                    for poly in path.toSubpathPolygons()]
        label = self.label_box
        box = None if label.isEmpty() else (
            round(label.left()*ratio)-2, round(label.top()*ratio)-2,
            round(label.right()*ratio)+2, round(label.bottom()*ratio)+2,
        )
        return polygons(self.path), polygons(self.head), math.ceil(self.width*ratio)+4, box


def project_drawing(drawing, color, transform, *, unit=1.):
    start = transform.map(QPointF(drawing.start.x, drawing.start.y))
    end = transform.map(QPointF(drawing.end.x, drawing.end.y))
    path, head = QPainterPath(), QPainterPath()
    if drawing.kind == 'arrow':
        delta = end-start
        distance = math.hypot(delta.x(), delta.y())
        path.moveTo(start)
        if distance > 0:
            heading = delta/distance
            size = min(drawing.head_size*unit, distance*.6)
            base = end-heading*size
            wing = QPointF(-heading.y(), heading.x())*size*.48
            path.lineTo(base+heading*(size*.22))
            head.addPolygon(QPolygonF([end, base+wing, base-wing, end]))
    else:
        box = QRectF(QPointF(drawing.start.x, drawing.start.y),
                     QPointF(drawing.end.x, drawing.end.y)).normalized()
        if drawing.kind == 'ellipse':
            path.addEllipse(box)
        else:
            path.addRect(box)
        path = transform.map(path)

    font = QFont('Segoe UI')
    font.setPixelSize(max(1, round(11*unit)))
    label_box = QRectF()
    if drawing.label:
        metrics = QFontMetricsF(font)
        width = metrics.horizontalAdvance(drawing.label)+12*unit
        center = (start+end)/2
        y = center.y()-metrics.height()-7*unit if drawing.kind == 'arrow' else path.boundingRect().top()-metrics.height()-7*unit
        label_box = QRectF(center.x()-width/2, y, width, metrics.height()+4*unit)
    return ProjectedDrawing(path, head, start, end, label_box, font, drawing.width*unit, color,
                            drawing.opacity, drawing.stroke == 'dashed', drawing.label)
