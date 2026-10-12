# SPDX-License-Identifier: GPL-3.0-only
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout
from app.ui.localized_widgets import QCheckBox, QComboBox, QLineEdit, QWidget

from app.modules.atlas.view import AtlasView
from app.modules.gatherables.service import FilterQuery, filter_points
from app.ui.widgets import button, card, label, page_header, row


class AtlasPage(QWidget):
    def __init__(self, context, cubes_only=False):
        super().__init__()
        self.context = context
        self.cubes_only = cubes_only
        self.selected = None
        self.dataset_identity = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 20, 26, 20)
        layout.addWidget(page_header("Cubos ocultos" if cubes_only else "Atlas de exploração", "Locais possíveis de cubos. Explore a área e registre suas visitas." if cubes_only else "Escolha seu destino. Trace sua própria jornada."))
        self.origin = label("", "subtitle", True)
        layout.addWidget(self.origin)
        self.maps = QComboBox()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar recurso, ponto ou nota…")
        self.search.setClearButtonEnabled(True)
        self.rarity = QComboBox()
        self.resource = QComboBox()
        for title, value in [("Todas as raridades", ""), ("Comum", "common"), ("Incomum", "uncommon"), ("Raro", "rare"), ("Épico", "epic"), ("Não informada", "unknown")]:
            self.rarity.addItem(title, value)
        layout.addLayout(row(self.maps, self.resource, self.search, self.rarity))
        body = QHBoxLayout()
        layout.addLayout(body, 1)
        self.view = AtlasView()
        body.addWidget(self.view, 1)
        side, side_layout = card()
        side.setFixedWidth(240)
        body.addWidget(side)
        side_layout.addWidget(label("CAMADAS DO ATLAS", "eyebrow"))
        self.category_box = QWidget()
        self.category_layout = QVBoxLayout(self.category_box)
        self.category_layout.setContentsMargins(0, 0, 0, 0)
        category_scroll = QScrollArea()
        category_scroll.setWidgetResizable(True)
        category_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        category_scroll.setMaximumHeight(250)
        category_scroll.setWidget(self.category_box)
        side_layout.addWidget(category_scroll)
        self.hide = QCheckBox("Ocultar visitados")
        self.hide.toggled.connect(self.hide_changed)
        side_layout.addWidget(self.hide)
        self.count = label("", "subtitle")
        side_layout.addWidget(self.count)
        side_layout.addSpacing(12)
        side_layout.addWidget(label("CADERNO DE CAMPO", "eyebrow"))
        self.details_toggle=QCheckBox('Ver origem e coordenadas')
        self.details_toggle.setEnabled(False)
        self.details_toggle.toggled.connect(self.refresh_detail)
        self.detail = label("Clique em um marcador para ver notas, origem e coordenadas.", "subtitle", True)
        side_layout.addWidget(self.detail)
        side_layout.addWidget(self.details_toggle)
        self.visit = button("Marcar como visitado", self.toggle_visit)
        self.visit.setEnabled(False)
        side_layout.addWidget(self.visit)
        side_layout.addStretch()
        side_layout.addWidget(label("Role para aproximar\nArraste para explorar", "subtitle", True))
        layout.addLayout(row(button("−", lambda: self.view.zoom(-1)), button("+", lambda: self.view.zoom(1)), button("Enquadrar mapa", self.view.fit_map)))
        layout.addWidget(button("Consultar mapa Global na fonte externa", self.open_global_map))
        self.view.point_selected.connect(self.select_point)
        self.maps.currentIndexChanged.connect(self.map_changed)
        self.search.textChanged.connect(self.refresh_points)
        self.rarity.currentIndexChanged.connect(self.refresh_points)
        self.resource.currentIndexChanged.connect(self.refresh_points)
        context.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        dataset = self.context.dataset
        if self.dataset_identity is not dataset:
            self.dataset_identity = dataset
            self.maps.blockSignals(True)
            self.maps.clear()
            for definition in dataset.maps:
                self.maps.addItem(definition.name.removesuffix(' • base compartilhada'), definition.id)
            self.maps.blockSignals(False)
            self.resource.blockSignals(True)
            self.resource.clear()
            self.resource.addItem("Todos os recursos", "")
            for resource in sorted(dataset.resources,key=lambda r:r.name):
                if self.cubes_only and resource.id not in {p.resource_id for p in dataset.cubes}:
                    continue
                self.resource.addItem(resource.name,resource.id)
            self.resource.blockSignals(False)
            while self.category_layout.count():
                item = self.category_layout.takeAt(0)
                item.widget().deleteLater()
            self.checks = {}
            self.resource_checks = {}
            cube_categories = {r.category for r in dataset.resources if any(p.resource_id == r.id for p in dataset.cubes)}
            resources_with_points = {p.resource_id for p in dataset.all_points}
            mapped_categories = {r.category for r in dataset.resources if r.id in resources_with_points}
            for category in dataset.categories:
                if category.id not in mapped_categories:
                    continue
                if self.cubes_only and category.id not in cube_categories:
                    continue
                checkbox = QCheckBox(f"●  {category.name}")
                checkbox.setStyleSheet(f"color: {category.color};")
                checkbox.toggled.connect(lambda checked, key=category.id: self.category_changed(key, checked))
                self.checks[category.id] = checkbox
                self.category_layout.addWidget(checkbox)
            if self.cubes_only:
                for resource in dataset.resources:
                    if resource.id != 'cube-spawns':
                        continue
                    checkbox = QCheckBox('Posições possíveis')
                    checkbox.toggled.connect(lambda checked, key=resource.id: self.resource_changed(key, checked))
                    self.resource_checks[resource.id] = checkbox
                    self.category_layout.addWidget(checkbox)
            self.view.map = None
            self.selected = None
            self.visit.setEnabled(False)
        self.maps.blockSignals(True)
        self.maps.setCurrentIndex(self.maps.findData(self.context.prefs.map_id))
        self.maps.blockSignals(False)
        for key, checkbox in self.checks.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(key not in self.context.prefs.disabled_categories)
            checkbox.blockSignals(False)
        self.hide.blockSignals(True)
        for key, checkbox in self.resource_checks.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(key not in self.context.prefs.disabled_resources)
            checkbox.blockSignals(False)
        self.hide.setChecked(self.context.prefs.hide_visited)
        self.hide.blockSignals(False)
        self.refresh_points()

    def category_changed(self, key, checked):
        disabled = self.context.prefs.disabled_categories
        disabled.discard(key) if checked else disabled.add(key)
        self.context.save()

    def hide_changed(self, checked):
        self.context.prefs.hide_visited = checked
        self.context.save()

    def resource_changed(self, key, checked):
        disabled = self.context.prefs.disabled_resources
        disabled.discard(key) if checked else disabled.add(key)
        self.context.save()

    def map_changed(self):
        if self.maps.currentData():
            self.context.prefs.map_id = self.maps.currentData()
            self.selected = None
            self.visit.setEnabled(False)
            self.context.save()

    def refresh_points(self):
        definition = next(m for m in self.context.dataset.maps if m.id == self.context.prefs.map_id)
        self.origin.hide()
        self.origin.setToolTip(definition.source)
        try:
            if self.view.map is not definition:
                self.view.set_map(definition)
            points = filter_points(self.context.dataset, self.context.prefs, FilterQuery(map_id=definition.id, resource_id=self.resource.currentData() or "", search=self.search.text(), rarity=self.rarity.currentData() or "", cubes_only=self.cubes_only))
            self.view.set_points(self.context.dataset, self.context.prefs, points)
            self.count.setText(f"{len(points)} pontos visíveis")
        except (OSError, ValueError) as exc:
            self.count.setText(f"Mapa indisponível: {exc}")

    def select_point(self, point):
        self.selected = point
        self.details_toggle.setEnabled(True)
        text=point.name
        if self.details_toggle.isChecked():
            text+=f"\n\n{point.notes}\n\nx {point.x:.3f} · y {point.y:.3f}\n\nOrigem: {point.source}"
            if hasattr(point,'route_hint'):text+=f"\n\n{point.route_hint}"
        elif point.resource_id=='cube-spawns':
            height=next((piece.strip()+'.' for piece in point.notes.split('.') if 'altura mediana' in piece),'')
            text+='\n\nLocal possível de aparecimento.'+('\n'+height if height else '')
        else:
            text+='\n\nMarque sua visita para acompanhar a exploração.'
        self.detail.setText(text)
        self.visit.setEnabled(True)
        self.visit.setText("Desmarcar visita" if point.id in self.context.prefs.visited else "Marcar como visitado")

    def refresh_detail(self):
        if self.selected:self.select_point(self.selected)

    def toggle_visit(self):
        if self.selected:
            visited = self.context.prefs.visited
            visited.discard(self.selected.id) if self.selected.id in visited else visited.add(self.selected.id)
            self.context.save()
            self.select_point(self.selected)

    def open_global_map(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl("https://aion2maps.com/"))
