# SPDX-License-Identifier: GPL-3.0-only
from types import SimpleNamespace
import numpy as np
import pytest
from app.services.context import AppContext
from app.ui.main_window import MainWindow
from app.ui.overlay_visibility import OverlayVisibility
from app.modules.overlay.foreground import GameWindow, GAME_NAMES
from app.modules.overlay.menu_monitor import classify_lines, fullscreen_close


class Probe:
    game = GameWindow(123,456,0,0,1920,1080)
    def game_foreground(self, owned=(), previous=None):
        return self.game


@pytest.fixture
def gated(qapp,tmp_path):
    main=MainWindow(AppContext(tmp_path))
    probe=Probe();gate=OverlayVisibility(main,probe)
    windows=[main.overlay.window,main.event_panel,main.combat_page.panel,main.sonar_alert,
             main.quick_menu,main.quick_menu.panel]
    for window,role in zip(windows,('map','hud','hud','alert','hud','hud')):
        gate.register(window,role)
    gate.poll()
    yield main,gate,probe,windows
    gate.shutdown();main.close()


def test_alt_tab_hides_every_window_and_module_refresh_cannot_reopen_it(gated):
    main,gate,probe,windows=gated
    for window in windows:window.show()
    assert all(window.isVisible() for window in windows)
    popup=main.event_panel.event_selector.menu_widget
    popup.show()
    assert popup in gate.associated_popups()
    before=main.context.prefs.model_dump()
    probe.game=None;gate.poll()
    assert not any(window.isVisible() for window in windows)
    assert not popup.isVisible()
    for window in windows:window.show()  # Includes setVisible and all periodic producers.
    assert not any(window.isVisible() for window in windows)
    assert main.context.prefs.model_dump()==before
    probe.game=Probe.game;gate.poll()
    assert all(window.isVisible() for window in windows if window is not main.sonar_alert)
    assert not main.sonar_alert.isVisible()  # Background alerts are not replayed.


def test_full_map_keeps_only_markers_and_menu_hides_everything(gated):
    _,gate,_,windows=gated
    for window in windows:window.show()
    gate.set_context(True,'map')
    assert windows[0].isVisible() and not any(w.isVisible() for w in windows[1:])
    gate.set_context(True,'menu')
    assert not any(w.isVisible() for w in windows)
    gate.set_context(True)
    assert all(w.isVisible() for w in windows if w._overlay_role!='alert')


def test_disable_and_expired_alert_while_hidden_stay_hidden_on_return(gated):
    main,gate,probe,windows=gated
    main.event_panel.show();main.sonar_alert.present()
    probe.game=None;gate.poll()
    main.event_panel.hide();main.sonar_alert.timer.timeout.emit()
    probe.game=Probe.game;gate.poll()
    assert not main.event_panel.isVisible() and not main.sonar_alert.isVisible()


def test_real_producers_keep_capture_and_preferences_intact(gated):
    main,gate,probe,_=gated
    main.context.prefs.overlay.events_panel=True
    main.context.prefs.combat.panel_visible=True
    main.combat.accept(dict(type='hello',protocol=1,saValidated=False))
    main.combat.engine.start_run('Visibility test');main.combat.auto_instances=True
    main.combat.accept(dict(type='event',session='visibility-test',sequence=1,time_ms=0,
        kind='ZoneChangedEvent',payload=dict(MapId=600001,IsDungeon=True)))
    main.event_panel.refresh();main.combat_page.panel.refresh()
    assert main.event_panel.isVisible() and main.combat_page.panel.isVisible()
    run=main.combat.engine.run_id
    probe.game=None;gate.poll()
    main.event_panel.refresh();main.combat_page.panel.refresh()
    main.quick_menu.runtime=True;main.quick_menu.refresh()
    assert not main.event_panel.isVisible() and not main.combat_page.panel.isVisible() and not main.quick_menu.isVisible()
    assert main.combat.engine.active and main.combat.engine.run_id==run
    assert main.context.prefs.combat.panel_visible and main.context.prefs.overlay.events_panel
    probe.game=Probe.game;gate.poll()
    assert main.event_panel.isVisible() and main.combat_page.panel.isVisible()


def test_old_menu_response_is_rejected_after_alt_tab_and_return(gated):
    _,gate,probe,_=gated
    old=(gate.game,gate.generation)
    probe.game=None;gate.poll();probe.game=Probe.game;gate.poll()
    gate.on_menu(old,'menu')
    assert gate.mode=='play' and gate.active
    gate.on_menu((gate.game,gate.generation),'menu')
    assert gate.mode=='menu'


def test_confirmed_large_map_registration_preserves_marker_exception(gated):
    main,gate,_,_=gated
    import time
    main.overlay.capture_area=SimpleNamespace(view_kind='large')
    main.overlay.window.registration=object()
    main.overlay.last_result=time.perf_counter()
    gate.on_menu((gate.game,gate.generation),'fullscreen')
    assert gate.mode=='map'
    gate.on_menu((gate.game,gate.generation),'menu')
    assert gate.mode=='menu'  # A definite menu title overrides old map registration.
    main.overlay.window.registration=None;main.overlay.capture_area=None


@pytest.mark.parametrize('text',['Settings','Inventory','Skills','Configurações','Inventário','Habilidades'])
def test_known_menu_headers(text):
    assert classify_lines([dict(text=text,x=30,y=25,height=26)],1920,1080)=='menu'


def test_header_recognition_excludes_quest_text_small_labels_and_minimap_titles():
    assert classify_lines([dict(text='Collect inventory supplies',x=100,y=100,height=20)],1920,1080)=='play'
    assert classify_lines([dict(text='Settings',x=10,y=20,height=8)],1920,1080)=='play'
    assert classify_lines([dict(text='Inventory',x=1700,y=80,height=16)],1920,1080)=='play'
    assert classify_lines([dict(text='Map: Verteron',x=50,y=20,height=28)],1920,1080)=='map'
    assert classify_lines([],1920,1080,True)=='play'


def test_gameplay_cross_without_menu_header_does_not_hide_hud():
    # Live city observations: close geometry was positive, but there was no
    # recognized menu header and the game retained foreground focus.
    assert classify_lines([],1920,1080,True)=='play'
    assert classify_lines([dict(text='A nearby player',x=900,y=140,height=24)],1920,1080,True)=='play'
    assert classify_lines([dict(text='Settings',x=30,y=25,height=26)],1920,1080,True)=='menu'
    assert classify_lines([dict(text='Map: Altgard',x=30,y=25,height=26)],1920,1080,True)=='map'


def test_monitor_emits_only_confirmed_classification(monkeypatch):
    from app.modules.overlay.menu_monitor import MenuMonitor
    import mss
    game=Probe.game
    monitor=MenuMonitor(Probe());job=(game,0);monitor.set_game(job)
    class Capture:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def grab(self,area):return np.zeros((area['height'],area['width'],4),np.uint8)
    monkeypatch.setattr(mss,'MSS',Capture)
    monkeypatch.setattr('app.modules.overlay.menu_monitor.fullscreen_close',lambda *args:True)
    def recognize(image):
        monitor.stopped.set()
        return []
    monkeypatch.setattr(monitor.ocr,'recognize',recognize)
    observed=[]
    monitor.observed.connect(lambda token,mode:observed.append((token,mode)))
    monitor.run()
    assert observed==[(job,'play')]


@pytest.mark.parametrize('width',[1280,1920,3840])
def test_close_geometry_works_with_full_frame_and_upper_crop(width):
    import cv2
    height=round(width*9/16);frame=np.zeros((height,width,3),np.uint8)
    x,y=round(width*.98),round(height*.038)
    radius=round(width*.008);pen=max(1,round(width*.001))
    cv2.line(frame,(x-radius,y-radius),(x+radius,y+radius),(225,225,225),pen)
    cv2.line(frame,(x-radius,y+radius),(x+radius,y-radius),(225,225,225),pen)
    assert fullscreen_close(frame)
    assert fullscreen_close(frame[:round(height*.45)],height)
    frame[:]=0
    assert not fullscreen_close(frame)


def test_supported_game_names_do_not_include_launchers_or_browsers():
    assert 'aion2.exe' in GAME_NAMES and 'aion2-win64-shipping.exe' in GAME_NAMES
    assert 'aion2-launcher.exe' not in GAME_NAMES and 'chrome.exe' not in GAME_NAMES


def test_sonar_visual_preview_stays_in_app_when_game_hud_is_blocked(gated,qapp,monkeypatch):
    from PySide6.QtCore import Qt
    from app.ui.localized_widgets import QDialog
    from app.ui.sonar_page import SonarAlert
    main,gate,probe,_=gated
    probe.game=None;gate.poll()
    checked=[]
    def examine(dialog):
        dialog.show();qapp.processEvents()
        preview=dialog.findChild(SonarAlert)
        assert preview.isVisible() and not preview.isWindow()
        assert not dialog.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
        assert preview.testing and not preview.intensity.isVisible()
        assert not main.sonar_alert.isVisible() and not main.sonar.active
        from PySide6.QtTest import QTest
        position=main.context.prefs.sonar_alert_position
        QTest.mouseClick(preview.title,Qt.MouseButton.LeftButton)
        assert main.context.prefs.sonar_alert_position==position
        checked.append(True);dialog.accept();return 0
    monkeypatch.setattr(QDialog,'exec',examine)
    main.sonar_page.test_notice()
    assert checked==[True]


def native_probe(name='aion2.exe', foreground=100, minimized=False):
    from app.modules.overlay.foreground import ForegroundProbe
    class User:
        def GetForegroundWindow(self):return foreground
        def IsIconic(self, handle):return minimized
        def IsWindowVisible(self, handle):return True
        def GetWindowThreadProcessId(self,handle,pid):pid._obj.value=45
        def GetClientRect(self,handle,rect):rect._obj.right=3840;rect._obj.bottom=2160;return True
        def ClientToScreen(self,handle,point):point._obj.x=-3840;return True
    probe=ForegroundProbe.__new__(ForegroundProbe);probe.available=True;probe.user=User()
    probe.process_name=lambda pid:name
    return probe


def test_native_probe_is_fail_closed_and_preserves_physical_negative_origin():
    assert native_probe().game_foreground()==GameWindow(100,45,-3840,0,3840,2160)
    assert native_probe('chrome.exe').game_foreground() is None
    assert native_probe(minimized=True).game_foreground() is None
    assert native_probe(foreground=0).game_foreground() is None


def test_owned_overlay_focus_is_allowed_but_main_app_focus_is_not():
    previous=GameWindow(100,45,-3840,0,3840,2160)
    probe=native_probe(foreground=200)
    probe.process_name=lambda pid:'aion2.exe' if current[0]==100 else 'strigoiaethermap.exe'
    current=[200]
    original=probe.user.GetWindowThreadProcessId
    def pid(handle,out):current[0]=handle;original(handle,out)
    probe.user.GetWindowThreadProcessId=pid
    assert probe.game_foreground({200},previous)==previous
    assert probe.game_foreground({300},previous) is None
