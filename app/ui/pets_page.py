# SPDX-License-Identifier: GPL-3.0-only
"""A portrait-first collection with a small, progressive-disclosure detail pane."""
from functools import lru_cache

from PySide6.QtCore import QRect, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QInputDialog, QListWidget, QListWidgetItem, QStyledItemDelegate,
    QStyle, QVBoxLayout)

from app.core.i18n import tr
from app.infrastructure.storage import PACKAGE
from app.ui.localized_widgets import (QCheckBox, QComboBox, QDialog, QLineEdit,
    QSpinBox, QToolButton, QWidget)
from app.ui.widgets import button, card, label, page_header, row


@lru_cache(maxsize=256)
def portrait_icon(path):
    return QIcon(str(PACKAGE/'assets'/path))


def progress_caption(entry):
    progress = entry.progress
    if progress is not None and progress.pending:
        return 'Atualização pendente'
    if progress is None or progress.level is None:
        return 'Progresso não informado'
    return 'Ainda não adquirido' if progress.level == 0 else f'Insight {progress.level}'


class PetCardDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(166, 182)

    def paint(self, painter, option, index):
        painter.save()
        rect = option.rect.adjusted(4, 4, -4, -4)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        painter.setBrush(QColor('#253d49' if selected else '#242d40' if hovered else '#191d2e'))
        painter.setPen(QColor('#91dedf' if selected else '#637b90' if hovered else '#30364c'))
        painter.drawRoundedRect(rect, 10, 10)
        picture = index.data(Qt.ItemDataRole.DecorationRole)
        picture.paint(painter, QRect(rect.center().x()-44, rect.top()+10, 88, 88))
        painter.setPen(QColor('#eff1f7'))
        painter.drawText(QRect(rect.left()+8,rect.top()+102,rect.width()-16,38),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            index.data(Qt.ItemDataRole.UserRole+1))
        painter.setPen(QColor('#9ba5bd'))
        font = painter.font(); font.setPointSizeF(max(8, font.pointSizeF()-1)); painter.setFont(font)
        painter.drawText(QRect(rect.left()+5, rect.bottom()-26, rect.width()-10, 20),
            Qt.AlignmentFlag.AlignCenter, tr(index.data(Qt.ItemDataRole.UserRole+2)))
        if index.data(Qt.ItemDataRole.UserRole+3):
            painter.setPen(QColor('#eac77b'))
            painter.drawText(QRect(rect.right()-25,rect.top()+4,20,20), Qt.AlignmentFlag.AlignCenter, '★')
        painter.restore()


class ProgressDialog(QDialog):
    def __init__(self, pet, entry, parent):
        super().__init__(parent)
        self.setWindowTitle(pet.name)
        self.setMinimumWidth(380)
        body = QVBoxLayout(self)
        body.addWidget(page_header('Registrar progresso', 'Copie o nível e as almas que aparecem na coleção do jogo.'))
        form = QFormLayout()
        self.level = QSpinBox()
        self.level.setRange(-1, 100)
        self.level.setSpecialValueText(tr('Não informado'))
        progress = entry.progress
        self.level.setValue(progress.level if progress and progress.level is not None else -1)
        self.souls = QSpinBox()
        self.souls.setRange(0, 10_000_000)
        self.souls.setValue(progress.souls if progress and progress.souls is not None else 0)
        self.known = QCheckBox('Registrar quantidade de almas')
        self.known.setChecked(progress is not None and progress.souls is not None)
        self.souls.setEnabled(self.known.isChecked())
        self.known.toggled.connect(self.souls.setEnabled)
        form.addRow(label('Pet Insight · 0 significa não adquirido'), self.level)
        form.addRow(self.known)
        form.addRow(label('Almas exibidas no jogo'), self.souls)
        body.addLayout(form)
        body.addWidget(label('Esse registro fica salvo apenas neste computador.', 'subtitle', True))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        body.addWidget(buttons)


class PetsPage(QWidget):
    def __init__(self, context, service, show_farm=None):
        super().__init__()
        self.context, self.service = context, service
        self.show_farm = show_farm
        self.selected_id = None
        self._refreshing = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 20, 26, 20)
        layout.setSpacing(12)
        layout.addWidget(page_header('Pets', 'Escolha seus favoritos e acompanhe sua coleção.'))
        top = QHBoxLayout()
        self.summary = label('', 'subtitle')
        top.addWidget(self.summary, 1)
        self.profiles = QComboBox()
        self.profiles.setMinimumWidth(160)
        self.profiles.setAccessibleName('Coleção selecionada')
        self.profiles.currentIndexChanged.connect(self.profile_changed)
        top.addWidget(self.profiles)
        top.addWidget(button('Nova coleção', self.new_profile))
        layout.addLayout(top)
        sync = QHBoxLayout()
        self.automatic = QCheckBox('Sincronizar com o jogo')
        self.automatic.setToolTip('A coleção é recebida ao entrar no personagem. O Npcap é necessário para a leitura automática.')
        self.automatic.toggled.connect(self.automatic_changed)
        sync.addWidget(self.automatic)
        self.connection = label(service.status, 'subtitle', True)
        service.status_changed.connect(self.connection.setText)
        sync.addWidget(self.connection, 1)
        self.region = QComboBox()
        for text,key in [('SA','sa'),('Europe','eu'),('North America East','nae'),('North America West','naw'),
                         ('Asia','asia'),('Korea','kr'),('Taiwan','tw')]:
            self.region.addItem(text,key)
        self.region.setAccessibleName('Região da coleção')
        self.region.currentIndexChanged.connect(self.region_changed)
        sync.addWidget(self.region)
        layout.addLayout(sync)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Buscar pet ou monstro…')
        self.search.setClearButtonEnabled(True)
        self.family = QComboBox()
        self.family.addItem('Todas as famílias', '')
        for family in ('Cogni', 'Fera', 'Natura', 'Varian', 'Special'):
            self.family.addItem('Especial' if family == 'Special' else family, family)
        self.state = QComboBox()
        for text, key in [('Todo o progresso',''), ('Ainda não adquiridos','missing'),
                          ('Em evolução','growing'), ('Meta atingida','complete'),
                          ('Não registrados','unknown')]:
            self.state.addItem(text, key)
        self.favorite_filter = QCheckBox('Só favoritos')
        layout.addLayout(row(self.search, self.family, self.state, self.favorite_filter))
        maps = QHBoxLayout()
        self.map_layer = QCheckBox('Mostrar locais nos mapas')
        self.map_layer.setToolTip('Locais de referência do cliente; confirme a presença no jogo.')
        self.map_layer.toggled.connect(self.map_enabled)
        maps.addWidget(self.map_layer)
        maps.addStretch()
        maps.addWidget(label('Nos mapas', 'subtitle'))
        self.map_filter = QComboBox()
        for text, key in [('Todos os pets','all'), ('Favoritos','favorites'), ('Metas pendentes','needed')]:
            self.map_filter.addItem(text, key)
        self.map_filter.currentIndexChanged.connect(self.map_filter_changed)
        maps.addWidget(self.map_filter)
        self.clear_focus = button('Limpar seleção do mapa', self.clear_map_focus)
        maps.addWidget(self.clear_focus)
        layout.addLayout(maps)
        body = QHBoxLayout()
        body.setSpacing(16)
        self.grid = QListWidget()
        self.grid.setViewMode(QListWidget.ViewMode.IconMode)
        self.grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.grid.setMovement(QListWidget.Movement.Static)
        self.grid.setIconSize(QSize(92, 92))
        self.grid.setGridSize(QSize(166, 182))
        self.grid.setItemDelegate(PetCardDelegate(self.grid))
        self.grid.setSpacing(8)
        self.grid.setWordWrap(True)
        self.grid.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.grid.setUniformItemSizes(True)
        self.grid.setAccessibleName('Catálogo de pets')
        self.grid.setStyleSheet('''QListWidget{background:transparent;border:0;outline:0;}
            QListWidget::item{background:#191d2e;border:1px solid #30364c;border-radius:10px;padding:10px;color:#c6cfdf;}
            QListWidget::item:selected{background:#253d49;border:1px solid #91dedf;color:#f1ffff;}
            QListWidget::item:hover{background:#242d40;border-color:#637b90;}''')
        self.grid.currentItemChanged.connect(self.selection_changed)
        body.addWidget(self.grid, 1)
        side, detail = card()
        side.setFixedWidth(294)
        self.picture = label('')
        self.picture.setFixedHeight(126)
        self.picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail.addWidget(self.picture)
        self.name = label('', 'cardTitle', True)
        detail.addWidget(self.name)
        self.family_caption = label('', 'eyebrow')
        detail.addWidget(self.family_caption)
        self.progress = label('', 'subtitle', True)
        detail.addWidget(self.progress)
        self.favorite = QCheckBox('Favorito')
        self.favorite.toggled.connect(self.favorite_changed)
        detail.addWidget(self.favorite)
        self.goal = QComboBox()
        for level in range(1, 4):
            self.goal.addItem('Desbloquear' if level == 1 else f'Chegar ao nível {level}', level)
        self.goal.setAccessibleName('Meta do pet')
        self.goal.currentIndexChanged.connect(self.goal_changed)
        detail.addWidget(self.goal)
        self.record_button = button('Registrar progresso', self.record, True)
        detail.addWidget(self.record_button)
        self.restore_button = button('Usar informação do jogo', self.restore_observed)
        self.restore_button.hide()
        detail.addWidget(self.restore_button)
        detail.addSpacing(6)
        detail.addWidget(label('ONDE ENCONTRAR', 'eyebrow'))
        self.sources = label('', 'subtitle', True)
        detail.addWidget(self.sources)
        self.farm_button = button('Ver locais no Atlas', self.open_farm)
        detail.addWidget(self.farm_button)
        detail.addStretch()
        self.provenance = QCheckBox('Ver origem dos dados')
        self.provenance.toggled.connect(self.refresh_detail)
        detail.addWidget(self.provenance)
        self.origin = label('', 'subtitle', True)
        self.origin.hide()
        detail.addWidget(self.origin)
        self.source_button = button('Consultar fonte', self.open_source)
        self.source_button.hide()
        detail.addWidget(self.source_button)
        body.addWidget(side)
        layout.addLayout(body, 1)
        self.empty = label('Nenhum pet com esses filtros. Ajuste a busca ou os filtros.', 'subtitle', True)
        self.empty.hide()
        layout.addWidget(self.empty)
        footer = QHBoxLayout()
        self.feedback = label('', 'subtitle', True)
        footer.addWidget(self.feedback, 1)
        footer.addWidget(button('Importar coleção', self.import_collection))
        footer.addWidget(button('Exportar coleção', self.export_collection))
        layout.addLayout(footer)
        self.search.textChanged.connect(self.refresh_grid)
        self.family.currentIndexChanged.connect(self.refresh_grid)
        self.state.currentIndexChanged.connect(self.refresh_grid)
        self.favorite_filter.toggled.connect(self.refresh_grid)
        service.changed.connect(self.refresh)
        service.error.connect(self.feedback.setText)
        context.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        current = self.service.store.collection.active_profile
        self.profiles.blockSignals(True)
        self.profiles.clear()
        for key, profile in self.service.store.collection.profiles.items():
            self.profiles.addItem(profile.name, key)
        self.profiles.setCurrentIndex(self.profiles.findData(current))
        self.profiles.blockSignals(False)
        self.automatic.blockSignals(True)
        self.automatic.setChecked(self.context.prefs.pets.auto_collection)
        self.automatic.blockSignals(False)
        self.region.blockSignals(True)
        self.region.setCurrentIndex(self.region.findData(self.context.prefs.pets.region))
        self.region.blockSignals(False)
        self.map_layer.blockSignals(True)
        self.map_layer.setChecked('pets' not in self.context.prefs.disabled_categories)
        self.map_layer.blockSignals(False)
        self.map_filter.blockSignals(True)
        self.map_filter.setCurrentIndex(self.map_filter.findData(self.context.prefs.pets.map_filter))
        self.map_filter.blockSignals(False)
        self.clear_focus.setVisible(self.context.prefs.pets.focus_id is not None)
        self.refresh_grid()

    def automatic_changed(self, checked):
        self.context.prefs.pets.auto_collection = checked
        self.service.disconnected()
        self.context.save()

    def region_changed(self, *_):
        region = self.region.currentData()
        if region and region != self.context.prefs.pets.region:
            self.service.disconnected()
            self.context.prefs.pets.region = region
            self.context.save()

    def map_enabled(self, enabled):
        disabled = self.context.prefs.disabled_categories
        disabled.discard('pets') if enabled else disabled.add('pets')
        self.context.save()

    def map_filter_changed(self, *_):
        self.context.prefs.pets.map_filter = self.map_filter.currentData()
        self.context.prefs.pets.focus_id = None
        self.service.sync_map_preferences()
        self.context.save()

    def clear_map_focus(self):
        self.context.prefs.pets.focus_id = None
        self.service.sync_map_preferences()
        self.context.save()

    def refresh_grid(self, *_):
        store = self.service.store
        pets = store.select(search=self.search.text(), family=self.family.currentData() or '',
            state=self.state.currentData() or '', favorites=self.favorite_filter.isChecked())
        entries = store.profile.entries.values()
        registered = sum(entry.progress is not None and entry.progress.level is not None for entry in entries)
        favorites = sum(entry.favorite for entry in store.profile.entries.values())
        self.summary.setText(f'{registered} registrados · {favorites} favoritos · {len(pets)} pets no catálogo')
        selected = self.selected_id
        self.grid.blockSignals(True)
        self.grid.clear()
        target = None
        for pet in pets:
            entry = store.entry(pet.id)
            title = ('★ ' if entry.favorite else '') + pet.name
            item = QListWidgetItem(portrait_icon(pet.portrait), f'{title}\n{tr(progress_caption(entry))}')
            item.setData(Qt.ItemDataRole.UserRole, pet.id)
            item.setData(Qt.ItemDataRole.UserRole+1, pet.name)
            item.setData(Qt.ItemDataRole.UserRole+2, 'Não registrado' if entry.state=='unknown' else progress_caption(entry))
            item.setData(Qt.ItemDataRole.UserRole+3, entry.favorite)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setToolTip(pet.name+' · '+pet.family+'\n'+tr(progress_caption(entry)))
            self.grid.addItem(item)
            if pet.id == selected:
                target = item
        if target is None and self.grid.count():
            target = self.grid.item(0)
        self.grid.setCurrentItem(target)
        self.grid.blockSignals(False)
        self.selected_id = target.data(Qt.ItemDataRole.UserRole) if target else None
        self.empty.setVisible(not pets)
        self.refresh_detail()

    def selection_changed(self, item, *_):
        self.selected_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.refresh_detail()

    def refresh_detail(self, *_):
        store = self.service.store
        pet = store.by_id.get(self.selected_id)
        self._refreshing = True
        for widget in (self.favorite, self.goal, self.record_button):
            widget.setEnabled(pet is not None)
        if pet is None:
            self.picture.clear(); self.name.setText('Escolha um pet'); self.progress.clear()
            self.family_caption.clear(); self.sources.clear(); self.farm_button.setEnabled(False)
            self.source_button.hide(); self.origin.hide(); self.restore_button.hide()
            self._refreshing = False
            return
        entry = store.entry(pet.id)
        self.picture.setPixmap(QPixmap(str(PACKAGE/'assets'/pet.portrait)).scaled(
            120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.name.setText(pet.name)
        self.family_caption.setText('Especial' if pet.family == 'Special' else pet.family)
        progress = entry.progress
        caption = progress_caption(entry)
        if progress and progress.souls is not None:
            caption += f'\n{progress.souls} almas registradas'
        if progress:
            caption += '\n' + ('Registrado por você' if progress.origin == 'manual' else 'Atualizado pelo jogo')
        self.progress.setText(caption)
        self.favorite.setChecked(entry.favorite)
        index = self.goal.findData(entry.goal)
        if index < 0:
            self.goal.addItem(f'Chegar ao nível {entry.goal}', entry.goal); index = self.goal.count()-1
        self.goal.setCurrentIndex(index)
        names = list(dict.fromkeys(m.name for m in pet.monsters))
        self.sources.setText('\n'.join(names[:5]) + (f'\n+{len(names)-5} outros monstros' if len(names)>5 else '')
            if names else 'Consulte a fonte de obtenção deste pet.')
        self.farm_button.setEnabled(self.show_farm is not None and self.has_farm(pet.id))
        self.farm_button.setToolTip('Locais documentados na referência do jogo.' if self.farm_button.isEnabled()
            else 'Ainda não há locais mapeados para este pet nesta base.')
        self.restore_button.setVisible(entry.observed is not None and entry.use_manual)
        visible = self.provenance.isChecked()
        self.origin.setVisible(visible); self.source_button.setVisible(visible)
        self.origin.setText('Catálogo de referência Global · cliente de 18/09/2026.\n'
            'A disponibilidade e os locais podem variar por região. Retrato original © NC Corporation.')
        self._refreshing = False

    def has_farm(self, pet_id):
        method = getattr(self.service, 'has_farm', None)
        return bool(method and method(pet_id))

    def favorite_changed(self, checked):
        if not self._refreshing and self.selected_id is not None:
            self.service.edit(self.selected_id, favorite=checked)

    def goal_changed(self, *_):
        if not self._refreshing and self.selected_id is not None and self.goal.currentData():
            self.service.edit(self.selected_id, goal=self.goal.currentData())

    def record(self):
        if self.selected_id is None:
            return
        store = self.service.store
        dialog = ProgressDialog(store.by_id[self.selected_id], store.entry(self.selected_id), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.service.record(self.selected_id, None if dialog.level.value()<0 else dialog.level.value(),
                                dialog.souls.value() if dialog.known.isChecked() else None)

    def restore_observed(self):
        if self.selected_id is not None:
            self.service.edit(self.selected_id, use_manual=False)

    def open_farm(self):
        if self.selected_id is not None and self.show_farm:
            self.show_farm(self.selected_id)

    def open_source(self):
        pet = self.service.store.by_id.get(self.selected_id)
        if pet:
            QDesktopServices.openUrl(QUrl(pet.source))

    def profile_changed(self, *_):
        key = self.profiles.currentData()
        if key and key != self.service.store.collection.active_profile:
            try:
                self.service.store.select_profile(key); self.service.changed.emit()
            except (OSError, ValueError):
                self.feedback.setText('Não foi possível salvar sua coleção. Tente novamente.')

    def new_profile(self):
        name, accepted = QInputDialog.getText(self, tr('Nova coleção'), tr('Nome da coleção'))
        if accepted and name.strip():
            try:
                self.service.store.create_profile(name); self.service.changed.emit()
            except (OSError, ValueError):
                self.feedback.setText('Não foi possível salvar sua coleção. Tente novamente.')

    def import_collection(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Importar coleção'), '', 'JSON (*.json)')
        if path:
            try:
                from pathlib import Path
                self.service.store.import_collection(Path(path)); self.service.changed.emit()
                self.feedback.setText('Coleção importada. A cópia anterior foi preservada.')
            except (OSError, ValueError):
                self.feedback.setText('Não foi possível importar esta coleção. Seu progresso foi preservado.')

    def export_collection(self):
        path, _ = QFileDialog.getSaveFileName(self, tr('Exportar coleção'), 'strigoi-pets.json', 'JSON (*.json)')
        if path:
            try:
                from pathlib import Path
                self.service.store.export_collection(Path(path))
                self.feedback.setText('Coleção exportada.')
            except (OSError, ValueError):
                self.feedback.setText('Não foi possível exportar sua coleção.')
