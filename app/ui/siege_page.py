# SPDX-License-Identifier: GPL-3.0-only
"""Siege Command workspace and controls shared with the expanded overlay."""
from pathlib import Path
import sys

from PySide6.QtCore import QProcess, QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QColorDialog, QFileDialog, QHBoxLayout, QInputDialog, QStackedWidget,
    QVBoxLayout,
)
from PySide6.QtGui import QColor

from app.core.i18n import Verbatim, tr, validation_text
from app.modules.siege.drawing import drawing_color
from app.modules.siege.live_sync import LiveSync
from app.modules.siege.markers import pin_color
from app.modules.siege.models import COLORS, LAYERS, OBJECTIVE_CATEGORY, SECTORS, Coordinate, RingPosition
from app.ui.localized_widgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QLineEdit, QMessageBox, QWidget
from app.ui.live_sync_panel import LiveSyncPanel
from app.ui.siege_drawings import translated
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


class DrawingPanel(QWidget):
    tools = {'rectangle': 'Retângulo', 'ellipse': 'Círculo / elipse', 'arrow': 'Seta'}

    def __init__(self, page):
        super().__init__()
        self.page, self.service, self.view = page, page.service, page.board.view
        self.selected = None
        self.preset_name = None
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        self.presets = QComboBox()
        self.presets.currentIndexChanged.connect(lambda: page.guard(self.service.select_preset, self.presets.currentData()))
        box.addWidget(self.presets)
        self.tool = QComboBox()
        self.tool.addItem('Selecionar forma', '')
        for kind, title in self.tools.items():
            self.tool.addItem(title, kind)
        self.tool.currentIndexChanged.connect(self.change_tool)
        box.addLayout(row(self.tool, button('Cancelar', self.cancel)))
        box.addWidget(label('Arraste para desenhar ou mover. Use Shift para criar um quadrado ou círculo. Arraste as alças para redimensionar.', 'subtitle', True))
        self.layer = QCheckBox('Formas táticas')
        self.layer.toggled.connect(lambda enabled: page.change_layer('TacticalShapes', enabled))
        box.addWidget(self.layer)

        self.items = QComboBox()
        self.items.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.items.currentIndexChanged.connect(lambda: self.select(self.items.currentData()))
        box.addWidget(self.items)
        self.details = QWidget()
        form = self.form = QFormLayout(self.details)
        form.setContentsMargins(0, 0, 0, 0)
        self.label = QLineEdit()
        self.label.setMaxLength(60)
        self.label.editingFinished.connect(lambda: self.edit(label=self.label.text()))
        form.addRow('Rótulo', self.label)
        self.color = button('Escolher cor', self.choose_color)
        form.addRow('Cor da forma', self.color)
        self.width = QDoubleSpinBox()
        self.width.setRange(.75, 10)
        self.width.setSingleStep(.25)
        self.width.setSuffix(' px')
        self.width.editingFinished.connect(lambda: self.edit(width=self.width.value()))
        form.addRow('Espessura', self.width)
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(10, 100)
        self.opacity.setDecimals(0)
        self.opacity.setSingleStep(5)
        self.opacity.setSuffix('%')
        self.opacity.editingFinished.connect(lambda: self.edit(opacity=self.opacity.value()/100))
        form.addRow('Opacidade', self.opacity)
        self.stroke = QComboBox()
        self.stroke.addItem('Tracejado', 'dashed')
        self.stroke.addItem('Sólido', 'solid')
        self.stroke.currentIndexChanged.connect(lambda: self.edit(stroke=self.stroke.currentData()))
        form.addRow('Traço', self.stroke)
        self.head_size = QDoubleSpinBox()
        self.head_size.setRange(4, 36)
        self.head_size.setSuffix(' px')
        self.head_size.editingFinished.connect(lambda: self.edit(head_size=self.head_size.value()))
        form.addRow('Ponta da seta', self.head_size)
        self.visible = QCheckBox('Forma visível')
        self.visible.toggled.connect(lambda visible: self.edit(visible=visible))
        form.addRow(self.visible)
        box.addWidget(self.details)
        self.actions = QWidget()
        actions = QVBoxLayout(self.actions)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.addLayout(row(button('Duplicar forma', self.duplicate), button('Excluir forma', self.delete)))
        box.addWidget(self.actions)
        box.addWidget(button('Importar marcações (.json)', page.import_preset))
        box.addWidget(button('Exportar marcações (.json)', page.export_preset))
        box.addStretch()
        self.view.drawing_created.connect(self.create)
        self.view.drawing_selected.connect(self.select)
        self.view.drawing_changed.connect(self.move)
        self.view.drawing_cancelled.connect(self.cancel)

    def activate(self, active):
        self.view.drawing.enabled = active
        self.cancel()
        self.view.drawing.refresh()

    def retranslate(self):
        super().retranslate()
        self.refresh()

    def change_tool(self):
        self.view.drawing.set_tool(self.tool.currentData() or '')
        if self.tool.currentData():
            self.page.message('Clique e arraste no mapa para desenhar.')
        else:
            self.page.message('')

    def cancel(self):
        update(self.tool, 'setCurrentIndex', 0)
        self.view.drawing.set_tool('')
        self.page.message('')

    def create(self, kind, start, end):
        drawing = self.page.guard(self.service.add_drawing, kind, start, end)
        if drawing is not None:
            self.cancel()
            self.select(drawing.id)

    def select(self, drawing_id):
        self.selected = drawing_id
        self.view.drawing.select(drawing_id)
        self.refresh()

    def current(self):
        return next((drawing for drawing in self.service.preset.drawings if drawing.id == self.selected), None)

    def edit(self, **changes):
        drawing = self.current()
        if drawing is not None:
            self.page.guard(self.service.edit_drawing, drawing.id, **changes)
            self.refresh()

    def move(self, drawing_id, start, end):
        self.page.guard(self.service.edit_drawing, drawing_id, start=start, end=end)

    def duplicate(self):
        drawing = self.current()
        if drawing is None:
            return
        shift = translated(drawing, .015, .015)
        if shift == {'start': drawing.start, 'end': drawing.end}:
            shift = translated(drawing, -.015, -.015)
        style = drawing.model_dump(exclude={'id', 'kind', 'start', 'end'})
        copy = self.page.guard(self.service.add_drawing, drawing.kind, **shift, **style)
        if copy is not None:
            self.select(copy.id)

    def delete(self):
        drawing = self.current()
        if drawing is not None and QMessageBox.question(
                self, tr('Excluir forma'), tr('Excluir esta forma do preset atual?'),
                QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel) == QMessageBox.Yes:
            self.page.guard(self.service.delete_drawing, drawing.id)

    def choose_color(self):
        drawing = self.current()
        if drawing is not None:
            selected = QColorDialog.getColor(QColor(drawing_color(drawing, self.service.preset)), self, tr('Cor da forma'))
            if selected.isValid():
                self.edit(color=selected.name())

    def refresh(self):
        preset = self.service.preset
        if preset.name != self.preset_name:
            if self.view.drawing.tool:
                self.cancel()
            self.preset_name = preset.name
            self.selected = None
            self.view.drawing.select(None)
        if self.selected and self.current() is None:
            self.selected = None
            self.view.drawing.select(None)
        choice(self.presets, preset.name, [(Verbatim(p.name), p.name) for p in self.service.state.presets])
        choice(self.items, self.selected, [('Selecione uma forma', None), *(
            (Verbatim(drawing.label or f'{tr(self.tools[drawing.kind])} {index}'), drawing.id)
            for index, drawing in enumerate(preset.drawings, 1)
        )])
        update(self.layer, 'setChecked', 'TacticalShapes' in preset.layers)
        self.tool.setEnabled(self.service.definition is not None)
        drawing = self.current()
        self.details.setVisible(drawing is not None)
        self.actions.setVisible(drawing is not None)
        self.form.setRowVisible(self.head_size, drawing is not None and drawing.kind == 'arrow')
        update(self.label, 'setText', drawing.label if drawing else '')
        update(self.width, 'setValue', drawing.width if drawing else 2)
        update(self.opacity, 'setValue', drawing.opacity*100 if drawing else 90)
        update(self.stroke, 'setCurrentIndex', self.stroke.findData(drawing.stroke if drawing else 'dashed'))
        update(self.head_size, 'setValue', drawing.head_size if drawing else 15)
        update(self.visible, 'setChecked', bool(drawing and drawing.visible))
        tint = drawing_color(drawing, preset) if drawing else COLORS['TacticalShapes']
        self.color.setStyleSheet(f'border-left: 4px solid {tint};')


class SiegePage(QWidget):
    def __init__(self, context, toggle_reshanta, setup_minimap, minimap_ready):
        super().__init__()
        self.context = context
        self.service = context.siege
        self.pin_id = None
        self.pin_preset = None
        self.minimap_ready = minimap_ready
        self.placement = None
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
        self.section.addItems(['Editar pins', 'Catálogo de anéis', 'Camadas e presets', 'Desenhos táticos', 'Live Sync'])
        side.addWidget(self.section)
        self.sections = QStackedWidget()
        side.addWidget(self.sections, 1)
        self.section.currentIndexChanged.connect(self.change_section)
        self.sections.addWidget(self.pin_page())
        self.sections.addWidget(self.catalogue_page())
        self.sections.addWidget(self.preset_page())
        self.drawings = DrawingPanel(self)
        self.sections.addWidget(self.drawings)
        self.live_sync = LiveSync(self.service, context.directory, parent=self)
        self.live_panel = LiveSyncPanel(self.live_sync)
        self.sections.addWidget(self.live_panel)
        self.live_sync.changed.connect(self.refresh_live_preview)
        self.service.session_changed.connect(self.refresh_live_preview)
        self.board.view.ring_selected.connect(self.select_ring_on_map)
        self.board.view.coordinate_selected.connect(self.placement_chosen)
        self.board.view.pin_selected.connect(self.select_pin_on_map)
        self.board.view.pin_moved.connect(self.move_pin)
        self.board.view.editing_cancelled.connect(self.cancel_placement)
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
            self.message(validation_text(error))
        return None

    def change_section(self, index):
        self.sections.setCurrentIndex(index)
        self.board.view.editing_pins = index == 0
        self.cancel_placement()
        self.drawings.activate(self.sections.currentWidget() is self.drawings)
        self.refresh_live_preview()

    def refresh_live_preview(self):
        view = self.board.view
        show = self.sections.currentWidget() is self.live_panel and self.live_sync.mode == 'player'
        shared = self.service.session_preset if show else None
        if view.session_preview != show or getattr(view, '_last_shared', None) is not shared:
            view.session_preview = show
            view._last_shared = shared
            view.refresh()

    def cancel_placement(self):
        view = self.board.view
        self.placement = None
        view.pick_position(False)
        view.cancel_drag()
        self.message('')
        self.pin_id = None
        view.select_pin(None)
        self.refresh_pins()

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
        self.section.setCurrentIndex(1)
        self.ring_filter.setCurrentIndex(0)
        self.catalogue.setCurrentIndex(self.catalogue.findData(ring_id))

    def start_ring_placement(self):
        self.placement = ('ring', self.catalogue.currentData())
        self.board.view.pick_position(True)
        self.message('Clique na posição conhecida. Use o botão direito para cancelar.')

    def placement_chosen(self, position):
        placement = self.placement
        self.placement = None
        self.board.view.pick_position(False)
        if position is None or placement is None:
            return
        kind, key = placement
        if kind == 'ring':
            self.catalogue.setCurrentIndex(self.catalogue.findData(key))
            self.x.setValue(position.x)
            self.y.setValue(position.y)
            self.message('Informe a fonte e salve a posição.')
        else:
            names = {pin.name for pin in self.service.preset.markers}
            number = 1
            while f'Pin {number}' in names:
                number += 1
            marker = self.guard(self.service.add_marker, f'Pin {number}', position)
            if marker is not None:
                self.select_pin(marker.id)
                self.pin_name.setFocus()
                self.pin_name.selectAll()
                self.message('Pin adicionado. Arraste no mapa para ajustar.')

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
        if self.sections.currentWidget() is self.drawings:
            self.drawings.cancel()
            drawings = self.service.preset.drawings
            self.drawings.select(drawings[0].id if drawings else None)
        elif self.service.preset.markers:
            self.section.setCurrentIndex(0)
            self.select_pin(self.service.preset.markers[0].id)
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

    def pin_page(self):
        widget = QWidget()
        box = QVBoxLayout(widget)
        box.setContentsMargins(0, 0, 0, 0)
        self.pin_presets = QComboBox()
        self.pin_presets.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.pin_presets.currentIndexChanged.connect(
            lambda: self.guard(self.service.select_preset, self.pin_presets.currentData()))
        box.addWidget(self.pin_presets)
        self.marker = button('Adicionar pin', self.start_marker, True)
        box.addLayout(row(self.marker, button('Cancelar edição', self.cancel_placement)))
        self.pin_list = QComboBox()
        self.pin_list.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.pin_list.currentIndexChanged.connect(lambda: self.select_pin(self.pin_list.currentData()))
        box.addWidget(self.pin_list)
        self.pin_details = QWidget()
        form = QFormLayout(self.pin_details)
        form.setContentsMargins(0, 0, 0, 0)
        self.pin_name = QLineEdit()
        self.pin_name.setMaxLength(60)
        self.pin_name.editingFinished.connect(lambda: self.edit_pin(name=self.pin_name.text()))
        self.pin_category = QLineEdit()
        self.pin_category.setMaxLength(32)
        self.pin_category.setToolTip('Use Objetivo de siege para incluir o pin na camada de objetivos.')
        self.pin_category.editingFinished.connect(self.edit_pin_category)
        self.pin_scale = QDoubleSpinBox()
        self.pin_scale.setRange(.65, 1.8)
        self.pin_scale.setSingleStep(.1)
        self.pin_scale.setSuffix('×')
        self.pin_scale.editingFinished.connect(lambda: self.edit_pin(scale=self.pin_scale.value()))
        self.pin_visibility = QCheckBox('Pin visível')
        self.pin_visibility.toggled.connect(lambda visible: self.edit_pin(visible=visible))
        self.pin_color = button('Escolher cor', self.choose_pin_color)
        form.addRow('Nome do pin', self.pin_name)
        form.addRow('Categoria', self.pin_category)
        form.addRow('Tamanho do pin', self.pin_scale)
        form.addRow('Cor do pin', self.pin_color)
        form.addRow(self.pin_visibility)
        form.addRow(button('Excluir pin', self.delete_marker))
        box.addWidget(self.pin_details)
        box.addWidget(button('Importar marcações (.json)', self.import_preset))
        box.addWidget(button('Exportar marcações (.json)', self.export_preset))
        box.addWidget(button('Restaurar marcações padrão', self.restore_preset))
        box.addStretch()
        return widget

    def start_marker(self):
        self.placement = ('marker', None)
        self.board.view.pick_position(True)
        self.message('Clique no mapa para adicionar um pin. Esc cancela.')

    def select_pin(self, marker_id):
        self.pin_id = marker_id
        self.board.view.select_pin(marker_id)
        self.refresh_pins()

    def select_pin_on_map(self, marker_id):
        self.pin_id = marker_id
        self.refresh_pins()

    def selected_marker(self):
        return next((pin for pin in self.service.preset.markers if pin.id == self.pin_id), None)

    def edit_pin(self, **changes):
        pin = self.selected_marker()
        if pin and any(getattr(pin, key) != value for key, value in changes.items()):
            self.guard(self.service.edit_marker, pin.id, **changes)
            self.refresh_pins()

    def edit_pin_category(self):
        category = self.pin_category.text()
        if category.casefold() in {tr('Objetivo de siege').casefold(), 'objetivo de siege', 'siege objective'}:
            category = OBJECTIVE_CATEGORY
        elif category == tr('Tático'):
            category = 'Tático'
        self.edit_pin(category=category)

    def move_pin(self, marker_id, position):
        try:
            self.service.edit_marker(marker_id, position=position)
        except (OSError, ValueError) as error:
            self.message(validation_text(error))
            self.board.view.refresh()

    def choose_pin_color(self):
        marker = self.selected_marker()
        if marker:
            color = pin_color(marker, self.service.preset)
            selected = QColorDialog.getColor(QColor(color), self, tr('Cor do pin'))
            if selected.isValid():
                self.edit_pin(color=selected.name())

    def delete_marker(self):
        marker = self.selected_marker()
        if marker is None:
            return
        reply = QMessageBox.question(
            self, tr('Excluir pin'),
            tr('Excluir este pin do preset atual?'),
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel,
        )
        if reply == QMessageBox.Yes:
            self.guard(self.service.delete_marker, marker.id)

    def refresh_pins(self):
        preset = self.service.preset
        names = [('Selecionar pin', None), *((Verbatim(pin.name), pin.id) for pin in preset.markers)]
        choice(self.pin_list, self.pin_id, names)
        pin = self.selected_marker()
        self.pin_details.setEnabled(pin is not None)
        update(self.pin_name, 'setText', pin.name if pin else '')
        category = pin.category if pin else ''
        label_for_category = {'Tático': 'Tático', OBJECTIVE_CATEGORY: 'Objetivo de siege'}
        update(self.pin_category, 'setText', label_for_category.get(category, Verbatim(category)))
        update(self.pin_scale, 'setValue', pin.scale if pin else 1.)
        update(self.pin_visibility, 'setChecked', bool(pin and pin.visible))
        color = pin_color(pin, preset) if pin else COLORS['CustomMarkers']
        self.pin_color.setStyleSheet(f'border-left: 4px solid {color};')

    def refresh(self):
        service = self.service
        count = sum(service.position(r) is not None for r in service.rings.values())
        self.summary.setText(f'{len(service.preset.markers)} pins · {count}/{len(service.rings)} anéis posicionados')
        self.refresh_catalogue()
        entries = [(Verbatim(p.name), p.name) for p in service.state.presets]
        choice(self.presets, service.preset.name, entries)
        choice(self.pin_presets, service.preset.name, entries)
        if self.pin_preset != service.preset.name or (self.pin_id and not self.selected_marker()):
            self.pin_preset = service.preset.name
            self.pin_id = None
            self.board.view.select_pin(None)
        self.refresh_pins()
        self.drawings.refresh()
        for key, checkbox in self.layers.items():
            update(checkbox, 'setChecked', key in service.preset.layers)
        update(self.local_calibration, 'setChecked', service.preset.use_local_calibration)
        update(self.marker_scale, 'setValue', service.preset.marker_scale)
        self.marker.setEnabled(service.definition is not None)
        update(self.overlay_toggle, 'setChecked', service.state.overlay.map_markers)
        self.refresh_minimap_button()

    def refresh_minimap_button(self):
        self.setup_minimap.setVisible(self.service.state.overlay.map_markers
                                     and self.service.definition is not None
                                     and not self.minimap_ready())
