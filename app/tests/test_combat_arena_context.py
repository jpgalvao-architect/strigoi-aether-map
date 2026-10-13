# SPDX-License-Identifier: GPL-3.0-only
"""Replay observed SA context IDs with synthetic identities and timestamps."""
from app.tests.test_combat_panel_context import scenario
import pytest


@pytest.mark.parametrize("zone,timer,team", [(61, 8, False), (60, 7, True)])
def test_observed_arena_panel_handles_timer_alias_reload_and_open_world_exit(qapp, tmp_path, zone, timer, team):
    window, service, send = scenario(tmp_path)
    try:
        panel = window.combat_page.panel
        send("ZoneChangedEvent", MapId=zone, IsDungeon=False)
        assert panel.isVisible() and service.engine.pvp and service.engine.team_pvp == team
        run = service.engine.run_id
        stamp = 1_800_000_000_000
        for kind in (1, 2):
            send("InstanceTimerEvent", MapId=timer, Kind=kind, StartMs=stamp + kind * 1000,
                 EndMs=stamp + 300_000)
        assert service.engine.map_id == zone and service.engine.run_id == run
        send("ZoneChangedEvent", MapId=zone, IsDungeon=False, IsTeleport=True)
        send("InstanceTimerEvent", MapId=timer, Kind=2, StartMs=stamp+2000, EndMs=stamp+300_000)
        assert service.engine.run_id == run and panel.isVisible()
        send("InstanceTimerEvent", MapId=timer, Kind=3, StartMs=stamp+3000, EndMs=stamp+300_000)
        assert service.engine.run_id == run
        send("ZoneChangedEvent", MapId=1110, IsDungeon=False)
        assert not panel.isVisible() and not service.engine.active
        send("InstanceTimerEvent", MapId=timer, Kind=2, StartMs=stamp+2000, EndMs=stamp+300_000)
        assert not panel.isVisible() and service.engine.map_id == 1110
        send("ZoneChangedEvent", MapId=zone, IsDungeon=False)
        assert panel.isVisible() and service.engine.run_id != run
    finally:
        window.close()


def test_timer_pair_is_specific_and_never_matches_other_arena(qapp, tmp_path):
    window, service, send = scenario(tmp_path)
    try:
        send("ZoneChangedEvent", MapId=61, IsDungeon=False)
        run = service.engine.run_id
        stamp = 1_800_000_000_000
        send("InstanceTimerEvent", MapId=7, Kind=1, StartMs=stamp, EndMs=stamp+300_000)
        assert service.instance_timers == {} and service.engine.run_id == run
        assert service.engine.map_id == 61
    finally:
        window.close()


def test_team_pending_message_clears_only_when_roster_is_confirmed(qapp, tmp_path):
    from app.ui.combat_page import team_pending
    window, service, send = scenario(tmp_path)
    try:
        send("ZoneChangedEvent", MapId=60, IsDungeon=False)
        assert team_pending(service.engine.snapshot())
        assert "Time ainda não identificado" in window.combat_page.panel.state.text()
        send("PartyRosterEvent", Members=[dict(Name="Fixture teammate", ServerId=4)], Complete=False)
        assert team_pending(service.engine.snapshot())
        send("PartyRosterEvent", Members=[dict(Name="Fixture teammate", ServerId=4)], Complete=True)
        assert not team_pending(service.engine.snapshot())
        assert "Time ainda não identificado" not in window.combat_page.panel.state.text()
    finally:
        window.close()


def test_new_arena_does_not_trust_previous_open_world_party(qapp, tmp_path):
    from app.ui.combat_page import team_pending
    window, service, send = scenario(tmp_path)
    try:
        send("ZoneChangedEvent", MapId=1110, IsDungeon=False)
        send("PartyRosterEvent", Members=[dict(Name="Old party fixture", ServerId=4, Class=7)], Complete=True)
        assert service.engine.roster_complete
        send("ZoneChangedEvent", MapId=60, IsDungeon=False)
        assert not service.engine.roster and not service.engine.roster_jobs
        assert not service.engine.roster_complete and team_pending(service.engine.snapshot())
    finally:
        window.close()


def test_unobserved_rotating_maps_and_timer_alias_alone_never_enable_pvp(qapp, tmp_path):
    window, service, send = scenario(tmp_path)
    try:
        # Arbitrary fixture adjacent to 61: no inferred arena range is allowed.
        send("ZoneChangedEvent", MapId=62, IsDungeon=False)
        send("InstanceTimerEvent", MapId=8, Kind=1, StartMs=1_800_000_000_000,
             EndMs=1_800_000_300_000)
        assert not service.in_instance and not service.engine.pvp
        assert not window.combat_page.panel.isVisible()
    finally:
        window.close()


def test_new_same_map_arena_match_resets_but_reload_does_not(qapp, tmp_path):
    window, service, send = scenario(tmp_path)
    try:
        send("ZoneChangedEvent", MapId=61, IsDungeon=False)
        stamp = 1_800_000_000_000
        send("InstanceTimerEvent", MapId=8, Kind=1, StartMs=stamp, EndMs=stamp+30_000)
        send("InstanceTimerEvent", MapId=8, Kind=2, StartMs=stamp+30_000, EndMs=stamp+300_000)
        run = service.engine.run_id
        send("ZoneChangedEvent", MapId=61, IsDungeon=False, IsTeleport=True)
        send("InstanceTimerEvent", MapId=8, Kind=1, StartMs=stamp+600_000, EndMs=stamp+630_000)
        assert service.engine.run_id != run and service.engine.map_id == 61
        assert service.engine.pvp and window.combat_page.panel.isVisible()
        new_run = service.engine.run_id
        send("InstanceTimerEvent", MapId=8, Kind=2, StartMs=stamp+30_000, EndMs=stamp+300_000)
        assert service.engine.run_id == new_run
    finally:
        window.close()
