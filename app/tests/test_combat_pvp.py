# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic PvP arithmetic fixtures, never evidence of SA packet accuracy."""
from app.modules.combat.engine import CombatEngine
from app.tests.test_combat import Feed, hit


def arena():
    engine = CombatEngine()
    engine.start_run(pvp=True)
    feed = Feed(engine)
    feed.send("SelfIdentifiedEvent", ActorId=1, Name="Local fixture", ServerId=4)
    feed.send("PlayerSeenEvent", ActorId=2, Name="Team fixture", ServerId=0)
    feed.send("PlayerSeenEvent", ActorId=3, Name="Opponent fixture", ServerId=9)
    feed.send("PartyRosterEvent", Members=[dict(Name="Local fixture", ServerId=4),
                                          dict(Name="Team fixture", ServerId=4)])
    return engine, feed


def test_pvp_ranks_only_outgoing_team_damage_and_not_received_hits():
    engine, feed = arena()
    hit(feed, actor=3, target=1, damage=9000, time=1000)
    hit(feed, actor=3, target=2, damage=8000, time=1100)
    hit(feed, actor=1, target=3, damage=100, time=2000)
    hit(feed, actor=2, target=3, damage=300, time=3000)
    hit(feed, actor=1, target=2, damage=7000, time=4000)
    result = engine.snapshot()
    assert result["total"] == 400 and result["unattributed"] == 0
    assert [row["damage"] for row in result["rows"]] == [300, 100]
    assert result["pvp"] and "pvp_experimental" in result["issues"]
    assert result["rows"][0]["share"] == .75


def test_pvp_counts_local_player_without_a_party_roster():
    engine, feed = arena()
    feed.send("PartyRosterEvent", Members=[])
    hit(feed, actor=1, target=3, damage=200)
    hit(feed, actor=3, target=1, damage=3000)
    assert engine.snapshot()["total"] == 200
    assert engine.snapshot()["rows"][0]["local"]


def test_1v1_ignores_an_open_world_party_roster():
    engine = CombatEngine()
    engine.start_run(pvp=True, team_pvp=False)
    feed = Feed(engine)
    feed.send("SelfIdentifiedEvent", ActorId=1, Name="Local fixture", ServerId=4)
    feed.send("PlayerSeenEvent", ActorId=2, Name="Former party fixture", ServerId=4)
    feed.send("PartyRosterEvent", Members=[dict(Name="Former party fixture", ServerId=4)])
    hit(feed, actor=2, target=1, damage=5000)
    hit(feed, actor=1, target=2, damage=200)
    assert engine.snapshot()["total"] == 200


def test_pvp_summon_owners_resolve_both_attacker_and_defender():
    engine, feed = arena()
    feed.send("SummonSeenEvent", ActorId=7, OwnerId=2)
    feed.send("SummonSeenEvent", ActorId=8, OwnerId=3)
    hit(feed, actor=7, target=3, damage=200)
    hit(feed, actor=8, target=1, damage=5000)
    hit(feed, actor=1, target=7, damage=5000)
    hit(feed, actor=1, target=8, damage=100)
    assert engine.snapshot()["total"] == 300


def test_pvp_unknown_actors_never_become_enemy_damage_in_team_total():
    engine, feed = arena()
    feed.send("PartyRosterEvent", Members=[], Complete=False)
    hit(feed, actor=77, target=1, damage=5000)
    hit(feed, actor=1, target=88, damage=300)
    assert engine.snapshot()["total"] == 0
    feed.send("PlayerSeenEvent", time=1100, ActorId=88, Name="Late opponent", ServerId=9)
    assert engine.snapshot()["total"] == 300
    assert "unattributed" in engine.snapshot()["issues"]


def test_closed_pvp_encounter_keeps_its_rules_after_mode_changes():
    engine, feed = arena()
    hit(feed, actor=1, target=3, damage=200)
    engine.finish_encounter("finished", 2000)
    engine.pvp = False
    assert engine.snapshot()["total"] == 200 and engine.snapshot()["pvp"]
    engine.stop_run()
    engine.start_run()
    assert not engine.pvp and engine.snapshot()["total"] == 0
    hit(feed, actor=1, target=3, damage=200)
    assert engine.snapshot()["total"] == 0
