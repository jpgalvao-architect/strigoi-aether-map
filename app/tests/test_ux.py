# SPDX-License-Identifier: GPL-3.0-only
from datetime import UTC,datetime,timedelta
from zoneinfo import ZoneInfo
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel
from app.core.models import EventFeed,EventSchedule,GameEvent
from app.infrastructure.storage import PACKAGE
from app.modules.events.day import day_events
from app.modules.events.service import occurrences, calendar_occurrences
from app.services.context import AppContext
from app.ui.event_panel import EventPanel
from app.ui.main_window import MainWindow
from app.ui.icons import icon,event_icon
import pytest


def daily_event(clock,id='test'):
    return GameEvent(id=id,name='Teste',kind='Fenda',region='SA',source='https://example.com',
        schedule=EventSchedule(timezone='UTC',times=[clock]))


def test_day_agenda_uses_display_timezone_includes_past_and_excludes_tomorrow():
    now=datetime(2026,10,12,15,tzinfo=UTC)
    events=[daily_event('01:00','previous'),daily_event('12:00','past'),daily_event('22:00','later')]
    items=day_events(events,now,'America/Fortaleza')
    assert [i.event.id for i in items]==['past','later','previous']
    # At UTC-3, today's 01:00 UTC occurrence falls on tomorrow's UTC date.
    assert {i.key for i in items}=={
        'past@2026-10-12T12:00:00+00:00','later@2026-10-12T22:00:00+00:00','previous@2026-10-13T01:00:00+00:00'}
    assert items==sorted(items,key=lambda i:i.starts_at)


@pytest.mark.parametrize('date,hours',[(datetime(2026,3,8,12,tzinfo=UTC),23),(datetime(2026,11,1,12,tzinfo=UTC),25)])
def test_calendar_day_honors_dst_boundaries(date,hours):
    event=daily_event('00:00')
    event.schedule.times=[f'{hour:02}:00' for hour in range(24)]
    items=day_events([event],date,'America/New_York')
    assert len(items)==hours
    assert all(i.starts_at.astimezone(ZoneInfo('America/New_York')).date()==date.astimezone(ZoneInfo('America/New_York')).date() for i in items)


def test_panel_switches_between_next_event_and_all_today_and_persists(qapp,tmp_path):
    context=AppContext(tmp_path);context.prefs.overlay.events_panel=True
    now=datetime(2026,10,12,15,tzinfo=UTC)
    panel=EventPanel(context);panel.timer.stop()
    try:
        panel.refresh(now)
        assert len(panel.items)==1 and panel.items[0]==calendar_occurrences(context.feed.events,now)[0]
        context.prefs.overlay.events_panel_expanded=True
        panel.refresh(now)
        assert panel.items==day_events(context.feed.events,now,context.prefs.timezone)
        assert len(panel.items)>3 and any(i.starts_at<now for i in panel.items)
        old_card=panel.cards[0]
        panel.refresh(now)
        assert panel.cards[0] is old_card # ticking does not rebuild all rows
        QTest.mouseClick(panel.expand_button,Qt.MouseButton.LeftButton)
        assert not context.prefs.overlay.events_panel_expanded
        assert len(panel.items)==1
        panel.toggle_expanded()
        assert AppContext(tmp_path).prefs.overlay.events_panel_expanded
        panel.dismiss()
        assert not panel.isVisible() and not context.prefs.overlay.events_panel
    finally:panel.shutdown()


def test_panel_handles_empty_agenda_and_changed_feed_with_same_identity(qapp,tmp_path):
    context=AppContext(tmp_path);context.prefs.overlay.events_panel=True
    panel=EventPanel(context);panel.timer.stop()
    try:
        context.feed=EventFeed(events=[])
        panel.refresh();assert panel.items==[] and panel.empty.isVisible()
        context.feed=EventFeed(events=[daily_event('23:00')])
        panel.refresh();assert panel.cards[0].name.text()=='Teste'
        context.feed=context.feed.model_copy(deep=True);context.feed.events[0].name='Novo nome'
        panel.refresh();assert panel.cards[0].name.text()=='Novo nome'
    finally:panel.shutdown()


def test_original_icons_and_mascot_assets_are_renderable(qapp):
    for path in (PACKAGE/'assets/icons').glob('*.svg'):
        assert not icon(path.stem).pixmap(24,24).isNull()
    for name in ['aether-asmodian-v2.png','aether-avatar-v2.png']:
        image=QImage(str(PACKAGE/'assets'/name))
        assert not image.isNull() and image.hasAlphaChannel() and image.pixelColor(0,0).alpha()==0
    assert event_icon(daily_event('23:00'))=='rift'


def test_panel_next_event_can_be_tomorrow_without_polluting_today(qapp,tmp_path):
    context=AppContext(tmp_path);context.prefs.overlay.events_panel=True
    now=datetime(2026,10,12,15,tzinfo=UTC)
    tomorrow=GameEvent(id='tomorrow',name='Amanhã',kind='Cerco',region='SA',source='https://example.com',
        schedule=EventSchedule(recurrence='once',starts_at=now+timedelta(days=1)))
    context.feed=EventFeed(events=[tomorrow])
    panel=EventPanel(context);panel.timer.stop()
    try:
        panel.refresh(now)
        assert len(panel.items)==1 and panel.cards[0].clock.text().startswith('Amanhã')
        context.prefs.overlay.events_panel_expanded=True
        panel.refresh(now)
        assert not panel.items and panel.empty.isVisible()
    finally:panel.shutdown()


def test_restored_panel_position_stays_on_available_screen(qapp,tmp_path):
    context=AppContext(tmp_path);context.prefs.overlay.events_panel=True
    context.prefs.overlay.events_panel_position=(99999,-99999)
    panel=EventPanel(context)
    try:
        assert qapp.primaryScreen().availableGeometry().contains(panel.frameGeometry())
    finally:panel.shutdown()


def test_ui_hides_technical_copy_and_uses_navigation_icons(qapp,tmp_path):
    window=MainWindow(AppContext(tmp_path));window.show();qapp.processEvents()
    try:
        assert [b.text() for b in window.nav]==['Início','Atlas','Coletas','Cubos ocultos','Eventos','Configurações','Overlay','Sonar','Combate','Donate','Sobre','Pets','Rotina']
        window.navigate(8)
        assert window.pages[8] is window.combat_page and window.nav[8].isChecked()
        assert 'cubes' not in window.cubes.resource_checks
        assert all(not b.icon().isNull() for b in window.nav)
        texts=' '.join(label.text() for label in window.findChildren(QLabel))
        assert 'recurso de acessibilidade' in texts and 'anticheat' not in texts and 'mascote oficial' not in texts
        assert window.overlay_page.advanced.isHidden() and window.events.advanced.isHidden()
        assert window.banner.isHidden()
        window.overlay_page.advanced_button.setChecked(True)
        assert not window.overlay_page.advanced.isHidden()
        window.events.panel_toggle.setChecked(True)
        assert window.event_panel.isVisible()
    finally:window.close()
