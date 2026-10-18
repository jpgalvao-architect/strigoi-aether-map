# SPDX-License-Identifier: GPL-3.0-only
from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import QHeaderView, QVBoxLayout
from app.ui.localized_widgets import QCheckBox, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QWidget

from app.ui.icons import icon
from app.ui.widgets import button, label, page_header, row
from app.core.i18n import tr


class CatalogPage(QWidget):
    route_requested=Signal(str,str)
    def __init__(self, context):
        super().__init__()
        self.context = context
        self.identity = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 20, 26, 20)
        layout.addWidget(page_header("Coletas e camadas", "Escolha o que você quer ver no atlas e no overlay."))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar recurso…")
        self.category = QComboBox()
        self.subcategory = QComboBox()
        self.map_combo = QComboBox()
        self.rarity = QComboBox()
        for title, value in [("Raridade", ""), ("Comum", "common"), ("Incomum", "uncommon"), ("Raro", "rare"), ("Épico", "epic"), ("Não informada", "unknown")]:
            self.rarity.addItem(title, value)
        layout.addLayout(row(self.search, self.category, self.subcategory, self.map_combo, self.rarity))
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Ativo", "Recurso", "Categoria", "Subcategoria", "Raridade", "Pontos"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        layout.addWidget(self.table, 1)
        layout.addLayout(row(button("Habilitar todos", lambda: self.toggle_all(True)), button("Desabilitar todos", lambda: self.toggle_all(False))))
        self.route_button=button('Criar rota do recurso selecionado',self.create_route)
        self.route_button.setEnabled(False);layout.addWidget(self.route_button)
        self.table.itemSelectionChanged.connect(lambda:self.route_button.setEnabled(self.table.currentRow()>=0))
        layout.addWidget(button("Consultar catálogo e posições na fonte Global", self.open_global_catalog))
        layout.addWidget(label("Passe o mouse sobre um recurso para ver fonte e escopo. Zero pontos significa que não há coordenadas incorporadas; não significa ausência do recurso no jogo.", "subtitle", True))
        for combo in [self.category, self.subcategory, self.rarity]:
            combo.currentIndexChanged.connect(self.populate)
        self.map_combo.currentIndexChanged.connect(self.map_changed)
        self.search.textChanged.connect(self.populate)
        context.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        if self.identity is not self.context.dataset:
            self.identity = self.context.dataset
            for combo, items, default in [(self.category, self.identity.categories, "Todas as categorias"), (self.subcategory, self.identity.subcategories, "Subcategorias"), (self.map_combo, self.identity.maps, "Todos os mapas")]:
                combo.blockSignals(True)
                combo.clear()
                combo.addItem(default, "")
                for item in items:
                    combo.addItem(item.name.removesuffix(' • base compartilhada'), item.id)
                combo.blockSignals(False)
        self.map_combo.blockSignals(True)
        self.map_combo.setCurrentIndex(max(0, self.map_combo.findData(self.context.prefs.catalog_map_id)))
        self.map_combo.blockSignals(False)
        self.populate()

    def map_changed(self):
        self.context.prefs.catalog_map_id = self.map_combo.currentData() or ""
        self.context.save()

    def populate(self):
        dataset = self.context.dataset
        category = self.category.currentData()
        sub = self.subcategory.currentData()
        map_id = self.map_combo.currentData()
        resources = [r for r in dataset.resources if (not category or r.category == category) and (not sub or r.subcategory == sub) and (not self.rarity.currentData() or r.rarity == self.rarity.currentData()) and self.search.text().casefold() in (r.name+' '+tr(r.name)).casefold() and (not map_id or any(p.resource_id == r.id and p.map_id == map_id for p in dataset.all_points))]
        categories = {c.id: c.name for c in dataset.categories}
        subs = {c.id: c.name for c in dataset.subcategories}
        self.table.setRowCount(len(resources))
        for index, resource in enumerate(resources):
            checked = QCheckBox()
            checked.setChecked(resource.id not in self.context.prefs.disabled_resources)
            checked.setToolTip("Categoria desabilitada no atlas" if resource.category in self.context.prefs.disabled_categories else "Visível quando a categoria está habilitada")
            checked.toggled.connect(lambda value, key=resource.id: self.toggle(key, value))
            self.table.setCellWidget(index, 0, checked)
            values = [resource.name, categories[resource.category], subs[resource.subcategory], {"common":"Comum","uncommon":"Incomum","rare":"Raro","epic":"Épico","unknown":"Não informada"}[resource.rarity], str(sum(p.resource_id == resource.id and (not map_id or p.map_id == map_id) for p in dataset.all_points))]
            for column, value in enumerate(values, 1):
                cell = QTableWidgetItem(value)
                if column==1:cell.setData(Qt.UserRole,resource.id)
                if column==1:cell.setIcon(icon("cube" if resource.category=="cubes" else "gatherables"))
                cell.setToolTip(f"{resource.verification}\n{resource.notes}\n{resource.source}")
                self.table.setItem(index, column, cell)
            self.table.setRowHeight(index, 48)

    def toggle(self, key, enabled):
        values = self.context.prefs.disabled_resources
        values.discard(key) if enabled else values.add(key)
        self.context.save()

    def create_route(self):
        index=self.table.currentRow()
        if index<0:return
        resource=self.table.item(index,1).data(Qt.UserRole)
        maps=[p.map_id for p in self.context.dataset.all_points if p.resource_id==resource]
        preferred=self.map_combo.currentData() or self.context.prefs.map_id
        if maps:self.route_requested.emit(preferred if preferred in maps else maps[0],resource)

    def open_global_catalog(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl("https://aion2maps.com/gathering/"))

    def toggle_all(self, enabled):
        self.context.prefs.disabled_resources = set() if enabled else {r.id for r in self.context.dataset.resources}
        if enabled:
            self.context.prefs.disabled_categories.clear()
        self.context.save()
