# SPDX-License-Identifier: GPL-3.0-only
from app.modules.combat.engine import CombatEngine
from app.tests.test_combat import Feed


def battle():
    engine=CombatEngine();engine.start_run()
    feed=Feed(engine)
    feed.send('SelfIdentifiedEvent',ActorId=1,Name='SM A',ServerId=4,Class=6)
    feed.send('NpcSeenEvent',ActorId=50)
    return engine,feed


def damage(feed,actor,amount=100,skill=16010000,scalar=17001,time=4000):
    feed.send('DamageEvent',time=time,SourceId=actor,TargetId=50,Damage=amount,SkillCode=skill,PowerScalar=scalar)


def rotation(feed,actor=1,scalar=17001):
    for i in range(3):damage(feed,actor,skill=16010000+i*10000,scalar=scalar)


def test_spirit_damage_merges_retroactively_with_owner_and_preserves_total_dps_share():
    engine,feed=battle()
    feed.send('SummonSeenEvent',time=1000,ActorId=7,OwnerId=0)
    damage(feed,7,500,time=2000)
    assert engine.snapshot()['unattributed']==500
    rotation(feed)
    result=engine.snapshot()
    assert result['unattributed']==0 and result['total']==800
    assert len(result['rows'])==1 and result['rows'][0]['damage']==800
    assert result['rows'][0]['dps']==400 and result['rows'][0]['share']==1
    assert 'inferred_summon_owner' in result['issues']
    assert engine.snapshot()['total']==800  # Repeated refresh never duplicates damage.


def test_two_spiritmasters_with_same_scalar_are_not_guessed_even_before_rotation():
    engine,feed=battle()
    feed.send('PlayerSeenEvent',ActorId=2,Name='SM B',ServerId=4,Class=6)
    feed.send('PartyRosterEvent',Members=[dict(Name='SM A',ServerId=4),dict(Name='SM B',ServerId=4)])
    feed.send('SummonSeenEvent',ActorId=7,OwnerId=0)
    rotation(feed);damage(feed,2);damage(feed,7,500)
    assert engine.snapshot()['unattributed']==500


def test_matching_other_player_blocks_scalar_link_even_on_a_different_target():
    engine,feed=battle()
    feed.send('PlayerSeenEvent',ActorId=2,Name='SM B',ServerId=4,Class=6)
    feed.send('PartyRosterEvent',Members=[dict(Name='SM A',ServerId=4),dict(Name='SM B',ServerId=4)])
    feed.send('SummonSeenEvent',ActorId=7,OwnerId=0)
    rotation(feed)
    feed.send('DamageEvent',time=4000,SourceId=2,TargetId=51,Damage=100,SkillCode=16010000,PowerScalar=17001)
    damage(feed,7,500)
    assert engine.snapshot()['unattributed']==500


def test_distinct_scalars_link_each_spirit_to_the_correct_spiritmaster():
    engine,feed=battle()
    feed.send('PlayerSeenEvent',ActorId=2,Name='SM B',ServerId=4,Class=6)
    feed.send('PartyRosterEvent',Members=[dict(Name='SM A',ServerId=4),dict(Name='SM B',ServerId=4)])
    feed.send('SummonSeenEvent',ActorId=7,OwnerId=0)
    feed.send('SummonSeenEvent',ActorId=8,OwnerId=0)
    rotation(feed,1,17001);rotation(feed,2,18543)
    damage(feed,7,500,scalar=17001);damage(feed,8,900,scalar=18543)
    assert {r['name']:r['damage'] for r in engine.snapshot()['rows']}=={'SM A':800,'SM B':1200}
    assert engine.snapshot()['unattributed']==0


def test_unknown_actor_npc_other_class_and_base_scalar_are_not_claimed_as_spirits():
    engine,feed=battle();rotation(feed)
    damage(feed,77,500)
    feed.send('SummonSeenEvent',ActorId=7,OwnerId=0);damage(feed,7,500,scalar=10000)
    assert engine.snapshot()['unattributed']==1000
    feed.send('SelfIdentifiedEvent',ActorId=1,Name='SM A',ServerId=4,Class=5)
    damage(feed,7,500)
    assert engine.snapshot()['unattributed']==1500


def test_known_summon_owner_survives_incomplete_repeat_announcement():
    engine,feed=battle()
    feed.send('SummonSeenEvent',ActorId=7,OwnerId=1)
    feed.send('SummonSeenEvent',ActorId=7,OwnerId=0)
    damage(feed,7,500)
    assert engine.snapshot()['unattributed']==0
    assert engine.snapshot()['rows'][0]['name']=='SM A'


def test_cast_variant_links_without_scalar_and_ambiguity_is_rejected():
    engine,feed=battle()
    feed.send('CastEvent',time=1000,ActorId=1,TargetId=50,SkillCode=16280140)
    feed.send('SummonSeenEvent',time=1500,ActorId=7,OwnerId=0)
    damage(feed,7,500,scalar=0,time=1600)
    feed.send('CastEvent',time=1700,ActorId=7,TargetId=7,SkillCode=16280141)
    assert engine.snapshot()['rows'][0]['damage']==500
    feed.send('PlayerSeenEvent',ActorId=2,Name='SM B',ServerId=4,Class=6)
    feed.send('CastEvent',time=1750,ActorId=2,TargetId=50,SkillCode=16280140)
    assert engine.snapshot()['unattributed']==500


def test_scalar_fallback_is_not_used_in_pvp():
    engine,feed=battle();engine.pvp=True
    feed.send('PlayerSeenEvent',ActorId=50,Name='Opponent',ServerId=5,Class=2)
    feed.send('SummonSeenEvent',ActorId=7,OwnerId=0)
    rotation(feed);damage(feed,7,500)
    assert engine.snapshot()['total']==300


def test_new_zone_clears_cast_links_and_does_not_rewrite_finished_results():
    engine,feed=battle()
    feed.send('ZoneChangedEvent',MapId=600001)
    feed.send('CastEvent',time=1000,ActorId=1,TargetId=50,SkillCode=16280140)
    feed.send('ZoneChangedEvent',time=1500,MapId=600002)
    assert engine.casts==[]


def test_invalid_summon_metadata_is_rejected():
    import pytest
    engine,feed=battle()
    with pytest.raises(ValueError):feed.send('SummonSeenEvent',ActorId=7,OwnerId=True)
    with pytest.raises(ValueError):damage(feed,1,scalar=-1)


def test_respawn_does_not_keep_the_previous_spirit_owner():
    engine,feed=battle()
    feed.send('SummonSeenEvent',ActorId=7,OwnerId=1)
    damage(feed,7,500)
    feed.send('DeathEvent',time=4100,ActorId=7)
    feed.send('SummonSeenEvent',time=5000,ActorId=7,OwnerId=0)
    damage(feed,7,600,scalar=0,time=5100)
    assert engine.snapshot()['unattributed']==600
    assert engine.snapshot('instance')['rows'][0]['damage']==500
    assert engine.snapshot('instance')['total']==1100


def test_official_class_icons_keep_original_bytes_and_unknown_class_is_neutral(qapp):
    import hashlib,json
    from pathlib import Path
    from app.infrastructure.storage import PACKAGE
    from app.ui.combat_classes import class_icon,CLASSES
    report=json.loads((PACKAGE.parent/'data-sources/class-icons.json').read_text(encoding='utf-8'))
    assets={asset['class_name']:asset for asset in report['assets']}
    assert len(assets)==8
    for job in range(1,9):
        asset=assets[CLASSES[job][0]]
        path=PACKAGE/'assets/icons/classes'/asset['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==asset['sha256']
        assert not class_icon(job).pixmap(20,20).isNull()
    assert class_icon(True).cacheKey()==class_icon(0).cacheKey()
    assert class_icon(9).cacheKey()==class_icon(0).cacheKey()
