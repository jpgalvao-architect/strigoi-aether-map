# SPDX-License-Identifier: GPL-3.0-only
from types import SimpleNamespace

from app.core.i18n import set_language
from app.services.context import AppContext
from app.ui.main_window import MainWindow
from app.ui.overlay_visibility import OverlayVisibility


def test_collection_panel_and_quick_controls_preserve_capture_and_gate_visibility(qapp,tmp_path):
    main=MainWindow(AppContext(tmp_path))
    gate=OverlayVisibility(main,SimpleNamespace())
    gate.register(main.pet_panel,'hud');gate.set_context(True)
    try:
        main.combat.feed.consumers={'combat','pets'}
        main.pets.store.record(1127,2,9)
        for pet in (1127,1069,1001):main.pets.edit(pet,favorite=True)
        main.quick_menu.toggle_pets(True);qapp.processEvents()
        assert main.pet_panel.isVisible() and main.context.prefs.pets.panel_visible
        assert main.pet_panel.scroller.height()==55
        main.pet_panel.toggle_expanded()
        assert main.pet_panel.scroller.height()==165
        gate.set_context(False);main.pet_panel.refresh()
        assert not main.pet_panel.isVisible() and main.combat.feed.consumers=={'combat','pets'}
        gate.set_context(True,'menu');assert not main.pet_panel.isVisible()
        gate.set_context(True);assert main.pet_panel.isVisible()
        main.pet_panel.dismiss()
        assert not main.pet_panel.isVisible() and main.combat.feed.consumers=={'combat','pets'}
        main.quick_menu.toggle_pets(True)
        main.pets_page.panel_opacity.setValue(.65)
        assert abs(main.pet_panel.windowOpacity()-.65)<.01
        main.pet_panel.toggle_locked();assert main.context.prefs.pets.panel_locked
        main.pets_page.restore_panel()
        assert not main.context.prefs.pets.panel_locked and main.context.prefs.pets.panel_opacity==.9
    finally:
        gate.shutdown();main.close()


def test_map_filter_language_and_panel_offline_mode(qapp,tmp_path):
    main=MainWindow(AppContext(tmp_path))
    try:
        page=main.pets_page
        total=page.grid.count()
        page.map_choice.setCurrentIndex(page.map_choice.findData('altgard'))
        assert 0<page.grid.count()<total
        visible=[page.grid.item(n).data(256) for n in range(page.grid.count())]
        assert all(any(site.map_id=='altgard' for site in main.pets.farm.by_pet[pet]) for pet in visible)
        main.context.prefs.pets.auto_collection=False
        main.pets.runtime=True
        main.quick_menu.toggle_pets(True)
        assert not main.combat.feed.consumers and main.combat.feed.process is None
        main.pets.edit(1127,favorite=True);main.pets.record(1127,2,9)
        set_language('en_US');main.pet_panel.refresh()
        assert main.pet_panel.heading.text()=='Favorite pets'
        from app.ui.localized_widgets import QLabel
        assert any('9 souls' in w.text() for w in main.pet_panel.findChildren(QLabel))
    finally:
        set_language('pt_BR');main.close()
