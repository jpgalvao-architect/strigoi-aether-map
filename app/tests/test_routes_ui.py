# SPDX-License-Identifier: GPL-3.0-only
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from app.core.i18n import set_language
from app.services.context import AppContext
from app.ui.main_window import MainWindow
from app.ui.overlay_visibility import OverlayVisibility
from app.modules.routes.models import Vertex


def test_route_ui_edits_saves_and_syncs_atlas_and_quick_menu(qapp,tmp_path):
    window=MainWindow(AppContext(tmp_path));window.show();qapp.processEvents()
    page=window.routes_page;service=window.routes
    try:
        window.show_route_target('altgard','azpha');qapp.processEvents()
        assert window.stack.currentIndex()==13 and window.inspector.isHidden()
        assert len(service.draft.stops)==12 and page.resources==['azpha']
        page.set_edit('passage');v=service.draft.legs[0].vertices
        page.map_clicked((v[0].x+v[1].x)/2,(v[0].y+v[1].y)/2)
        assert any(l.origin=='edited' for l in service.draft.legs)
        page.review.setChecked(True);assert any(l.reviewed for l in service.draft.legs)
        page.undo_edit();assert all(l.origin=='suggested' for l in service.draft.legs)
        page.set_edit('origin');target=service.draft.stops[3]
        page.map_clicked(target.x,target.y);assert service.draft.stops[0].id==target.id
        page.save();assert len(service.library.routes)==1
        # Starting a service does not create another capture or network consumer.
        service.start();assert window.overlay.worker is None
        assert window.route_panel.isVisible() and window.route_panel.height()==38
        assert window.atlas.view.route_items
        assert window.quick_menu.switches['routes'].isChecked()
        window.route_panel.toggle_style();assert window.route_panel.height()==54
        assert AppContext(tmp_path).prefs.routes.panel_style=='guide'
        window.quick_menu.toggle_routes(False);assert not window.route_panel.isVisible() and service.active
        window.quick_menu.toggle_routes(True);assert window.route_panel.isVisible()
        window.navigate('atlas');assert not window.inspector.isHidden()
        service.stop();assert not window.atlas.view.route_items and not window.route_panel.isVisible()
        set_language('en_US');service.start();window.route_panel.refresh()
        assert window.nav[13].text()=='Routes' and page.start_button.text()=='Start on minimap'
        assert window.route_panel.detail.text()=='Identify your character'
        window.route_panel.hide_guide();assert not window.context.prefs.routes.panel_visible
        page.change_mode('open');page.set_edit('custom');assert service.draft is None and not page.resources
        page.map_clicked(.4,.4);page.map_clicked(.5,.5)
        assert len(service.draft.stops)==2 and all(p.custom for p in service.draft.stops) and service.draft.mode=='open'
        page.change_mode('open');assert len(service.draft.legs)==1
    finally:window.close();set_language('pt_BR')


def test_route_hud_is_hidden_in_menus_and_alt_tab_without_losing_session(qapp,tmp_path):
    window=MainWindow(AppContext(tmp_path));service=window.routes
    gate=OverlayVisibility(window);gate.timer.stop()
    try:
        gate.register(window.route_panel,'hud');gate.set_context(True,'play');service.start()
        assert window.route_panel.isVisible()
        gate.set_context(True,'menu');assert not window.route_panel.isVisible() and not service.allowed
        service.notify();assert not window.route_panel.isVisible()
        gate.set_context(False);assert not window.route_panel.isVisible()
        gate.set_context(True,'play');assert window.route_panel.isVisible() and service.current==0
        assert window.overlay.worker is None
    finally:gate.shutdown();window.close()


def test_route_page_fits_small_window_and_projection_uses_same_transform(qapp,tmp_path):
    import numpy as np
    from app.modules.overlay.tracking import Registration
    from app.modules.routes.drawing import project_lines
    window=MainWindow(AppContext(tmp_path));window.resize(1120,780);window.show();window.navigate('routes');qapp.processEvents()
    try:
        page=window.routes_page;scroll=window.stack.currentWidget()
        assert page.height()<=scroll.viewport().height()
        page.advanced_toggle.setChecked(True);qapp.processEvents()
        assert page.height()<=scroll.viewport().height()
        assert page.start_button.isVisible() and page.status.isVisible()
        window.routes.start();target=window.routes.target
        assert window.overlay.window.route_target[:2]==(target.x,target.y)
        lines=window.overlay.window.route_lines
        transform=Registration(np.array([[1200,0,-200],[0,900,-100]],float),25,.95)
        projected=project_lines(lines,transform,1.5)
        first=window.routes.route.legs[0].vertices[0]
        assert projected[0][0][0]==((1200*first.x-200)/1.5,(900*first.y-100)/1.5)
        window.routes.skip();assert window.overlay.window.route_target[2]==2
        # A recorded journey must restore its own map/targets, even after previewing another map.
        leg=window.routes.route.legs[0]
        window.routes.recordings={0:[v.model_copy() for v in leg.vertices]}
        other=next(i for i in range(page.maps.count()) if page.maps.itemData(i)!=window.routes.route.map_id)
        page.maps.setCurrentIndex(other);qapp.processEvents();page.review_recorded()
        assert page.maps.currentData()==window.routes.route.map_id==page.view.map.id
        assert page.resources==window.routes.route.resources and page.mode==window.routes.route.mode
    finally:window.close()
