# SPDX-License-Identifier: GPL-3.0-only
"""Native vector atlas with pan/zoom and a constant-size marker layer."""
from html import escape
from functools import lru_cache
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImageReader, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsScene, QGraphicsView

from app.core.models import Dataset, MapDefinition, PointOfInterest, Preferences
from app.infrastructure.storage import resolve_map_image
from app.modules.atlas.heights import point_marker_shape


def marker_path(shape: str, radius: float = 7) -> QPainterPath:
    path = QPainterPath()
    if shape == "circle":
        path.addEllipse(QPointF(0, 0), radius, radius)
    elif shape == 'pets':
        path.addEllipse(QPointF(0, radius*.35), radius*.55, radius*.52)
        for x, y in [(-.68,-.1),(-.28,-.66),(.28,-.66),(.68,-.1)]:
            path.addEllipse(QPointF(x*radius,y*radius), radius*.23, radius*.29)
    elif shape == "wood":
        path.addRoundedRect(QRectF(-radius, -radius*.7, radius*2, radius*1.4), 2, 2)
    elif shape == "leaf":
        path.moveTo(0, -radius)
        path.cubicTo(radius*2, 0, radius, radius, 0, radius)
        path.cubicTo(-radius*2, 0, -radius, -radius, 0, -radius)
    elif shape == "star":
        for index in range(10):
            angle = math.pi*index/5-math.pi/2
            r = radius if index % 2 == 0 else radius*.45
            point = QPointF(math.cos(angle)*r, math.sin(angle)*r)
            path.moveTo(point) if index == 0 else path.lineTo(point)
        path.closeSubpath()
    elif shape in ("cube", "cube-up", "cube-down"):
        for index, (x,y) in enumerate([(0,-radius),(.87*radius,-.5*radius),(.87*radius,.5*radius),(0,radius),(-.87*radius,.5*radius),(-.87*radius,-.5*radius)]):
            path.moveTo(x,y) if index==0 else path.lineTo(x,y)
        path.closeSubpath()
        path.moveTo(0,0);path.lineTo(0,radius)
        path.moveTo(0,0);path.lineTo(.87*radius,-.5*radius)
        path.moveTo(0,0);path.lineTo(-.87*radius,-.5*radius)
        if shape != "cube":
            direction = -1 if shape == "cube-up" else 1
            path.moveTo(1.3*radius, 0)
            path.lineTo(1.8*radius, direction*.6*radius)
            path.lineTo(2.3*radius, 0)
            path.moveTo(1.8*radius, direction*.6*radius)
            path.lineTo(1.8*radius, -direction*.6*radius)
    else:
        path.moveTo(0, -radius)
        path.lineTo(radius, 0)
        path.lineTo(0, radius)
        path.lineTo(-radius, 0)
        path.closeSubpath()
    return path


class Marker(QGraphicsPathItem):
    def __init__(self, point, category, visited, callback):
        super().__init__(marker_path(point_marker_shape(point, category.icon), 6 if category.icon == "cube" else 4))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setBrush(QColor(category.color))
        self.setPen(QPen(QColor("#f2f1ff" if visited else "#101c2a"), 1.3))
        self.setOpacity(.4 if visited else 1)
        self.setZValue(10)
        self.setToolTip(f"{escape(point.name)}<br>{escape(point.notes)}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.point = point
        self.callback = callback

    def mousePressEvent(self, event):
        self.callback(self.point)
        event.accept()


@lru_cache(maxsize=2)
def map_pixmap(path: str) -> QPixmap:
    """Share decoded maps across the atlas and cubes; keep full-size source files intact."""
    reader = QImageReader(path)
    size = reader.size()
    if max(size.width(), size.height()) > 4096:
        reader.setScaledSize(size.scaled(4096, 4096, Qt.AspectRatioMode.KeepAspectRatio))
    return QPixmap.fromImage(reader.read())


class AtlasView(QGraphicsView):
    point_selected = Signal(object)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor("#101b2b"))
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setMinimumSize(320, 300)
        self._markers = []
        self.map = None
        self.zoom_level = 0

    def set_map(self, definition: MapDefinition):
        self.scene().clear()
        self._markers = []
        self.map = definition
        image = resolve_map_image(definition.image)
        if image.suffix.lower() == ".svg":
            item = QGraphicsSvgItem(str(image))
            if not item.renderer().isValid():
                raise ValueError("SVG do mapa inválido")
        else:
            pixmap = map_pixmap(str(image))
            if pixmap.isNull():
                raise ValueError("Imagem do mapa inválida")
            item = self.scene().addPixmap(pixmap)
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        if item.scene() is None:
            self.scene().addItem(item)
        item.setZValue(-1)
        bounds = item.boundingRect()
        from PySide6.QtGui import QTransform
        item.setTransform(QTransform.fromScale(definition.width / bounds.width(), definition.height / bounds.height()))
        self.scene().setSceneRect(0, 0, definition.width, definition.height)
        self.fit_map()

    def set_points(self, dataset: Dataset, prefs: Preferences, points: list[PointOfInterest]):
        for marker in self._markers:
            self.scene().removeItem(marker)
        self._markers.clear()
        if not self.map:
            return
        resources = {r.id: r for r in dataset.resources}
        categories = {c.id: c for c in dataset.categories}
        for point in points:
            category = categories[resources[point.resource_id].category]
            item = Marker(point, category, point.id in prefs.visited, self.point_selected.emit)
            item.setPos(point.x*self.map.width, point.y*self.map.height)
            self.scene().addItem(item)
            self._markers.append(item)

    def fit_map(self):
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.zoom_level = 0

    def zoom(self, delta: int):
        proposed = self.zoom_level + delta
        if -2 <= proposed <= 15:
            factor = 1.18 ** delta
            self.scale(factor, factor)
            self.zoom_level = proposed

    def wheelEvent(self, event):
        self.zoom(1 if event.angleDelta().y() > 0 else -1)
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.zoom_level == 0:
            self.fit_map()
