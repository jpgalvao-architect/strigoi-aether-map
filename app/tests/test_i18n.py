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
    assert window.sonar_alert.title.text()=='Possible cube nearby'
    assert window.sonar_alert.detail.text()=='Search nearby before another player collects it!'
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
