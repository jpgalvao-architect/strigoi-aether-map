# SPDX-License-Identifier: GPL-3.0-only
from types import SimpleNamespace
import pytest
from app.modules.pets.screen import PetScreenReading,ReadingConsensus,parse_detail
from app.modules.overlay.menu_monitor import MenuConsensus,pet_menu,classify_lines
from app.modules.pets.service import PetService
from app.services.context import AppContext
from app.tests.test_pet_sync import Feed,identity,event,collection


PETS=[SimpleNamespace(id=1217,name='Congealed Drana'),SimpleNamespace(id=1218,name='Faded Drana')]


def row(text,x,y,height=22):return dict(text=text,x=x,y=y,height=height)


def detail(value='Lv. 2 (63/75)'):
    return [row('Congealed Drana',80,132,40),row('Lv.8',535,153,15),
            row('Pet Insight',32,215),row(value,345,215)]


def test_only_insight_row_counts_and_exact_name_is_required():
    assert parse_detail(detail(),PETS)==PetScreenReading(1217,2,63,75)
    assert parse_detail([r for r in detail() if r['text']!='Pet Insight'],PETS) is None
    assert parse_detail([row('Unknown pet',80,132,40),*detail()[1:]],PETS) is None
    assert parse_detail([*detail(),row('Faded Drana',80,155,35)],PETS) is None
    assert parse_detail([*detail(),row('Lv. 2 (62/75)',345,215)],PETS) is None


@pytest.mark.parametrize('value',['Lv. 8','Lv. 2 (76/75)','Lv. 2 (0/0)','Lv. 11 (1/75)',
    'Insight 2 · 60 almas','Lv. 2 (63/75) other text'])
def test_invalid_or_overlay_text_never_becomes_an_absolute_reading(value):
    assert parse_detail(detail(value),PETS) is None


def test_consensus_requires_same_pet_count_and_scope_twice():
    consensus=ReadingConsensus();first=PetScreenReading(1217,2,63,75)
    assert consensus.observe('character-a',first) is None
    assert consensus.observe('character-a',first)==first
    assert consensus.observe('character-b',first) is None
    assert consensus.observe(None,None) is None
    assert consensus.observe('character-b',first) is None


def test_pet_menu_needs_title_and_tabs_and_misses_cannot_flicker():
    lines=[row('Pets',30,25,30),row('Genus Insight',1000,80)]
    assert pet_menu(lines,1920,1080) and classify_lines(lines,1920,1080)=='menu'
    assert not pet_menu(lines[:1],1920,1080)
    assert not pet_menu([row('Pets',500,350,30),lines[1]],1920,1080)
    assert classify_lines([row('Inventory',900,300,26)],1920,1080)=='play'
    consensus=MenuConsensus()
    assert consensus.observe('menu')=='play'
    assert consensus.observe('menu')=='menu'
    assert consensus.observe(None)=='menu'
    for _ in range(4):
        assert consensus.observe('play')=='menu'
        assert consensus.observe('menu')=='menu'
    assert consensus.observe('play')=='menu'
    assert consensus.observe('play')=='menu'
    assert consensus.observe('play')=='play'


@pytest.fixture
def service(qapp,tmp_path):
    service=PetService(AppContext(tmp_path),Feed());service.accept(identity())
    yield service
    service.shutdown()


def test_manual_sixty_is_replaced_by_screen_baseline_and_pickups_continue_without_login_list(service):
    service.record(1217,2,60);service.edit(1217,favorite=True,goal=3)
    read=PetScreenReading(1217,2,62,75)
    assert service.from_screen(service.screen_scope(),read)
    entry=service.store.entry(1217)
    assert entry.favorite and entry.goal==3 and entry.manual.souls==60
    assert not entry.use_manual and entry.progress.souls==62 and entry.progress.level==2
    assert entry.progress.required==75 and not service.collection_ready
    before=service.store.path.read_bytes()
    assert service.from_screen(service.screen_scope(),read)
    assert before==service.store.path.read_bytes()
    gain=event(2,'PetSoulAcquiredEvent',dict(PetId=1217,Amount=1))
    service.accept(gain);service.accept(gain)
    assert service.store.entry(1217).progress.souls==63


def test_old_screen_after_pickup_character_change_disabled_sync_or_gap_is_rejected(service):
    read=PetScreenReading(1217,2,62,75)
    assert service.from_screen(service.screen_scope(),read)
    scope=service.screen_scope()
    service.accept(event(2,'PetSoulAcquiredEvent',dict(PetId=1217,Amount=1)))
    assert not service.from_screen(scope,read)
    assert service.store.entry(1217).progress.souls==63
    service.accept({'type':'feed_quality','reason':'capture_gap'})
    service.accept(event(3,'PetSoulAcquiredEvent',dict(PetId=1217,Amount=1)))
    assert service.store.entry(1217).progress.souls==63
    assert service.progress_status(1217)=='Registro salvo'
    assert service.from_screen(service.screen_scope(),PetScreenReading(1217,2,64,75))
    old=service.screen_scope();service.accept(identity(4,name='Other character',stamp=5000))
    assert not service.from_screen(old,read)
    service.context.prefs.pets.auto_collection=False
    assert service.screen_scope() is None and not service.from_screen(None,read)


def test_collection_waits_for_delayed_identity_instead_of_discarding_at_three_seconds(service):
    old=service.profile_key
    service.accept(collection(2,stamp=10000));service.flush_pending()
    assert service.pending and not service.collection_ready and service.screen_scope() is None
    service.accept(identity(3,name='Next character',stamp=17000));service.flush_pending()
    assert service.profile_key!=old and service.collection_ready
    assert service.store.entry(1127).progress.souls==9


def test_screen_reply_after_alt_tab_generation_is_not_applied(qapp,tmp_path):
    from app.ui.main_window import MainWindow
    from app.ui.overlay_visibility import OverlayVisibility
    main=MainWindow(AppContext(tmp_path));gate=OverlayVisibility(main,SimpleNamespace())
    main.pets.accept(identity());gate.active=True;gate.game='fixture';gate.generation=2
    read=PetScreenReading(1217,2,63,75);scope=main.pets.screen_scope()
    try:
        gate.on_pet(('fixture',1),scope,read)
        assert main.pets.store.entry(1217).progress is None
        gate.on_pet(('fixture',2),scope,read)
        assert main.pets.store.entry(1217).progress.souls==63
    finally:gate.shutdown();main.close()


def test_failed_identity_or_screen_save_cannot_reuse_an_old_baseline(service,monkeypatch):
    read=PetScreenReading(1217,2,63,75)
    assert service.from_screen(service.screen_scope(),read)
    before=service.store.path.read_bytes()
    def cannot_save(*args,**kwargs):raise OSError('Synthetic failure')
    with monkeypatch.context() as patch:
        patch.setattr(service.store,'accept_snapshot',cannot_save)
        assert not service.from_screen(service.screen_scope(),PetScreenReading(1217,2,64,75))
    assert not service.fresh_pets and not service.collection_ready
    assert service.store.path.read_bytes()==before
    with monkeypatch.context() as patch:
        patch.setattr(service.store,'observed_profile',cannot_save)
        service.from_feed(identity(2,name='Next character'))
    assert service.screen_scope() is None and service.profile_key is None
    assert service.store.path.read_bytes()==before
