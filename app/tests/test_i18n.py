# SPDX-License-Identifier: GPL-3.0-only
import json
from datetime import datetime,UTC
import pytest
from PySide6.QtWidgets import QApplication
from app.core.i18n import set_language,tr,language
from app.services.context import AppContext
from app.ui.main_window import MainWindow
from app.modules.events.service import display_time


@pytest.fixture
def qapp():
    app=QApplication.instance() or QApplication([])
    set_language('pt_BR')
    yield app
    set_language('pt_BR')


def test_installer_default_and_explicit_preference_have_separate_priority(tmp_path):
    (tmp_path/'installation.json').write_text(json.dumps({'default_language':'en_US'}))
    context=AppContext(tmp_path)
    assert context.prefs.ui_language=='en_US'
    context.prefs.ui_language='pt_BR';context.save()
    assert AppContext(tmp_path).prefs.ui_language=='pt_BR'


def test_live_switch_translates_dynamic_controls_without_changing_user_state(qapp,tmp_path):
    context=AppContext(tmp_path)
    context.prefs.notifications.enabled=False
    window=MainWindow(context)
    window.show();qapp.processEvents()
    window.atlas.search.setText('user note: Minha rota')
    window.settings.timezone.setCurrentText('America/Fortaleza')
    context.prefs.visited.add(context.dataset.cubes[0].id)
    selected=window.events.panel_event.currentData()
    window.settings.language.setCurrentIndex(window.settings.language.findData('en_US'))
    qapp.processEvents()
    assert language()=='en_US' and window.nav[0].text()=='Home'
    assert window.statusBar().currentMessage()=='Ready to explore'
    assert window.catalog.table.horizontalHeaderItem(1).text()=='Resource'
    assert window.events.panel_event.currentData()==selected
    assert window.atlas.search.text()=='user note: Minha rota'
    assert window.settings.timezone.currentText()=='America/Fortaleza'
    window.sonar_alert.present(test=False)
    assert window.sonar_alert.title.text()=='Hidden cube detected!'
    assert window.sonar_alert.detail.text()=='There’s a cube nearby.'
    window.sonar_page.status.setText('Ouvindo o jogo')
    assert window.sonar_page.status.text()=='Listening to the game'
    window.settings.language.setCurrentIndex(window.settings.language.findData('pt_BR'))
    qapp.processEvents()
    assert window.nav[0].text()=='Início'
    assert window.catalog.table.horizontalHeaderItem(1).text()=='Recurso'
    assert window.sonar_page.status.text()=='Ouvindo o jogo'
    assert context.dataset.cubes[0].id in context.prefs.visited
    window.close()
    assert AppContext(tmp_path).prefs.ui_language=='pt_BR'


def test_us_dates_do_not_change_event_instant_or_timezone(qapp):
    instant=datetime(2026,10,12,18,0,tzinfo=UTC)
    original=display_time(instant,'America/Sao_Paulo')
    set_language('en_US')
    assert display_time(instant,'America/Sao_Paulo')=='10/12 • 3:00 PM UTC-03:00'
    set_language('pt_BR')
    assert display_time(instant,'America/Sao_Paulo')==original
    assert tr('Avisar 15 minutos antes')=='Avisar 15 minutos antes'
    set_language('en_US')
    assert tr('Avisar 15 minutos antes')=='Notify 15 minutes before'



def test_es419_live_switch_and_tactical_json(qapp, tmp_path):
    from PySide6.QtCore import QLocale
    from app.modules.siege.models import Coordinate
    from app.modules.siege.service import SiegeService

    context = AppContext(tmp_path / 'source')
    context.prefs.ui_language = 'pt_BR'
    siege = context.siege
    siege.create_preset('Minha coleção')
    pin = siege.add_marker('Início', Coordinate(x=.3, y=.4))
    drawing = siege.add_drawing('arrow', Coordinate(x=.3, y=.4), Coordinate(x=.4, y=.5), label='Objetivo')
    source = tmp_path / 'pt.json'
    siege.export_preset(source)
    window = MainWindow(context, runtime=False)
    try:
        window.show()
        window.navigate('settings')
        spanish = window.settings.language.findData('es-419')
        assert window.settings.language.itemText(spanish) == 'Español (Latinoamérica)'
        window.sonar_alert.present()
        window.settings.language.setCurrentIndex(spanish)
        qapp.processEvents()

        assert language() == 'es-419' and QLocale().bcp47Name() == 'es-419'
        assert window.nav[0].text() == 'Inicio'
        assert window.nav[5].toolTip() == 'Configuración'
        assert window.nav[11].text() == 'Mascotas'
        assert window.settings.quick_enabled.text() == 'Mostrar menú rápido de superposición'
        assert window.catalog.table.horizontalHeaderItem(1).text() == 'Recurso'
        assert window.quick_menu.switches['pets'].toolTip() == 'Panel de mascotas'
        assert window.quick_menu.switches['maps'].accessibleName() == 'Mapa + minimapa'
        assert window.sonar_alert.title.text() == '¡Cubo oculto detectado!'
        assert window.sonar_alert.detail.text() == 'Hay un cubo cerca.'
        window.sonar_page.show_confirmation(True)
        assert window.sonar_page.presence.text() == 'Cubo detectado'

        page = window.siege_page
        assert page.section.itemText(0) == 'Editar marcadores'
        assert page.section.itemText(3) == 'Dibujos tácticos'
        assert page.drawings.tool.findText('Flecha') >= 0
        assert page.pin_list.itemText(page.pin_list.findData(pin.id)) == 'Início'
        assert page.drawings.items.itemText(page.drawings.items.findData(drawing.id)) == 'Objetivo'
        assert page.pin_presets.currentText() == 'Minha coleção'
        assert tr('P1 · M2 · B3 · BF1 · DR2 · LR3') == 'P1 · M2 · B3 · BF1 · DR2 · LR3'
        assert display_time(datetime(2026, 10, 12, 18, tzinfo=UTC), 'America/Sao_Paulo') == '12/10 • 15:00 UTC-03:00'

        target = SiegeService(tmp_path / 'receiving')
        target.import_preset(source)
        exported = tmp_path / 'es.json'
        target.export_preset(exported)
        assert exported.read_bytes() == source.read_bytes()
        assert AppContext(tmp_path / 'source').prefs.ui_language == 'es-419'
        window.settings.language.setCurrentIndex(window.settings.language.findData('en_US'))
        assert window.nav[0].text() == 'Home'
        assert page.section.itemText(3) == 'Tactical drawings'
        assert page.pin_list.itemText(page.pin_list.findData(pin.id)) == 'Início'
        window.settings.language.setCurrentIndex(window.settings.language.findData('pt_BR'))
        assert window.nav[0].text() == 'Início'
    finally:
        window.sonar_alert.close()
        window.close()


def test_system_suggestion_only_applies_without_an_installer_or_saved_language(tmp_path, monkeypatch):
    monkeypatch.setattr('app.services.context.suggested_language', lambda: 'es-419')
    assert AppContext(tmp_path / 'portable').prefs.ui_language == 'es-419'
    installed = tmp_path / 'installed'
    installed.mkdir()
    (installed / 'installation.json').write_text(json.dumps({'default_language': 'en_US'}))
    context = AppContext(installed)
    assert context.prefs.ui_language == 'en_US'
    context.prefs.ui_language = 'pt_BR'
    context.save()
    assert AppContext(installed).prefs.ui_language == 'pt_BR'
