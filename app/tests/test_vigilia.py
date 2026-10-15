# SPDX-License-Identifier: GPL-3.0-only
"""Isolated presentation fixtures; no capture or claims about SA damage."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from app.core.i18n import set_language
from app.services.context import AppContext
from app.ui.main_window import MainWindow
from app.ui.combat_bars import ranked_rows
from app.ui.combat_classes import class_color, colored_class_icon
from app.ui.overlay_visibility import OverlayVisibility


def snapshot():
    return dict(run_name='Fixture',duration_ms=10000,total=4000,unattributed=1000,issues=['unattributed'],
        rows=[dict(actor_id=1,server=1,name='Local',rank=1,damage=2000,dps=200,share=.5,job=4,local=True),
              dict(actor_id=2,server=1,name='Remote',rank=2,damage=1000,dps=100,share=.25,job=6,local=False)])


def test_dps_fills_are_relative_to_leader_without_changing_damage_or_inventing_unknown_dps():
    data=snapshot();original=deepcopy(data)
    rows=ranked_rows(data)
    assert data==original
    assert [r['fraction'] for r in rows]==[1,.5,0]
    assert rows[-1]['rank'] is None and rows[-1]['dps'] is None and rows[-1]['damage']==1000
    data['rows'][1]['dps']=300
    assert ranked_rows(data)[0]['actor_id']==2
    for row in data['rows']:row['dps']=None
    assert all(r['fraction']==0 for r in ranked_rows(data))


@pytest.mark.parametrize('lang',['pt_BR','en_US'])
def test_impacto_reorders_preserves_row_details_collapses_and_stays_inside_visibility_gate(qapp,tmp_path,lang):
    main=MainWindow(AppContext(tmp_path));set_language(lang)
    panel=main.combat_page.panel;data=snapshot()
    main.combat.in_instance=True
    main.combat_page.selected_snapshot=lambda:data
    gate=OverlayVisibility(main,SimpleNamespace());gate.register(panel,'hud');gate.set_context(True)
    try:
        panel.refresh();qapp.processEvents()
        assert panel.width()==346 and len(panel.rows)==3
        assert '400' in panel.group_total.text()  # Includes observed unassigned damage.
        local=panel.rows[0]
        QTest.mouseClick(local,Qt.MouseButton.LeftButton)
        assert local.expanded and local.height()==55
        data['rows'][1]['dps']=300;panel.refresh();qapp.processEvents()
        assert panel.rows[1] is local and local.expanded
        assert panel.rows[0].item['fraction']==1
        panel.toggle_expanded();qapp.processEvents()
        assert not panel.scroller.isVisible() and panel.summary.isVisible() and panel.height()<150
        assert AppContext(tmp_path).prefs.combat.panel_expanded is False
        panel.toggle_details();assert AppContext(tmp_path).prefs.combat.panel_details
        gate.set_context(False);panel.refresh();assert not panel.isVisible()
        gate.set_context(True,'menu');panel.refresh();assert not panel.isVisible()
        gate.set_context(True);assert panel.isVisible()
    finally:gate.shutdown();main.close();set_language('pt_BR')


def test_history_selection_never_replays_an_old_result_on_live_hud(qapp,tmp_path):
    main=MainWindow(AppContext(tmp_path));main.combat.in_instance=True
    main.combat_page.scope.setCurrentIndex(main.combat_page.scope.findData('history'))
    main.combat_page.selected_snapshot=lambda:snapshot()
    try:
        main.combat_page.panel.refresh()
        assert main.combat_page.panel.rows==[]
    finally:main.close()


def test_fita_returns_to_48px_after_expanding_and_changing_language(qapp,tmp_path):
    main=MainWindow(AppContext(tmp_path));panel=main.event_panel
    try:
        main.quick_menu.toggle_events(True);qapp.processEvents()
        assert panel.width()==303 and panel.height()==48
        panel.toggle_expanded();qapp.processEvents();assert panel.height()>100
        set_language('en_US');panel.refresh();qapp.processEvents()
        panel.toggle_expanded();qapp.processEvents()
        assert panel.height()==48 and len(panel.cards)==1
        assert panel.cards[0].clock.text().startswith(('Today','Tomorrow'))
        assert qapp.primaryScreen().availableGeometry().contains(panel.frameGeometry())
    finally:main.close();set_language('pt_BR')


def test_vigilia_switches_share_state_with_pages_without_starting_collectors(qapp,tmp_path):
    main=MainWindow(AppContext(tmp_path))
    try:
        main.inspector.switches['events'].setChecked(True)
        assert main.events.panel_toggle.isChecked() and main.quick_menu.switches['events'].isChecked()
        main.quick_menu.toggle_events(False)
        assert not main.inspector.switches['events'].isChecked()
        for key in main.page_indices:
            main.navigate(key);assert main.nav[main.page_indices[key]].isChecked()
        main.inspector.switches['combat'].setChecked(False)
        assert not main.context.prefs.combat.panel_visible
        assert main.combat.process is None and main.sonar.worker is None and main.overlay.worker is None
        assert 'Azphelumbra' in main.windowTitle()
        assert main.combat_page.advanced.isHidden()
    finally:main.close()


def test_map_chips_share_atlas_filters_and_do_not_change_capture(qapp,tmp_path):
    main=MainWindow(AppContext(tmp_path))
    try:
        controls=main.map_controls
        controls.cubes.setChecked(False)
        assert controls.cube_categories <= main.context.prefs.disabled_categories
        controls.cubes.setChecked(True)
        assert not controls.cube_categories.intersection(main.context.prefs.disabled_categories)
        assert main.overlay.worker is None and not controls.isVisible()
    finally:main.close()


def test_approved_class_palette_preserves_original_alpha_silhouettes(qapp):
    assert class_color(4)=='#8bdc85'
    assert class_color(True)==class_color(999)
    for job in range(10):
        image=colored_class_icon(job).pixmap(32,32).toImage()
        assert not image.isNull() and image.hasAlphaChannel()
        assert image.pixelColor(0,0).alpha()==0
