# SPDX-License-Identifier: GPL-3.0-only
"""Vigília's session sidebar shares the existing module controls and preferences."""
from datetime import UTC, datetime, timedelta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from app.core.i18n import tr
from app.modules.events.service import calendar_occurrences as occurrences, display_occurrence, countdown
from app.ui.localized_widgets import QFrame, QCheckBox, QPushButton
from app.ui.widgets import label
from app.ui.mascot import MascotWidget


class SessionInspector(QFrame):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setObjectName('sessionInspector')
        self.setFixedWidth(200)
        box = QVBoxLayout(self); box.setContentsMargins(15,22,15,16); box.setSpacing(12)
        box.addWidget(label('SUA SESSÃO','eyebrow'))
        self.place = label('Em Atréia', 'sessionTitle', True); box.addWidget(self.place)
        self.party = label('', 'subtitle', True); box.addWidget(self.party)
        self.divider(box)
        box.addWidget(label('O que aparece no jogo','sectionTitle',True))
        self.switches = {}
        self.states = {}
        for key, title in [('maps','Mapa + minimapa'),('routes','Guia de rotas'),('sonar','Sonar'),('combat','Combate'),('events','Eventos'),('pets','Pets'),('routine','Rotina')]:
            line = QHBoxLayout(); line.setSpacing(4)
            copy = QVBoxLayout(); copy.setSpacing(3); copy.addWidget(label(title))
            state = label('', 'sessionState'); copy.addWidget(state); self.states[key] = state
            line.addLayout(copy,1)
            switch = QCheckBox(); switch.setObjectName('moduleSwitch'); switch.setAccessibleName(title)
            switch.toggled.connect(lambda enabled, name=key: self.toggle(name,enabled))
            line.addWidget(switch); box.addLayout(line); self.switches[key] = switch
        self.divider(box)
        self.explore = QVBoxLayout(); self.explore.setSpacing(3); box.addLayout(self.explore)
        self.divider(box)
        box.addWidget(label('NO SEU RADAR','eyebrow'))
        self.event = label('', 'sectionTitle',True); box.addWidget(self.event)
        self.when = label('', 'subtitle',True); box.addWidget(self.when)
        change = QPushButton('Trocar evento'); change.setObjectName('quiet')
        change.clicked.connect(lambda: main.navigate('events')); box.addWidget(change)
        box.addStretch()
        footer = QHBoxLayout(); footer.setSpacing(7)
        avatar = MascotWidget(compact=True); avatar.setFixedSize(38,38); footer.addWidget(avatar)
        footer.addWidget(label('Você cuida da partida.','subtitle',True),1); box.addLayout(footer)

    @staticmethod
    def divider(layout):
        line = QFrame(); line.setObjectName('divider'); line.setFixedHeight(1); layout.addWidget(line)

    def toggle(self, name, enabled):
        menu = self.main.quick_menu
        getattr(menu,{'maps':'toggle_maps','sonar':'toggle_sonar','combat':'toggle_combat',
                      'events':'toggle_events','pets':'toggle_pets','routine':'toggle_routine','routes':'toggle_routes'}[name])(enabled)

    def refresh(self, *_):
        main = self.main
        if not hasattr(main,'quick_menu'): return
        engine=main.combat.engine
        self.place.setText((engine.run_name or tr('Instância')) if main.combat.in_instance else 'Em Atréia')
        count = len(engine.roster)
        self.party.setText(tr('Grupo · {numero} participantes').format(numero=count)
                           if main.combat.in_instance and count else 'Aguardando o combate' if main.combat.in_instance else 'Aguardando uma instância')
        for key,switch in self.switches.items():
            source = main.quick_menu.switches[key]
            switch.blockSignals(True); switch.setChecked(source.isChecked()); switch.blockSignals(False)
            self.states[key].setText(main.quick_menu.states[key].text())
        now = datetime.now(UTC); selected = main.context.prefs.overlay.events_panel_event
        events = [e for e in main.context.calendar_events if not selected or e.id==selected]
        upcoming = occurrences(events,now)[:1]
        self.event.setText(upcoming[0].event.name if upcoming else 'Nenhum evento agendado')
        if upcoming:
            item=upcoming[0];remaining=countdown(item.starts_at,now)
            if item.event.kind=='Battlefield' and item.event.duration_minutes and item.starts_at<=now:
                remaining='Fecha em '+countdown(item.starts_at+timedelta(minutes=item.event.duration_minutes),now)
            self.when.setText(display_occurrence(item,main.context.prefs.timezone)+'\n'+remaining)
        else:self.when.setText('')
