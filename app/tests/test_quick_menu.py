# SPDX-License-Identifier: GPL-3.0-only
"""Module controls tested with isolated preferences; no game/audio capture."""
from types import SimpleNamespace
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from app.services.context import AppContext
from app.ui.main_window import MainWindow
from app.core.i18n import set_language


def test_quick_menu_visibility_keeps_capture_separate_and_syncs_pages(qapp, tmp_path):
    context = AppContext(tmp_path)
    window = MainWindow(context)
    menu = window.quick_menu
    try:
        assert window.combat.process is None and not menu.isVisible()
        menu.runtime = True; menu.refresh()
        QTest.mouseClick(menu.launcher, Qt.MouseButton.LeftButton)
        assert menu.panel.isVisible()
        qapp.processEvents()
        assert menu.panel.grab().toImage().pixelColor(6, 120).alpha() >= 240
        assert menu.switches["combat"].isChecked()
        assert menu.states["combat"].text() == "Aguardando instância"
        assert not window.combat_page.panel.isVisible()
        window.combat.engine.start_run()
        window.combat.auto_instances = True
        window.combat.accept(dict(type="hello", protocol=1, saValidated=False))
        window.combat.accept(dict(type="event", session="synthetic-menu-instance", sequence=1,
            time_ms=0, kind="ZoneChangedEvent", payload=dict(MapId=600001, IsDungeon=True)))
        assert window.combat_page.panel.isVisible()
        assert window.combat_page.panel_visible.isChecked()
        assert window.combat.process is None
        menu.switches["combat"].setChecked(False)
        assert window.combat.engine.active and not window.combat_page.panel.isVisible()
        menu.switches["events"].setChecked(True)
        assert window.event_panel.isVisible() and window.events.panel_toggle.isChecked()
        window.event_panel.dismiss()
        assert not menu.switches["events"].isChecked()
        set_language("en_US"); menu.refresh()
        assert menu.states["events"].text() == "Hidden"
        menu.toggle_panel()
        assert not menu.panel.isVisible()
        context.prefs.quick_menu.enabled = False; context.save()
        assert not menu.isVisible()
    finally:
        window.close(); set_language("pt_BR")


def test_quick_menu_recovers_and_saves_logical_screen_position(qapp, tmp_path):
    context = AppContext(tmp_path)
    context.prefs.quick_menu.position = (99999, -99999)
    window = MainWindow(context)
    try:
        menu = window.quick_menu
        assert qapp.primaryScreen().availableGeometry().contains(menu.geometry())
        menu.move(qapp.primaryScreen().availableGeometry().topLeft()+QPoint(21, 90))
        menu.save_position()
        assert AppContext(tmp_path).prefs.quick_menu.position == (menu.x(), menu.y())
        menu.runtime = True; menu.refresh(); menu.toggle_panel()
        assert qapp.primaryScreen().availableGeometry().contains(menu.panel.geometry())
    finally:
        window.close()


def test_quick_map_uses_calibration_or_opens_configuration(qapp, tmp_path, monkeypatch):
    window = MainWindow(AppContext(tmp_path))
    try:
        window.quick_menu.toggle_maps(True)
        assert window.stack.currentIndex() == 6 and window.overlay.worker is None
        area = tmp_path / "saved-area.json"; area.write_text("{}")
        window.context.prefs.overlay.minimap_area = str(area)
        calls = []
        monkeypatch.setattr(window.overlay_page, "start", lambda: calls.append(window.overlay_page.view_kind.currentData()))
        window.quick_menu.toggle_maps(True)
        assert calls == ["minimap"]
    finally:
        window.close()


def test_automatic_combat_retries_without_duplicate_collectors_and_can_be_disabled(qapp, tmp_path, monkeypatch):
    from app.modules.combat import service as module
    context = AppContext(tmp_path)
    service = module.CombatService(context)
    monkeypatch.setattr(module, "HELPER", SimpleNamespace(is_file=lambda: True))
    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setenv("WINDIR", str(tmp_path))
    starts, stops = [], []
    def start():
        starts.append(True); service.process = object()
    def stop():
        stops.append(True); service.process = None
    monkeypatch.setattr(service, "start", start)
    monkeypatch.setattr(service, "stop", stop)
    try:
        service.enable_automatic()
        assert not starts and service.status == "Npcap necessário para medir dano"
        driver = tmp_path / "System32/Npcap/wpcap.dll"
        driver.parent.mkdir(parents=True); driver.write_bytes(b"isolated readiness fixture, never loaded")
        service.ensure_automatic(); service.ensure_automatic()
        assert len(starts) == 1
        service.process = None; service.ensure_automatic()
        assert len(starts) == 2
        context.prefs.combat.auto_capture = False; context.save()
        assert service.process is None and service.status == "Medição automática desativada"
        service.ensure_automatic(); assert len(starts) == 2
    finally:
        service.shutdown()
        assert not service.watchdog.isActive()


def test_main_runtime_starts_automatic_combat_but_preview_never_captures(qapp, tmp_path, monkeypatch):
    from app.modules.combat.service import CombatService
    from app.modules.pets.service import PetService
    from app.ui.overlay_visibility import OverlayVisibility
    started = []
    monkeypatch.setattr(CombatService, "enable_automatic", lambda service: started.append(service))
    monkeypatch.setattr(PetService, "enable_automatic", lambda service: started.append(service))
    monkeypatch.setattr(OverlayVisibility, "start", lambda gate: gate.set_context(True))
    preview = MainWindow(AppContext(tmp_path / "preview"))
    actual = MainWindow(AppContext(tmp_path / "actual"), runtime=True)
    try:
        qapp.processEvents()
        assert started == [actual.combat, actual.pets]
        assert not hasattr(actual.combat_page, "name")
        assert not hasattr(actual.combat_page, "start_button")
        assert not hasattr(actual.combat_page, "stop_button")
        assert actual.quick_menu.isVisible() and not preview.quick_menu.isVisible()
    finally:
        preview.close(); actual.close()
