# SPDX-License-Identifier: GPL-3.0-only
"""Tactical layers on the same normalized coordinate frame as the Atlas."""
from html import escape

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPen, QBrush
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem, QGraphicsSimpleTextItem

from app.core.i18n import tr
from app.modules.atlas.view import AtlasView
from app.modules.siege.models import COLORS, LAYERS, MAP_ID, SECTORS, Coordinate

# Initial view frames the islands. Full extent remains available via Fit map.
ISLANDS = (.295, .310, .47, .365)


class TacticalMarker(QGraphicsEllipseItem):
    def __init__(self, caption, color, size, tooltip, callback, *, selected=False, provisional=False):
        super().__init__(-size, -size, 2 * size, 2 * size)
        self.callback = callback
        self.radius = size
        self.priority = 3 if selected else 0
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setZValue(30 if selected else 12)
        edge = QPen(QColor('#ffffff' if selected else color), 2.7 if selected else 1.4)
        if provisional:
            edge.setStyle(Qt.PenStyle.DashLine)
        self.setPen(edge)
        self.setBrush(QBrush(QColor('#292139' if selected else '#171522')))
        self.setToolTip(escape(tooltip).replace('\n', '<br>'))
        self.setCursor(Qt.CursorShape.PointingHandCursor if callback else Qt.CursorShape.ArrowCursor)
        self.leader = QGraphicsLineItem(self)
        self.leader.setPen(QPen(QColor(color), 1.15))
        self.leader.setFlag(QGraphicsItem.GraphicsItemFlag.ItemStacksBehindParent)
        self.leader.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.anchor = QGraphicsEllipseItem(-2.5, -2.5, 5, 5, self)
        self.anchor.setPen(QPen(QColor('#171522'), 1))
        self.anchor.setBrush(QBrush(QColor(color)))
        self.anchor.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.caption = text = QGraphicsSimpleTextItem(caption, self)
        font = QFont('Segoe UI')
        font.setPixelSize(round(size * .9 + 1))
        font.setBold(True)
        text.setFont(font)
        text.setBrush(QBrush(QColor('#ffffff' if selected else color)))
        text.setPos(-text.boundingRect().width() / 2, -text.boundingRect().height() / 2)
        text.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        if not callback:
            self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def shift_badge(self, x, y):
        radius = self.radius
        self.setRect(x-radius, y-radius, 2*radius, 2*radius)
        self.caption.setPos(x-self.caption.boundingRect().width()/2, y-self.caption.boundingRect().height()/2)
        self.leader.setLine(0, 0, x, y)
        shifted = bool(x or y)
        self.leader.setVisible(shifted)
        self.anchor.setVisible(shifted)

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

    def _add(self, item, position, *, objective=False):
        item.setPos(self._at(position))
        self.scene().addItem(item)
        self.tactical_items.append(item)
        if isinstance(item, TacticalMarker):
            item.priority += 4 if objective else 0
            self.badges.append(item)

    def position_badges(self):
        occupied = []
        for item in sorted(self.badges, key=lambda badge: -badge.priority):
            point = self.mapFromScene(item.pos())
            radius = item.radius
            for distance in (0, radius*2.1, radius*3.1, radius*4.2, radius*6):
                offsets = [(0, 0)] if distance == 0 else [
                    (distance, 0), (-distance, 0), (0, -distance), (0, distance),
                    (distance*.8, -distance*.8), (-distance*.8, -distance*.8),
                    (distance*.8, distance*.8), (-distance*.8, distance*.8),
                ]
                for x, y in offsets:
                    rect = QRectF(point.x()+x-radius-2, point.y()+y-radius-2, 2*radius+4, 2*radius+4)
                    if not any(rect.intersects(other) for other in occupied):
                        occupied.append(rect)
                        item.shift_badge(x, y)
                        break
                else:
                    continue
                break
            else:
                item.shift_badge(0, 0)

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
                self._add(TacticalMarker(
                    objective.code, colors['SiegeObjectives'], 14 * preset.marker_scale, tooltip,
                    lambda n=objective.number: self.objective_selected.emit(n),
                    selected=call.objective == objective.number, provisional=objective.status != 'verified',
                ), objective.map_position, objective=True)
        for ring in self.service.rings.values():
            position = self.service.position(ring)
            layer = 'SiegeRings' if ring.category == 'siege' else 'TransitRings'
            if position is not None and layer in preset.layers:
                code = self.service.callsign(ring)
                state = tr('Verificado') if position.status == 'verified' else tr('Provisório')
                note = f'{self.service.ring_label(ring)}\n{ring.display_name}\n{state} · {position.source}'
                if position.altitude is not None:
                    note += f'\n{tr("Altitude")} {position.altitude:g}'
                coordinates = position.world_coordinates
                if coordinates:
                    note += f'\nX {coordinates[0]:.2f} · Y {coordinates[1]:.2f}'
                item = TacticalMarker(
                    code or ('?' if position.status == 'provisional' else '○'),
                    colors[layer], 12 * preset.marker_scale, note,
                    lambda key=ring.ring_id: self.ring_selected.emit(key),
                    selected=call.ring_id == ring.ring_id, provisional=position.status == 'provisional',
                )
                self._add(item, position.map_position)

        if 'CustomMarkers' in preset.layers:
            for marker in preset.markers:
                self._add(TacticalMarker(
                    marker.name[:4], colors['CustomMarkers'], 14 * preset.marker_scale, marker.name, None,
                ), marker.position)
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
            item = QGraphicsEllipseItem(-3, -3, 6, 6)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
            item.setBrush(QColor(colors[layer]))
            item.setPen(QPen(QColor('#211827'), 1))
            item.setToolTip(escape(resource.name + ' · ' + point.name + '\n' + point.source))
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self._add(item, Coordinate(x=point.x, y=point.y))

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
