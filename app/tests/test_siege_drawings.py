# SPDX-License-Identifier: GPL-3.0-only
import json

import cv2
import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QTransform
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QColorDialog, QMessageBox

from app.modules.overlay.selection import CaptureArea
from app.modules.overlay.service import OverlayService
from app.modules.overlay.stencil import apply_drawing_stencil
from app.modules.overlay.tracking import Registration
from app.modules.siege.drawing import project_drawing, visible_drawings
from app.modules.siege.models import Coordinate, MAP_ID, OFFICIAL
from app.modules.siege.service import SiegeService
from app.services.context import AppContext
from app.ui.main_window import MainWindow


def test_editor_draw_move_resize_style_duplicate_and_delete(qapp, tmp_path, monkeypatch):
    context = AppContext(tmp_path)
    siege = context.siege
    assert cv2.imwrite(str(siege.map_path), np.full((320, 320, 3), 40, np.uint8))
    siege._set_map()
    window = MainWindow(context)
    window.navigate('siege')
    window.show()
    qapp.processEvents()
    page = window.siege_page
    panel = page.editor
    view = page.board.view
    view.fit_full()
    left = Qt.MouseButton.LeftButton

    def point(x, y):
        return view.mapFromScene(QPointF(x*view.map.width, y*view.map.height))

    def drag(start, end):
        QTest.mousePress(view.viewport(), left, pos=start)
        QTest.mouseMove(view.viewport(), end)
        QTest.mouseRelease(view.viewport(), left, pos=end)

    try:
        for kind, bounds in (
            ('rectangle', (.22, .22, .36, .33)),
            ('ellipse', (.51, .24, .63, .36)),
            ('arrow', (.28, .55, .46, .71)),
        ):
            panel.toolbar.buttons[kind].click()
            assert panel.toolbar.buttons[kind].isChecked()
            begin, end = point(*bounds[:2]), point(*bounds[2:])
            drag(begin, end)
            drawing = panel.selected_drawing()
            assert panel.toolbar.buttons['select'].isChecked()
            assert drawing.kind == kind
            assert drawing.stroke == ('solid' if kind == 'arrow' else 'dashed')
            assert abs(drawing.start.x-bounds[0]) < .003
            assert abs(drawing.end.y-bounds[3]) < .003
            assert 'TacticalShapes' in siege.preset.layers

            panel.select(None)
            center = (begin+end)/2
            delta = QPoint(22, 16)
            drag(center, center+delta)
            moved = panel.selected_drawing()
            assert moved.id == drawing.id
            expected = view.mapToScene(center+delta)-view.mapToScene(center)
            assert moved.start.x-drawing.start.x == pytest.approx(expected.x()/view.map.width, abs=.001)
            assert moved.end.y-drawing.end.y == pytest.approx(expected.y()/view.map.height, abs=.001)
            handle = point(moved.end.x, moved.end.y)
            drag(handle, handle+QPoint(25, 27))
            resized = panel.selected_drawing()
            assert resized.start == moved.start and resized.end.x > moved.end.x
            assert resized.end.y > moved.end.y

        panel.label.setText('Avançar')
        panel.label.editingFinished.emit()
        panel.width.setValue(4.25)
        panel.width.editingFinished.emit()
        panel.opacity.setValue(65)
        panel.opacity.editingFinished.emit()
        panel.head_size.setValue(23)
        panel.head_size.editingFinished.emit()
        panel.stroke.setCurrentIndex(panel.stroke.findData('dashed'))
        monkeypatch.setattr(QColorDialog, 'getColor', lambda *_: QColor('#6acccc'))
        panel.choose_drawing_color()
        arrow = panel.selected_drawing()
        assert (arrow.label, arrow.width, arrow.opacity, arrow.head_size, arrow.stroke, arrow.color) == (
            'Avançar', 4.25, .65, 23, 'dashed', '#6acccc',
        )
        panel.duplicate()
        copied = panel.selected_drawing()
        assert copied.id != arrow.id and copied.kind == 'arrow' and copied.start != arrow.start
        metadata = {'id', 'start', 'end'}
        assert copied.model_dump(exclude=metadata) == arrow.model_dump(exclude=metadata)
        assert SiegeService(tmp_path).preset == siege.preset

        panel.toolbar.buttons['rectangle'].click()
        QTest.mousePress(view.viewport(), left, pos=point(.3, .8))
        QTest.mouseMove(view.viewport(), point(.45, .9))
        QTest.keyClick(view, Qt.Key_Escape)
        QTest.mouseRelease(view.viewport(), left, pos=point(.45, .9))
        assert len(siege.preset.drawings) == 4 and not view.drawing.tool
        monkeypatch.setattr(QMessageBox, 'question', lambda *_: QMessageBox.Cancel)
        panel.toolbar.buttons['delete'].click()
        assert len(siege.preset.drawings) == 4
        monkeypatch.setattr(QMessageBox, 'question', lambda *_: QMessageBox.Yes)
        for drawing in list(siege.preset.drawings):
            panel.items.setCurrentIndex(panel.items.findData(f'drawing:{drawing.id}'))
            panel.toolbar.buttons['delete'].click()
            assert drawing.id not in view.drawing.items
        assert not SiegeService(tmp_path).preset.drawings
        assert len(siege.preset.markers) == 12
    finally:
        window.close()


def test_share_drawings_and_migrate_v2_without_recreating_pins(qapp, tmp_path):
    source = SiegeService(tmp_path/'source')
    source.delete_marker('objective-p4')
    source.add_drawing('rectangle', Coordinate(x=.14,y=.22), Coordinate(x=.35,y=.42),
                       width=3.5, opacity=.67, label='Base', color='#f9b45a')
    source.add_drawing('ellipse', Coordinate(x=.5,y=.3), Coordinate(x=.75,y=.5), visible=False)
    source.add_drawing('arrow', Coordinate(x=.3,y=.63), Coordinate(x=.72,y=.81), head_size=22.5, stroke='dashed')
    export = tmp_path/'drawings.json'
    source.export_preset(export)
    payload = json.loads(export.read_text(encoding='utf8'))
    assert payload['schema_version'] == 3 and len(payload['drawings']) == 3
    other = SiegeService(tmp_path/'imported')
    other.import_preset(export, replace=True)
    assert other.preset == source.exportable_preset()
    same = tmp_path/'exported-again.json'
    other.export_preset(same)
    assert same.read_bytes() == export.read_bytes()

    def image(preset):
        canvas = QImage(400, 360, QImage.Format_ARGB32_Premultiplied)
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        for drawing, color in visible_drawings(preset):
            project_drawing(drawing, color, QTransform.fromScale(400, 360)).paint(painter)
        painter.end()
        return canvas

    assert image(source.preset) == image(other.preset)
    assert image(other.preset).pixelColor(56, 90).alpha() > 0
    for invalid in (
        [payload['drawings'][0]]*2,
        [{**payload['drawings'][0], 'end': payload['drawings'][0]['start']}],
        [{**payload['drawings'][0], 'width': -1}],
        [{**payload['drawings'][0], 'start': {'x': 1.2, 'y': .2}}],
    ):
        export.write_text(json.dumps({**payload, 'drawings': invalid}), encoding='utf8')
        with pytest.raises(ValueError, match='JSON de marcações inválido'):
            other.import_preset(export, replace=True)
        assert other.preset == source.exportable_preset()

    legacy = {key: value for key, value in payload.items() if key not in ('drawings', 'ring_catalogue')}
    legacy['schema_version'] = 2
    legacy['layers'].remove('TacticalShapes')
    export.write_text(json.dumps(legacy), encoding='utf8')
    other.import_preset(export, replace=True)
    assert not other.preset.drawings and 'objective-p4' not in {pin.id for pin in other.preset.markers}
    assert other.preset.schema_version == 3
    assert SiegeService(tmp_path/'imported').preset.name == OFFICIAL


def test_overlay_projects_drawings_and_masks_only_painted_areas(qapp, tmp_path):
    context = AppContext(tmp_path)
    siege = context.siege
    siege._set_map()
    rectangle = siege.add_drawing('rectangle', Coordinate(x=.12,y=.20), Coordinate(x=.64,y=.61))
    siege.add_drawing('arrow', Coordinate(x=.2,y=.7), Coordinate(x=.5,y=.73))
    siege.edit_preset(layers={'TacticalShapes'})
    siege.update_overlay(map_markers=True)
    context.prefs.overlay.enabled = True
    service = OverlayService(context)

    class Worker:
        def set_exclusion(self, *_):
            pass

        def set_drawing_exclusion(self, shapes, view):
            self.stencil, self.view = shapes, view

    service.worker = Worker()
    screen = qapp.primaryScreen()
    geom = screen.geometry()
    try:
        for view, scale, x, y in [('minimap', 240., 12., 14.), ('large', 460., 35., 21.)]:
            area = CaptureArea(map_id=MAP_ID, screen_name=screen.name(), screen_x=geom.x(),
                               screen_y=geom.y(), screen_width=geom.width(), screen_height=geom.height(),
                               pixel_ratio=screen.devicePixelRatio(), x=0, y=0, width=min(540, geom.width()),
                               height=min(490, geom.height()), view_kind=view)
            logical = np.array([[scale, 0, x], [0, scale, y]])
            registration = Registration(logical*area.pixel_ratio, 55, .99)
            service.on_registration(registration, {'area': area})
            service.on_registration(registration, {'area': area})
            assert service.window.isVisible() and not service.window.markers
            assert len(service.window.drawings) == 2
            first, arrow = service.window.project_drawings(registration)
            assert first.start == QPointF(rectangle.start.x*scale+x, rectangle.start.y*scale+y)
            assert first.path.boundingRect().height() == pytest.approx((.61-.20)*scale)
            assert arrow.head.contains((arrow.end+arrow.path.currentPosition())/2)
            assert service.worker.view == view
            ratio = area.pixel_ratio
            frame = np.zeros((round(area.height*ratio), round(area.width*ratio),3),dtype=np.uint8)
            mask = np.full(frame.shape[:2],255,dtype=np.uint8)
            apply_drawing_stencil(frame, mask, service.worker.stencil)
            middle = first.path.boundingRect().center()
            assert mask[round(first.start.y()*ratio), round(middle.x()*ratio)] == 0
            assert mask[round(middle.y()*ratio), round(middle.x()*ratio)] == 255

        current = service.window.project_drawings(registration)[0]
        service.window.ratio = 2*area.pixel_ratio
        doubled = Registration(registration.matrix*2, 55, .99)
        assert service.window.project_drawings(doubled)[0].path == current.path
        siege.update_overlay(map_markers=False)
        assert not service.window.drawings and not service.worker.stencil
        siege.update_overlay(map_markers=True)
        assert len(service.window.drawings) == 2
        service.update_location('altgard','minimap',observe_minimap=True)
        assert not service.window.drawings and not service.worker.stencil
    finally:
        service.worker = None
        service.stop()
        service.watchdog.stop()
