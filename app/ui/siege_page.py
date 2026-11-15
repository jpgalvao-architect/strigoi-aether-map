# SPDX-License-Identifier: GPL-3.0-only
"""Siege Command workspace and controls shared with the expanded overlay."""
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QColorDialog, QFileDialog, QHBoxLayout, QInputDialog, QStackedWidget,
    QVBoxLayout,
)
from PySide6.QtGui import QColor

from app.core.i18n import tr
from app.modules.siege.models import COLORS, LAYERS, OFFICIAL, SECTORS, Coordinate, Preset, RingPosition
from app.ui.localized_widgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QLineEdit, QWidget
from app.ui.siege_map import SiegeMapView
from app.ui.widgets import button, card, label, page_header, row

ACTION_LABELS = {'regroup': 'Reagrupar', 'attack': 'Atacar', 'defend': 'Defender', 'retreat': 'Recuar'}


def choice(combo, current, entries):
    with QSignalBlocker(combo):
        combo.clear()
        for caption, value in entries:
            combo.addItem(caption, value)
        combo.setCurrentIndex(max(0, combo.findData(current)))


def update(widget, setter, value):
    with QSignalBlocker(widget):
        getattr(widget, setter)(value)


class SiegeCallControls(QWidget):
    sector_focused = Signal(str)
    notice = Signal(str)

    def __init__(self, service):
        super().__init__()
        self.service = service
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.sectors = {}
        sector_row = QHBoxLayout()
        self.sector_group = QButtonGroup(self)
        for sector, name in SECTORS.items():
            control = button(sector, lambda _checked=False, key=sector: self.change_sector(key))
            control.setCheckable(True)
            control.setStyleSheet('QPushButton:checked{background:#3b2d53;border-color:#bba9ee;color:#f4eaff;}')
            control.setToolTip(name)
            self.sector_group.addButton(control)
            sector_row.addWidget(control)
            self.sectors[sector] = control
        layout.addLayout(sector_row)
        self.objective = QComboBox()
        self.ring = QComboBox()
        self.action = QComboBox()
        form = QFormLayout()
        form.addRow('Ação', self.action)
        form.addRow('Reagrupamento', self.ring)
        form.addRow('Objetivo', self.objective)
        layout.addLayout(form)
        self.preview = label('', 'siegeCall', True)
        self.preview.setStyleSheet('font-size:17px;font-weight:700;color:#eee6ff;padding:10px;background:#2c2441;border-radius:6px;')
        layout.addWidget(self.preview)
        self.detail = label('', 'subtitle', True)
        layout.addWidget(self.detail)
        self.copy = button('Copiar call', self.copy_call, True)
        layout.addWidget(self.copy)
        layout.addStretch()
        choice(self.action, service.call.action, [(name, key) for key, name in ACTION_LABELS.items()])
        self.action.currentIndexChanged.connect(lambda: self.change(action=self.action.currentData()))
        self.objective.currentIndexChanged.connect(lambda: self.change(objective=self.objective.currentData()))
        self.ring.currentIndexChanged.connect(lambda: self.change(ring_id=self.ring.currentData()))
        service.changed.connect(self.refresh)
        self.refresh()

    def change(self, **changes):
        try:
            self.service.set_call(**changes)
        except (OSError, ValueError) as error:
            self.notice.emit(str(error))
            self.refresh()

    def change_sector(self, sector):
        try:
            self.service.select_sector(sector)
            self.sector_focused.emit(sector)
        except (OSError, ValueError) as error:
            self.notice.emit(str(error))
            self.refresh()

    def select_objective(self, number):
        objective = self.service.objectives[number]
        if objective.sector != self.service.call.sector:
            self.change(sector=objective.sector, objective=number, ring_id=None)
        else:
            self.change(objective=number)

    def select_ring(self, ring_id):
        ring = self.service.rings[ring_id]
        if not self.service.callsign(ring):
            self.notice.emit('Consulte o status e a origem deste anel no catálogo.')
            return
        if ring.sector != self.service.call.sector:
            self.change(sector=ring.sector, objective=None, ring_id=ring_id)
        else:
            self.change(ring_id=ring_id)

    def refresh(self):
        service = self.service
        call = service.call
        self.sectors[call.sector].setChecked(True)
        update(self.action, 'setCurrentIndex', self.action.findData(call.action))
        objectives = [(p.code, p.number) for p in service.objectives.values() if p.sector == call.sector]
        rings = sorted((r for r in service.rings.values() if r.sector == call.sector and service.callsign(r)),
                       key=lambda r: int(service.callsign(r)[1:]))
        choice(self.objective, call.objective, [('Selecionar ponto', None), *objectives])
        choice(self.ring, call.ring_id, [('Selecionar anel', None), *[(service.ring_label(r), r.ring_id) for r in rings]])
        text = service.call_text()
        self.preview.setText(text or 'Selecione um destino')
        objective = service.objectives.get(call.objective)
        note = 'Posição transcrita da referência visual; validação em jogo pendente.' if (
            objective and objective.status == 'reference'
        ) else SECTORS[call.sector]
        if not rings:
            note += '\n' + 'Nenhum anel numerado neste setor.'
        self.detail.setText(note)
        self.copy.setEnabled(bool(text))

    def copy_call(self):
        text = self.service.call_text(tr)
        if text:
            QApplication.clipboard().setText(text)
            self.notice.emit('Call copiada.')


class SiegeBoard(QWidget):
    """Map canvas, view controls and an import prompt for the local map."""
    import_requested = Signal()

    def __init__(self, context):
        super().__init__()
        self.view = SiegeMapView(context)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(8)
        toolbar = QHBoxLayout()
        toolbar.addWidget(label('Chaotic Lower Reshanta', 'eyebrow'), 1)
        for title, action in [('−', lambda: self.view.zoom(-1)), ('+', lambda: self.view.zoom(1)),
                              ('Ilhas', self.view.fit_islands), ('Mapa inteiro', self.view.fit_full)]:
            toolbar.addWidget(button(title, action))
        toolbar.addWidget(button('Importar mapa local', lambda: self.import_requested.emit()))
        box.addLayout(toolbar)
        self.stack = QStackedWidget()
        empty, content = card()
        content.addStretch()
        content.addWidget(label('Importe a base calibrada de Lower Reshanta', 'title', True))
        content.addWidget(label(
            'Use o PNG de 4096 × 4096 do quadro Abyss_Reshanta_A. Veja a preparação da imagem no guia do Siege Command.',
            'subtitle', True,
        ))
        content.addWidget(button('Importar mapa local', lambda: self.import_requested.emit(), True))
        content.addStretch()
        self.stack.addWidget(empty)
        self.stack.addWidget(self.view)
        box.addWidget(self.stack, 1)
        def refresh():
            self.stack.setCurrentIndex(1 if context.siege.definition else 0)
        context.siege.map_changed.connect(refresh)
        refresh()


class SiegePage(QWidget):
    def __init__(self, context, start_map_overlay, configure_shortcut):
        super().__init__()
        self.context = context
        self.service = context.siege
        self.configure_shortcut = configure_shortcut
        self.placement = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.addWidget(page_header('Siege Command', 'Prepare calls para Lower Reshanta e acompanhe o setor no jogo.'))
        self.summary = label('', 'subtitle', True)
        layout.addWidget(self.summary)
        body = QHBoxLayout()
        self.board = SiegeBoard(context)
        self.board.import_requested.connect(self.import_map)
        body.addWidget(self.board, 1)
        sidebar, side = card()
        sidebar.setFixedWidth(320)
        side.setContentsMargins(12, 12, 12, 12)
        self.section = QComboBox()
        self.section.addItems(['Call tática', 'Catálogo de anéis', 'Camadas e presets', 'Overlay de siege'])
        side.addWidget(self.section)
        self.sections = QStackedWidget()
        side.addWidget(self.sections, 1)
        self.section.currentIndexChanged.connect(self.change_section)
        self.controls = SiegeCallControls(self.service)
        self.controls.sector_focused.connect(self.board.view.focus_sector)
        self.controls.notice.connect(self.message)
        self.board.view.objective_selected.connect(self.controls.select_objective)
        self.board.view.ring_selected.connect(self.select_ring_on_map)
        self.board.view.coordinate_selected.connect(self.placement_chosen)
        self.sections.addWidget(self.controls)
        self.sections.addWidget(self.catalogue_page())
        self.sections.addWidget(self.preset_page())
        self.sections.addWidget(self.overlay_page(start_map_overlay))
        body.addWidget(sidebar)
        layout.addLayout(body, 1)
        self.feedback = label(self.service.warning, 'subtitle', True)
        layout.addWidget(self.feedback)
        self.service.changed.connect(self.refresh)
        self.refresh()

    def message(self, text):
        self.feedback.setText(text)

    def guard(self, callback, *args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except (OSError, ValueError) as error:
            self.message(str(error))
        return None

    def change_section(self, index):
        self.sections.setCurrentIndex(index)
        self.cancel_placement()

    def cancel_placement(self):
        self.placement = None
        self.board.view.pick_position(False)

    def import_map(self):
        name, _ = QFileDialog.getOpenFileName(self, tr('Importar mapa local'), '', 'PNG (*.png)')
        if name:
            def load():
                self.service.import_map(Path(name))
                self.board.view.fit_islands()
                self.message('Base cartográfica conferida e importada.')
            self.guard(load)

    def catalogue_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.ring_filter = QComboBox()
        for caption, value in [('Todos os anéis', ''), *[(s, s) for s in SECTORS], ('Trânsito', 'transit')]:
            self.ring_filter.addItem(caption, value)
        self.catalogue = QComboBox()
        self.catalogue.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.catalogue.setMinimumContentsLength(22)
        layout.addWidget(button('Importar catálogo local', self.import_catalogue))
        layout.addWidget(self.ring_filter)
        layout.addWidget(self.catalogue)
        self.ring_info = label('', 'subtitle', True)
        layout.addWidget(self.ring_info)
        self.x = self.coordinate_input()
        self.y = self.coordinate_input()
        self.source = QLineEdit()
        self.source.setMaxLength(420)
        self.source.setPlaceholderText('URL, print ou evidência in-game')
        self.verified = QCheckBox('Posição conferida na fonte')
        form = QFormLayout()
        form.addRow('X normalizado', self.x)
        form.addRow('Y normalizado', self.y)
        form.addRow('Fonte da posição', self.source)
        layout.addLayout(form)
        layout.addWidget(self.verified)
        self.pick_ring = button('Posicionar no mapa', self.start_ring_placement)
        self.save_ring = button('Salvar calibração local', self.save_calibration)
        self.reset_ring = button('Restaurar posição do anel', lambda: self.guard(
            self.service.reset_ring, self.catalogue.currentData()))
        self.freeze = button('Fixar novos callsigns', self.freeze_codes)
        layout.addWidget(self.pick_ring)
        layout.addWidget(self.save_ring)
        layout.addWidget(self.reset_ring)
        layout.addWidget(self.freeze)
        layout.addStretch()
        self.ring_filter.currentIndexChanged.connect(self.refresh_catalogue)
        self.catalogue.currentIndexChanged.connect(self.refresh_ring)
        return widget

    def import_catalogue(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Importar catálogo local'), '', 'JSON (*.json)')
        if path:
            def load():
                self.service.import_catalogue(Path(path))
                self.message('Catálogo local de anéis importado.')
            self.guard(load)

    @staticmethod
    def coordinate_input():
        field = QDoubleSpinBox()
        field.setDecimals(7)
        field.setRange(0, 1)
        field.setSingleStep(.0005)
        field.setKeyboardTracking(False)
        return field

    def refresh_catalogue(self):
        key = self.ring_filter.currentData()
        desired = self.catalogue.currentData()
        rings = [r for r in self.service.rings.values() if not key or r.sector == key or
                 (key == 'transit' and r.category == 'transit')]
        captions = []
        for ring in rings:
            position = self.service.position(ring)
            status = 'Pendente' if position is None else 'Verificado' if position.status == 'verified' else 'Provisório'
            captions.append((f'{self.service.ring_label(ring)} · {tr(status)}', ring.ring_id))
        choice(self.catalogue, desired, captions)
        self.refresh_ring()

    def refresh_ring(self):
        ring = self.service.rings.get(self.catalogue.currentData())
        if not ring:
            return
        local = self.service.state.local_rings.get(ring.ring_id)
        position = local or ring.position
        code = self.service.callsign(ring)
        state = 'Pendente de calibração' if position is None else 'Verificado' if position.status == 'verified' else 'Provisório'
        note = f'{ring.display_name}\n{ring.sector or tr("Trânsito")} · {tr(state)}'
        if local:
            note += '\n' + tr('Calibração local salva. Ative no preset personalizado.')
        self.ring_info.setText(note if code is None else f'{code}\n{note}')
        self.ring_info.setToolTip(position.source if position else ring.source)
        update(self.x, 'setValue', position.map_position.x if position else 0)
        update(self.y, 'setValue', position.map_position.y if position else 0)
        self.source.setText(position.source if position else '')
        self.source.setCursorPosition(0)
        self.verified.setChecked(bool(position and position.status == 'verified'))
        self.pick_ring.setEnabled(self.service.definition is not None)
        self.reset_ring.setEnabled(local is not None)
        self.freeze.setEnabled(ring.sector is not None)

    def select_ring_on_map(self, ring_id):
        ring = self.service.rings[ring_id]
        if self.section.currentIndex() == 1 or not self.service.callsign(ring):
            self.section.setCurrentIndex(1)
            self.ring_filter.setCurrentIndex(0)
            self.catalogue.setCurrentIndex(self.catalogue.findData(ring_id))
        else:
            self.controls.select_ring(ring_id)

    def start_ring_placement(self):
        self.placement = ('ring', self.catalogue.currentData())
        self.board.view.pick_position(True)
        self.message('Clique na posição conhecida. Use o botão direito para cancelar.')

    def placement_chosen(self, position):
        placement = self.placement
        self.cancel_placement()
        if position is None or placement is None:
            return
        kind, key = placement
        if kind == 'ring':
            self.catalogue.setCurrentIndex(self.catalogue.findData(key))
            self.x.setValue(position.x)
            self.y.setValue(position.y)
            self.message('Informe a fonte e salve a posição.')
        else:
            name, accepted = QInputDialog.getText(self, tr('Marcador local'), tr('Nome do marcador'))
            if accepted and name.strip():
                self.guard(self.service.add_marker, name.strip(), position)

    def save_calibration(self):
        def save():
            source = self.source.text().strip()
            if not source:
                raise ValueError(tr('Informe a fonte da posição.'))
            ring = self.service.rings[self.catalogue.currentData()]
            previous = self.service.position(ring)
            self.service.calibrate_ring(ring.ring_id, RingPosition(
                map_position=Coordinate(x=self.x.value(), y=self.y.value()), source=source,
                status='verified' if self.verified.isChecked() else 'provisional',
                altitude=previous.altitude if previous else None,
            ))
            self.message('Calibração local salva. Ative no preset personalizado.')
        self.guard(save)

    def freeze_codes(self):
        ring = self.service.rings.get(self.catalogue.currentData())
        if ring and ring.sector:
            count = self.guard(self.service.freeze_callsigns, ring.sector)
            if count is not None:
                self.message(f'{count} novos callsigns fixados em {ring.sector}.')

    def preset_page(self):
        widget = QWidget()
        box = QVBoxLayout(widget)
        box.setContentsMargins(0, 0, 0, 0)
        self.presets = QComboBox()
        self.presets.currentIndexChanged.connect(lambda: self.guard(self.service.select_preset, self.presets.currentData()))
        box.addWidget(self.presets)
        box.addLayout(row(button('Duplicar preset', self.duplicate_preset), button('Restaurar Global', self.restore_preset)))
        box.addLayout(row(button('Importar JSON', self.import_preset), button('Exportar JSON', self.export_preset)))
        self.layers = {}
        self.layer_color = QComboBox()
        for key, title in LAYERS.items():
            checkbox = QCheckBox(title)
            checkbox.toggled.connect(lambda checked, layer=key: self.change_layer(layer, checked))
            self.layers[key] = checkbox
            box.addWidget(checkbox)
            self.layer_color.addItem(title, key)
        self.local_calibration = QCheckBox('Aplicar calibrações locais')
        self.local_calibration.toggled.connect(lambda enabled: self.guard(
            self.service.edit_preset, use_local_calibration=enabled))
        box.addWidget(self.local_calibration)
        self.explore = QCheckBox('Mostrar exploração nesta tela')
        self.explore.toggled.connect(self.toggle_exploration)
        box.addWidget(self.explore)
        self.palette = button('Cor da camada', self.set_color)
        box.addLayout(row(self.layer_color, self.palette))
        self.marker_scale = QDoubleSpinBox()
        self.marker_scale.setRange(.65, 1.8)
        self.marker_scale.setSingleStep(.1)
        self.marker_scale.setSuffix('×')
        self.marker_scale.editingFinished.connect(
            lambda: self.guard(self.service.edit_preset, marker_scale=self.marker_scale.value())
            if self.service.preset.name != OFFICIAL else None)
        form = QFormLayout()
        form.addRow('Tamanho dos marcadores', self.marker_scale)
        box.addLayout(form)
        self.alias = button('Editar apelido do anel', self.edit_alias)
        self.marker = button('Adicionar marcador', self.start_marker)
        self.remove_marker = button('Remover marcador', self.delete_marker)
        box.addWidget(self.alias)
        box.addLayout(row(self.marker, self.remove_marker))
        box.addWidget(button('Importar locais de pets', self.import_pet_sites))
        box.addStretch()
        return widget

    def import_pet_sites(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Importar locais de pets'), '', 'JSON (*.json)')
        if path:
            def load():
                self.context.pets.farm.import_reshanta_sites(Path(path))
                self.context.pets.changed.emit()
                self.message('Locais de pets de Lower Reshanta importados.')
            self.guard(load)

    def duplicate_preset(self):
        name, accepted = QInputDialog.getText(self, tr('Duplicar preset'), tr('Nome do preset'))
        if accepted and name.strip():
            def duplicate():
                if any(name.strip() == preset.name for preset in self.service.state.presets):
                    raise ValueError(tr('Já existe um preset com este nome.'))
                self.service.save_preset(Preset.model_validate({**self.service.preset.model_dump(), 'name': name.strip()}))
            self.guard(duplicate)

    def restore_preset(self):
        self.guard(self.service.select_preset, OFFICIAL)

    def import_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Importar JSON'), '', 'JSON (*.json)')
        if path:
            self.guard(self.service.import_preset, Path(path))

    def export_preset(self):
        path, _ = QFileDialog.getSaveFileName(self, tr('Exportar JSON'), 'siege-preset.json', 'JSON (*.json)')
        if path:
            self.guard(self.service.export_preset, Path(path))

    def toggle_exploration(self, enabled):
        self.board.view.exploration = enabled
        self.board.view.refresh()

    def change_layer(self, layer, checked):
        layers = set(self.service.preset.layers)
        if checked:
            layers.add(layer)
        else:
            layers.discard(layer)
        self.guard(self.service.edit_preset, layers=layers)

    def set_color(self):
        layer = self.layer_color.currentData()
        colors = dict(self.service.preset.colors)
        selected = QColorDialog.getColor(QColor(colors.get(layer, COLORS[layer])), self, tr('Cor da camada'))
        if selected.isValid():
            colors[layer] = selected.name()
            self.guard(self.service.edit_preset, colors=colors)

    def edit_alias(self):
        rings = list(self.service.rings.values())
        captions = [self.service.ring_label(ring) for ring in rings]
        title, accepted = QInputDialog.getItem(self, tr('Editar apelido do anel'), tr('Anel'), captions, 0, False)
        if accepted:
            ring_id = rings[captions.index(title)].ring_id
            aliases = dict(self.service.preset.aliases)
            value, ok = QInputDialog.getText(self, tr('Editar apelido do anel'), tr('Apelido'),
                                            text=aliases.get(ring_id, ''))
            if ok:
                if value.strip():
                    aliases[ring_id] = value.strip()
                else:
                    aliases.pop(ring_id, None)
                self.guard(self.service.edit_preset, aliases=aliases)

    def start_marker(self):
        self.placement = ('marker', None)
        self.board.view.pick_position(True)
        self.message('Clique no mapa para adicionar o marcador.')

    def delete_marker(self):
        markers = self.service.preset.markers
        names = [f'{n}. {mark.name}' for n, mark in enumerate(markers, 1)]
        selected, accepted = QInputDialog.getItem(self, tr('Remover marcador'), tr('Marcador local'), names, 0, False)
        if accepted:
            index = names.index(selected)
            self.guard(self.service.edit_preset, markers=[mark for n, mark in enumerate(markers) if n != index])

    def overlay_page(self, start_map_overlay):
        widget = QWidget()
        box = QVBoxLayout(widget)
        box.setContentsMargins(0, 0, 0, 0)
        self.map_markers = QCheckBox('Mostrar marcadores de siege')
        self.map_markers.toggled.connect(lambda enabled: self.guard(self.service.update_overlay, map_markers=enabled))
        box.addWidget(self.map_markers)
        self.start_map_button = button('Ativar no mapa e minimapa', start_map_overlay, True)
        box.addWidget(self.start_map_button)
        box.addWidget(label('Veja as camadas do preset no minimapa e no mapa do jogo ao abrir com M.', 'subtitle', True))
        self.hud_visible = QCheckBox('Mostrar HUD compacto')
        self.hud_locked = QCheckBox('Clique através do HUD')
        self.hud_visible.toggled.connect(lambda visible: self.guard(self.service.update_overlay, visible=visible))
        self.hud_locked.toggled.connect(lambda locked: self.guard(self.service.update_overlay, locked=locked))
        box.addWidget(self.hud_visible)
        box.addWidget(self.hud_locked)
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(.25, 1)
        self.opacity.setSingleStep(.05)
        self.opacity.editingFinished.connect(lambda: self.guard(self.service.update_overlay, opacity=self.opacity.value()))
        self.hud_scale = QDoubleSpinBox()
        self.hud_scale.setRange(.75, 1.6)
        self.hud_scale.setSingleStep(.05)
        self.hud_scale.setSuffix('×')
        self.hud_scale.editingFinished.connect(lambda: self.guard(self.service.update_overlay, scale=self.hud_scale.value()))
        self.hud_key = QLineEdit()
        self.hud_key.setMaxLength(40)
        self.hud_key.setPlaceholderText('Ctrl+Alt+F9')
        form = QFormLayout()
        form.addRow('Opacidade', self.opacity)
        form.addRow('Escala do HUD', self.hud_scale)
        form.addRow('Atalho do HUD', self.hud_key)
        box.addLayout(form)
        box.addWidget(button('Salvar atalho do HUD', self.save_shortcut))
        box.addWidget(label('Use Ctrl ou Alt com F1–F12. Limpe o campo para desativar o atalho.', 'subtitle', True))
        box.addWidget(button('Restaurar posição do HUD', lambda: self.guard(self.service.update_overlay, position=None)))
        box.addWidget(label('Arraste pelo título com o HUD destravado. Volte ao jogo para ver os overlays.', 'subtitle', True))
        box.addStretch()
        return widget

    def save_shortcut(self):
        result = self.guard(self.configure_shortcut, self.hud_key.text().strip())
        if result:
            self.message(result)

    def refresh(self):
        service = self.service
        count = sum(service.position(r) is not None for r in service.rings.values())
        self.summary.setText(f'12 objetivos de referência · {count}/{len(service.rings)} anéis posicionados')
        self.refresh_catalogue()
        choice(self.presets, service.preset.name, [(OFFICIAL, OFFICIAL), *[(p.name, p.name) for p in service.state.presets]])
        custom = service.preset.name != OFFICIAL
        for key, checkbox in self.layers.items():
            update(checkbox, 'setChecked', key in service.preset.layers)
            checkbox.setEnabled(custom)
        update(self.local_calibration, 'setChecked', service.preset.use_local_calibration)
        self.local_calibration.setEnabled(custom)
        self.palette.setEnabled(custom)
        self.marker_scale.setEnabled(custom)
        update(self.marker_scale, 'setValue', service.preset.marker_scale)
        self.alias.setEnabled(custom)
        self.marker.setEnabled(custom and service.definition is not None)
        self.remove_marker.setEnabled(custom and bool(service.preset.markers))
        prefs = service.state.overlay
        self.start_map_button.setEnabled(service.definition is not None)
        update(self.map_markers, 'setChecked', prefs.map_markers)
        update(self.hud_visible, 'setChecked', prefs.visible)
        update(self.hud_locked, 'setChecked', prefs.locked)
        update(self.opacity, 'setValue', prefs.opacity)
        update(self.hud_scale, 'setValue', prefs.scale)
        self.hud_key.setText(prefs.hud_shortcut)
