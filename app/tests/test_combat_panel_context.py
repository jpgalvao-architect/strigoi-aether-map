# SPDX-License-Identifier: GPL-3.0-only
"""Panel context tests use synthetic events, never live capture or arena IDs."""
import json
from app.services.context import AppContext
from app.ui.main_window import MainWindow


def scenario(tmp_path):
    window = MainWindow(AppContext(tmp_path))
    service = window.combat
    service.engine.start_run()
    service.auto_instances = True
    service.accept(dict(type="hello", protocol=1, saValidated=False))
    sequence = 0
    def send(kind, **payload):
        nonlocal sequence
        sequence += 1
        message = dict(type="event", session="synthetic-panel-only", sequence=sequence,
            time_ms=sequence * 100, kind=kind, payload=payload)
        service.accept(message);service.changed.emit()
        return message
    return window, service, send


def test_panel_enters_leaves_reenters_and_does_not_stop_capture(qapp, tmp_path):
    window, service, send = scenario(tmp_path)
    try:
        panel = window.combat_page.panel
        assert window.context.prefs.combat.panel_visible and not panel.isVisible()
        send("ZoneChangedEvent", MapId=240000, IsDungeon=False)
        assert not panel.isVisible()
        send("ZoneChangedEvent", MapId=600001, IsDungeon=True)
        assert panel.isVisible() and service.in_instance
        send("ZoneChangedEvent", MapId=600001, IsDungeon=True, IsTeleport=True)
        assert panel.isVisible()
        send("ZoneChangedEvent", MapId=240000, IsDungeon=False)
        assert not panel.isVisible() and not service.in_instance and service.auto_instances
        assert window.context.prefs.combat.panel_visible
        send("ZoneChangedEvent", MapId=600001, IsDungeon=True)
        assert panel.isVisible() and service.engine.active
        window.quick_menu.toggle_combat(False)
        assert not panel.isVisible() and service.engine.active
        send("ZoneChangedEvent", MapId=600002, IsDungeon=True)
        assert not panel.isVisible()  # Explicit off remains respected.
        window.quick_menu.toggle_combat(True)
        assert panel.isVisible()
    finally:
        window.close()


def test_only_valid_instance_timers_arm_unknown_maps_and_old_timers_cannot_show(qapp, tmp_path):
    window, service, send = scenario(tmp_path)
    try:
        # This arbitrary map fixture is not a claimed PvP identifier.
        zone = 812345
        send("ZoneChangedEvent", MapId=zone, IsDungeon=False)
        stamp = 1_800_000_000_000
        send("InstanceTimerEvent", MapId=zone, Kind=256, StartMs=stamp, EndMs=stamp+300_000)
        assert not service.in_instance and not window.combat_page.panel.isVisible()
        send("InstanceTimerEvent", MapId=zone, Kind=1, StartMs=stamp, EndMs=stamp+300_000)
        assert service.in_instance and window.combat_page.panel.isVisible()
        run_id = service.engine.run_id
        service.accept(dict(type="status", code="WaitingForGame", reset_zone=True));service.changed.emit()
        assert not window.combat_page.panel.isVisible()
        send("InstanceTimerEvent", MapId=zone, Kind=1, StartMs=stamp, EndMs=stamp+300_000)
        assert window.combat_page.panel.isVisible() and service.engine.run_id == run_id
        send("ZoneChangedEvent", MapId=zone, IsDungeon=False, IsTeleport=True)
        assert window.combat_page.panel.isVisible()
        send("ZoneChangedEvent", MapId=240000, IsDungeon=False)
        send("InstanceTimerEvent", MapId=zone, Kind=1, StartMs=stamp, EndMs=stamp+300_000)
        assert not service.in_instance and not window.combat_page.panel.isVisible()
    finally:
        window.close()


def test_disconnect_and_shutdown_hide_the_panel_without_showing_stale_context(qapp, tmp_path):
    window, service, send = scenario(tmp_path)
    try:
        send("ZoneChangedEvent", MapId=600001, IsDungeon=True)
        service.accept(dict(type="status", code="WaitingForGame", reset_zone=False))
        service.changed.emit()
        assert window.combat_page.panel.isVisible()  # Quiet but connected is not an exit.
        service.accept(dict(type="status", code="WaitingForGame", reset_zone=True))
        service.changed.emit()
        assert not service.in_instance and not window.combat_page.panel.isVisible()
        service.accept(dict(type="status", code="Capturing"));service.changed.emit()
        assert not window.combat_page.panel.isVisible()  # Fresh entry evidence is required.
        previous = service.engine.run_id
        send("ZoneChangedEvent", MapId=600001, IsDungeon=True, IsTeleport=True)
        assert window.combat_page.panel.isVisible() and service.engine.run_id == previous
        service.stop()
        assert not window.combat_page.panel.isVisible() and not service.in_instance
    finally:
        window.close()


def test_panel_default_upgrade_happens_once_and_preserves_later_opt_out(tmp_path):
    context = AppContext(tmp_path)
    assert context.prefs.combat.panel_visible
    context.prefs.combat.panel_visible = False
    context.save()
    assert AppContext(tmp_path).prefs.combat.panel_visible is False
    old = json.loads((tmp_path / "preferences.json").read_text(encoding="utf-8"))
    old["combat"].pop("panel_mode_release")
    (tmp_path / "preferences.json").write_text(json.dumps(old),encoding="utf-8")
    upgraded = AppContext(tmp_path)
    assert upgraded.prefs.combat.panel_visible
    upgraded.prefs.combat.panel_visible = False;upgraded.save()
    assert AppContext(tmp_path).prefs.combat.panel_visible is False
