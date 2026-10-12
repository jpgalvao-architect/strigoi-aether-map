# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic isolated fixtures exercise arithmetic, not regional protocol claims."""
import pytest
from app.modules.combat.engine import CombatEngine
from app.modules.combat.history import CombatHistory


class Feed:
    def __init__(self, engine):
        self.engine, self.sequence = engine, 0

    def send(self, kind, time=0, **payload):
        self.sequence += 1
        message = dict(type="event", session="synthetic-unit-test", sequence=self.sequence,
                       time_ms=time, kind=kind, payload=payload)
        self.engine.process(message)
        return message


@pytest.fixture
def fight():
    engine = CombatEngine(); engine.start_run("Synthetic test only")
    feed = Feed(engine)
    feed.send("SelfIdentifiedEvent", ActorId=1, Name="Fixture A", ServerId=4, Class=1)
    feed.send("PlayerSeenEvent", ActorId=2, Name="Fixture B", ServerId=4, Class=2)
    feed.send("PlayerSeenEvent", ActorId=3, Name="Outsider fixture", ServerId=4)
    feed.send("NpcSeenEvent", ActorId=50)
    feed.send("NpcSeenEvent", ActorId=51)
    feed.send("PartyRosterEvent", Members=[dict(Name="Fixture A", ServerId=4), dict(Name="Fixture B", ServerId=4)])
    engine.select_boss(50)
    return engine, feed


def hit(feed, actor=1, target=50, damage=100, time=1000):
    return feed.send("DamageEvent", time=time, SourceId=actor, TargetId=target, Damage=damage, SkillCode=11020000)


def test_damage_ranking_common_duration_share_and_outsider_exclusion(fight):
    engine, feed = fight
    hit(feed, damage=100, time=1000)
    hit(feed, actor=2, damage=300, time=3000)
    hit(feed, actor=3, damage=10000, time=3000)
    rows = engine.snapshot()["rows"]
    assert [r["name"] for r in rows] == ["Fixture B", "Fixture A"]
    assert [r["damage"] for r in rows] == [300, 100]
    assert rows[0]["dps"] == 150 and rows[1]["dps"] == 50
    assert rows[0]["share"] == .75
    assert engine.snapshot()["total"] == 400


def test_duplicate_envelope_is_removed_but_equal_hits_are_kept(fight):
    engine, feed = fight
    message = hit(feed)
    engine.process(message)
    hit(feed)
    assert engine.snapshot()["total"] == 200
    assert engine.snapshot()["rows"][0]["dps"] is None


def test_summon_late_owner_reclassifies_without_changing_total(fight):
    engine, feed = fight
    feed.send("SummonSeenEvent", ActorId=7, OwnerId=0)
    hit(feed, actor=7, damage=500)
    assert engine.snapshot()["unattributed"] == 500
    feed.send("SummonSeenEvent", time=1100, ActorId=7, OwnerId=2)
    result = engine.snapshot()
    assert result["unattributed"] == 0 and result["total"] == 500
    assert result["rows"][0]["name"] == "Fixture B"


def test_cycles_and_ambiguous_owner_names_remain_unattributed(fight):
    engine, feed = fight
    feed.send("SummonSeenEvent", ActorId=7, OwnerId=8)
    feed.send("SummonSeenEvent", ActorId=8, OwnerId=7)
    hit(feed, actor=7)
    assert engine.snapshot()["unattributed"] == 100
    feed.send("PlayerSeenEvent", ActorId=9, Name="Fixture B", ServerId=99)
    feed.send("SummonSeenEvent", ActorId=10, OwnerId=0, OwnerName="Fixture B")
    hit(feed, actor=10)
    assert engine.snapshot()["unattributed"] == 200


def test_selected_target_and_instance_include_different_scopes(fight):
    engine, feed = fight
    hit(feed, damage=100)
    hit(feed, target=51, damage=400)
    assert engine.snapshot(boss_only=True)["total"] == 100
    assert engine.snapshot("instance", boss_only=True)["total"] == 500


def test_damage_to_player_and_from_npc_never_ranked(fight):
    engine, feed = fight
    hit(feed, target=2)
    hit(feed, actor=50, target=51)
    assert engine.snapshot()["total"] == 0
    hit(feed, actor=77, target=51)
    feed.send("NpcSeenEvent", time=1100, ActorId=77)
    assert engine.snapshot()["total"] == 0


def test_defeat_final_hit_reconciliation_and_manual_new_attempt(fight):
    engine, feed = fight
    hit(feed)
    feed.send("DeathEvent", time=2000, ActorId=50)
    hit(feed, damage=50, time=2100)
    assert len(engine.encounters) == 1
    assert engine.snapshot()["total"] == 150
    assert engine.snapshot()["result"] == "target_defeated"
    hit(feed, time=4000)
    engine.finish_encounter("wipe", 5000)
    assert len(engine.encounters) == 2
    assert engine.snapshot("instance")["total"] == 250
    assert engine.snapshot("instance")["duration_ms"] == 2000


def test_id_reuse_does_not_relabel_old_damage(fight):
    engine, feed = fight
    hit(feed, actor=2)
    feed.send("PlayerSeenEvent", time=1100, ActorId=2, Name="New entity fixture", ServerId=4)
    assert engine.current is None
    assert engine.snapshot()["rows"][0]["name"] == "Fixture B"
    assert "entity_reused" in engine.snapshot()["issues"]


def test_unknown_target_lacuna_and_capture_reconnect_are_partial(fight):
    engine, feed = fight
    hit(feed, target=999)
    feed.sequence += 1
    hit(feed)
    assert {"sa_unvalidated", "unknown_target", "event_gap"} <= set(engine.snapshot()["issues"])
    engine.process(dict(type="event", session="new-fixture-session", sequence=1, time_ms=0,
        kind="NpcSeenEvent", payload=dict(ActorId=50)))
    assert engine.current is None and engine.roster == set()
    assert "reconnected" in engine.snapshot()["issues"]


def test_instance_map_change_stops_collection(fight):
    engine, feed = fight
    feed.send("ZoneChangedEvent", MapId=101)
    hit(feed)
    feed.send("ZoneChangedEvent", time=2000, MapId=102)
    hit(feed, time=3000)
    assert not engine.active
    assert engine.snapshot("instance")["total"] == 100


@pytest.mark.parametrize("damage", [-1, 0, True, 1.5, 10**13])
def test_invalid_damage_is_not_accepted(fight, damage):
    engine, feed = fight
    with pytest.raises(ValueError):
        hit(feed, damage=damage)
    assert engine.snapshot()["total"] == 0


def test_hit_limit_is_signaled_and_existing_total_preserved(fight):
    engine, feed = fight
    engine.MAX_HITS = 1
    hit(feed); hit(feed)
    assert engine.snapshot()["total"] == 100
    assert "event_limit" in engine.snapshot()["issues"]


def test_ties_and_unattributed_denominator(fight):
    engine, feed = fight
    hit(feed); hit(feed, actor=2); hit(feed, actor=99)
    result = engine.snapshot()
    assert [r["rank"] for r in result["rows"]] == [1, 1]
    assert result["rows"][0]["share"] == pytest.approx(1 / 3)


def test_history_persistence_and_delete_are_local(fight, tmp_path):
    engine, feed = fight
    hit(feed); engine.stop_run()
    history = CombatHistory(tmp_path / "combat.sqlite")
    history.save(engine.snapshot("instance")); history.close()
    history = CombatHistory(tmp_path / "combat.sqlite")
    assert history.list()[0][1]["total"] == 100
    history.delete(engine.run_id)
    assert history.list() == []
    history.close()


def test_combat_ui_translates_without_capture_and_keeps_game_names(qapp, tmp_path):
    from app.services.context import AppContext
    from app.modules.combat.service import CombatService
    from app.ui.combat_page import CombatPage
    from app.core.i18n import set_language
    context = AppContext(tmp_path)
    service = CombatService(context)
    page = CombatPage(context, service)
    assert service.process is None and not page.panel.isVisible()
    service.engine.start_run()
    feed = Feed(service.engine)
    feed.send("SelfIdentifiedEvent", ActorId=1, Name="Sobre", ServerId=1)
    hit(feed)
    service.changed.emit()
    set_language("en_US"); service.changed.emit(); qapp.processEvents()
    assert page.start_button.text() == "Measure instance"
    assert page.table.item(0, 1).text() == "Sobre"
    assert page.table.horizontalHeaderItem(2).text() == "Damage"
    page.copy_result()
    assert "partial data" in qapp.clipboard().text()
    assert "Sobre" in qapp.clipboard().text()
    page.shutdown(); service.shutdown(); page.close()
    set_language("pt_BR")


def test_service_requires_handshake_and_signals_capture_loss(qapp, tmp_path):
    from app.services.context import AppContext
    from app.modules.combat.service import CombatService
    service = CombatService(AppContext(tmp_path))
    message = dict(type="event", session="fixture", sequence=1, time_ms=0,
                   kind="NpcSeenEvent", payload=dict(ActorId=50))
    with pytest.raises(ValueError):
        service.accept(message)
    service.accept(dict(type="hello", protocol=1, saValidated=False))
    service.accept(message)
    service.accept(dict(type="health", dropped=1, gaps=0, rejected=0))
    assert "capture_gap" in service.engine.issues
    assert service.process is None
    service.shutdown()


@pytest.mark.parametrize("reason,expected", [
    ("multiple_clients", "Mais de um cliente conectado; mantenha apenas um para medir"),
    ("adapter_not_found", "Conexão encontrada, mas o adaptador de captura está indisponível"),
    ("npcap_load_failed", "Não foi possível carregar o Npcap; verifique a instalação"),
    ("capture_failed", "Falha na captura pelo Npcap; reinicie a medição"),
    ("unknown", "Não foi possível ler a conexão do jogo"),
])
def test_service_reports_safe_capture_failure(qapp, tmp_path, reason, expected):
    from app.services.context import AppContext
    from app.modules.combat.service import CombatService
    service = CombatService(AppContext(tmp_path))
    service.accept(dict(type="status", code="Error", reason=reason, detail="private raw diagnostic"))
    assert service.status == expected
    assert "capture_error" in service.engine.issues
    service.shutdown()


def test_bad_history_does_not_block_combat_ui(qapp, tmp_path):
    from app.services.context import AppContext
    from app.modules.combat.service import CombatService
    from app.ui.combat_page import CombatPage
    bad = tmp_path / "combat.sqlite"
    original = b"deliberately-invalid-test-database"
    bad.write_bytes(original)
    context = AppContext(tmp_path)
    service = CombatService(context)
    page = CombatPage(context, service)
    assert service.history is None
    assert bad.read_bytes() == original
    assert context.messages
    page.shutdown(); service.shutdown(); page.close()


def test_checkpoint_after_interrupted_capture_is_not_presented_as_live(fight, tmp_path):
    engine, feed = fight
    hit(feed)
    history = CombatHistory(tmp_path / "combat.sqlite")
    summary = engine.snapshot("instance")
    summary["attempts"] = [engine.snapshot()]
    history.save(summary)
    saved = history.list()[0][1]
    assert not saved["active"] and saved["attempts"][0]["result"] == "interrupted"
    assert "unfinished_capture" in saved["issues"]
    history.close()


def test_class_icons_follow_verified_identity_and_survive_unknown_update(qapp, fight):
    from app.ui.combat_page import damage_table, fill_table
    from app.ui.combat_classes import class_icon, class_label
    from app.core.i18n import set_language
    engine, feed = fight
    hit(feed)
    feed.send("SelfIdentifiedEvent", ActorId=1, Name="Fixture A", ServerId=4, Class=0)
    assert engine.snapshot()["rows"][0]["job"] == 1
    table = damage_table()
    fill_table(table, engine.snapshot())
    assert not table.item(0, 1).icon().isNull()
    assert table.item(0, 1).toolTip() == "Gladiador"
    for job in range(10):
        assert not class_icon(job).pixmap(20, 20).isNull()
    set_language("en_US")
    fill_table(table, engine.snapshot())
    assert table.item(0, 1).toolTip() == "Gladiator"
    assert class_label(999) == "Class not identified"
    assert class_label(True) == "Class not identified"
    set_language("pt_BR")
    table.close()


def test_roster_class_does_not_modify_closed_history_or_other_server(fight):
    engine, feed = fight
    hit(feed)
    engine.finish_encounter()
    feed.send("PartyRosterEvent", Members=[dict(Name="Fixture A", ServerId=4, Class=7),
                                            dict(Name="Fixture B", ServerId=99, Class=8)])
    assert engine.snapshot()["rows"][0]["job"] == 1
    assert engine.entities[1].job == 7 and engine.entities[2].job == 2
    hit(feed, time=3000)
    assert engine.snapshot()["rows"][0]["job"] == 7


def test_teammate_without_wire_server_joins_unique_roster_name(fight):
    engine, feed = fight
    feed.send("PlayerSeenEvent", ActorId=2, Name="Fixture B", ServerId=0, Class=2)
    hit(feed); hit(feed, actor=2, damage=300, time=3000)
    rows = engine.snapshot()["rows"]
    assert [row["name"] for row in rows] == ["Fixture B", "Fixture A"]
    assert [row["dps"] for row in rows] == [150, 50]
    assert engine.snapshot()["unattributed"] == 0


def test_ambiguous_missing_server_is_unattributed_and_known_outsider_excluded(fight):
    engine, feed = fight
    feed.send("PartyRosterEvent", Members=[dict(Name="Fixture A", ServerId=4),
                                          dict(Name="Fixture B", ServerId=4),
                                          dict(Name="Fixture B", ServerId=99)])
    feed.send("PlayerSeenEvent", ActorId=2, Name="Fixture B", ServerId=0)
    hit(feed, actor=2, damage=300)
    assert engine.snapshot()["unattributed"] == 300
    feed.send("PlayerSeenEvent", ActorId=2, Name="Fixture B", ServerId=98)
    assert engine.snapshot()["total"] == 0


def test_partial_roster_does_not_silently_hide_unread_members(fight):
    engine, feed = fight
    feed.send("PartyRosterEvent", Members=[dict(Name="Fixture A", ServerId=4)], Complete=False)
    hit(feed); hit(feed, actor=2, damage=300)
    result = engine.snapshot()
    assert result["total"] == 400 and result["unattributed"] == 300
    assert "missing_roster" in result["issues"]


def test_party_membership_survives_map_change_with_fresh_actor_ids(fight):
    engine, feed = fight
    feed.send("ZoneChangedEvent", MapId=600001)
    hit(feed)
    feed.send("ZoneChangedEvent", time=2000, MapId=600002)
    assert engine.roster == {("Fixture A", 4), ("Fixture B", 4)}
    assert not engine.entities
    engine.start_run()
    feed.send("SelfIdentifiedEvent", ActorId=10, Name="Fixture A", ServerId=4)
    feed.send("PlayerSeenEvent", ActorId=11, Name="Fixture B", ServerId=0, Class=2)
    hit(feed, actor=11, time=4000)
    assert engine.snapshot()["rows"][0]["name"] == "Fixture B"


def auto_service(tmp_path):
    from app.services.context import AppContext
    from app.modules.combat.service import CombatService
    service = CombatService(AppContext(tmp_path))
    service.engine.start_run("Old fixture run")
    service.auto_instances = True
    service.accept(dict(type="hello", protocol=1, saValidated=False))
    class ServiceFeed(Feed):
        def send(self, kind, time=0, **payload):
            self.sequence += 1
            message = dict(type="event", session="auto-fixture", sequence=self.sequence,
                           time_ms=time, kind=kind, payload=payload)
            service.accept(message)
            return message
    return service, ServiceFeed(service.engine)


def test_new_dungeon_resets_and_archives_previous_run_without_new_capture(qapp, tmp_path):
    service, feed = auto_service(tmp_path)
    feed.send("ZoneChangedEvent", MapId=600001, IsDungeon=True)
    feed.send("SelfIdentifiedEvent", ActorId=1, Name="Fixture", ServerId=1, Class=7)
    hit(feed)
    previous = service.engine.run_id
    feed.send("ZoneChangedEvent", time=2000, MapId=600002, IsDungeon=True)
    assert service.engine.active and service.engine.run_id != previous
    assert service.engine.snapshot()["total"] == 0 and service.auto_instances
    assert service.history.list()[0][1]["total"] == 100
    feed.send("ZoneChangedEvent", time=3000, MapId=240000, IsDungeon=False)
    assert not service.engine.active and service.auto_instances
    feed.send("ZoneChangedEvent", time=4000, MapId=600001, IsDungeon=True)
    assert service.engine.active
    service.shutdown()


def test_instance_timer_ignores_phase_change_reload_and_old_packets(qapp, tmp_path):
    service, feed = auto_service(tmp_path)
    start = 1_800_000_000_000
    def timer(kind, stamp):
        return feed.send("InstanceTimerEvent", MapId=600001, Kind=kind,
                         StartMs=stamp, EndMs=stamp+3_600_000)
    timer(1, start)
    first = service.engine.run_id
    timer(2, start+30_000)
    feed.send("ZoneChangedEvent", MapId=600001, IsDungeon=True, IsTeleport=True)
    timer(2, start+30_000)
    assert service.engine.run_id == first
    message = timer(1, start+4_000_000)
    second = service.engine.run_id
    assert second != first and service.engine.active
    service.accept(message)  # Duplicate IPC event must not reset again.
    timer(2, start+30_000)   # Old timer from the previous instance.
    timer(2, start+4_030_000)
    assert service.engine.run_id == second
    service.stop()
    timer(1, start+8_000_000)
    assert not service.engine.active and service.engine.run_id == second
    service.shutdown()
