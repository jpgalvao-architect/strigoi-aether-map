# SPDX-License-Identifier: GPL-3.0-only
"""Drawing gestures on the same scene and coordinate frame as siege pins."""
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPainterPathStroker, QPen, QTransform
from PySide6.QtWidgets import QApplication, QGraphicsItem

from app.modules.siege.drawing import drawing_color, project_drawing
from app.modules.siege.models import Coordinate, TacticalDrawing


def translated(drawing, dx, dy):
    x0, x1 = sorted((drawing.start.x, drawing.end.x))
    y0, y1 = sorted((drawing.start.y, drawing.end.y))
    dx = max(-x0, min(dx, 1-x1))
    dy = max(-y0, min(dy, 1-y1))
    return {key: Coordinate(x=max(0., min(1., point.x+dx)), y=max(0., min(1., point.y+dy)))
            for key, point in (('start', drawing.start), ('end', drawing.end))}


def square_corner(anchor, point):
    dx, dy = point.x-anchor.x, point.y-anchor.y
    sx, sy = (1 if dx >= 0 else -1), (1 if dy >= 0 else -1)
    limit_x = 1-anchor.x if sx > 0 else anchor.x
    limit_y = 1-anchor.y if sy > 0 else anchor.y
    side = min(max(abs(dx), abs(dy)), limit_x, limit_y)
    return Coordinate(x=anchor.x+sx*side, y=anchor.y+sy*side)


class DrawingItem(QGraphicsItem):
    def __init__(self, drawing, color, view, selected=False):
        super().__init__()
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.view, self.drawing, self.color, self.selected = view, drawing, color, selected
        self.setZValue(6 if selected else 5)
        self.update_projection()

    def update_projection(self):
        self.prepareGeometryChange()
        self.unit = 1/max(.0001, self.view.transform().m11())
        self.projected = project_drawing(
            self.drawing, self.color, QTransform.fromScale(self.view.map.width, self.view.map.height),
            unit=self.unit,
        )
        self.update()

    def boundingRect(self):
        margin = 9*self.unit
        return self.projected.bounds().adjusted(-margin, -margin, margin, margin)

    def shape(self):
        path = self.projected.path
        stroker = QPainterPathStroker()
        stroker.setWidth(max(12*self.unit, self.projected.width))
        hit = stroker.createStroke(path).united(path if self.drawing.kind != 'arrow' else self.projected.head)
        if not self.projected.label_box.isEmpty():
            label = QPainterPath()
            label.addRect(self.projected.label_box)
            hit = hit.united(label)
        return hit

    def paint(self, painter, *_):
        self.projected.paint(painter)
        if self.selected:
            painter.save()
            painter.setOpacity(1)
            painter.setPen(QPen(QColor('#ece5ff'), self.unit))
            painter.setBrush(QColor('#4c366f'))
            for point in (self.projected.start, self.projected.end):
                size = 8*self.unit
                painter.drawRect(QRectF(point.x()-size/2, point.y()-size/2, size, size))
            painter.restore()


@dataclass
class DrawingGesture:
    cursor: QPoint
    anchor: Coordinate
    drawing: TacticalDrawing
    handle: str | None
    creating: bool


class DrawingCanvas:
    def __init__(self, view):
        self.view = view
        self.enabled = False
        self.tool = ''
        self.selected = None
        self.items = {}
        self.gesture = None
        self.preview = None

    def set_tool(self, tool):
        self.cancel()
        self.tool = tool

    def cancel(self):
        if self.preview is not None:
            self.view.scene().removeItem(self.preview)
            self.preview = None
        if self.gesture is not None and not self.gesture.creating:
            item = self.items.get(self.gesture.drawing.id)
            if item is not None:
                item.setVisible(True)
        self.gesture = None

    def clear(self):
        self.cancel()
        for item in self.items.values():
            self.view.scene().removeItem(item)
        self.items.clear()

    def refresh(self):
        self.clear()
        if self.view.map is None:
            return
        preset = self.view.preset
        for drawing in preset.drawings:
            selected = self.enabled and not self.tool and drawing.id == self.selected
            visible = drawing.visible and 'TacticalShapes' in preset.layers
            if visible or selected:
                item = DrawingItem(drawing, drawing_color(drawing, preset), self.view, selected)
                if not visible:
                    item.setOpacity(.45)
                self.view.scene().addItem(item)
                self.items[drawing.id] = item

    def rescale(self):
        for item in self.items.values():
            item.update_projection()
        if self.preview is not None:
            self.preview.update_projection()

    def press_handle(self, cursor):
        selected = self.items.get(self.selected)
        if selected is None:
            return False
        for key, point in (('start', selected.projected.start), ('end', selected.projected.end)):
            if (self.view.mapFromScene(point)-cursor).manhattanLength() <= 12:
                anchor = self.view._coordinate(self.view.mapToScene(cursor))
                self.gesture = DrawingGesture(cursor, anchor, selected.drawing, key, False)
                return True
        return False

    def press(self, cursor):
        view = self.view
        point = view.mapToScene(cursor)
        anchor = view._coordinate(point)
        if self.tool:
            if view.sceneRect().contains(point):
                drawing = TacticalDrawing.model_construct(
                    id='shape-preview', kind=self.tool, start=anchor, end=anchor,
                    stroke='solid' if self.tool == 'arrow' else 'dashed',
                )
                self.gesture = DrawingGesture(cursor, anchor, drawing, 'end', True)
            return True

        item = next((item for item in view.items(cursor) if isinstance(item, DrawingItem)), None)
        if item is None:
            return False
        drawing = item.drawing
        view.drawing_selected.emit(drawing.id)
        self.gesture = DrawingGesture(cursor, anchor, drawing, None, False)
        return True

    def move(self, cursor, *, square=False):
        gesture = self.gesture
        if gesture is None:
            return False
        if self.preview is None and (cursor-gesture.cursor).manhattanLength() < QApplication.startDragDistance():
            return True
        point = self.view._coordinate(self.view.mapToScene(cursor))
        if square and gesture.handle and gesture.drawing.kind != 'arrow':
            anchor = gesture.drawing.start if gesture.handle == 'end' else gesture.drawing.end
            point = square_corner(anchor, point)
        changes = ({gesture.handle: point} if gesture.handle else
                   translated(gesture.drawing, point.x-gesture.anchor.x, point.y-gesture.anchor.y))
        drawing = gesture.drawing.model_copy(update=changes)
        if self.preview is None:
            item = self.items.get(drawing.id)
            if item is not None:
                item.hide()
            self.preview = DrawingItem(drawing, drawing_color(drawing, self.view.service.preset), self.view, True)
            self.preview.setZValue(7)
            self.view.scene().addItem(self.preview)
        else:
            self.preview.drawing = drawing
            self.preview.update_projection()
        return True

    def release(self, cursor, *, square=False):
        if self.gesture is None:
            return False
        self.move(cursor, square=square)
        gesture = self.gesture
        drawing = self.preview.drawing if self.preview is not None else None
        self.cancel()
        if drawing is not None and gesture.creating:
            self.view.drawing_created.emit(drawing.kind, drawing.start, drawing.end)
        elif drawing is not None and drawing != gesture.drawing:
            self.view.drawing_changed.emit(drawing.id, drawing.start, drawing.end)
        return True
