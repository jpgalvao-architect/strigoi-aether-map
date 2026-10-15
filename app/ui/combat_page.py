# SPDX-License-Identifier: GPL-3.0-only
"""Compact observed-damage table, local history and optional external overlay."""
from datetime import datetime
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QHeaderView, QApplication, QScrollArea
from PySide6.QtWidgets import QTableWidgetItem as DataItem
from app.ui.localized_widgets import (QWidget, QFrame, QComboBox, QCheckBox, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QDoubleSpinBox, QToolButton)
from app.ui.widgets import label, page_header, row
from app.core.i18n import tr, clock, calendar_date
from app.ui.combat_classes import colored_class_icon as class_icon, class_label
from app.ui.overlay_visibility import OverlayVisibilityMixin
from app.ui.hud import HudSurface
from app.ui.icons import icon
from app.ui.identity import emblem_icon
from app.ui.combat_bars import DpsRow, ranked_rows


def short_number(value):
    if value is None:
        return "—"
    suffix = ""
    for cutoff, unit in ((10**9, "B"), (10**6, "M"), (10**3, "K")):
        if value >= cutoff:
            value, suffix = value / cutoff, unit
            break
    return (f"{value:.1f}" if suffix else f"{value:.0f}") + suffix


def duration(ms):
    seconds = ms // 1000
    return f"{seconds // 60:02}:{seconds % 60:02}"


def team_pending(snapshot):
    return snapshot.get("team_pvp", False) and "missing_roster" in snapshot["issues"]


def damage_table():
    table = QTableWidget(0, 5)
    table.setIconSize(QSize(20, 20))
    table.setHorizontalHeaderLabels(["Posição", "Jogador", "Dano", "DPS", "Participação"])
    table.verticalHeader().hide()
    table.verticalHeader().setDefaultSectionSize(42)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.setMinimumHeight(120)
    return table


def fill_table(table, snapshot):
    rows = list(snapshot["rows"])
    if snapshot["unattributed"]:
        rows.append({"rank": None, "name": tr("Não atribuído"), "damage": snapshot["unattributed"],
            "share": snapshot["unattributed"] / snapshot["total"], "dps": None, "local": False})
    table.setRowCount(len(rows))
    for index, item in enumerate(rows):
        name = item["name"] or tr("Participante não identificado")
        values = [str(item["rank"]) if item["rank"] is not None else "—", name,
            short_number(item["damage"]), short_number(item["dps"]), f"{item['share'] * 100:.1f}%"]
        for column, value in enumerate(values):
            cell = DataItem(value)  # User/game identities are never translated.
            if column == 1 and item["rank"] is not None:
                job = item.get("job", 0)  # Older history entries may have no class metadata.
                cell.setIcon(class_icon(job))
                cell.setToolTip(class_label(job))
            if column != 1:
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if item["local"]:
                font = cell.font(); font.setBold(True); cell.setFont(font)
            if column == 2:
                cell.setToolTip(str(item["damage"]))
            table.setItem(index, column, cell)


class CombatPanel(HudSurface):
    def __init__(self, service, page):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.service, self.page = service, page
        self.drag = None
        self.setWindowTitle("Azphelumbra · Combate")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(346)
        layout = QVBoxLayout(self); layout.setContentsMargins(6, 3, 6, 4); layout.setSpacing(4)
        self.heading = label("Combate")
        from PySide6.QtWidgets import QSizePolicy
        self.heading.setMinimumWidth(0)
        self.heading.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.heading.mousePressEvent = self.press
        self.heading.mouseMoveEvent = self.move_panel
        self.heading.mouseReleaseEvent = self.release
        top = QHBoxLayout(); top.setContentsMargins(4,0,4,0); top.setSpacing(6)
        mark = label(''); mark.setPixmap(emblem_icon().pixmap(21,21)); top.addWidget(mark)
        top.addWidget(self.heading, 1)
        self.lock = QToolButton(); self.lock.setFixedSize(24,24)
        self.lock.clicked.connect(lambda: page.locked.setChecked(not page.locked.isChecked())); top.addWidget(self.lock)
        self.expand_button = QToolButton(); self.expand_button.setFixedSize(24,24)
        self.expand_button.clicked.connect(self.toggle_expanded); top.addWidget(self.expand_button)
        layout.addLayout(top)
        self.scroller = QScrollArea(); self.scroller.setWidgetResizable(True)
        self.scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget = QWidget(); self.list_widget.setObjectName('hudList')
        self.rows_layout = QVBoxLayout(self.list_widget); self.rows_layout.setContentsMargins(0,0,0,0); self.rows_layout.setSpacing(4)
        self.scroller.setWidget(self.list_widget); layout.addWidget(self.scroller)
        self.rows = []; self.row_keys = None
        self.summary = label('', 'subtitle'); layout.addWidget(self.summary)
        self.state = label('', 'subtitle', True); layout.addWidget(self.state)
        bottom = QHBoxLayout(); bottom.setContentsMargins(4,0,4,0)
        self.group_total = label('', 'subtitle'); bottom.addWidget(self.group_total,1)
        self.details_button = QToolButton(); self.details_button.setText('Detalhes +')
        self.details_button.clicked.connect(self.toggle_details); bottom.addWidget(self.details_button)
        layout.addLayout(bottom)
        prefs = service.context.prefs.combat
        if prefs.position:
            self.move(*prefs.position)
        self.apply_settings()
        service.changed.connect(self.refresh)

    def press(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.service.context.prefs.combat.locked:
            self.drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def move_panel(self, event):
        if self.drag is not None:
            self.move(event.globalPosition().toPoint() - self.drag)

    def release(self, _):
        self.drag = None
        self.save_geometry()

    def save_geometry(self):
        prefs = self.service.context.prefs.combat
        prefs.position = (self.x(), self.y())
        self.service.context.save()

    def apply_settings(self):
        prefs = self.service.context.prefs.combat
        visible = prefs.panel_visible and self.service.in_instance
        # Pin locks dragging; controls remain usable. Hiding/capture are independent.
        self.setWindowOpacity(prefs.opacity)
        self.lock.setIcon(icon('lock' if prefs.locked else 'unlock'))
        self.lock.setToolTip('Destravar posição' if prefs.locked else 'Travar posição')
        if visible:
            available = QGuiApplication.screens()
            rectangle = self.frameGeometry()
            if not any(screen.availableGeometry().intersects(rectangle) for screen in available):
                self.move(QGuiApplication.primaryScreen().availableGeometry().topLeft() + QPoint(40, 100))
            self.show()
        else:
            self.hide()

    def refresh(self):
        prefs = self.service.context.prefs.combat
        if not prefs.panel_visible or not self.service.in_instance:
            self.hide(); return
        self.show()
        snapshot = (self.service.engine.snapshot() if self.page.scope.currentData()=='history'
                    else self.page.selected_snapshot())
        self.heading.setText((snapshot.get('run_name') or tr('Combate'))+'  '+duration(snapshot['duration_ms']))
        self.heading.setToolTip(snapshot.get('run_name') or tr('Combate'))
        self.state.setText('Time ainda não identificado · dano confirmado apenas' if team_pending(snapshot)
                           else 'Dados parciais' if snapshot.get('issues') and snapshot['total'] else '')
        self.state.setVisible(bool(self.state.text()))
        data = ranked_rows(snapshot)
        keys = tuple((r.get('actor_id'),r.get('server'),r.get('name'),r['rank'] is None) for r in data)
        if keys != self.row_keys:
            pool = dict(zip(self.row_keys or (),self.rows))
            self.row_keys = keys
            while self.rows_layout.count(): self.rows_layout.takeAt(0)
            self.rows = []
            for key,item in zip(keys,data):
                row_widget = pool.pop(key,None)
                if row_widget is None:
                    row_widget = DpsRow(item)
                    row_widget.clicked.connect(self.fit_content)
                self.rows.append(row_widget)
                self.rows_layout.addWidget(row_widget)
            for removed in pool.values():
                removed.hide();removed.setParent(None);removed.deleteLater()
        for row_widget, item in zip(self.rows,data):
            row_widget.set_data(item); row_widget.set_details(prefs.panel_details)
        mine = next((r for r in data if r.get('local')),None)
        self.summary.setText(tr('Você · {dps} DPS').format(dps=short_number(mine['dps'])) if mine else 'Aguardando dano observado')
        group_dps = snapshot['total']*1000/snapshot['duration_ms'] if snapshot['duration_ms'] else None
        self.group_total.setText(tr('Grupo · {dps} DPS').format(dps=short_number(group_dps)))
        self.details_button.setText('Detalhes −' if prefs.panel_details else 'Detalhes +')
        self.expand_button.setIcon(icon('chevron-up' if prefs.panel_expanded else 'chevron-down'))
        self.expand_button.setToolTip('Recolher painel' if prefs.panel_expanded else 'Expandir painel')
        self.fit_content()

    def fit_content(self):
        expanded = self.service.context.prefs.combat.panel_expanded
        self.scroller.setVisible(expanded and bool(self.rows))
        self.summary.setVisible(not expanded or not self.rows)
        screen = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        available = max(70,min(440,screen.availableGeometry().height()-160))
        self.scroller.setFixedHeight(min(available,sum(r.height()+4 for r in self.rows)))
        self.layout().activate()
        self.setFixedHeight(self.layout().sizeHint().height())
        area = screen.availableGeometry()
        self.move(max(area.left(),min(self.x(),area.right()-self.width()+1)),
                  max(area.top(),min(self.y(),area.bottom()-self.height()+1)))

    def toggle_expanded(self):
        prefs = self.service.context.prefs.combat
        prefs.panel_expanded = not prefs.panel_expanded
        self.service.context.save(); self.refresh()

    def toggle_details(self):
        prefs = self.service.context.prefs.combat
        prefs.panel_details = not prefs.panel_details
        self.service.context.save(); self.refresh()


class CombatPage(QWidget):
    def __init__(self, context, service):
        super().__init__()
        self.context, self.service = context, service
        self.saved = []
        self.target_ids = []
        layout = QVBoxLayout(self); layout.setContentsMargins(28, 22, 28, 22)
        layout.addWidget(page_header("Cada contribuição conta.", "Combate · relatório do grupo"))
        self.advanced = QWidget(); options = QVBoxLayout(self.advanced); options.setContentsMargins(0,0,0,0)
        options.addWidget(label("Experimental: a leitura de combate ainda precisa de validação em SA.", "subtitle", True))
        self.status = label("", "subtitle", True)
        options.addWidget(self.status)
        options.addWidget(label("A medição começa automaticamente e aguarda o jogo. O painel aparece nas instâncias reconhecidas e se oculta ao sair, mantendo a leitura ativa. A próxima entrada reconhecida zera o placar e preserva o histórico.", "subtitle", True))
        component = QPushButton("Abrir download oficial do Npcap")
        component.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://npcap.com/#download")))
        options.addWidget(component)
        self.scope = QComboBox()
        for title, value in (("Encontro atual", "encounter"), ("Instância inteira", "instance"), ("Histórico", "history")):
            self.scope.addItem(title, value)
        self.boss_only = QCheckBox("Só o alvo selecionado")
        self.target = QComboBox(); self.target.addItem("Selecione o boss para filtrar", None)
        self.target.currentIndexChanged.connect(self.choose_target)
        self.history_combo = QComboBox()
        self.history_combo.currentIndexChanged.connect(self.refresh)
        self.scope.currentIndexChanged.connect(self.refresh)
        self.boss_only.toggled.connect(self.refresh)
        layout.addLayout(row(self.scope, self.boss_only, self.target))
        layout.addWidget(self.history_combo)
        self.quality = label("", "eyebrow", True); layout.addWidget(self.quality)
        summary = QHBoxLayout(); summary.setSpacing(35)
        self.metrics = []
        for title in ('Dano do grupo','Seu DPS','Tempo de combate'):
            copy = QVBoxLayout(); copy.setSpacing(4); copy.addWidget(label(title,'subtitle'))
            value = label('—','number'); copy.addWidget(value); summary.addLayout(copy)
            self.metrics.append(value)
        summary.addStretch(); layout.addLayout(summary)
        self.table = damage_table(); layout.addWidget(self.table, 1)
        self.total = label("", "subtitle", True); layout.addWidget(self.total)
        self.copy = QPushButton("Copiar resultado"); self.copy.clicked.connect(self.copy_result)
        self.finish = QPushButton("Encerrar encontro"); self.finish.clicked.connect(self.finish_encounter)
        self.delete = QPushButton("Excluir resultado salvo"); self.delete.clicked.connect(self.delete_saved)
        actions = QHBoxLayout(); actions.addWidget(label('A medição acompanha a instância automaticamente.','subtitle'),1)
        actions.addWidget(self.copy);layout.addLayout(actions)
        options.addLayout(row(self.finish,self.delete))
        self.panel_visible = QCheckBox("Mostrar painel automaticamente em instâncias")
        self.panel_visible.setChecked(context.prefs.combat.panel_visible)
        self.locked = QCheckBox("Travar posição do painel")
        self.locked.setChecked(context.prefs.combat.locked)
        self.opacity = QDoubleSpinBox(); self.opacity.setRange(.2, 1); self.opacity.setSingleStep(.1)
        self.opacity.setValue(context.prefs.combat.opacity)
        options.addLayout(row(self.panel_visible, self.locked, label("Opacidade"), self.opacity))
        self.panel = CombatPanel(service, self)
        restore = QPushButton("Restaurar painel"); restore.clicked.connect(self.restore_panel)
        options.addWidget(restore)
        self.advanced_button = QPushButton('Ajustes de combate'); self.advanced_button.setCheckable(True)
        self.advanced_button.setObjectName('quiet'); self.advanced_button.toggled.connect(self.advanced.setVisible)
        layout.addWidget(self.advanced_button);layout.addWidget(self.advanced);self.advanced.hide()
        self.panel_visible.toggled.connect(self.set_panel)
        self.locked.toggled.connect(self.set_locked)
        self.opacity.valueChanged.connect(self.set_opacity)
        service.changed.connect(self.refresh)
        service.error.connect(self.status.setText)
        service.history_changed.connect(self.reload_history)
        service.run_started.connect(self.new_instance)
        self.reload_history()
        self.refresh()

    def new_instance(self):
        self.target_ids = []
        self.target.blockSignals(True)
        self.target.clear()
        self.target.addItem("Selecione o boss para filtrar", None)
        self.target.blockSignals(False)
        self.scope.setCurrentIndex(0)
        self.refresh()

    def choose_target(self):
        self.service.engine.select_boss(self.target.currentData())
        self.refresh()

    def selected_snapshot(self):
        if self.scope.currentData() == "history" and self.saved:
            index = max(0, self.history_combo.currentIndex())
            return self.saved[index][1]
        return self.service.engine.snapshot(self.scope.currentData() or "encounter", self.boss_only.isChecked())

    def refresh(self, *_):
        self.panel_visible.blockSignals(True)
        self.panel_visible.setChecked(self.context.prefs.combat.panel_visible)
        self.panel_visible.blockSignals(False)
        self.finish.setEnabled(self.service.engine.current is not None)
        self.status.setText(self.service.status)
        history = self.scope.currentData() == "history"
        self.history_combo.setVisible(history)
        self.delete.setEnabled(history and bool(self.saved))
        self.target.setEnabled(not history and self.scope.currentData() == "encounter")
        self.boss_only.setEnabled(self.target.isEnabled())
        encounter = self.service.engine.current or (self.service.engine.encounters[-1] if self.service.engine.encounters else None)
        targets = sorted({hit.target for hit in encounter.hits}) if encounter else []
        ids = [(actor, self.service.engine.entities[actor].name if actor in self.service.engine.entities else "") for actor in targets]
        if ids != self.target_ids:
            selected = self.target.currentData()
            self.target.blockSignals(True); self.target.clear()
            self.target.addItem("Selecione o boss para filtrar", None)
            for actor, name in ids:
                self.target.addItem(name or "Alvo #{numero}".format(numero=actor), actor)
            self.target.setCurrentIndex(max(0, self.target.findData(selected)))
            self.target.blockSignals(False); self.target_ids = ids
        snapshot = self.selected_snapshot()
        self.copy.setEnabled(snapshot["total"] > 0)
        fill_table(self.table, snapshot)
        self.quality.setText("Time ainda não identificado · dano confirmado apenas" if team_pending(snapshot)
            else "Dados parciais · SA experimental" if snapshot["total"] else "Aguardando dano observado")
        self.total.setText("Dano observado: {dano} · Tempo: {tempo}".format(
            dano=short_number(snapshot["total"]), tempo=duration(snapshot["duration_ms"])))
        mine = next((r for r in snapshot['rows'] if r.get('local')),None)
        for widget,value in zip(self.metrics,[short_number(snapshot['total']),short_number(mine['dps']) if mine else '—',duration(snapshot['duration_ms'])]):
            widget.setText(value)

    def reload_history(self):
        self.saved = []
        self.history_combo.blockSignals(True); self.history_combo.clear()
        for stamp, summary in (self.service.history.list() if self.service.history is not None else []):
            self.saved.append((summary["run_id"], summary))
            when = datetime.fromisoformat(stamp).astimezone()
            prefix = f"{calendar_date(when)} {clock(when)} · " + (summary["run_name"] or tr("Instância"))
            self.history_combo.addItem(prefix)
            for number, attempt in enumerate(summary.get("attempts", []), 1):
                self.saved.append((summary["run_id"], attempt))
                self.history_combo.addItem(prefix + tr(" · Encontro {numero}").format(numero=number))
        self.history_combo.blockSignals(False)

    def finish_encounter(self):
        self.service.engine.finish_encounter()
        self.service.save(); self.reload_history(); self.service.changed.emit()

    def copy_result(self):
        data = self.selected_snapshot()
        if not data["total"]:
            return
        lines = [tr("Dano observado · dados parciais") + " · " + duration(data["duration_ms"])]
        for item in data["rows"]:
            lines.append(f"{item['rank']}. {item['name'] or tr('Participante não identificado')}: {item['damage']} · {short_number(item['dps'])} DPS · {item['share']*100:.1f}%")
        if data["unattributed"]:
            lines.append(tr("Não atribuído") + ": " + str(data["unattributed"]))
        QApplication.clipboard().setText("\n".join(lines))

    def delete_saved(self):
        if self.saved and self.service.history is not None:
            self.service.history.delete(self.saved[max(0, self.history_combo.currentIndex())][0])
            self.reload_history(); self.refresh()

    def set_panel(self, visible):
        self.context.prefs.combat.panel_visible = visible
        self.context.save(); self.panel.apply_settings(); self.panel.refresh()

    def set_locked(self, locked):
        self.context.prefs.combat.locked = locked
        self.context.save(); self.panel.apply_settings()

    def set_opacity(self, opacity):
        self.context.prefs.combat.opacity = opacity
        self.context.save(); self.panel.apply_settings()

    def restore_panel(self):
        self.panel.fit_content()
        self.panel.move(QGuiApplication.primaryScreen().availableGeometry().topLeft() + QPoint(40, 100))
        self.panel.save_geometry()

    def shutdown(self):
        self.panel.close()
