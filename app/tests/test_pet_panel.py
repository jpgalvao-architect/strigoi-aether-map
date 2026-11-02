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
        assert main.pet_panel.heading.text()=='Tracked pets'
        from app.ui.localized_widgets import QLabel
        assert any('9 souls' in w.text() for w in main.pet_panel.findChildren(QLabel))
    finally:
        set_language('pt_BR');main.close()


def test_unknown_duduka_shows_verified_gains_instead_of_misleading_saved_label(qapp,tmp_path):
    from app.tests.test_pet_sync import event
    from app.ui.localized_widgets import QLabel
    main=MainWindow(AppContext(tmp_path))
    try:
        main.context.prefs.pets.panel_visible=True
        main.pets.edit(1172,favorite=True)
        main.pets.accept(event(1,'PetSoulAcquiredEvent',dict(PetId=1172,Amount=1)))
        main.pets.accept(event(2,'PetSoulAcquiredEvent',dict(PetId=1172,Amount=2)))
        main.pet_panel.refresh()
        labels=main.pet_panel.findChildren(QLabel)
        assert any(w.text()=='+3 almas nesta captura' for w in labels)
        assert not any('Salvo' in w.text() for w in labels)
        from app.modules.pets.screen import PetScreenReading
        main.pets.from_screen(main.pets.screen_scope(),PetScreenReading(1172,2,62,75))
        main.pets.accept(event(3,'PetSoulAcquiredEvent',dict(PetId=1172,Amount=1)))
        main.pet_panel.refresh()
        assert any('63/75 almas' in w.text() for w in main.pet_panel.findChildren(QLabel))
        main.pets.disconnected()
        main.pets.accept(event(1,'PetSoulAcquiredEvent',dict(PetId=1172,Amount=3)))
        set_language('en_US');main.pet_panel.refresh()
        assert any(w.text()=='+3 souls this capture' for w in main.pet_panel.findChildren(QLabel))
    finally:
        set_language('pt_BR');main.close()


def test_known_total_survives_quality_loss_and_other_pet_pickups(qapp,tmp_path):
    from app.tests.test_pet_sync import event,identity
    from app.modules.pets.screen import PetScreenReading
    from app.ui.localized_widgets import QLabel
    main=MainWindow(AppContext(tmp_path))
    try:
        main.context.prefs.pets.panel_visible=True
        service=main.pets
        service.accept(identity())
        for pet in (1127,1172,1173):
            service.edit(pet,favorite=True)
            assert service.from_screen(service.screen_scope(),PetScreenReading(pet,2,38,75))
        pickup=event(2,'PetSoulAcquiredEvent',dict(PetId=1172,Amount=1))
        service.accept(pickup);service.accept(pickup)
        assert service.entry(1172).progress.souls==39
        assert service.entry(1127).progress.souls==38
        assert service.entry(1173).progress.souls==38
        service.accept({'type':'feed_quality','reason':'capture_gap'})
        service.accept(event(3,'PetSoulAcquiredEvent',dict(PetId=1172,Amount=1)))
        main.pet_panel.refresh()
        labels=main.pet_panel.findChildren(QLabel)
        assert any('39/75 almas · Salvo' in w.text() for w in labels)
        assert not any(w.text().startswith('+') for w in labels)
        assert any('+2 almas nesta captura' in w.toolTip() for w in labels)
        assert service.entry(1172).progress.souls==39  # Gap prevents claiming an exact live balance.
        assert service.from_screen(service.screen_scope(),PetScreenReading(1172,2,40,75))
        service.accept(event(4,'PetSoulAcquiredEvent',dict(PetId=1172,Amount=1)))
        main.pet_panel.refresh()
        assert any(w.text().endswith('41/75 almas') for w in main.pet_panel.findChildren(QLabel))
        set_language('en_US');main.pet_panel.refresh()
        assert any('38/75 souls' in w.text() for w in main.pet_panel.findChildren(QLabel))
    finally:
        set_language('pt_BR');main.close()


def test_unbound_screen_total_keeps_ratio_when_capture_confirmation_is_lost(qapp,tmp_path):
    from app.tests.test_pet_sync import event
    from app.modules.pets.screen import PetScreenReading
    from app.ui.localized_widgets import QLabel
    main=MainWindow(AppContext(tmp_path))
    try:
        main.context.prefs.pets.panel_visible=True
        service=main.pets
        service.edit(1173,favorite=True)
        service.accept(event(1,'PetSoulAcquiredEvent',dict(PetId=1173,Amount=1)))
        assert service.from_screen(service.screen_scope(),PetScreenReading(1173,2,36,75))
        service.accept(event(2,'PetSoulAcquiredEvent',dict(PetId=1173,Amount=1)))
        service.accept({'type':'feed_quality','reason':'pet_record_rejected'})
        service.accept(event(3,'PetSoulAcquiredEvent',dict(PetId=1173,Amount=1)))
        main.pet_panel.refresh()
        labels=main.pet_panel.findChildren(QLabel)
        assert any('37/75 almas · Conferir' in w.text() for w in labels)
        assert not any(w.text().startswith('+') for w in labels)
        assert service.store.entry(1173).progress is None  # Never save under a guessed character.
    finally:
        main.close()
