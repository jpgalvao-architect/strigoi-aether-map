# SPDX-License-Identifier: GPL-3.0-only
from datetime import UTC,datetime
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from app.core.models import EventFeed
from app.modules.gatherables.service import FilterQuery,filter_points
from app.modules.overlay.service import OverlayService
from app.services.context import AppContext
from app.ui.event_panel import EventPanel
from app.ui.event_selector import EventSelector
from app.ui.layer_menu import AtlasLayerMenu
from app.ui.sonar_page import SonarAlert
from app.ui.donate_page import DonatePage,INSTITUTIONS,CREATOR_URL


def test_chosen_event_shared_between_page_panel_and_restart(qapp,tmp_path):
    context=AppContext(tmp_path);context.prefs.overlay.events_panel=True
    selector=EventSelector(context);panel=EventPanel(context);panel.timer.stop()
    event=next(e for e in context.feed.events if e.enabled)
    try:
        selector.setCurrentIndex(selector.findData(event.id))
        now=datetime(2026,10,12,12,tzinfo=UTC)
        panel.refresh(now)
        assert panel.items and all(i.event.id==event.id for i in panel.items)
        assert panel.event_selector.currentData()==event.id
        context.prefs.overlay.events_panel_expanded=True;panel.refresh(now)
        assert all(i.event.id==event.id for i in panel.items)
        assert AppContext(tmp_path).prefs.overlay.events_panel_event==event.id
        context.feed=EventFeed(demo=False,events=[]);context.events_changed.emit();panel.refresh(now)
        assert panel.items==[] and selector.currentData()==event.id
        selector.setCurrentIndex(0)
        assert context.prefs.overlay.events_panel_event==''
    finally:panel.shutdown();selector.close()


def test_atlas_menu_updates_all_overlay_modes_without_extra_cube_filter(qapp,tmp_path):
    context=AppContext(tmp_path)
    categories={r.id:r.category for r in context.dataset.resources}
    herb=next(c.id for c in context.dataset.categories if 'herb' in c.id)
    context.prefs.disabled_categories={c.id for c in context.dataset.categories if c.id not in [herb,'cubes']}
    service=OverlayService(context);menu=AtlasLayerMenu(context)
    try:
        context.prefs.overlay.enabled=True
        # Historical settings must no longer veto checked Atlas categories.
        context.prefs.overlay.layers='cubes'
        for mode in ['large','minimap']:
            context.prefs.overlay.map_view=mode;service.sync()
            expected=filter_points(context.dataset,context.prefs,FilterQuery(map_id='altgard',overlay=True))
            assert len(service.window.markers)==len(expected)
            assert {categories[p.resource_id] for p in expected}=={herb,'cubes'}
        menu.actions_by_category[herb].setChecked(False)
        expected=filter_points(context.dataset,context.prefs,FilterQuery(map_id='altgard',overlay=True))
        assert len(service.window.markers)==len(expected) and all(categories[p.resource_id]=='cubes' for p in expected)
        assert herb in AppContext(tmp_path).prefs.disabled_categories
    finally:service.stop();service.watchdog.stop();service.window.close();menu.close()


def test_visual_test_does_not_claim_cube_detection(qapp,tmp_path):
    alert=SonarAlert(AppContext(tmp_path))
    try:
        alert.present(test=True)
        assert alert.isVisible() and alert.title.text()=='Teste do aviso do sonar'
        alert.present()
        assert alert.title.text()=='Possível cubo por perto'
    finally:alert.timer.stop();alert.close()


def test_donate_buttons_open_only_authorized_channels(qapp,monkeypatch):
    from PySide6.QtGui import QDesktopServices
    opened=[]
    monkeypatch.setattr(QDesktopServices,'openUrl',lambda url:opened.append(url.toString()) or True)
    page=DonatePage()
    QTest.mouseClick(page.creator_button,Qt.MouseButton.LeftButton)
    for b in page.buttons:QTest.mouseClick(b,Qt.MouseButton.LeftButton)
    assert opened==[CREATOR_URL,*[item['url'] for item in INSTITUTIONS]]
    page.open_channel('https://example.com/')
    assert len(opened)==3
    page.close()
