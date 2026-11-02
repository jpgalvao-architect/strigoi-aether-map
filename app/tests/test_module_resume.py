# SPDX-License-Identifier: GPL-3.0-only
"""First-run selection and saved module intent without any game/audio capture."""
from types import SimpleNamespace
from PySide6.QtCore import QRect
from app.infrastructure.storage import atomic_json
from app.modules.overlay.selection import CaptureArea
from app.services.context import AppContext
from app.ui.main_window import MainWindow
from app.ui.module_resume import ModuleResume
from app.core.models import Preferences,OverlaySettings


def save_area(window,tmp_path):
    page=window.overlay_page;screen=window.screen();g=screen.geometry()
    area=CaptureArea(map_id=page.maps.currentData(),screen_name=screen.name(),screen_x=g.x(),screen_y=g.y(),
        screen_width=g.width(),screen_height=g.height(),pixel_ratio=screen.devicePixelRatio(),
        x=10,y=10,width=200,height=120,view_kind='minimap')
    path=tmp_path/'area.json';atomic_json(path,area)
    window.context.prefs.overlay.minimap_area=str(path)
    return path


def test_legacy_enabled_choices_migrate_to_saved_requests_without_capture(qapp,tmp_path):
    atomic_json(tmp_path/'preferences.json',Preferences(overlay=OverlaySettings(enabled=True),sonar_enabled=True))
    context=AppContext(tmp_path)
    assert context.prefs.overlay.resume_enabled and context.prefs.sonar_resume
    assert not context.prefs.overlay.enabled and not context.prefs.sonar_enabled


def test_first_toggle_opens_one_selection_and_cancel_restores_window(qapp,tmp_path,monkeypatch):
    window=MainWindow(AppContext(tmp_path));window.show()
    window.navigate('overlay')
    page=window.overlay_page;opened=[]
    monkeypatch.setattr(page,'show_selector',lambda:opened.append(True))
    try:
        assert page.view_kind.currentData()=='minimap' and page.select_button.isVisible()
        window.quick_menu.toggle_maps(True);window.quick_menu.toggle_maps(True)
        assert page._selection_pending and not window.isVisible()
        assert not page.select_button.isEnabled()
        page.cancel_area()
        assert window.isVisible() and not page._selection_pending
        assert not window.context.prefs.overlay.resume_enabled
        assert window.overlay.worker is None
    finally:window.close()


def test_selection_auto_activates_then_later_toggles_do_not_minimize(qapp,tmp_path,monkeypatch):
    window=MainWindow(AppContext(tmp_path));window.show();page=window.overlay_page
    monkeypatch.setattr(page,'show_selector',lambda:None)
    starts=[]
    def start():
        starts.append(True);window.context.prefs.overlay.enabled=True
    monkeypatch.setattr(window.overlay,'start',start)
    try:
        window.quick_menu.toggle_maps(True)
        page.accept_area(QRect(10,10,200,120))
        assert len(starts)==1 and page.minimap_ready() and window.isMinimized()
        window.showNormal();page.stop();window.quick_menu.toggle_maps(True)
        assert len(starts)==2 and not window.isMinimized() and window.isVisible()
    finally:window.close()


def test_invalid_selection_requires_setup_and_shutdown_blocks_delayed_selector(qapp,tmp_path,monkeypatch):
    import app.ui.live_overlay_page as module
    window=MainWindow(AppContext(tmp_path));page=window.overlay_page
    path=save_area(window,tmp_path);assert page.minimap_ready()
    path.write_text('{}');assert not page.minimap_ready()
    opened=[];monkeypatch.setattr(module,'ScreenSelection',lambda *args:opened.append(True))
    page.select_area();page.shutdown();page.show_selector()
    assert opened==[]
    window.close()


def test_enabled_and_disabled_choices_survive_close_without_preview_capture(qapp,tmp_path):
    context=AppContext(tmp_path);window=MainWindow(context)
    context.prefs.overlay.resume_enabled=True;context.prefs.sonar_resume=True
    context.prefs.overlay.events_panel=True;context.prefs.pets.panel_visible=True
    context.prefs.routine.panel_visible=True;context.prefs.combat.panel_visible=False
    context.prefs.routes.panel_visible=False;context.save();window.close()
    reloaded=AppContext(tmp_path);preview=MainWindow(reloaded)
    try:
        assert reloaded.prefs.overlay.resume_enabled and reloaded.prefs.sonar_resume
        assert not reloaded.prefs.overlay.enabled and not reloaded.prefs.sonar_enabled
        assert reloaded.prefs.overlay.events_panel and reloaded.prefs.pets.panel_visible and reloaded.prefs.routine.panel_visible
        assert not reloaded.prefs.combat.panel_visible and not reloaded.prefs.routes.panel_visible
        assert preview.overlay.worker is None and preview.sonar.worker is None and preview.module_resume is None
        preview.overlay_page.stop();preview.sonar.stop()
        assert not reloaded.prefs.overlay.resume_enabled and not reloaded.prefs.sonar_resume
    finally:preview.close()
    assert not AppContext(tmp_path).prefs.overlay.resume_enabled and not AppContext(tmp_path).prefs.sonar_resume


def test_resume_waits_for_game_uses_fresh_pid_and_does_not_repeat_or_minimize(qapp,tmp_path,monkeypatch):
    import app.ui.module_resume as module
    window=MainWindow(AppContext(tmp_path));window.show();save_area(window,tmp_path)
    context=window.context;context.prefs.overlay.resume_enabled=True;context.prefs.sonar_resume=True
    context.prefs.sonar_process_name='AION2.exe'
    available=[];monkeypatch.setattr(module,'processes',lambda:available)
    maps=[];audio=[]
    monkeypatch.setattr(window.overlay_page,'start',lambda:maps.append(True))
    def refresh():
        window.sonar_page.process.clear();window.sonar_page.process.addItem('AION2.exe · 555',555)
    monkeypatch.setattr(window.sonar_page,'refresh_processes',refresh)
    monkeypatch.setattr(window.sonar_page,'start',lambda:audio.append(window.sonar_page.process.currentData()))
    window.sonar.available=True;resume=ModuleResume(window);resume.timer.stop()
    try:
        resume.refresh();assert not maps and not audio
        available.append(SimpleNamespace(pid=444,name='unrelated.exe'))
        resume.refresh();assert not maps and not audio
        available.append(SimpleNamespace(pid=555,name='AION2.exe'))
        resume.refresh();resume.refresh()
        assert maps==[True] and audio==[555] and not window.isMinimized()
        assert window.overlay.worker is None and window.sonar.worker is None
    finally:resume.shutdown();window.close()
