# SPDX-License-Identifier: GPL-3.0-only
"""Tactical layers on the same normalized coordinate frame as the Atlas."""
from html import escape

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainterPath, QPen, QBrush
from PySide6.QtWidgets import QGraphicsItem

from app.core.i18n import tr
from app.modules.atlas.view import AtlasView
from app.modules.overlay.badges import label_indices
from app.modules.siege.markers import badge_for
from app.modules.siege.models import COLORS, MAP_ID, SECTORS, Coordinate

# Initial view frames the islands. Full extent remains available via Fit map.
ISLANDS = (.295, .310, .47, .365)


class TacticalMarker(QGraphicsItem):
    def __init__(self, badge, color, tooltip, callback=None):
        super().__init__()
        self.badge = badge
        self.color = color
        self.callback = callback
        self.draw_label = True
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setZValue(30 if badge.selected else 10 + badge.priority)
        self.setToolTip(escape(tooltip).replace('\n', '<br>'))
        if callback:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def boundingRect(self):
        return self.badge.bounds(1.)

    def paint(self, painter, option, widget=None):
        self.badge.paint(painter, self.color, 1., self.draw_label)

    def shape(self):
        icon, label, _ = self.badge.layout(1.)
        shape = QPainterPath()
        shape.addRect(icon)
        if self.draw_label and not label.isEmpty():
            shape.addRect(label)
        return shape

    def set_label_visible(self, visible):
        if visible != self.draw_label:
            self.draw_label = visible
            self.update()

    def mousePressEvent(self, event):
        if self.callback and event.button() == Qt.MouseButton.LeftButton:
            self.callback()
            event.accept()
        else:
            super().mousePressEvent(event)


class SiegeMapView(AtlasView):
    objective_selected = Signal(int)
    ring_selected = Signal(str)
    coordinate_selected = Signal(object)

    def __init__(self, context):
        super().__init__()
        self.context = context
        self.service = context.siege
        self.tactical_items = []
        self.placement = False
        self.exploration = False
        self.frames = {}
        self.badges = []
        self.setAccessibleName('Mapa tático de Lower Reshanta')
        self.service.changed.connect(self.refresh)
        context.changed.connect(self.refresh)
        self.horizontalScrollBar().valueChanged.connect(self.position_badges)
        self.verticalScrollBar().valueChanged.connect(self.position_badges)
        self.refresh()

    def fit_islands(self):
        if self.map:
            x, y, width, height = ISLANDS
            self.fitInView(QRectF(x*self.map.width, y*self.map.height,
                                 width*self.map.width, height*self.map.height), Qt.KeepAspectRatio)
            self.zoom_level = 0
            self.position_badges()

    def fit_map(self):
        self.fit_islands()

    def fit_full(self):
        if self.map:
            super().fit_map()
            self.zoom_level = 1
            self.position_badges()

    def focus_sector(self, sector):
        if not self.map:
            return
        frame = self.frames.get(sector)
        if frame is not None:
            for ring in self.service.rings.values():
                position = self.service.position(ring)
                if ring.sector == sector and position:
                    center = self._at(position.map_position)
                    frame = frame.united(QRectF(center.x()-5, center.y()-5, 10, 10))
            self.fitInView(frame.adjusted(-70, -70, 70, 70), Qt.KeepAspectRatio)
            self.zoom_level = 1
            self.position_badges()

    def _at(self, position):
        return QPointF(position.x * self.map.width, position.y * self.map.height)

    def _add(self, item, position):
        item.setPos(self._at(position))
        self.scene().addItem(item)
        self.tactical_items.append(item)
        self.badges.append(item)

    def position_badges(self):
        markers = []
        for item in self.badges:
            point = self.mapFromScene(item.pos())
            markers.append((point.x(), point.y(), item.badge))
        labels = label_indices(markers, 1., QRectF(self.viewport().rect()))
        for index, item in enumerate(self.badges):
            item.set_label_visible(index in labels)

    def zoom(self, delta):
        super().zoom(delta)
        self.position_badges()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_badges()

    def refresh(self):
        definition = self.service.definition
        if definition is None:
            return
        self.badges.clear()
        if self.map is not definition:
            self.set_map(definition)
            self.tactical_items.clear()
        for item in self.tactical_items:
            self.scene().removeItem(item)
        self.tactical_items.clear()
        preset, call = self.service.preset, self.service.call
        colors = COLORS | preset.colors
        self.frames = {}
        for sector, name in SECTORS.items():
            points = [self._at(p.map_position) for p in self.service.objectives.values() if p.sector == sector]
            xs = [p.x() for p in points]
            ys = [p.y() for p in points]
            frame = QRectF(QPointF(min(xs), min(ys)), QPointF(max(xs), max(ys))).adjusted(-38, -34, 38, 38)
            self.frames[sector] = frame
            if 'SiegeObjectives' not in preset.layers:
                continue
            color = QColor(colors['SiegeObjectives'])
            fill = QColor(color)
            fill.setAlpha(32 if sector == call.sector else 14)
            border = QPen(color, 2)
            border.setCosmetic(True)
            border.setStyle(Qt.DashLine)
            self.tactical_items.append(self.scene().addRect(frame, border, QBrush(fill)))
            for objective in self.service.objectives.values():
                if objective.sector != sector:
                    continue
                tooltip = f'{objective.code} · {tr(name)}'
                if objective.status == 'reference':
                    tooltip += '\n' + tr('Posição transcrita da referência visual; validação em jogo pendente.')
                badge = badge_for('SiegeObjectives', objective.code, preset.marker_scale,
                                  selected=call.objective == objective.number,
                                  provisional=objective.status != 'verified')
                self._add(TacticalMarker(badge, colors['SiegeObjectives'], tooltip,
                                         lambda n=objective.number: self.objective_selected.emit(n)),
                          objective.map_position)
        for ring in self.service.rings.values():
            position = self.service.position(ring)
            layer = 'SiegeRings' if ring.category == 'siege' else 'TransitRings'
            if position is not None and layer in preset.layers:
                code = self.service.ring_code(ring)
                state = tr('Verificado') if position.status == 'verified' else tr('Provisório')
                note = f'{self.service.ring_label(ring)}\n{ring.display_name}\n{state} · {position.source}'
                if position.altitude is not None:
                    note += f'\n{tr("Altitude")} {position.altitude:g}'
                coordinates = position.world_coordinates
                if coordinates:
                    note += f'\nX {coordinates[0]:.2f} · Y {coordinates[1]:.2f}'
                badge = badge_for(layer, code or '?', preset.marker_scale,
                                  selected=call.ring_id == ring.ring_id,
                                  provisional=position.status == 'provisional')
                self._add(TacticalMarker(badge, colors[layer], note,
                                         lambda key=ring.ring_id: self.ring_selected.emit(key)),
                          position.map_position)

        if 'CustomMarkers' in preset.layers:
            for marker in preset.markers:
                badge = badge_for('CustomMarkers', marker.name[:4], preset.marker_scale)
                self._add(TacticalMarker(badge, colors['CustomMarkers'], marker.name), marker.position)
        self._refresh_exploration(preset, colors)
        self.position_badges()

    def _refresh_exploration(self, preset, colors):
        dataset = self.context.atlas_dataset
        resources = {resource.id: resource for resource in dataset.resources}
        for point in dataset.points:
            if point.map_id != MAP_ID or not point.enabled:
                continue
            resource = resources[point.resource_id]
            layer = 'Pets' if resource.category == 'pets' else 'Gathering'
            if layer not in preset.layers and not self.exploration:
                continue
            badge = badge_for(layer, '', preset.marker_scale)
            note = f'{resource.name} · {point.name}\n{point.source}'
            self._add(TacticalMarker(badge, colors[layer], note), Coordinate(x=point.x, y=point.y))

    def pick_position(self, enabled):
        self.placement = enabled
        self.viewport().setCursor(Qt.CrossCursor if enabled else Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if self.placement and self.map:
            if event.button() == Qt.RightButton:
                self.coordinate_selected.emit(None)
                event.accept()
                return
            if event.button() == Qt.LeftButton:
                point = self.mapToScene(event.position().toPoint())
                if self.sceneRect().contains(point):
                    self.coordinate_selected.emit(Coordinate(x=point.x()/self.map.width, y=point.y()/self.map.height))
                event.accept()
                return
        super().mousePressEvent(event)
