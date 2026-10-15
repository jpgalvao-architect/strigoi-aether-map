# SPDX-License-Identifier: GPL-3.0-only
from datetime import UTC, datetime

from PySide6.QtCore import QTimer, Qt
from app.ui.mascot import MascotWidget, MASCOT_PATH
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from app.ui.localized_widgets import QFrame, QWidget

from app.infrastructure.storage import PACKAGE
from app.modules.events.service import countdown, display_time, occurrences
from app.modules.gatherables.service import FilterQuery, filter_points
from app.ui.widgets import button, card, label, page_header, row
from app.ui.icons import icon,event_icon


class Dashboard(QWidget):
    def __init__(self, context, overlay, navigate):
        super().__init__()
        self.context = context
        self.overlay = overlay
        self.navigate = navigate
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 20)
        layout.setSpacing(18)
        header = QHBoxLayout()
        header.addWidget(page_header("Vamos explorar?", "Seu mapa, suas descobertas e os próximos eventos."), 1)
        layout.addLayout(header)
        hero = QFrame()
        hero.setObjectName("hero")
        hero.setMinimumHeight(170)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(26, 14, 18, 14)
        hero_copy = QVBoxLayout()
        hero_copy.setSpacing(12)
        hero_copy.addWidget(label("SEU COMPANION EM ATRÉIA", "eyebrow"))
        headline = label("Explorar. Jogar. Descobrir.")
        headline.setStyleSheet("font-size: 23px; font-weight: 600; color: #eeedf8;")
        hero_copy.addWidget(headline)
        hero_copy.addWidget(label("Mapas, combate e descobertas. Tudo ao seu alcance.", "subtitle", True))
        hero_copy.addLayout(row(button("Explorar o atlas  →", lambda: navigate(1), True), button("Encontrar cubos", lambda: navigate(3))))
        hero_layout.addLayout(hero_copy, 1)
        from app.ui.identity import emblem_icon
        mascot = label(''); mascot.setPixmap(emblem_icon().pixmap(120,120))
        mascot.setFixedSize(130,130)
        hero_layout.addWidget(mascot)
        layout.addWidget(hero)
        statistics = QHBoxLayout()
        self.stat_labels = []
        for caption in ["PONTOS NO ATLAS", "ITENS NO CATÁLOGO", "CUBOS VISITADOS"]:
            frame, inner = card()
            inner.addWidget(label(caption, "eyebrow"))
            number = label("", "number")
            inner.addWidget(number)
            self.stat_labels.append(number)
            statistics.addWidget(frame)
        layout.addLayout(statistics)
        lower = QHBoxLayout()
        lower.setSpacing(18)
        events_frame, events_layout = card()
        events_layout.addWidget(label("NO SEU RADAR", "eyebrow"))
        self.event_labels = []
        self.event_icons = []
        for _ in range(3):
            name = label("", wrap=True)
            clock = label("", "subtitle")
            line=QHBoxLayout()
            picture=label('');picture.setFixedSize(34,34)
            line.addWidget(picture)
            text=QVBoxLayout();text.addWidget(name);text.addWidget(clock)
            line.addLayout(text,1);events_layout.addLayout(line)
            self.event_icons.append(picture)
            self.event_labels.append((name, clock))
        events_layout.addStretch()
        events_layout.addWidget(button("Ver agenda completa  →", lambda: navigate(4)))
        lower.addWidget(events_frame, 3)
        status_frame, status_layout = card()
        status_layout.addWidget(label("SUA EXPLORAÇÃO", "eyebrow"))
        self.provider = label("", "subtitle", True)
        self.overlay_label = label("", "subtitle", True)
        self.filters = label("", "subtitle", True)
        status_layout.addWidget(self.provider)
        status_layout.addWidget(self.overlay_label)
        status_layout.addWidget(self.filters)
        status_layout.addStretch()
        status_layout.addWidget(button("Abrir overlay", lambda: navigate(6)))
        lower.addWidget(status_frame, 2)
        layout.addLayout(lower, 1)
        context.changed.connect(self.refresh)
        context.events_changed.connect(self.refresh)
        overlay.status_changed.connect(self.refresh)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def refresh(self):
        dataset = self.context.dataset
        prefs = self.context.prefs
        self.stat_labels[0].setText(str(len(filter_points(dataset, prefs, FilterQuery()))))
        self.stat_labels[1].setText(f"{len(dataset.resources):02}")
        sites = [c for c in dataset.cubes if c.resource_id=='cube-spawns']
        if sites:
            visited = sum(c.id in prefs.visited for c in sites)
            historical = sum(c.id in prefs.visited for c in dataset.cubes if c.resource_id!='cube-spawns')
            self.stat_labels[2].setText(f"{visited} / {len(sites)}")
            self.stat_labels[2].setToolTip(f'Posições possíveis visitadas. {historical} visitas históricas preservadas na camada antiga.')
        else:
            self.stat_labels[2].setText(f"{sum(c.id in prefs.visited for c in dataset.cubes):02} / {len(dataset.cubes):02}")
        now = datetime.now(UTC)
        items = []
        seen = set()
        for occurrence in occurrences(self.context.feed.events, now):
            if occurrence.event.id not in seen:
                items.append(occurrence)
                seen.add(occurrence.event.id)
            if len(items) == 3:
                break
        for index, (name, clock) in enumerate(self.event_labels):
            if index < len(items):
                item = items[index]
                self.event_icons[index].setPixmap(icon(event_icon(item.event)).pixmap(30,30))
                name.setText(f"{item.event.name}   ·   {item.event.region}")
                clock.setText(f"{display_time(item.starts_at, prefs.timezone)}   /   {countdown(item.starts_at, now)}")
            else:
                self.event_icons[index].clear()
                name.setText("Nenhum evento agendado" if index == 0 else "")
                clock.clear()
        self.provider.setText("Visitas salvas neste computador")
        self.overlay_label.setText(f"Overlay\n{self.overlay.status}")
        mapped = {p.resource_id for p in dataset.all_points}
        categories = {r.category for r in dataset.resources if r.id in mapped}
        active = len(categories-prefs.disabled_categories)
        self.filters.setText(f"Camadas no atlas\n{active} de {len(categories)} habilitadas")
