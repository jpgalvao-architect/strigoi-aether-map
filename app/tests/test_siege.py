# SPDX-License-Identifier: GPL-3.0-only
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PySide6.QtCore import Qt

from app.core.i18n import set_language
from app.infrastructure.storage import atomic_json
from app.modules.siege.models import OFFICIAL, Coordinate, Preset, Ring, RingCatalogue, RingPosition
from app.modules.siege.service import SiegeService
from app.services.context import AppContext
from app.ui.main_window import MainWindow
from app.ui.overlay_visibility import OverlayVisibility
from app.ui.siege_overlay import shortcut


def ring(key, *, x=.55, y=.55, callsign=None, status='verified'):
    return Ring(
        ring_id=f'ring-fixture-{key}', zone_id='fixture', sector='BOT', category='siege',
        display_name=f'Fixture {key}', source='Controlled test', default_callsign=callsign,
        position=RingPosition(map_position=Coordinate(x=x, y=y), source='Controlled test', status=status),
    )


def import_rings(service, tmp_path, *rings):
    path = tmp_path/'catalogue-test.json'
    atomic_json(path, RingCatalogue(map_frame=service.data.map_frame, rings=list(rings)))
    service.import_catalogue(path)


def test_reference_numbers_and_relative_positions_replay_from_calibration(tmp_path):
    from app.infrastructure.storage import PACKAGE
    manifest = json.loads((PACKAGE.parent/'data-sources/siege-reshanta.json').read_text(encoding='utf-8'))
    service = SiegeService(tmp_path)
    assert set(service.objectives) == set(range(1, 13))
    assert service.objectives[8].reference_label == service.objectives[9].reference_label == '8'
    assert service.objectives[8].sector == 'BOT' and service.objectives[9].sector == 'TOP'
    for objective in service.objectives.values():
        fit = manifest['registration'][objective.sector]
        position = np.array(fit['matrix_to_map_px']) @ np.r_[objective.reference_pixel, 1]
        assert np.allclose([objective.map_position.x, objective.map_position.y], position/4096, atol=1e-8)
        assert objective.status == 'reference'
    assert len(service.rings) == 49
    assert all(r.position is None and not service.callsign(r) for r in service.rings.values())


def test_setup_uses_cached_map_and_loads_it_in_the_atlas(tmp_path, monkeypatch):
    import hashlib
    import cv2
    from app.modules.siege import map_setup

    tiles = {(col, row): np.full((1024, 1024, 3), col + 4*row, dtype=np.uint8)
             for row in range(4) for col in range(4)}
    pixels = np.vstack([np.hstack([tiles[col, row] for col in range(4)]) for row in range(4)])
    monkeypatch.setattr(map_setup, 'MAP_PIXELS_SHA256', hashlib.sha256(pixels).hexdigest())
    monkeypatch.setattr(map_setup, 'download_tile', lambda col, row, _: (col, row, tiles[col, row]))
    manual = tmp_path / map_setup.LOCAL_MAP
    manual.write_bytes(b'preserve this invalid local file')
    path = map_setup.prepare_map(tmp_path)
    assert path.name == map_setup.PREPARED_MAP
    assert np.array_equal(cv2.imread(str(path)), pixels)
    assert manual.read_bytes() == b'preserve this invalid local file'
    context = AppContext(tmp_path)
    assert context.siege.definition.image == str(path)
    assert any(item.id == 'lower-reshanta' for item in context.atlas_dataset.maps)
    assert sum(point.map_id == 'lower-reshanta' for point in context.atlas_dataset.points) == 240
    monkeypatch.setattr(map_setup, 'download_tile', lambda *_: pytest.fail('unexpected network request'))
    assert map_setup.prepare_map(tmp_path) == path


def test_map_setup_keeps_partial_download_out_of_the_profile(tmp_path, monkeypatch):
    from app.modules.siege import map_setup

    def fail_download(*_):
        raise OSError('offline')

    monkeypatch.setattr(map_setup, 'download_tile', fail_download)
    with pytest.raises(OSError, match='offline'):
        map_setup.prepare_map(tmp_path)
    assert not (tmp_path / map_setup.PREPARED_MAP).exists()
    assert not list(tmp_path.glob('siege-map-*'))


def test_catalogue_updates_keep_frozen_callsigns_and_old_records(tmp_path):
    service = SiegeService(tmp_path)
    old = ring(1, callsign='B1')
    import_rings(service, tmp_path, old)
    newer = ring(2, x=.51, y=.42, callsign='B2')
    import_rings(service, tmp_path, newer)
    assert set(service.rings) == {old.ring_id, newer.ring_id}
    with pytest.raises(ValueError, match='callsign'):
        import_rings(service, tmp_path, ring(1, callsign='B3'))
    service = SiegeService(tmp_path)
    assert service.callsign(service.rings[old.ring_id]) == 'B1'
    assert service.callsign(service.rings[newer.ring_id]) == 'B2'


def test_transit_codes_use_source_identity_even_with_a_partial_catalogue(tmp_path):
    service = SiegeService(tmp_path)
    transit = Ring(ring_id='ring-reshanta-295279', zone_id='2616', category='transit',
        display_name='Flight Circle', source='Controlled test',
        position=RingPosition(map_position=Coordinate(x=.59, y=.40), source='Controlled test', status='verified'))
    import_rings(service, tmp_path, transit)
    assert service.ring_label(transit) == 'ER1'
    assert service.callsign(transit) is None  # Transit IDs do not enter tactical call selection.
    service.calibrate_ring(transit.ring_id, transit.position.model_copy(update={'map_position':Coordinate(x=.43,y=.55)}))
    service.save_preset(Preset(name='Calibração local', use_local_calibration=True))
    restored = SiegeService(tmp_path)
    assert restored.ring_code(restored.rings[transit.ring_id]) == 'ER1'
    assert restored.rings[transit.ring_id].position == transit.position


def test_ring_labels_are_centred_below_and_declutter_by_priority(qapp):
    from PySide6.QtCore import QRectF
    from app.modules.overlay.badges import label_indices
    from app.modules.siege.markers import badge_for

    transit = badge_for('TransitRings', 'BF1', 1.)
    siege = badge_for('SiegeRings', 'B1', 1.)
    pin = badge_for('SiegeObjectives', 'P1', 1.)
    icon, label, _ = transit.layout(1.)
    assert transit.ring and siege.ring and not pin.ring
    assert icon == siege.layout(1.)[0]
    assert pin.layout(1.)[0].bottom() == 0
    assert label.center().x() == icon.center().x() == 0
    assert label.top() > icon.bottom()
    viewport = QRectF(0, 0, 180, 150)
    assert pin.pin_code and pin.layout(1.)[1].isEmpty()
    assert label_indices([(40, 40, transit), (61, 40, siege), (110, 50, pin)], 1., viewport) == {1}
    assert label_indices([(34, 40, transit), (80, 40, siege), (131, 50, pin)], 1., viewport) == {0, 1}


def test_local_calibration_and_aliases_stay_out_of_official_preset(tmp_path):
    service = SiegeService(tmp_path)
    official = ring(1, callsign='B1')
    unnumbered = ring(2, x=.52, status='provisional')
    import_rings(service, tmp_path, official, unnumbered)
    service.save_preset(Preset(name='Guild', use_local_calibration=True, aliases={official.ring_id:'Ponte'}))
    service.add_marker('Entrada', Coordinate(x=.4, y=.6))
    local = RingPosition(map_position=Coordinate(x=.60, y=.62), status='verified', source='Local check')
    service.calibrate_ring(unnumbered.ring_id, local)
    assert service.freeze_callsigns('BOT') == 1
    assert service.callsign(unnumbered) == 'B2'
    service.calibrate_ring(official.ring_id, local.model_copy(update={'status':'provisional'}))
    assert service.callsign(official) is None
    export = tmp_path/'guild.json'
    service.export_preset(export)
    raw = json.loads(export.read_text(encoding='utf-8'))
    assert raw['aliases'][official.ring_id] == 'Ponte' and len(raw['markers']) == 1
    assert 'local_rings' not in raw and 'world_coordinates' not in raw
    service.select_preset(OFFICIAL)
    assert service.position(official) == official.position
    assert service.callsign(official) == 'B1'
    assert not service.preset.markers and not service.preset.aliases
    with pytest.raises(ValueError, match='outro nome'):
        service.save_preset(Preset(name=OFFICIAL))


def test_known_calls_copy_and_hud_visibility_respects_game_context(qapp, tmp_path):
    context = AppContext(tmp_path)
    service = context.siege
    rally = ring(3, callsign='B3')
    import_rings(service, tmp_path, rally)
    window = MainWindow(context)
    overlay = window.siege_overlay
    gate = OverlayVisibility(window, SimpleNamespace())
    overlay.bind_visibility(gate)
    try:
        calls = []
        service.call_changed.connect(calls.append)
        window.navigate('siege')
        window.siege_page.controls.sectors['BOT'].click()
        assert service.call.sector == 'BOT'
        assert service.call.objective is None
        window.siege_page.controls.select_objective(7)
        window.siege_page.controls.select_ring(rally.ring_id)
        window.siege_page.controls.copy_call()
        assert qapp.clipboard().text() == 'REAGRUPAR B3 → ATACAR P7'
        assert calls[-1].objective == 7
        with pytest.raises(ValueError, match='outro setor'):
            service.set_call(objective=2)
        service.update_overlay(visible=True, locked=True, opacity=.8)
        assert not overlay.hud.isVisible()
        gate.set_context(True)
        assert overlay.hud.isVisible()
        assert overlay.hud.windowFlags() & Qt.WindowTransparentForInput
        gate.set_context(True, 'menu')
        assert not overlay.hud.isVisible()
        gate.set_context(False)
        assert not overlay.hud.isVisible() and service.state.overlay.visible
        set_language('en_US')
        assert overlay.hud.call_label.text() == 'REGROUP B3 → ATTACK P7'
        service.set_call(action='retreat')
        assert service.call_text() == 'RECUAR B3'
        persisted = SiegeService(tmp_path)
        assert persisted.call == service.call
        assert persisted.state.overlay.opacity == .8
    finally:
        gate.shutdown()
        set_language('pt_BR')
        window.close()


def test_shortcut_parser_rejects_plain_keys_and_canonicalizes_modifiers():
    assert shortcut('alt+Ctrl+f9') == shortcut('Ctrl+Alt+F9')
    assert shortcut('') is None
    with pytest.raises(ValueError):
        shortcut('F9')
    with pytest.raises(ValueError):
        shortcut('Ctrl+Ctrl+F9')


def test_siege_uses_shared_overlay_for_minimap_full_map_and_return(qapp, tmp_path, monkeypatch):
    from app.modules.overlay.badges import Badge
    from app.modules.overlay.selection import CaptureArea
    from app.modules.overlay.tracking import Registration
    from app.modules.siege.models import COLORS, MAP_ID, OverlayOptions

    context = AppContext(tmp_path)
    siege = context.siege
    rally = ring(3, callsign='B3')
    objective = siege.objectives[7].map_position
    transit = Ring(ring_id='ring-fixture-transit', zone_id='fixture', category='transit',
        display_name='Transit fixture', source='Controlled test',
        position=RingPosition(map_position=Coordinate(x=objective.x-.02, y=objective.y),
                              source='Controlled test', status='verified'))
    import_rings(siege, tmp_path, rally, transit)
    import cv2
    assert cv2.imwrite(str(siege.map_path), np.full((320, 320, 3), 30, np.uint8))
    siege._set_map()  # Exercise drawing with a stand-in for the local reference.
    siege.set_call(sector='BOT', objective=7, ring_id=rally.ring_id)
    assert OverlayOptions.model_validate({'map_shortcut':'Alt+F9', 'visible':True}).map_markers
    window = MainWindow(context)
    overlay = window.overlay
    screen = qapp.primaryScreen()
    geometry = screen.geometry()
    mini = CaptureArea(map_id='altgard', screen_name=screen.name(), screen_x=geometry.x(),
        screen_y=geometry.y(), screen_width=geometry.width(), screen_height=geometry.height(),
        pixel_ratio=screen.devicePixelRatio(), x=450, y=40, width=290, height=210, view_kind='minimap')
    path = tmp_path/'selected-minimap.json'
    atomic_json(path, mini)
    context.prefs.overlay.minimap_area = str(path)
    observations = []

    class Worker:
        def set_exclusion(self, *args):
            observations.append(args)

    def start():
        assert context.prefs.overlay.map_id == MAP_ID
        assert window.overlay_page.minimap_ready()
        context.prefs.overlay.enabled = True
        overlay.worker = Worker()
        overlay.sync()

    monkeypatch.setattr(overlay, 'start', start)
    try:
        window.siege_page.start_map_button.click()
        assert context.prefs.overlay.map_view == 'minimap'
        assert not hasattr(window.siege_overlay, 'expanded')
        shared = overlay.window
        assert shared.windowFlags() & Qt.WindowTransparentForInput
        assert len(shared.markers) == 14
        caption = next(shape for _, _, _, shape in shared.markers if isinstance(shape, Badge) and shape.text == 'P7')
        assert caption.selected and caption.provisional
        mini = mini.model_copy(update={'map_id': MAP_ID})
        full = mini.model_copy(update={'x':0, 'y':0, 'width':geometry.width(), 'height':geometry.height(), 'view_kind':'large'})
        for area, zoom, center in [(mini, 1100, (140, 95)), (full, 620, (430, 340)),
                                   (full, 920, (470, 390)), (mini, 1150, (118, 92))]:
            with_area = overlay.capture_area == area
            px, py = np.asarray(center) * area.pixel_ratio
            registration = Registration(np.array([[zoom,0,px-zoom*objective.x],
                                                  [0,zoom,py-zoom*objective.y]]), 55, .99)
            overlay.on_registration(registration, {'area':area})
            assert with_area or not shared.isVisible()
            overlay.on_registration(registration, {'area':area})
            assert shared.isVisible() and overlay.window is shared
            visible = shared.visible_markers(registration)
            point = next((x, y) for x, y, _, shape in visible if shape == caption)
            assert point == pytest.approx(center)
            transit_point = next((x, y) for x, y, color, _ in visible if color == COLORS['TransitRings'])
            assert transit_point == pytest.approx((center[0]-.02*zoom/area.pixel_ratio, center[1]))
            swatch = shared.symbol('#f7cb74', caption).toImage()
            assert swatch.pixelColor(0, 0).alpha() == 0
            assert swatch.pixelColor(swatch.width()//2, swatch.height()//2).alpha() > 0
            assert observations[-1][2] == area.view_kind
        siege.save_preset(Preset(name='Só objetivos', layers={'SiegeObjectives'}))
        assert len(shared.markers) == 12
        assert SiegeService(tmp_path).preset.layers == {'SiegeObjectives'}
        siege.select_preset(OFFICIAL)
        assert len(shared.markers) == 14
        siege.update_overlay(map_markers=False)
        assert not shared.markers
        assert observations[-1][1] == []
        overlay.on_registration(None, {'area':mini})
        assert not shared.isVisible()
    finally:
        overlay.worker = None
        window.close()
        overlay.watchdog.stop()
