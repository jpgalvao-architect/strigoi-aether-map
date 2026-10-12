# SPDX-License-Identifier: GPL-3.0-only
"""Compact observed-damage table, local history and optional external overlay."""
from datetime import datetime
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QHeaderView, QApplication, QSizeGrip
from PySide6.QtWidgets import QTableWidgetItem as DataItem
from app.ui.localized_widgets import (QWidget, QFrame, QComboBox, QCheckBox, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QDoubleSpinBox)
from app.ui.widgets import label, page_header, row
from app.core.i18n import tr, clock, calendar_date
from app.ui.combat_classes import class_icon, class_label


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


def damage_table():
    table = QTableWidget(0, 5)
    table.setIconSize(QSize(20, 20))
    table.setHorizontalHeaderLabels(["Posição", "Jogador", "Dano", "DPS", "Participação"])
    table.verticalHeader().hide()
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


class CombatPanel(QFrame):
    def __init__(self, service, page):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.service, self.page = service, page
        self.drag = None
        self.setWindowTitle("Strigoi · Combate")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet("QFrame{background:#171e26;color:#eaf0f8;border:1px solid #53616d;} QLabel{border:0;} QTableWidget{border:0;background:#171e26;} QPushButton{padding:3px 8px;}")
        self.resize(460, 250)
        self.setMinimumSize(360, 180)
        self.setMaximumSize(3840, 2160)
        layout = QVBoxLayout(self); layout.setContentsMargins(8, 6, 8, 6)
        self.heading = label("Dano observado", "eyebrow")
        self.heading.mousePressEvent = self.press
        self.heading.mouseMoveEvent = self.move_panel
        self.heading.mouseReleaseEvent = self.release
        top = QHBoxLayout(); top.addWidget(self.heading, 1)
        hide = QPushButton("Ocultar"); hide.clicked.connect(lambda: page.panel_visible.setChecked(False)); top.addWidget(hide)
        layout.addLayout(top)
        self.state = label("", "subtitle", True); layout.addWidget(self.state)
        self.table = damage_table(); layout.addWidget(self.table, 1)
        layout.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignRight)
        prefs = service.context.prefs.combat
        if prefs.position:
            self.move(*prefs.position)
        if prefs.size:
            self.resize(*prefs.size)
        self.apply_settings()
        service.changed.connect(self.refresh)

    def press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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
        prefs.size = (self.width(), self.height())
        self.service.context.save()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.isVisible():
            self.save_geometry()

    def apply_settings(self):
        prefs = self.service.context.prefs.combat
        visible = prefs.panel_visible
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, prefs.locked)
        self.setWindowOpacity(prefs.opacity)
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
        if not prefs.panel_visible:
            self.hide(); return
        self.show()
        snapshot = self.page.selected_snapshot()
        self.heading.setText("Dano observado · {tempo}".format(tempo=duration(snapshot["duration_ms"])))
        self.state.setText("Dados parciais · SA experimental" if snapshot["total"] else self.service.status)
        fill_table(self.table, snapshot)


class CombatPage(QWidget):
    def __init__(self, context, service):
        super().__init__()
        self.context, self.service = context, service
        self.saved = []
        self.target_ids = []
        layout = QVBoxLayout(self); layout.setContentsMargins(28, 22, 28, 22)
        layout.addWidget(page_header("Combate", "Acompanhe o dano observado do grupo e guarde os resultados da instância."))
        layout.addWidget(label("Experimental: a leitura de combate ainda precisa de validação em SA.", "banner", True))
        self.status = label("", "subtitle", True); layout.addWidget(self.status)
        layout.addWidget(label("O combate é medido automaticamente enquanto o Strigoi está aberto. A próxima instância reconhecida começa com um placar zerado e preserva o histórico. Você pode desativar a medição nas Configurações.", "subtitle", True))
        component = QPushButton("Abrir download oficial do Npcap")
        component.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://npcap.com/#download")))
        layout.addWidget(component)
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
        self.table = damage_table(); layout.addWidget(self.table, 1)
        self.total = label("", "subtitle", True); layout.addWidget(self.total)
        self.copy = QPushButton("Copiar resultado"); self.copy.clicked.connect(self.copy_result)
        self.finish = QPushButton("Encerrar encontro"); self.finish.clicked.connect(self.finish_encounter)
        self.delete = QPushButton("Excluir resultado salvo"); self.delete.clicked.connect(self.delete_saved)
        layout.addLayout(row(self.copy, self.finish, self.delete))
        self.panel_visible = QCheckBox("Mostrar painel flutuante")
        self.panel_visible.setChecked(context.prefs.combat.panel_visible)
        self.locked = QCheckBox("Travar painel · clique através")
        self.locked.setChecked(context.prefs.combat.locked)
        self.opacity = QDoubleSpinBox(); self.opacity.setRange(.2, 1); self.opacity.setSingleStep(.1)
        self.opacity.setValue(context.prefs.combat.opacity)
        layout.addLayout(row(self.panel_visible, self.locked, label("Opacidade"), self.opacity))
        self.panel = CombatPanel(service, self)
        restore = QPushButton("Restaurar painel"); restore.clicked.connect(self.restore_panel)
        layout.addWidget(restore)
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
        self.quality.setText("Dados parciais · SA experimental" if snapshot["total"] else "Aguardando dano observado")
        self.total.setText("Dano observado: {dano} · Tempo: {tempo}".format(
            dano=short_number(snapshot["total"]), tempo=duration(snapshot["duration_ms"])))

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
        self.panel.resize(460, 250)
        self.panel.move(QGuiApplication.primaryScreen().availableGeometry().topLeft() + QPoint(40, 100))
        self.panel.save_geometry()

    def shutdown(self):
        self.panel.close()
