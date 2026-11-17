# SPDX-License-Identifier: GPL-3.0-only
"""Tactical editing shared by the Siege Command editor and the Live Sync caller."""
from PySide6.QtCore import QSignalBlocker, QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QHBoxLayout, QVBoxLayout

from app.core.i18n import Verbatim, tr, validation_text
from app.modules.siege.drawing import drawing_color
from app.modules.siege.markers import pin_color
from app.modules.siege.models import COLORS, OBJECTIVE_CATEGORY
from app.ui.icons import navigation_icon
from app.ui.localized_widgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QLineEdit, QMessageBox, QToolButton, QWidget,
)
from app.ui.siege_drawings import translated
from app.ui.widgets import button, label


def choice(combo, current, entries):
    with QSignalBlocker(combo):
        combo.clear()
        for caption, value in entries:
            combo.addItem(caption, value)
        combo.setCurrentIndex(max(0, combo.findData(current)))


def update(widget, setter, value):
    with QSignalBlocker(widget):
        getattr(widget, setter)(value)


TACTICAL_TOOLS = {
    'select': ('tactical-select', 'Selecionar e mover'),
    'pin': ('tactical-pin', 'Adicionar pin'),
    'rectangle': ('tactical-rectangle', 'Desenhar retângulo'),
    'ellipse': ('tactical-circle', 'Desenhar círculo ou elipse'),
    'arrow': ('tactical-arrow', 'Desenhar seta'),
    'delete': ('tactical-delete', 'Excluir marcação selecionada'),
    'cancel': ('close', 'Cancelar edição'),
}


class TacticalToolbar(QWidget):
    requested = Signal(str)

    def __init__(self, *, quick=False):
        super().__init__()
        self.setStyleSheet("""
            QToolButton {background:#22222e;border:1px solid #393545;border-radius:6px;}
            QToolButton:hover {background:#302943;border-color:#8875ad;}
            QToolButton:checked {background:#3f3457;border-color:#c2b2fc;}
            QToolButton:focus {border-color:#e1d6ff;}
            QToolButton:disabled {background:#191923;border-color:#30303e;}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.buttons = {}
        for key, (image, caption) in TACTICAL_TOOLS.items():
            if quick and key == 'delete':
                continue
            control = QToolButton()
            control.setIcon(navigation_icon(image))
            control.setIconSize(QSize(17, 17))
            control.setFixedSize(34, 32)
            control.setCursor(Qt.PointingHandCursor)
            control.setFocusPolicy(Qt.StrongFocus)
            control.setAccessibleName(caption)
            control.setToolTip(caption)
            control.setCheckable(key not in ('delete', 'cancel'))
            control.clicked.connect(lambda _checked, action=key: self.requested.emit(action))
            layout.addWidget(control)
            self.buttons[key] = control
        layout.addStretch()

    def show_state(self, tool, map_ready, deletable):
        for key, control in self.buttons.items():
            if control.isCheckable():
                control.setChecked(tool == key)
            elif key == 'delete':
                control.setEnabled(deletable)
                continue
            elif key == 'cancel':
                control.setEnabled(tool not in (None, 'select'))
                continue
            control.setEnabled(map_ready)


class TacticalEditor(QWidget):
    shape_names = {'rectangle': 'Retângulo', 'ellipse': 'Círculo / elipse', 'arrow': 'Seta'}
    tool_hints = {
        'select': 'Clique para selecionar ou arraste para mover. Use as alças para redimensionar.',
        'pin': 'Clique no mapa para adicionar um pin. Esc cancela.',
        'rectangle': 'Arraste no mapa. Use Shift para desenhar um quadrado.',
        'ellipse': 'Arraste no mapa. Use Shift para desenhar um círculo.',
        'arrow': 'Clique e arraste no mapa para desenhar.',
    }

    def __init__(self, page):
        super().__init__()
        self.page, self.service, self.view = page, page.service, page.board.view
        self.active = False
        self.tool = 'select'
        self.selection = None
        self.preset_name = self.service.preset.name
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)

        self.presets = QComboBox()
        self.presets.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.presets.setAccessibleName('Preset atual')
        self.presets.currentIndexChanged.connect(lambda: page.guard(self.service.select_preset, self.presets.currentData()))
        box.addWidget(self.presets)

        self.toolbar = TacticalToolbar()
        self.toolbar.requested.connect(self.use_tool)
        self.tool_hint = label('', 'subtitle', True)
        box.addWidget(self.toolbar)
        box.addWidget(self.tool_hint)

        self.items = QComboBox()
        self.items.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.items.setAccessibleName('Selecionar marcação')
        self.items.currentIndexChanged.connect(lambda: self.select(self.items.currentData()))
        box.addWidget(self.items)

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
        box.addWidget(self.pin_details)

        self.ring_details = QWidget()
        form = QFormLayout(self.ring_details)
        form.setContentsMargins(0, 0, 0, 0)
        self.ring_original = QLineEdit()
        self.ring_original.setReadOnly(True)
        self.ring_original.setAccessibleName('Identificador original do anel')
        form.addRow('Identificador original', self.ring_original)
        self.ring_name = QLineEdit()
        self.ring_name.setAccessibleName('Nome personalizado')
        self.ring_name.setToolTip('Use até 36 caracteres. Deixe vazio para usar o nome original.')
        self.ring_name.editingFinished.connect(lambda: self.edit_ring_name(self.ring_name.text()))
        form.addRow('Nome personalizado', self.ring_name)
        self.ring_reset = button('Restaurar nome original', lambda: self.edit_ring_name(''))
        form.addRow(self.ring_reset)
        box.addWidget(self.ring_details)

        self.drawing_details = QWidget()
        form = self.form = QFormLayout(self.drawing_details)
        form.setContentsMargins(0, 0, 0, 0)
        self.label = QLineEdit()
        self.label.setMaxLength(60)
        self.label.editingFinished.connect(lambda: self.edit_drawing(label=self.label.text()))
        form.addRow('Rótulo', self.label)
        self.color = button('Escolher cor', self.choose_drawing_color)
        form.addRow('Cor da forma', self.color)
        self.width = QDoubleSpinBox()
        self.width.setRange(.75, 10)
        self.width.setSingleStep(.25)
        self.width.setSuffix(' px')
        self.width.editingFinished.connect(lambda: self.edit_drawing(width=self.width.value()))
        form.addRow('Espessura', self.width)
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(10, 100)
        self.opacity.setDecimals(0)
        self.opacity.setSingleStep(5)
        self.opacity.setSuffix('%')
        self.opacity.editingFinished.connect(lambda: self.edit_drawing(opacity=self.opacity.value()/100))
        form.addRow('Opacidade', self.opacity)
        self.stroke = QComboBox()
        self.stroke.addItem('Tracejado', 'dashed')
        self.stroke.addItem('Sólido', 'solid')
        self.stroke.currentIndexChanged.connect(lambda: self.edit_drawing(stroke=self.stroke.currentData()))
        form.addRow('Traço', self.stroke)
        self.head_size = QDoubleSpinBox()
        self.head_size.setRange(4, 36)
        self.head_size.setSuffix(' px')
        self.head_size.editingFinished.connect(lambda: self.edit_drawing(head_size=self.head_size.value()))
        form.addRow('Ponta da seta', self.head_size)
        self.visible = QCheckBox('Forma visível')
        self.visible.toggled.connect(lambda visible: self.edit_drawing(visible=visible))
        form.addRow(self.visible)
        box.addWidget(self.drawing_details)
        self.duplicate_button = button('Duplicar forma', self.duplicate)
        box.addWidget(self.duplicate_button)
        self.layer = QCheckBox('Formas táticas')
        self.layer.toggled.connect(lambda enabled: page.change_layer('TacticalShapes', enabled))
        box.addWidget(self.layer)
        box.addWidget(button('Importar marcações (.json)', page.import_preset))
        box.addWidget(button('Exportar marcações (.json)', page.export_preset))
        box.addWidget(button('Restaurar marcações padrão', page.restore_preset))
        box.addStretch()

        self.quick_tools = QWidget()
        quick = QVBoxLayout(self.quick_tools)
        quick.setContentsMargins(0, 0, 0, 0)
        quick.setSpacing(5)
        quick.addWidget(label('Ferramentas rápidas', 'sectionTitle'))
        self.quick_toolbar = TacticalToolbar(quick=True)
        self.quick_toolbar.requested.connect(self.use_tool)
        quick.addWidget(self.quick_toolbar)
        self.quick_hint = label('', 'subtitle', True)
        quick.addWidget(self.quick_hint)
        self.properties = button('Editar propriedades', self.show_properties)
        self.properties.setObjectName('quiet')
        quick.addWidget(self.properties)

        self.view.pin_selected.connect(lambda marker_id: self.select(f'pin:{marker_id}'))
        self.view.drawing_selected.connect(lambda drawing_id: self.select(f'drawing:{drawing_id}'))
        self.view.pin_moved.connect(self.move_pin)
        self.view.drawing_created.connect(self.create_drawing)
        self.view.drawing_changed.connect(self.move_drawing)
        self.service.map_changed.connect(self.refresh_map_tools)

    @property
    def map_ready(self):
        return self.active and self.service.definition is not None

    def set_active(self, active):
        if self.active != active:
            self.active = active
            self.set_tool('select')

    def refresh_map_tools(self):
        if self.active:
            self.cancel()

    def show_properties(self):
        self.cancel()
        self.page.show_editor()

    def use_tool(self, tool):
        if tool == 'delete':
            if self.selected_marker():
                self.delete_marker()
            else:
                self.delete_drawing()
        elif tool == 'cancel':
            self.cancel()
        elif self.map_ready:
            self.page.message('')
            self.set_tool(tool)

    def set_tool(self, tool):
        self.tool = tool
        self.view.set_editor_tool(tool if self.map_ready else None)
        self.refresh_tools()

    def refresh_tools(self):
        tool = self.tool if self.map_ready else None
        selected = self.selection is not None and self.active
        for toolbar in (self.toolbar, self.quick_toolbar):
            toolbar.show_state(tool, self.map_ready, selected and not self.selection.startswith('ring:'))
        hint = self.tool_hints[tool] if tool else 'Baixe o mapa de Lower Reshanta para usar as ferramentas.'
        self.tool_hint.setText(hint)
        self.quick_hint.setText(hint if tool != 'select' else 'As marcações só são enviadas ao publicar.')
        self.properties.setVisible(selected)

    def cancel(self):
        self.set_tool('select')
        self.page.message('')

    def select(self, selection):
        if self.tool != 'select':
            self.cancel()
        self.selection = selection
        self.refresh()

    def select_first(self):
        preset = self.service.preset
        if preset.markers:
            self.select(f'pin:{preset.markers[0].id}')
        elif preset.drawings:
            self.select(f'drawing:{preset.drawings[0].id}')
        else:
            self.select(None)

    def selected_marker(self):
        if self.selection and self.selection.startswith('pin:'):
            marker_id = self.selection.removeprefix('pin:')
            return next((pin for pin in self.service.preset.markers if pin.id == marker_id), None)

    def selected_drawing(self):
        if self.selection and self.selection.startswith('drawing:'):
            drawing_id = self.selection.removeprefix('drawing:')
            return next((shape for shape in self.service.preset.drawings if shape.id == drawing_id), None)

    def selected_ring(self):
        if self.selection and self.selection.startswith('ring:'):
            return self.service.rings.get(self.selection.removeprefix('ring:'))

    def edit_ring_name(self, text):
        ring = self.selected_ring()
        if ring:
            self.page.guard(self.service.set_ring_alias, ring.ring_id, text)
            self.refresh_ring()

    def place_pin(self, position):
        names = {pin.name for pin in self.service.preset.markers}
        number = 1
        while f'Pin {number}' in names:
            number += 1
        marker = self.page.guard(self.service.add_marker, f'Pin {number}', position)
        if marker is not None:
            self.select(f'pin:{marker.id}')
            if self.isVisible():
                self.pin_name.setFocus()
                self.pin_name.selectAll()
            self.page.message('Pin adicionado. Arraste no mapa para ajustar.')

    def create_drawing(self, kind, start, end):
        drawing = self.page.guard(self.service.add_drawing, kind, start, end)
        if drawing is not None:
            self.select(f'drawing:{drawing.id}')

    def edit_pin(self, **changes):
        pin = self.selected_marker()
        if pin and any(getattr(pin, key) != value for key, value in changes.items()):
            self.page.guard(self.service.edit_marker, pin.id, **changes)
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
            self.page.message(validation_text(error))
            self.view.refresh()

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
            self.page.guard(self.service.delete_marker, marker.id)

    def edit_drawing(self, **changes):
        drawing = self.selected_drawing()
        if drawing and any(getattr(drawing, key) != value for key, value in changes.items()):
            self.page.guard(self.service.edit_drawing, drawing.id, **changes)
            self.refresh()

    def move_drawing(self, drawing_id, start, end):
        self.page.guard(self.service.edit_drawing, drawing_id, start=start, end=end)

    def duplicate(self):
        drawing = self.selected_drawing()
        if drawing is None:
            return
        shift = translated(drawing, .015, .015)
        if shift == {'start': drawing.start, 'end': drawing.end}:
            shift = translated(drawing, -.015, -.015)
        style = drawing.model_dump(exclude={'id', 'kind', 'start', 'end'})
        copy = self.page.guard(self.service.add_drawing, drawing.kind, **shift, **style)
        if copy is not None:
            self.select(f'drawing:{copy.id}')

    def delete_drawing(self):
        drawing = self.selected_drawing()
        if drawing is not None and QMessageBox.question(
                self, tr('Excluir forma'), tr('Excluir esta forma do preset atual?'),
                QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel) == QMessageBox.Yes:
            self.page.guard(self.service.delete_drawing, drawing.id)

    def choose_drawing_color(self):
        drawing = self.selected_drawing()
        if drawing is not None:
            selected = QColorDialog.getColor(QColor(drawing_color(drawing, self.service.preset)), self, tr('Cor da forma'))
            if selected.isValid():
                self.edit_drawing(color=selected.name())

    def refresh(self):
        preset = self.service.preset
        if preset.name != self.preset_name:
            self.preset_name = preset.name
            self.selection = None
            if self.active:
                self.cancel()
        pin, shape, ring = self.selected_marker(), self.selected_drawing(), self.selected_ring()
        if pin is None and shape is None and ring is None:
            self.selection = None
        self.view.select_element(pin.id if pin else None, shape.id if shape else None, ring.ring_id if ring else None)
        choice(self.presets, preset.name, [(Verbatim(p.name), p.name) for p in self.service.state.presets])
        with QSignalBlocker(self.items):
            self.items.clear()
            self.items.addItem('Selecionar marcação', None)
            for pin in preset.markers:
                self.items.addItem(navigation_icon('tactical-pin'), Verbatim(pin.name), f'pin:{pin.id}')
            for index, shape in enumerate(preset.drawings, 1):
                caption = shape.label or f'{tr(self.shape_names[shape.kind])} {index}'
                icon = navigation_icon(TACTICAL_TOOLS[shape.kind][0])
                self.items.addItem(icon, Verbatim(caption), f'drawing:{shape.id}')
            rings = self.service.rings
            if rings:
                self.items.insertSeparator(self.items.count())
            for ring in rings.values():
                caption = self.service.ring_label(ring)
                if not self.service.ring_code(ring):
                    caption = f'{caption} · {ring.ring_id}'
                self.items.addItem(navigation_icon('tactical-ring'), Verbatim(caption), f'ring:{ring.ring_id}')
            self.items.setCurrentIndex(max(0, self.items.findData(self.selection)))
        update(self.layer, 'setChecked', 'TacticalShapes' in preset.layers)
        self.refresh_pins()
        self.refresh_drawings()
        self.refresh_ring()
        self.refresh_tools()

    def refresh_ring(self):
        ring = self.selected_ring()
        ring_id = ring.ring_id if ring else ''
        original = (self.service.ring_code(ring) or ring_id) if ring else ''
        alias = self.service.preset.aliases.get(ring_id, '')
        update(self.ring_original, 'setText', original)
        self.ring_original.setToolTip(Verbatim(ring_id))
        with QSignalBlocker(self.ring_name):
            self.ring_name.setText(alias)
            self.ring_details.setVisible(ring is not None)
        self.ring_reset.setEnabled(bool(alias))

    def refresh_pins(self):
        preset = self.service.preset
        pin = self.selected_marker()
        self.pin_details.setVisible(pin is not None)
        update(self.pin_name, 'setText', pin.name if pin else '')
        category = pin.category if pin else ''
        label_for_category = {'Tático': 'Tático', OBJECTIVE_CATEGORY: 'Objetivo de siege'}
        update(self.pin_category, 'setText', tr(label_for_category[category]) if category in label_for_category else category)
        update(self.pin_scale, 'setValue', pin.scale if pin else 1.)
        update(self.pin_visibility, 'setChecked', bool(pin and pin.visible))
        color = pin_color(pin, preset) if pin else COLORS['CustomMarkers']
        self.pin_color.setStyleSheet(f'border-left: 4px solid {color};')

    def refresh_drawings(self):
        preset = self.service.preset
        drawing = self.selected_drawing()
        self.drawing_details.setVisible(drawing is not None)
        self.duplicate_button.setVisible(drawing is not None)
        self.form.setRowVisible(self.head_size, drawing is not None and drawing.kind == 'arrow')
        update(self.label, 'setText', drawing.label if drawing else '')
        update(self.width, 'setValue', drawing.width if drawing else 2)
        update(self.opacity, 'setValue', drawing.opacity*100 if drawing else 90)
        update(self.stroke, 'setCurrentIndex', self.stroke.findData(drawing.stroke if drawing else 'dashed'))
        update(self.head_size, 'setValue', drawing.head_size if drawing else 15)
        update(self.visible, 'setChecked', bool(drawing and drawing.visible))
        tint = drawing_color(drawing, preset) if drawing else COLORS['TacticalShapes']
        self.color.setStyleSheet(f'border-left: 4px solid {tint};')
