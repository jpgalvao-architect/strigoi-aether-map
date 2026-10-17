# SPDX-License-Identifier: GPL-3.0-only
import pytest
from app.modules.pets.screen import PetScreenReading
from app.tests.test_pet_sync import sync,event,identity,loaded


def gain(number,pet=1172,amount=1):
    return event(number,'PetSoulAcquiredEvent',dict(PetId=pet,Amount=amount))


def test_duduka_pickups_before_identity_show_gains_without_inventing_total(sync):
    sync.edit(1172,favorite=True)
    sync.record(1173,None,13)
    sync.accept(gain(1));sync.accept(gain(1));sync.accept(gain(2,amount=2))
    sync.accept(gain(3,1173))
    assert sync.gain_count(1172)==3 and sync.gain_count(1173)==1
    assert not sync.pending and sync.store.entry(1172).progress is None
    assert sync.store.entry(1173).manual.souls==13
    assert sync.progress_status(1172)=='Aguardando leitura'


def test_screen_baseline_without_identity_updates_in_memory_and_then_tracks_real_total(sync):
    sync.accept(gain(1));before=sync.store.path.read_bytes() if sync.store.path.exists() else None
    read=PetScreenReading(1172,2,62,75)
    assert sync.from_screen(sync.screen_scope(),read)
    old_scope=sync.screen_scope()
    sync.accept(gain(2))
    assert sync.entry(1172).progress.souls==63 and sync.gain_count(1172)==2
    assert not sync.from_screen(old_scope,read)
    assert sync.store.entry(1172).progress is None
    assert (sync.store.path.read_bytes() if sync.store.path.exists() else None)==before
    assert sync.progress_status(1172)=='Leitura desta captura'
    sync.accept(identity(3,name='Next character'))
    assert not sync.capture_progress and not sync.session_gains
    assert sync.entry(1172).progress is None
    assert not sync.from_screen(old_scope,read)


def test_gap_keeps_verified_gains_but_stops_absolute_increment_until_screen_read(sync):
    sync.accept(gain(1));sync.from_screen(sync.screen_scope(),PetScreenReading(1172,2,62,75))
    sync.accept({'type':'feed_quality','reason':'capture_gap'})
    sync.accept(gain(2))
    assert sync.entry(1172).progress.souls==62 and sync.gain_count(1172)==2
    assert sync.progress_status(1172)=='Aguardando leitura'
    sync.from_screen(sync.screen_scope(),PetScreenReading(1172,2,63,75))
    sync.accept(gain(3))
    assert sync.entry(1172).progress.souls==64
    sync.disconnected()
    assert sync.entry(1172).progress is None and sync.gain_count(1172)==0


def test_bound_gains_without_baseline_and_profile_changes_are_separate(sync):
    sync.accept(identity());sync.accept(gain(2));sync.accept(gain(3))
    assert sync.gain_count(1172)==2 and sync.store.entry(1172).progress is None
    sync.store.select_profile('local')
    assert sync.gain_count(1172)==0
    sync.store.select_profile(sync.profile_key)
    assert sync.gain_count(1172)==2
    sync.accept(identity(4,name='Another character'))
    assert sync.gain_count(1172)==0


@pytest.mark.parametrize('amount',[True,-1,0,100001])
def test_invalid_gains_never_reach_counter(sync,amount):
    sync.from_feed(gain(1,amount=amount))
    assert not sync.session_gains


def test_known_absolute_total_and_capture_count_do_not_double_add(sync):
    loaded(sync)
    sync.accept(gain(3,1127));sync.accept(gain(4,1127))
    assert sync.store.entry(1127).progress.souls==11 and sync.gain_count(1127)==2


def test_pickup_without_baseline_invalidates_inflight_older_screen(sync):
    sync.accept(gain(1))
    old=sync.screen_scope()
    sync.accept(gain(2))
    assert not sync.from_screen(old,PetScreenReading(1172,2,62,75))
    assert sync.from_screen(sync.screen_scope(),PetScreenReading(1172,2,63,75))
    sync.accept(gain(3))
    assert sync.entry(1172).progress.souls==64
