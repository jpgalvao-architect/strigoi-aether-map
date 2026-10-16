# SPDX-License-Identifier: GPL-3.0-only
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Signal

from app.modules.pets.service import PetService
from app.services.context import AppContext
from app.services.game_feed import GameFeedService


class Feed(QObject):
    message = Signal(dict)
    ended = Signal()

    def __init__(self):
        super().__init__()
        self.consumers = {'pets'}

    def acquire(self, name):
        self.consumers.add(name)

    def release(self, name):
        self.consumers.discard(name)


@pytest.fixture
def sync(qapp, tmp_path):
    context = AppContext(tmp_path)
    feed = Feed()
    service = PetService(context, feed)
    yield service
    service.shutdown()


def event(sequence, kind, payload, stamp=1000, session='synthetic'):
    return {'type':'event','session':session,'sequence':sequence,'time_ms':stamp,
            'kind':kind,'payload':payload}


def identity(sequence=1, name='Fixture A', stamp=1000):
    return event(sequence,'SelfIdentifiedEvent',{'Name':name,'ServerId':2401},stamp)


def collection(sequence=2, level=2, souls=9, stamp=1100):
    return event(sequence,'PetCollectionEvent',{'Levels':[{'PetId':1127,'Level':level}],
        'Souls':[{'PetId':1127,'Souls':souls}]},stamp)


def loaded(sync):
    sync.accept(identity()); sync.accept(collection()); sync.flush_pending()
    assert sync.collection_ready


def test_collection_before_identity_matches_independent_insight_fixture(sync):
    sync.accept(collection(1, stamp=900))
    assert sync.store.entry(1127).progress is None
    sync.accept(identity(2)); sync.flush_pending()
    assert sync.store.profile.character == 'Fixture A'
    assert sync.store.entry(1127).observed.level == 2
    assert sync.store.entry(1127).observed.souls == 9
    assert sync.store.entry(1127).observed.level != 8  # Genus level is a different field.


def test_pickup_is_increment_duplicate_ignored_and_manual_override_preserved(sync):
    loaded(sync)
    sync.store.record(1127,1,3)
    gain=event(3,'PetSoulAcquiredEvent',{'PetId':1127,'Amount':1})
    sync.accept(gain); sync.accept(gain)
    assert sync.store.entry(1127).observed.souls == 10
    assert sync.store.entry(1127).progress.souls == 3
    sync.store.edit(1127,use_manual=False)
    assert sync.store.entry(1127).progress.souls == 10


def test_reconnect_and_quality_loss_never_add_to_old_baseline(sync):
    loaded(sync)
    sync.accept({'type':'feed_quality','reason':'capture_gap'})
    sync.accept(event(3,'PetSoulAcquiredEvent',{'PetId':1127,'Amount':1}))
    assert sync.store.entry(1127).observed.souls == 9
    sync.disconnected()
    sync.accept(identity())
    sync.accept(event(2,'PetSoulAcquiredEvent',{'PetId':1127,'Amount':1}))
    assert sync.store.entry(1127).observed.souls == 9
    sync.accept(collection(3,souls=7)); sync.flush_pending()
    assert sync.store.entry(1127).observed.souls == 7


def test_character_switch_snapshot_cannot_be_filed_under_previous_character(sync):
    loaded(sync)
    old_key=sync.profile_key
    sync.accept(collection(3,souls=4,stamp=10000))
    assert sync.store.entry(1127).observed.souls == 9
    sync.accept(identity(4,name='Fixture B',stamp=10100)); sync.flush_pending()
    assert sync.store.entry(1127).observed.souls == 4
    assert sync.store.collection.profiles[old_key].entries['1127'].observed.souls == 9
    assert sync.store.profile.character == 'Fixture B'


def test_snapshot_without_current_identity_never_reuses_stale_character(sync):
    loaded(sync)
    sync.accept(collection(3,souls=4,stamp=10000)); sync.flush_pending()
    assert not sync.collection_ready
    assert sync.store.entry(1127).observed.souls == 9


def test_sparse_souls_for_explicit_pet_is_zero_absent_catalogue_pet_stays_unknown(sync):
    sync.accept(identity())
    sync.accept(event(2,'PetCollectionEvent',{'Levels':[{'PetId':1127,'Level':0}], 'Souls':[]}))
    sync.flush_pending()
    assert sync.store.entry(1127).observed.souls == 0
    assert sync.store.entry(1127).state == 'missing'
    assert sync.store.entry(1069).progress is None


def test_new_complete_snapshot_invalidates_absent_old_observation_without_guessing_zero(sync):
    loaded(sync)
    sync.accept(event(3,'PetCollectionEvent',{'Levels':[], 'Souls':[]}));sync.flush_pending()
    assert sync.collection_ready and sync.store.entry(1127).state=='unknown'
    assert sync.store.entry(1127).observed.level is None


def test_threshold_does_not_claim_unobserved_level_or_duplicate_level_reset(sync):
    sync.accept(identity());sync.accept(collection(souls=74));sync.flush_pending()
    sync.accept(event(3,'PetSoulAcquiredEvent',{'PetId':1127,'Amount':1}))
    assert sync.store.entry(1127).observed.level == 2
    assert sync.store.entry(1127).observed.pending
    assert sync.store.entry(1127).observed.souls is None
    sync.accept(event(4,'PetLevelReachedEvent',{'PetId':1127,'Level':3}))
    assert sync.store.entry(1127).observed.souls == 0
    sync.accept(event(5,'PetSoulAcquiredEvent',{'PetId':1127,'Amount':1}))
    sync.accept(event(6,'PetLevelReachedEvent',{'PetId':1127,'Level':3}))
    assert sync.store.entry(1127).observed.souls == 1
    sync.accept(event(7,'PetLevelReachedEvent',{'PetId':1127,'Level':2}))
    assert sync.store.entry(1127).observed.level == 3


@pytest.mark.parametrize('payload',[
    {'Levels':[{'PetId':1127,'Level':True}],'Souls':[]},
    {'Levels':[{'PetId':1127,'Level':2}]*2,'Souls':[]},
    {'Levels':[None],'Souls':[]},
    {'Levels':[]},
])
def test_invalid_snapshot_preserves_disk_and_invalidates_baseline(sync,payload):
    loaded(sync); before=sync.store.path.read_bytes()
    sync.from_feed(event(3,'PetCollectionEvent',payload));sync.flush_pending()
    assert not sync.collection_ready and sync.store.path.read_bytes()==before


def test_shared_helper_reference_count_and_envelope_quality(qapp,monkeypatch):
    feed=GameFeedService()
    starts=[];stops=[];messages=[]
    def start():
        if feed.process is None:
            starts.append(True);feed.process=SimpleNamespace()
    monkeypatch.setattr(feed,'ensure_running',start)
    monkeypatch.setattr(feed,'stop',lambda:stops.append(True))
    feed.message.connect(messages.append)
    try:
        feed.acquire('combat');feed.acquire('pets');feed.acquire('pets');feed.acquire('routine')
        assert len(starts)==1
        feed.release('combat');assert not stops and feed.consumers=={'pets','routine'}
        feed.release('routine');assert not stops and feed.consumers=={'pets'}
        feed.accept({'type':'hello','protocol':1,'saValidated':False})
        assert feed.accept(identity()) and not feed.accept(identity())
        feed.accept(event(3,'PetSoulAcquiredEvent',{'PetId':1127,'Amount':1}))
        assert any(m.get('reason')=='event_gap' for m in messages)
        before=len(messages)
        feed.accept({'type':'health','dropped':1,'gaps':0,'pets_rejected':0})
        assert messages[before]['type']=='feed_quality'
        before=len(messages)
        feed.accept({'type':'health','dropped':1,'gaps':0,'pets_rejected':0})
        assert len(messages)==before+1
        before=len(messages)
        feed.accept({'type':'health','dropped':1,'gaps':0,'pets_rejected':0,'routine_rejected':1})
        assert messages[before]=={'type':'feed_quality','reason':'routine_record_rejected'}
        assert not any(m.get('reason')=='pet_record_rejected' for m in messages[before:])
        with pytest.raises(ValueError):feed.accept(event(4,'PetCollectionEvent',{},session='other'))
        feed.release('pets');assert stops==[True]
    finally:
        feed.shutdown()
