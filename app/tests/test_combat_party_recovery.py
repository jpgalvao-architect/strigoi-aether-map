# SPDX-License-Identifier: GPL-3.0-only
from app.modules.combat.engine import CombatEngine
from app.tests.test_combat import Feed


def test_full_late_roster_restores_two_missing_players_without_changing_damage():
    engine=CombatEngine();engine.start_run()
    feed=Feed(engine)
    names=['Alpha','Beta','Gamma','Delta','Epsilon']
    for actor,name in enumerate(names,1):
        feed.send('PlayerSeenEvent',ActorId=actor,Name=name,ServerId=0,Class=actor)
    feed.send('PartyRosterEvent',Members=[dict(Name=name,ServerId=2401) for name in names[:3]],Complete=False)
    for actor in range(1,6):
        feed.send('DamageEvent',time=1000+actor*100,SourceId=actor,TargetId=50,Damage=actor*100,SkillCode=11010000)
    before=engine.snapshot()
    assert len(before['rows'])==3 and before['unattributed']==900 and before['total']==1500
    feed.send('PartyRosterEvent',Members=[dict(Name=name,ServerId=2401,Class=i) for i,name in enumerate(names,1)],Complete=True)
    after=engine.snapshot()
    assert len(after['rows'])==5 and after['unattributed']==0 and after['total']==before['total']
    assert {row['name']:row['damage'] for row in after['rows']}==dict(zip(names,[100,200,300,400,500]))
    assert sum(row['share'] for row in after['rows'])==1
    assert after['rows'][0]['dps']==1250


def test_partial_recovery_does_not_assign_unknown_actor_to_the_unread_member():
    engine=CombatEngine();engine.start_run();feed=Feed(engine)
    feed.send('PartyRosterEvent',Members=[dict(Name='Alpha',ServerId=2401)],Complete=False)
    feed.send('DamageEvent',time=1000,SourceId=99,TargetId=50,Damage=500,SkillCode=11010000)
    assert engine.snapshot()['rows']==[] and engine.snapshot()['unattributed']==500
