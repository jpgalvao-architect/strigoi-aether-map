# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic protocol envelopes; no sample balance is bundled as user data."""
from datetime import UTC,datetime
from types import SimpleNamespace
import pytest
from PySide6.QtCore import QObject,Signal,Qt
from PySide6.QtTest import QTest
from app.core.i18n import set_language
from app.services.context import AppContext
from app.modules.routine.service import RoutineService
from app.modules.routine.store import RoutineStore
from app.ui.main_window import MainWindow
from app.ui.overlay_visibility import OverlayVisibility


class Feed(QObject):
    message=Signal(dict)
    ended=Signal()

    def __init__(self):
        super().__init__();self.consumers={'routine'}

    def acquire(self,name):self.consumers.add(name)
    def release(self,name):self.consumers.discard(name)


def event(n,kind,payload=None,stamp=None,session='fixture'):
    return dict(type='event',session=session,sequence=n,time_ms=stamp if stamp is not None else n*100,
                kind=kind,payload=payload or {})


def identity(n=3,name='Fixture Alt',server=2402,actor=50,stamp=8000):
    return event(n,'SelfIdentifiedEvent',dict(Name=name,ServerId=server,ActorId=actor,Class=5),stamp)


def energy(n=2,basic=840,charged=0,full=True,key=51591,stamp=1100):
    return event(n,'OdyleEnergyEvent',dict(Basic=basic,Charged=charged,EntryKey=key,FullSnapshot=full),stamp)


def initial(service):
    service.accept(event(1,'OdyleListStartedEvent',stamp=1000))
    service.accept(energy());service.accept(identity())
    return service.profile_key


@pytest.fixture
def routine(qapp,tmp_path):
    context=AppContext(tmp_path);service=RoutineService(context,Feed())
    yield service
    service.shutdown()


def test_login_balance_waits_for_identity_seven_seconds_later(routine):
    routine.accept(event(1,'OdyleListStartedEvent',stamp=1000))
    routine.accept(energy())
    assert not routine.store.collection.profiles and not routine.fresh
    routine.accept(identity())
    key=routine.profile_key
    assert routine.store.reading(key,'odyle').value==840
    assert routine.store.reading(key,'odyle_charged').value==0
    assert routine.fresh


def test_consumption_is_an_absolute_reading_duplicate_events_do_not_subtract_again(routine):
    key=initial(routine)
    change=energy(4,basic=800,full=False,stamp=9000)
    routine.accept(change);routine.accept(change)
    assert routine.store.reading(key,'odyle').value==800
    routine.accept(energy(5,basic=0,charged=90,full=False,stamp=9200))
    assert routine.store.reading(key,'odyle').value==0
    assert routine.store.reading(key,'odyle_charged').value==90


def test_new_character_list_never_overwrites_previous_owner_and_late_identity_is_discarded(routine):
    old=initial(routine)
    routine.accept(event(4,'OdyleListStartedEvent',stamp=10000))
    routine.accept(energy(5,basic=400,charged=100,stamp=10100))
    assert routine.profile_key is None
    assert routine.store.reading(old,'odyle').value==840
    routine.accept(identity(6,name='Fixture Main',stamp=18000))
    new=routine.profile_key
    assert new!=old and routine.store.reading(new,'odyle').value==400
    routine.accept(event(7,'OdyleListStartedEvent',stamp=20000))
    routine.accept(energy(8,basic=1,stamp=20100))
    routine.accept(identity(9,name='Too late',stamp=60000))
    assert routine.store.reading(routine.profile_key,'odyle') is None


def test_unknown_or_mismatched_updates_never_attach_to_a_previous_character(routine):
    routine.accept(identity(1))
    key=routine.profile_key
    routine.accept(energy(2,full=False))
    assert routine.store.reading(key,'odyle') is None
    routine.disconnected();old=initial(routine)
    routine.accept(energy(4,basic=1,full=False,key=999,stamp=10000))
    assert routine.store.reading(old,'odyle').value==840
    routine.accept(identity(5,name='Other',stamp=11000))
    new=routine.profile_key
    routine.accept(energy(6,basic=20,full=False,stamp=12000))
    assert routine.store.reading(new,'odyle') is None


def test_session_switch_and_capture_gap_preserve_saved_values_without_claiming_live(routine):
    key=initial(routine)
    routine.accept({'type':'feed_quality','reason':'capture_gap'})
    assert not routine.fresh and routine.profile_status(key)=='Registro salvo'
    routine.accept(energy(4,basic=800,full=False,stamp=10000))
    assert routine.fresh
    routine.accept({'type':'feed_quality','reason':'pet_record_rejected'})
    assert routine.fresh
    routine.disconnected()
    assert routine.profile_key is None and routine.store.reading(key,'odyle').value==800
    assert RoutineStore(routine.context.directory).collection.last_profile==key


@pytest.mark.parametrize('bad',[True,-1,100001,'840',None])
def test_invalid_balances_cannot_mutate_a_valid_record(routine,bad):
    key=initial(routine)
    with pytest.raises(ValueError):routine.accept(energy(4,basic=bad,full=False))
    assert routine.store.reading(key,'odyle').value==840


def test_profiles_are_scoped_by_region_and_server_and_have_no_estimated_cap(tmp_path):
    store=RoutineStore(tmp_path)
    keys=[store.identify(region,server,'Same name') for region,server in [('sa',2401),('sa',2402),('tw',2401)]]
    assert len(set(keys))==3
    assert all(store.reading(key,'odyle') is None for key in keys)
    store.observe(keys[0],840,0)
    assert store.reading(keys[0],'odyle').model_dump()==dict(value=840,
        observed_at=store.reading(keys[0],'odyle').observed_at,source='game-entry-counts-v1')


def test_identity_write_failure_cannot_send_new_character_updates_to_old_owner(routine,monkeypatch):
    old=initial(routine)
    def cannot_save(*args,**kwargs):raise OSError('Synthetic disk failure')
    with monkeypatch.context() as patch:
        patch.setattr(routine.store,'identify',cannot_save)
        routine.from_feed(identity(4,name='New character',stamp=10000))
    routine.from_feed(energy(5,basic=50,full=False,stamp=11000))
    assert routine.profile_key is None and routine.entry_key is None and not routine.fresh
    assert routine.store.reading(old,'odyle').value==840


@pytest.mark.parametrize('lang',['pt_BR','en_US'])
def test_panorama_and_both_hud_styles_share_data_persist_selection_and_respect_visibility(qapp,tmp_path,lang):
    main=MainWindow(AppContext(tmp_path));set_language(lang)
    key=initial(main.routine)
    gate=OverlayVisibility(main,SimpleNamespace());gate.register(main.routine_panel,'hud')
    try:
        main.navigate('routine');main.show();main.routine_page.refresh()
        main.quick_menu.toggle_routine(True);gate.set_context(True);qapp.processEvents()
        panel=main.routine_panel
        assert panel.width()==220 and panel.height()<=120 and panel.isVisible()
        saved=main.routine.store.collection.model_dump_json()
        panel.move(77,88);main.context.prefs.routine.panel_position=(77,88);main.context.save()
        panel.toggle_style();qapp.processEvents()
        assert panel.height()==34 and main.context.prefs.routine.panel_style=='strip'
        assert panel.pos().x()==77 and panel.pos().y()==88
        assert main.routine.store.collection.model_dump_json()==saved
        assert AppContext(tmp_path).prefs.routine.panel_style=='strip'
        panel.toggle_locked();panel.toggle_expanded();qapp.processEvents()
        assert main.context.prefs.routine.panel_locked and not main.context.prefs.routine.panel_expanded
        gate.set_context(False);panel.refresh();assert not panel.isVisible()
        gate.set_context(True,'menu');panel.refresh();assert not panel.isVisible()
        gate.set_context(True);assert panel.isVisible()
        main.routine_page.open_detail(key)
        main.routine_page.toggle_pin('odyle_charged',False)
        assert main.context.prefs.routine.pinned==['odyle']
        main.quick_menu.toggle_routine(False)
        assert not panel.isVisible()
    finally:gate.shutdown();main.close();set_language('pt_BR')
