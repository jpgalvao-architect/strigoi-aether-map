# SPDX-License-Identifier: GPL-3.0-only
from datetime import UTC, datetime, timedelta
import pytest
from app.core.i18n import set_language
from app.core.models import EventFeed
from app.infrastructure.storage import PACKAGE, atomic_json, load_model
from app.modules.events.boss_timer import BossConsensus, BossReading, read_gartua
from app.modules.events.service import calendar_occurrences, display_occurrence, occurrences
from app.services.context import AppContext


NOW = datetime(2026, 10, 17, 15, 0, tzinfo=UTC)


def lines(text='Time Left 2h 23min 38s', title='Immortal Gartua'):
    return [dict(text=title,x=124,y=55,height=28),
        dict(text=text,x=39,y=149,height=23),
        dict(text='Artwork: Immortal Gartua',x=113,y=247,height=22)]


def test_exact_title_and_countdown_are_required_together():
    assert read_gartua(lines()) == BossReading(8618)
    assert read_gartua(lines('Tempo restante: 2h 23m 38s')) == BossReading(8618)
    assert read_gartua(lines('Time Left 1d 2h')) == BossReading(93600)
    for text in ['Time Left 2h 63min', 'Time Left 0s', 'Time Left 8d', '2h 23min 38s', 'Time Left']:
        assert read_gartua(lines(text)) is None
    assert read_gartua(lines(title='Artwork: Immortal Gartua')) is None
    assert read_gartua(lines(title='Eternal Gartua')) is None
    assert read_gartua(lines()+[dict(text='Time Left 1h',x=39,y=170,height=23)]) is None
    assert read_gartua([lines()[0],dict(text='Time Left 2h',x=1600,y=149,height=23)]) is None


def test_consensus_compares_deadlines_not_equal_clock_strings():
    reader=BossConsensus()
    assert reader.observe('a',BossReading(8618),NOW) is None
    assert reader.observe('a',BossReading(8617),NOW+timedelta(seconds=1)) == BossReading(8617)
    assert reader.observe('b',BossReading(8616),NOW+timedelta(seconds=2)) is None
    assert reader.observe('b',None,NOW) is None
    assert reader.observe('b',BossReading(8616),NOW) is None
    assert reader.observe('b',BossReading(4000),NOW) is None


def test_observed_timer_is_once_only_utc_and_never_written_to_cache(qapp,tmp_path):
    context=AppContext(tmp_path);boss=context.boss_timer;boss.set_game((123,456))
    changed=[];context.events_changed.connect(lambda:changed.append(True))
    assert boss.accept(boss.screen_scope(),BossReading(8618),NOW,NOW)
    event=boss.events()[0]
    assert event.schedule.recurrence=='once' and event.schedule.timezone=='UTC'
    assert event.schedule.starts_at==NOW+timedelta(seconds=8618)
    assert event in context.calendar_events and event not in context.feed.events
    assert not occurrences([event],NOW+timedelta(days=1))
    assert boss.accept(boss.screen_scope(),BossReading(8617),NOW+timedelta(seconds=1),NOW+timedelta(seconds=1))
    assert len(changed)==1
    context.save()
    assert not AppContext(tmp_path).boss_timer.events()


@pytest.mark.parametrize('reason',['scope','disabled','old','future','naive','bad-seconds','naive-now'])
def test_stale_or_untrusted_readings_are_rejected(qapp,tmp_path,reason):
    context=AppContext(tmp_path);boss=context.boss_timer;boss.set_game((123,456))
    scope=boss.screen_scope();captured=NOW;reading=BossReading(8618);now=NOW
    if reason=='scope':boss.revision+=1
    if reason=='disabled':context.prefs.boss_timers_enabled=False
    if reason=='old':captured-=timedelta(seconds=7)
    if reason=='future':captured+=timedelta(seconds=2)
    if reason=='naive':captured=captured.replace(tzinfo=None)
    if reason=='bad-seconds':reading=BossReading(True)
    if reason=='naive-now':now=NOW.replace(tzinfo=None)
    assert not boss.accept(scope,reading,captured,now)
    assert not boss.events()


def test_identity_and_session_changes_invalidate_old_readings(qapp,tmp_path):
    boss=AppContext(tmp_path).boss_timer;boss.set_game((123,456))
    identify=lambda name:dict(type='event',kind='SelfIdentifiedEvent',payload=dict(ServerId=1,Name=name))
    boss.from_feed(identify('Test A'));scope=boss.screen_scope()
    assert boss.accept(scope,BossReading(100),NOW,NOW)
    boss.from_feed(dict(type='event',kind='ZoneChangedEvent',payload={}))
    assert boss.events() and not boss.accept(scope,BossReading(100),NOW,NOW)
    boss.from_feed(identify('Test B'))
    assert not boss.events()
    assert boss.accept(boss.screen_scope(),BossReading(100),NOW,NOW)
    boss.set_game((124,457));assert not boss.events()
    assert boss.accept(boss.screen_scope(),BossReading(100),NOW,NOW)
    boss.from_feed(dict(type='status',reset_zone=True));assert not boss.events()


def battlefield():
    return [e for e in load_model(PACKAGE/'data/events.json',EventFeed).events if e.kind=='Battlefield']


def test_battlefield_windows_are_daily_in_sa_and_active_until_close():
    events=battlefield();assert len(events)==2
    assert [e.duration_minutes for e in events]==[180,120]
    for offset in range(7):
        day=NOW+timedelta(days=offset)
        start=day.replace(hour=3)
        starts=occurrences(events,start,days=1)
        assert [o.starts_at.hour for o in starts]==[14,22]  # 11 and 19 BRT, once converted.
    active=calendar_occurrences(events,NOW)
    assert active[0].starts_at==NOW.replace(hour=14)
    assert calendar_occurrences(events,NOW.replace(hour=17))[0].starts_at.hour==22
    assert calendar_occurrences(events,NOW.replace(hour=23))[0].starts_at.hour==22
    assert calendar_occurrences(events,NOW+timedelta(hours=9))[0].starts_at.hour==14
    assert '14:00' in display_occurrence(active[0],'America/Sao_Paulo')


def test_reference_upgrade_preserves_disabled_choices_and_custom_agendas(qapp,tmp_path):
    old=load_model(PACKAGE/'tests/fixtures/sa-events-v031.json',EventFeed)
    old.events[0].enabled=False
    atomic_json(tmp_path/'events-cache.json',old)
    context=AppContext(tmp_path)
    assert context.feed.release=='reference-sa-v032'
    assert len(context.feed.events)==10 and not context.feed.events[0].enabled
    assert load_model(tmp_path/'events-cache.pre-calendar-20261017.json',EventFeed)==old
    assert AppContext(tmp_path).feed==context.feed
    custom=tmp_path/'custom';custom.mkdir()
    old.events[0].schedule.times=['02:47']
    atomic_json(custom/'events-cache.json',old)
    assert AppContext(custom).feed==old
    assert not (custom/'events-cache.pre-calendar-20261017.json').exists()


def test_abyss_reference_exposes_its_global_origin():
    events={e.id:e for e in load_model(PACKAGE/'data/events.json',EventFeed).events}
    for key in ['siege-bosses','guardian-nahma','watcher-kaira']:
        event=events['reference-sa-'+key]
        assert 'Global' in event.verification and 'SA' in event.notes
        assert event.source=='https://aion2.gaming.tools/maps/20'
        assert event.duration_minutes is None
    assert events['reference-sa-siege-bosses'].schedule.times==['21:30']
    assert events['reference-sa-watcher-kaira'].schedule.times==['01:00','04:00','07:00','10:00','13:00','16:00','19:00','22:00']


def test_worker_reuses_existing_capture_and_requires_two_consistent_reads(monkeypatch):
    import numpy as np
    import mss
    from app.modules.overlay.foreground import GameWindow
    from app.modules.overlay.menu_monitor import MenuMonitor
    game=GameWindow(123,456,0,0,1920,1080)
    class Probe:
        def game_foreground(self):return game
    monitor=MenuMonitor(Probe());job=(game,1);scope=((123,456),0)
    monitor.set_game(job);monitor.set_boss_scope(scope)
    grabs=[];reads=[];observed=[]
    class Capture:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def grab(self,area):
            grabs.append(area)
            return np.zeros((area['height'],area['width'],4),np.uint8)
    def recognize(image):
        reads.append(True)
        if len(reads)==2:monitor.stopped.set()
        return lines()
    monkeypatch.setattr(mss,'MSS',Capture)
    monkeypatch.setattr(monitor.ocr,'recognize',recognize)
    monitor.boss_observed.connect(lambda *args:observed.append(args))
    monitor.run()
    assert len(grabs)==len(reads)==2 and len(observed)==1
    assert grabs[0]['height']==486  # Existing upper-game strip, no second full-screen capture.
    assert observed[0][:3]==(job,scope,BossReading(8618))


def test_sidebar_uses_the_same_open_battlefield_window(qapp,tmp_path,monkeypatch):
    from app.ui.main_window import MainWindow
    import app.ui.session_inspector as inspector_module
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return NOW.astimezone(tz)
    monkeypatch.setattr(inspector_module,'datetime',Clock)
    main=MainWindow(AppContext(tmp_path))
    try:
        main.context.prefs.overlay.events_panel_event=battlefield()[0].id
        main.inspector.refresh()
        assert '11:00' in main.inspector.when.text() and '14:00' in main.inspector.when.text()
        assert main.inspector.when.text().endswith('Fecha em 02:00:00')
    finally:main.close()


@pytest.mark.parametrize('event_index',[0,1])
def test_battlefield_stays_in_app_and_saved_hud_choice_falls_back(qapp,tmp_path,monkeypatch,event_index):
    import app.ui.events_page as page_module
    from app.ui.event_panel import EventPanel
    context=AppContext(tmp_path);context.prefs.overlay.events_panel=True
    context.prefs.overlay.events_panel_event=battlefield()[event_index].id
    context.save();context=AppContext(tmp_path)
    panel=EventPanel(context);panel.timer.stop()
    try:
        panel.refresh(NOW)
        assert panel.items==calendar_occurrences(context.panel_events,NOW)[:1]
        assert panel.items and panel.items[0].event.kind!='Battlefield'
        assert panel.event_selector.currentData()==''
        assert panel.event_selector.actions_by_event[''].isChecked()
        context.prefs.overlay.events_panel_expanded=True;panel.refresh(NOW)
        assert panel.items and all(item.event.kind!='Battlefield' for item in panel.items)
        assert all(event.id not in panel.event_selector.actions_by_event for event in battlefield())
        context.boss_timer.set_game((123,456))
        assert context.boss_timer.accept(context.boss_timer.screen_scope(),BossReading(8618),NOW,NOW)
        context.prefs.overlay.events_panel_event='observed-immortal-gartua';panel.refresh(NOW)
        assert panel.items[0].event.id=='observed-immortal-gartua'
        assert panel.event_selector.menu_widget is not None
        page=page_module.EventsPage(context);page.timer.stop()
        assert page.panel_event.currentData()=='observed-immortal-gartua'
        assert all(page.panel_event.findData(event.id)<0 for event in battlefield())
        opened=[]
        monkeypatch.setattr(page_module.QMessageBox,'information',lambda *args:opened.append(args))
        # A screen-based source shows its provenance instead of opening an invented URL.
        index=next(i for i,item in enumerate(page.items) if item.event.kind=='Battlefield')
        page.table.setCurrentCell(index,0);page.open_source()
        assert opened and opened[0][1]=='Leitura do jogo'
        page.close()
    finally:panel.shutdown();set_language('pt_BR')


def test_battlefield_only_agenda_has_no_floating_events(qapp,tmp_path):
    from app.ui.event_panel import EventPanel
    from app.ui.event_selector import EventSelector
    context=AppContext(tmp_path);context.prefs.overlay.events_panel=True
    context.feed=EventFeed(events=battlefield());context.save()
    panel=EventPanel(context);panel.timer.stop();selector=EventSelector(context)
    try:
        for selected in ['',*(event.id for event in battlefield())]:
            context.prefs.overlay.events_panel_event=selected;selector.refresh()
            for expanded in [False,True]:
                context.prefs.overlay.events_panel_expanded=expanded;panel.refresh(NOW)
                assert panel.items==[] and panel.empty.isVisible()
            assert selector.currentData()=='' and selector.count()==1
            assert len(context.calendar_events)==2  # Source schedule is never deleted/disabled.
            assert calendar_occurrences(context.calendar_events,NOW)[0].event.kind=='Battlefield'
    finally:panel.shutdown();selector.close()
