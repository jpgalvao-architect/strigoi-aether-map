# SPDX-License-Identifier: GPL-3.0-only
"""Siege Command workspace and controls shared with the expanded overlay."""
import json
from pathlib import Path
import sys

from PySide6.QtCore import QProcess, Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QColorDialog, QFileDialog, QHBoxLayout, QInputDialog, QScrollArea, QStackedWidget,
    QVBoxLayout,
)
from PySide6.QtGui import QColor

from app.core.i18n import Verbatim, tr, validation_text
from app.modules.siege.live_sync import LiveSync
from app.modules.siege.models import COLORS, LAYERS, SECTORS, Coordinate, RingPosition
from app.ui.localized_widgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QLineEdit, QMessageBox, QWidget,
)
from app.ui.live_sync_panel import LiveSyncPanel
from app.ui.siege_editor import TacticalEditor, choice, update
from app.ui.siege_map import SiegeMapView
from app.ui.widgets import button, card, label, page_header, row

ACTION_LABELS = {'regroup': 'Reagrupar', 'attack': 'Atacar', 'defend': 'Defender', 'retreat': 'Recuar'}


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

    def retranslate(self):
        super().retranslate()
        self.refresh()

    def refresh(self):
        service = self.service
        call = service.call
        self.sectors[call.sector].setChecked(True)
        update(self.action, 'setCurrentIndex', self.action.findData(call.action))
        objectives = [(p.code, p.number) for p in service.objectives.values() if p.sector == call.sector]
        rings = sorted((r for r in service.rings.values() if r.sector == call.sector and service.callsign(r)),
                       key=lambda r: int(service.callsign(r)[1:]))
        choice(self.objective, call.objective, [('Selecionar ponto', None), *objectives])
        choice(self.ring, call.ring_id, [('Selecionar anel', None), *[(Verbatim(service.ring_label(r)), r.ring_id) for r in rings]])
        text = service.call_text(tr)
        self.preview.setText(Verbatim(text) if text else 'Selecione um destino')
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
    """Map canvas and actions for preparing the calibrated base."""
    import_requested = Signal()
    download_requested = Signal()

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
        content.addWidget(label('Mapa de Lower Reshanta', 'title', True))
        content.addWidget(label(
            'Baixe o mapa uma vez para usá-lo no Siege Command e no Atlas, inclusive offline.',
            'subtitle', True,
        ))
        self.download_button = button('Baixar mapa', lambda: self.download_requested.emit(), True)
        content.addWidget(self.download_button)
        content.addStretch()
        self.stack.addWidget(empty)
        self.stack.addWidget(self.view)
        box.addWidget(self.stack, 1)
        def refresh():
            self.stack.setCurrentIndex(1 if context.siege.definition else 0)
        context.siege.map_changed.connect(refresh)
        refresh()


class SiegePage(QWidget):
    def __init__(self, context, toggle_reshanta, setup_minimap, minimap_ready):
        super().__init__()
        self.context = context
        self.service = context.siege
        self.minimap_ready = minimap_ready
        self.ring_placement = None
        self._last_shared = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.addWidget(page_header('Siege Command', 'Edite marcações de Lower Reshanta e veja o plano no mapa do jogo.'))
        self.summary = label('', 'subtitle', True)
        layout.addWidget(self.summary)
        body = QHBoxLayout()
        self.board = SiegeBoard(context)
        self.board.import_requested.connect(self.import_map)
        self.board.download_requested.connect(self.download_map)
        self.map_downloader = QProcess(self)
        self.map_downloader.finished.connect(self.finish_map_download)
        self.map_downloader.errorOccurred.connect(self.map_download_error)
        body.addWidget(self.board, 1)
        sidebar, side = card()
        sidebar.setFixedWidth(320)
        side.setContentsMargins(12, 12, 12, 12)
        self.section = QComboBox()
        self.overlay_toggle = QCheckBox('Overlay de Reshanta')
        self.overlay_toggle.toggled.connect(toggle_reshanta)
        side.addWidget(self.overlay_toggle)
        side.addWidget(label('Mostra os marcadores táticos no minimapa e no mapa do jogo (M).', 'subtitle', True))
        self.setup_minimap = button('Selecionar minimapa', setup_minimap)
        side.addWidget(self.setup_minimap)
        context.changed.connect(self.refresh_minimap_button)
        for caption, key in (
            ('Editor tático', 'editor'), ('Catálogo de anéis', 'rings'),
            ('Camadas e presets', 'presets'), ('Live Sync', 'live'),
        ):
            self.section.addItem(caption, key)
        side.addWidget(self.section)
        self.sections = QStackedWidget()
        side.addWidget(self.sections, 1)
        self.editor = TacticalEditor(self)
        self.add_section(self.editor)
        self.add_section(self.catalogue_page())
        self.add_section(self.preset_page())
        self.live_sync = LiveSync(self.service, context.directory, parent=self)
        self.live_panel = LiveSyncPanel(self.live_sync, quick_tools=self.editor.quick_tools)
        self.add_section(self.live_panel)
        self.live_sync.changed.connect(self.refresh_live_preview)
        self.service.session_changed.connect(self.refresh_live_preview)
        self.board.view.ring_selected.connect(self.select_ring_on_map)
        self.board.view.coordinate_selected.connect(self.placement_chosen)
        self.board.view.editing_cancelled.connect(self.cancel_editing)
        self.section.currentIndexChanged.connect(self.change_section)
        body.addWidget(sidebar)
        layout.addLayout(body, 1)
        self.feedback = label(self.service.warning, 'subtitle', True)
        layout.addWidget(self.feedback)
        self.service.changed.connect(self.refresh)
        self.refresh()
        self.refresh_live_preview()

    def message(self, text):
        self.feedback.setText(text)

    def guard(self, callback, *args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except (OSError, ValueError) as error:
            self.message(validation_text(error))
        return None

    def show_editor(self):
        self.section.setCurrentIndex(self.section.findData('editor'))

    def add_section(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(widget)
        self.sections.addWidget(scroll)

    def change_section(self, index):
        self.cancel_ring_placement()
        self.sections.setCurrentIndex(index)
        self.refresh_live_preview()

    def refresh_live_preview(self):
        view = self.board.view
        section = self.section.currentData()
        mode = self.live_sync.mode
        show = section == 'live' and mode == 'player'
        shared = self.service.session_preset if show else None
        self.editor.set_active(section == 'editor' or (section == 'live' and mode == 'host'))
        if view.session_preview != show or self._last_shared is not shared:
            view.session_preview = show
            self._last_shared = shared
            view.refresh()

    def cancel_editing(self):
        if self.ring_placement is not None:
            self.cancel_ring_placement()
        else:
            self.editor.cancel()

    def cancel_ring_placement(self):
        if self.ring_placement is not None:
            self.ring_placement = None
            self.board.view.pick_position(False)
            self.message('')

    def import_map(self):
        name, _ = QFileDialog.getOpenFileName(self, tr('Importar mapa local'), '', 'PNG (*.png)')
        if name:
            def load():
                self.service.import_map(Path(name))
                self.board.view.fit_islands()
                self.message('Base cartográfica conferida e importada.')
            self.guard(load)

    def download_map(self):
        if self.map_downloader.state() != QProcess.NotRunning:
            return
        self.board.download_button.setEnabled(False)
        self.message('Preparando o mapa de Lower Reshanta…')
        args = [] if getattr(sys, 'frozen', False) else [str(Path(__file__).resolve().parents[2] / 'launcher.py')]
        self.map_downloader.start(sys.executable, [*args, '--prepare-reshanta-map', str(self.context.directory)])

    def finish_map_download(self, exit_code, status):
        self.board.download_button.setEnabled(True)
        if status == QProcess.NormalExit and exit_code == 0 and self.service.refresh_map():
            self.board.view.fit_islands()
            self.message('Mapa pronto no Siege Command e no Atlas.')
        else:
            self.map_download_error()

    def map_download_error(self, *_):
        self.board.download_button.setEnabled(True)
        self.message('O download do mapa está indisponível. Confira a conexão e tente novamente.')

    def shutdown(self):
        self.live_sync.shutdown()
        if self.map_downloader.state() != QProcess.NotRunning:
            self.map_downloader.blockSignals(True)
            self.map_downloader.kill()
            self.map_downloader.waitForFinished(1500)

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
        self.catalogue_notice = label('', 'subtitle', True)
        layout.addWidget(self.catalogue_notice)
        layout.addWidget(button('Copiar diagnóstico do catálogo', self.copy_catalogue_diagnostics))
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

    def copy_catalogue_diagnostics(self):
        report = json.dumps(self.service.catalogue_diagnostics(), ensure_ascii=False, indent=2)
        QApplication.clipboard().setText(report)
        self.message('Diagnóstico do catálogo copiado.')

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

    def retranslate(self):
        super().retranslate()
        self.refresh()

    def refresh_catalogue(self):
        key = self.ring_filter.currentData()
        desired = self.catalogue.currentData()
        rings = [r for r in self.service.rings.values() if not key or r.sector == key or
                 (key == 'transit' and r.category == 'transit')]
        captions = []
        for ring in rings:
            position = self.service.position(ring)
            status = 'Pendente' if position is None else 'Verificado' if position.status == 'verified' else 'Provisório'
            captions.append((Verbatim(f'{self.service.ring_label(ring)} · {tr(status)}'), ring.ring_id))
        choice(self.catalogue, desired, captions)
        self.refresh_ring()

    def refresh_ring(self):
        ring = self.service.rings.get(self.catalogue.currentData())
        if not ring:
            return
        local = self.service.local_position(ring.ring_id)
        position = local or ring.position
        code = self.service.ring_code(ring)
        state = 'Pendente de calibração' if position is None else 'Verificado' if position.status == 'verified' else 'Provisório'
        note = f'{ring.display_name}\n{ring.sector or tr("Trânsito")} · {tr(state)}'
        if local:
            note += '\n' + tr('Calibração local salva. Ative no preset personalizado.')
        self.ring_info.setText(Verbatim(note if code is None else f'{code}\n{note}'))
        self.ring_info.setToolTip(Verbatim(position.source if position else ring.source))
        update(self.x, 'setValue', position.map_position.x if position else 0)
        update(self.y, 'setValue', position.map_position.y if position else 0)
        self.source.setText(position.source if position else '')
        self.source.setCursorPosition(0)
        self.verified.setChecked(bool(position and position.status == 'verified'))
        self.pick_ring.setEnabled(self.service.definition is not None)
        self.reset_ring.setEnabled(local is not None)
        self.freeze.setEnabled(ring.sector is not None)

    def select_ring_on_map(self, ring_id):
        if self.editor.active:
            self.editor.select(f'ring:{ring_id}')
            return
        self.section.setCurrentIndex(self.section.findData('rings'))
        self.ring_filter.setCurrentIndex(0)
        self.catalogue.setCurrentIndex(self.catalogue.findData(ring_id))

    def start_ring_placement(self):
        ring_id = self.catalogue.currentData()
        if ring_id is None:
            return
        self.ring_placement = ring_id
        self.board.view.pick_position(True)
        self.message('Clique na posição conhecida. Use o botão direito para cancelar.')

    def placement_chosen(self, position):
        if self.ring_placement is not None:
            key = self.ring_placement
            self.cancel_ring_placement()
            self.catalogue.setCurrentIndex(self.catalogue.findData(key))
            self.x.setValue(position.x)
            self.y.setValue(position.y)
            self.message('Informe a fonte e salve a posição.')
        elif self.editor.tool == 'pin' and self.editor.map_ready:
            self.editor.place_pin(position)

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
        box.addLayout(row(button('Novo preset', self.create_preset), button('Duplicar preset', self.duplicate_preset)))
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
            lambda: self.guard(self.service.edit_preset, marker_scale=self.marker_scale.value()))
        form = QFormLayout()
        form.addRow('Tamanho dos marcadores', self.marker_scale)
        box.addLayout(form)
        self.alias = button('Editar apelido do anel', self.edit_alias)
        box.addWidget(self.alias)
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

    def create_preset(self):
        name, accepted = QInputDialog.getText(self, tr('Novo preset'), tr('Nome do preset'))
        if accepted and name.strip():
            self.guard(self.service.create_preset, name.strip())

    def duplicate_preset(self):
        name, accepted = QInputDialog.getText(self, tr('Duplicar preset'), tr('Nome do preset'))
        if accepted and name.strip():
            preset = self.service.preset.model_copy(update={'name': name.strip()})
            self.guard(self.service.save_preset, preset, replace=False)

    def restore_preset(self):
        reply = QMessageBox.question(
            self, tr('Restaurar marcações padrão'),
            tr('Restaurar P1–P12 no preset atual? As edições desses 12 pins serão substituídas. Os demais pins serão mantidos.'),
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel,
        )
        if reply == QMessageBox.Yes:
            self.guard(self.service.restore_standard_markers)

    def import_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Importar marcações (.json)'), '', 'JSON (*.json)')
        if path:
            self.guard(self.import_markers, Path(path))

    def import_markers(self, path):
        preset = self.service.read_preset(path)
        dialog = QMessageBox(self)
        dialog.setWindowTitle(tr('Importar marcações (.json)'))
        dialog.setTextFormat(Qt.PlainText)
        dialog.setText(tr('Importe como novo ou substitua as marcações, as formas e as opções do preset atual.'))
        dialog.setInformativeText(f"{tr('Preset atual')} · {self.service.preset.name}")
        new = dialog.addButton(tr('Importar como novo'), QMessageBox.AcceptRole)
        overwrite = dialog.addButton(tr('Substituir preset atual'), QMessageBox.DestructiveRole)
        dialog.addButton(QMessageBox.Cancel)
        dialog.setDefaultButton(new)
        dialog.exec()
        if dialog.clickedButton() not in (new, overwrite):
            return
        self.service.accept_preset(preset, replace=dialog.clickedButton() is overwrite)
        self.show_editor()
        self.editor.select_first()
        if preset.ring_catalogue is None:
            self.message('Preset antigo importado. Confira as posições dos anéis no catálogo.')
        elif any(self.service.position(ring) is None for ring in self.service.rings.values()):
            self.message('Marcações importadas. O preset inclui anéis com posição pendente.')
        else:
            self.message('Marcações importadas.')

    def export_preset(self):
        path, _ = QFileDialog.getSaveFileName(self, tr('Exportar marcações (.json)'), 'siege-preset.json', 'JSON (*.json)')
        if path:
            path = Path(path)
            if not path.suffix:
                path = path.with_suffix('.json')
            self.guard(self.service.export_preset, path)

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
        ring = self.editor.selected_ring() or next(iter(self.service.rings.values()), None)
        if ring:
            self.show_editor()
            self.editor.select(f'ring:{ring.ring_id}')
            self.editor.items.showPopup()

    def refresh(self):
        service = self.service
        count = sum(service.position(r) is not None for r in service.rings.values())
        self.summary.setText(f'{len(service.preset.markers)} pins · {count}/{len(service.rings)} anéis posicionados')
        notice = service.catalogue_warning or ('O catálogo contém anéis sem posição confirmada.' if
                                                count < len(service.rings) else '')
        self.catalogue_notice.setText(notice)
        self.catalogue_notice.setVisible(bool(notice))
        self.refresh_catalogue()
        entries = [(Verbatim(p.name), p.name) for p in service.state.presets]
        choice(self.presets, service.preset.name, entries)
        self.editor.refresh()
        for key, checkbox in self.layers.items():
            update(checkbox, 'setChecked', key in service.preset.layers)
        update(self.local_calibration, 'setChecked', service.preset.use_local_calibration)
        update(self.marker_scale, 'setValue', service.preset.marker_scale)
        update(self.overlay_toggle, 'setChecked', service.state.overlay.map_markers)
        self.refresh_minimap_button()

    def refresh_minimap_button(self):
        self.setup_minimap.setVisible(self.service.state.overlay.map_markers
                                     and self.service.definition is not None
                                     and not self.minimap_ready())
