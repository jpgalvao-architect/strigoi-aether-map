# SPDX-License-Identifier: GPL-3.0-only
import numpy as np

from app.modules.overlay.automatic import AutomaticMapTracker
from app.modules.overlay.selection import CaptureArea
from app.modules.overlay.tracking import Registration


def areas(screen_name='test'):
    mini=CaptureArea(map_id='altgard',screen_name=screen_name,screen_x=0,screen_y=0,
        screen_width=1000,screen_height=700,pixel_ratio=1.,x=670,y=40,width=330,height=220,view_kind='minimap')
    full=mini.model_copy(update=dict(x=0,y=0,width=1000,height=700,view_kind='large'))
    return mini,full


def test_selected_terrain_adapts_to_resolution_and_dpi_without_rewriting_selection():
    from types import SimpleNamespace
    from PySide6.QtCore import QRect
    from app.modules.overlay.selection import physical_region

    mini, full = areas()
    screen = SimpleNamespace(name=lambda: 'test', geometry=lambda: QRect(-1600, 20, 1200, 800),
                             devicePixelRatio=lambda: 1.5)
    moved = mini.on_screen(screen)
    assert (moved.x, moved.y, moved.width, moved.height) == (804, 46, 396, 251)
    monitor = {'left':-1600, 'top':20, 'width':1800, 'height':1200}
    assert physical_region(moved, monitor) == {'left':-394, 'top':89, 'width':594, 'height':377}
    assert (mini.x, mini.y, mini.pixel_ratio) == (670, 40, 1.)
    area = full.on_screen(screen)
    assert (area.x, area.y, area.width, area.height) == (0, 0, 1200, 800)


def test_automatic_priority_and_return_to_minimap():
    mini,full=areas()
    registration=object()
    frames={'large':None,'minimap':registration}
    reads=[]
    class Tracker:
        def __init__(self):self.resets=0
        def observe(self,frame,now,**kwargs):return frame,'reference'
        def reset(self):self.resets+=1
    small,big=Tracker(),Tracker()
    automatic=AutomaticMapTracker(small,big,mini,full)
    def capture(area):
        reads.append(area.view_kind)
        return frames[area.view_kind],None
    assert automatic.observe(capture,0,minimum=18)[2]==mini
    reads.clear()
    automatic.observe(capture,.1,minimum=18)
    assert reads==['minimap']  # No full-screen capture at the minimap frame rate.
    frames['large']=registration;frames['minimap']=None
    result=automatic.observe(capture,.6,minimum=18)
    assert result[0] is registration and result[2]==full
    reads.clear()
    assert automatic.observe(capture,.62,minimum=18)[2]==full
    assert reads==['large']  # A missing minimap cannot hide the recognized full map.
    frames['large']=None;frames['minimap']=registration
    assert automatic.observe(capture,.64,minimum=18)[2]==mini
    assert small.resets==2
    frames['minimap']=None
    assert automatic.observe(capture,.66,minimum=18)[0] is None


def test_probable_large_map_suspends_player_crop_until_confirmed():
    from types import SimpleNamespace

    mini, large = areas()
    reads = []
    region = object()
    minimap = SimpleNamespace(reset=lambda: None, observe=lambda *_args, **_kwargs: (region, 'reference'))
    fullscreen = SimpleNamespace(pending=None)

    def observe_large(*_args, **_kwargs):
        fullscreen.pending = 'different-region'
        return None, 'search'

    fullscreen.observe = observe_large
    detector = AutomaticMapTracker(minimap, fullscreen, mini, large)

    def read(area):
        reads.append(area.view_kind)
        return None, None

    assert detector.observe(read, 0, minimum=18, probe_large=lambda: False) == (region, 'reference', mini)
    assert reads == ['minimap']
    reads.clear()
    assert detector.observe(read, .55, minimum=18, probe_large=lambda: True) == (None, 'search', large)
    assert reads == ['large']
    reads.clear()
    assert detector.observe(read, .6, minimum=18, large_only=True) == (None, 'search', large)
    assert reads == ['large']


def test_full_map_is_still_detected_if_header_cue_is_missing():
    from types import SimpleNamespace

    mini, large = areas()
    hit = object()
    minimap = SimpleNamespace(reset=lambda: None, observe=lambda *_args, **_kwargs: (None, 'search'))
    fullscreen = SimpleNamespace(observe=lambda *_args, **_kwargs: (hit, 'reference'))
    detector = AutomaticMapTracker(minimap, fullscreen, mini, large)
    for time in (0, .6, 1.1):
        assert detector.observe(lambda _area: (None, None), time, minimum=18,
                                probe_large=lambda: False)[2] == mini
    assert detector.observe(lambda _area: (None, None), 1.7, minimum=18,
                            probe_large=lambda: False) == (hit, 'reference', large)


def test_window_changes_geometry_and_requires_confirmation_in_each_mode(qapp,tmp_path):
    from app.services.context import AppContext
    from app.modules.overlay.service import OverlayService
    screen=qapp.primaryScreen();g=screen.geometry()
    mini=CaptureArea(map_id='altgard',screen_name=screen.name(),screen_x=g.x(),screen_y=g.y(),
        screen_width=g.width(),screen_height=g.height(),pixel_ratio=screen.devicePixelRatio(),
        x=100,y=40,width=330,height=220,view_kind='minimap')
    full=mini.model_copy(update=dict(x=0,y=0,width=g.width(),height=g.height(),view_kind='large'))
    service=OverlayService(AppContext(tmp_path))
    class Worker:
        def __init__(self):self.exclusions=[]
        def set_exclusion(self,*args):self.exclusions.append(args)
    worker=Worker();service.worker=worker
    service.context.prefs.overlay.enabled=True
    registration=Registration(np.array([[600.,0,0],[0,600.,0]]),40,.9)
    try:
        for area in [mini,full,mini]:
            service.on_registration(registration,{'area':area})
            assert not service.window.isVisible()
            service.on_registration(registration,{'area':area})
            assert service.window.isVisible()
            assert service.window.geometry().getRect()==(area.screen_x+area.x,area.screen_y+area.y,area.width,area.height)
            assert worker.exclusions[-1][2]==area.view_kind
            assert 'pontos desta camada' in service.status
        service.on_registration(None,{'area':mini})
        assert not service.window.isVisible() and service.window.registration is None
    finally:
        service.worker=None;service.stop();service.watchdog.stop()


def test_map_candidates_confirm_switch_and_probe_one_alternative_per_interval():
    from app.modules.overlay.live_worker import MapCandidates

    calls = []

    class Tracker:
        def __init__(self, name):
            self.name = name

        def observe(self, frame, now, **kwargs):
            calls.append(self.name)
            return (frame if self.name == frame else None), 'reference'

        def reset(self):
            pass

    refs = [(name, name) for name in ('altgard', 'verteron', 'reshanta')]
    candidates = MapCandidates(Tracker)
    candidates.configure(refs)
    assert candidates.observe('altgard', 0)[0] is None
    assert candidates.observe('altgard', .1)[0] == 'altgard'
    calls.clear()
    assert candidates.observe('altgard', .2)[0] == 'altgard' and calls == ['altgard']
    assert candidates.observe('reshanta', .4)[0] is None and candidates.map_id is None
    assert calls[-2:] == ['altgard', 'verteron']
    calls.clear()
    assert candidates.observe('reshanta', .5)[0] is None and not calls
    assert candidates.observe('reshanta', .7)[0] is None and calls[-1] == 'reshanta'
    assert candidates.observe('reshanta', .8)[0] == 'reshanta'
    assert candidates.map_id == 'reshanta'
    assert candidates.observe('unknown', 1.2)[0] is None and candidates.map_id is None
    candidates.configure([refs[1], refs[0], refs[2]])
    assert candidates.observe('verteron', 1.6)[0] is None  # user fallback leads the search
    assert candidates.observe('altgard', 1.7)[0] is None  # one candidate frame never publishes
    assert candidates.observe('altgard', 1.9)[0] is None
    assert candidates.observe('altgard', 2.0)[0] == 'altgard'


def test_large_view_keeps_player_region_and_unknown_hides_markers(qapp, tmp_path, monkeypatch):
    from app.core.models import MapLocation
    from app.services.context import AppContext
    from app.ui.main_window import MainWindow
    from app.modules.overlay import service as mod

    context = AppContext(tmp_path)
    window = MainWindow(context)
    service = window.overlay
    monkeypatch.setattr(service, "set_exclusion", lambda registration: None)
    clock = [10.]
    monkeypatch.setattr(mod.time, 'monotonic', lambda: clock[0])
    screen = qapp.primaryScreen()
    geom = screen.geometry()
    mini = CaptureArea(map_id='altgard', screen_name=screen.name(), screen_x=geom.x(), screen_y=geom.y(),
                       screen_width=geom.width(), screen_height=geom.height(), x=20, y=30, width=300,
                       height=220, pixel_ratio=screen.devicePixelRatio(), view_kind='minimap')
    other = mini.model_copy(update={'map_id': 'verteron', 'view_kind': 'large', 'x': 0, 'y': 0,
                                    'width': geom.width(), 'height': geom.height()})
    unknown = mini.model_copy(update={'map_id': ''})
    registration = Registration(np.array([[740., 0, -80.], [0, 740., -80.]]), 40, .9)
    settings = context.prefs.overlay
    settings.enabled = True
    try:
        assert context.map_location == MapLocation() and not service.window.markers
        service.on_registration(registration, {'area': mini})
        assert context.map_location == MapLocation()
        service.on_registration(registration, {'area': mini})
        assert context.map_location == MapLocation('altgard', 'altgard', 'minimap')
        assert 'Altgard' in window.overlay_page.map_status.text()
        layer_altgard = service.window.markers
        service.on_registration(registration, {'area': other})
        assert context.map_location == MapLocation('altgard')
        service.on_registration(registration, {'area': other})
        assert context.map_location == MapLocation('altgard', 'verteron', 'large')
        assert 'Verteron' in window.overlay_page.map_status.text() and 'Altgard' in window.overlay_page.map_status.text()
        assert service.window.markers != layer_altgard
        settings_fallback = window.overlay_page.maps.findData('verteron')
        window.overlay_page.maps.setCurrentIndex(settings_fallback)
        assert settings.fallback_map_id == 'verteron' and settings.map_id == 'altgard'
        assert service.references()[0][0] == 'verteron'
        service.on_registration(None, {'area': unknown})
        assert context.map_location == MapLocation('altgard') and not service.window.isVisible()
        assert not service.window.markers and 'Mapa não identificado' in window.overlay_page.map_status.text()
        clock[0] += 1.3
        service.on_registration(None, {'area': unknown})
        assert context.map_location == MapLocation() and not service.window.markers
        service.on_registration(registration, {'area': mini})
        service.on_registration(registration, {'area': mini})
        assert context.map_location == MapLocation('altgard', 'altgard', 'minimap')
        assert service.window.markers == layer_altgard and settings.enabled
        service.set_capture_context(True, 'menu')
        assert context.map_location == MapLocation('altgard') and not service.window.markers
        service.on_registration(registration, {'area': mini, 'epoch': 0})
        assert context.map_location == MapLocation('altgard')
        saved = AppContext(tmp_path)
        assert saved.prefs.overlay.fallback_map_id == 'verteron' and saved.map_location == MapLocation()
    finally:
        window.close()
