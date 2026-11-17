# SPDX-License-Identifier: GPL-3.0-only
"""Tactical layers on the same normalized coordinate frame as the Atlas."""
from html import escape

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QPainterPath
from PySide6.QtWidgets import QApplication, QGraphicsItem

from app.core.i18n import tr
from app.modules.atlas.view import AtlasView
from app.modules.overlay.badges import label_indices
from app.modules.siege.markers import badge_for, pin_badge, pin_color, pin_visible, ring_badge, ring_layer
from app.modules.siege.models import COLORS, MAP_ID, OBJECTIVE_CATEGORY, Coordinate
from app.ui.siege_drawings import DrawingCanvas

# Initial view frames the islands. Full extent remains available via Fit map.
ISLANDS = (.295, .310, .47, .365)


class TacticalMarker(QGraphicsItem):
    def __init__(self, badge, color, tooltip, callback=None, *, pin_id=None):
        super().__init__()
        self.badge = badge
        self.color = color
        self.callback = callback
        self.pin_id = pin_id
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
    ring_selected = Signal(str)
    coordinate_selected = Signal(object)
    pin_selected = Signal(str)
    pin_moved = Signal(str, object)
    editing_cancelled = Signal()
    drawing_selected = Signal(str)
    drawing_created = Signal(str, object, object)
    drawing_changed = Signal(str, object, object)

    def __init__(self, context):
        super().__init__()
        self.context = context
        self.drawing = DrawingCanvas(self)
        self.service = context.siege
        self.tactical_items = []
        self.placement = False
        self.editing_pins = False
        self.selected_pin = None
        self.selected_ring = None
        self.drag = None
        self.exploration = False
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
            self.drawing.rescale()

    def fit_map(self):
        self.fit_islands()

    def fit_full(self):
        if self.map:
            super().fit_map()
            self.zoom_level = 1
            self.position_badges()
            self.drawing.rescale()

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
        self.drawing.rescale()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_badges()

    session_preview = False

    @property
    def shared_preset(self):
        return self.service.session_preset if self.session_preview else None

    @property
    def preset(self):
        return self.shared_preset or self.service.preset

    def refresh(self):
        definition = self.service.definition
        if definition is None:
            return
        self.cancel_drag()
        self.drawing.clear()
        self.badges.clear()
        if self.map is not definition:
            self.set_map(definition)
            self.tactical_items.clear()
        for item in self.tactical_items:
            self.scene().removeItem(item)
        self.tactical_items.clear()
        shared = self.shared_preset is not None
        preset = self.preset
        colors = COLORS | preset.colors
        for ring, position, code in self.service.display_rings(preset, shared=shared):
            layer = ring_layer(ring)
            selected = self.editing_pins and ring.ring_id == self.selected_ring
            if position is not None and (layer in preset.layers or selected):
                alias = preset.aliases.get(ring.ring_id)
                title = code or ring.display_name
                title = f'{title} · {alias}' if alias else title
                state = tr('Verificado') if position.status == 'verified' else tr('Provisório')
                note = f'{title}\n{ring.display_name}\n{state} · {position.source}'
                if position.altitude is not None:
                    note += f'\n{tr("Altitude")} {position.altitude:g}'
                coordinates = position.world_coordinates
                if coordinates:
                    note += f'\nX {coordinates[0]:.2f} · Y {coordinates[1]:.2f}'
                badge = ring_badge(ring, position, code, preset, selected=selected)
                select = None if self.session_preview else lambda key=ring.ring_id: self.ring_selected.emit(key)
                item = TacticalMarker(badge, colors[layer], note, select)
                if layer not in preset.layers:
                    item.setOpacity(.6)
                self._add(item, position.map_position)

        for marker in preset.markers:
            selected = self.editing_pins and marker.id == self.selected_pin
            visible = pin_visible(marker, preset)
            if visible or selected:
                badge = pin_badge(marker, preset, selected=selected)
                category = 'Objetivo de siege' if marker.category == OBJECTIVE_CATEGORY else marker.category
                if marker.category in (OBJECTIVE_CATEGORY, 'Tático'):
                    category = tr(category)
                item = TacticalMarker(badge, pin_color(marker, preset),
                                      f'{marker.name} · {category}', pin_id=marker.id)
                if not visible:
                    item.setOpacity(.6)
                self._add(item, marker.position)
        local = self.service.preset
        self._refresh_exploration(local, COLORS | local.colors)
        self.drawing.refresh()
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
        self.update_cursor()
        if enabled:
            self.setFocus()

    def update_cursor(self):
        self.viewport().setCursor(Qt.CrossCursor if self.placement or self.drawing.tool else Qt.ArrowCursor)

    def set_editor_tool(self, tool):
        selecting = tool == 'select'
        redraw_selection = self.editing_pins != selecting
        self.cancel_drag()
        self.editing_pins = selecting
        self.drawing.enabled = selecting or tool in ('rectangle', 'ellipse', 'arrow')
        self.drawing.set_tool(tool if self.drawing.enabled and not selecting else '')
        self.pick_position(tool == 'pin')
        if self.drawing.tool:
            self.setFocus()
        if redraw_selection:
            self.refresh()

    def select_element(self, pin_id, drawing_id, ring_id):
        if (pin_id, drawing_id, ring_id) != (self.selected_pin, self.drawing.selected, self.selected_ring):
            self.selected_pin, self.drawing.selected, self.selected_ring = pin_id, drawing_id, ring_id
            self.refresh()

    def cancel_drag(self):
        if self.drag:
            _, item, _, initial, _ = self.drag
            item.setPos(initial)
            self.drag = None
            self.position_badges()

    def mousePressEvent(self, event):
        if self.map:
            if event.button() == Qt.RightButton and (self.placement or self.drag or self.drawing.tool or self.drawing.gesture):
                self.editing_cancelled.emit()
                event.accept()
                return
            if event.button() == Qt.LeftButton:
                cursor = event.position().toPoint()
                point = self.mapToScene(cursor)
                if self.drawing.tool and self.drawing.press(cursor):
                    event.accept()
                    return
                if self.placement:
                    if 0 <= point.x() <= self.map.width and 0 <= point.y() <= self.map.height:
                        self.coordinate_selected.emit(self._coordinate(point))
                    event.accept()
                    return
                if self.editing_pins:
                    if self.drawing.press_handle(cursor):
                        event.accept()
                        return
                    markers = [item for item in self.items(cursor) if isinstance(item, TacticalMarker)]
                    pin = next((item for item in markers if item.pin_id), None)
                    if pin is not None:
                        marker_id = pin.pin_id
                        self.pin_selected.emit(marker_id)
                        pin = next(item for item in self.badges if item.pin_id == marker_id)
                        self.drag = (cursor, pin, point, pin.pos(), False)
                        event.accept()
                        return
                    if not any(item.callback for item in markers) and self.drawing.press(cursor):
                        event.accept()
                        return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drawing.move(event.position().toPoint(), square=bool(event.modifiers() & Qt.ShiftModifier)):
            event.accept()
            return
        if self.drag:
            cursor, item, start, initial, moved = self.drag
            pointer = event.position().toPoint()
            if moved or (pointer-cursor).manhattanLength() >= QApplication.startDragDistance():
                point = initial + self.mapToScene(pointer) - start
                coordinate = self._coordinate(point)
                item.setPos(self._at(coordinate))
                self.drag = (cursor, item, start, initial, True)
                self.position_badges()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing.release(
                event.position().toPoint(), square=bool(event.modifiers() & Qt.ShiftModifier)):
            event.accept()
            return
        if self.drag and event.button() == Qt.LeftButton:
            self.mouseMoveEvent(event)
            _, item, _, initial, moved = self.drag
            self.drag = None
            if moved and item.pos() != initial:
                self.pin_moved.emit(item.pin_id, self._coordinate(item.pos()))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and (self.placement or self.drawing.enabled or self.drag):
            self.editing_cancelled.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def _coordinate(self, point):
        return Coordinate(x=max(0., min(1., point.x()/self.map.width)),
                          y=max(0., min(1., point.y()/self.map.height)))
