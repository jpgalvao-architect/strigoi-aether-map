# SPDX-License-Identifier: GPL-3.0-only
from datetime import UTC, datetime
from pathlib import Path
import json

from PySide6.QtCore import QThread, QTimer, Signal, Qt
from PySide6.QtWidgets import QHeaderView, QVBoxLayout
from app.ui.localized_widgets import QCheckBox, QComboBox, QFileDialog, QGroupBox, QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem, QWidget

from app.modules.events.providers import RemoteJsonProvider
from app.infrastructure.storage import PACKAGE
from app.modules.events.service import countdown, display_time, occurrences
from app.ui.icons import icon,event_icon
from app.ui.widgets import button, label, page_header, row


class RefreshWorker(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            self.loaded.emit(RemoteJsonProvider(self.url).load())
        except Exception as exc:
            self.failed.emit(str(exc))


class EventsPage(QWidget):
    def __init__(self, context):
        super().__init__()
        self.context = context
        self.worker = None
        self.last_auto_refresh = datetime.now(UTC)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 20, 26, 20)
        layout.addWidget(page_header("Eventos", "Acompanhe os próximos horários e organize seu dia."))
        self.status = label("", "badge", True)
        layout.addWidget(self.status)
        self.profile = QComboBox()
        self.profile.addItem("Agenda importada / personalizada", "custom")
        profiles = json.loads((PACKAGE/"data/schedule-profiles.json").read_text(encoding="utf-8"))
        for profile in profiles:
            self.profile.addItem("América do Sul" if profile["id"]=="reference-sa" else ("América do Sul · agenda alternativa" if profile["id"]=="curated-sa" else profile["name"]),profile["id"])
            self.profile.setItemData(self.profile.count()-1,profile["name"],Qt.ItemDataRole.ToolTipRole)
        layout.addWidget(self.profile)
        self.profile.currentIndexChanged.connect(self.change_profile)
        self.unique = QCheckBox("Mostrar o próximo horário de cada evento")
        self.unique.setChecked(True)
        self.unique.toggled.connect(self.rebuild)
        layout.addWidget(self.unique)
        self.panel_toggle=QCheckBox('Mostrar painel flutuante')
        self.panel_toggle.toggled.connect(self.toggle_panel)
        layout.addWidget(self.panel_toggle)
        from app.ui.event_selector import EventSelector
        self.panel_event = EventSelector(context)
        layout.addLayout(row(label('Evento no painel'), self.panel_event))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Evento", "Região", "Horário", "Começa em"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)
        self.url = QLineEdit(context.prefs.remote_events_url)
        self.url.setPlaceholderText("https://seu-provider/events.json (opcional)")
        self.refresh_button = button("Atualizar remoto", self.refresh_remote)
        self.import_button=button('Importar agenda',self.import_json)
        self.advanced=QGroupBox('Agenda personalizada')
        custom=QVBoxLayout(self.advanced)
        custom.addLayout(row(self.url,self.refresh_button,self.import_button))
        self.advanced.setVisible(False)
        from app.ui.localized_widgets import QToolButton
        advanced_toggle=QToolButton();advanced_toggle.setText('Usar outra agenda');advanced_toggle.setCheckable(True)
        advanced_toggle.toggled.connect(self.advanced.setVisible)
        layout.addWidget(advanced_toggle);layout.addWidget(self.advanced)
        layout.addWidget(label("Selecione um evento para consultar sua origem. Os horários seguem o fuso escolhido nas configurações.", "subtitle", True))
        layout.addWidget(button("Abrir fonte do evento selecionado", self.open_source))
        context.events_changed.connect(self.rebuild)
        context.changed.connect(self.rebuild)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        self.rebuild()

    def rebuild(self):
        now = datetime.now(UTC)
        upcoming = occurrences(self.context.feed.events, now)
        if self.unique.isChecked():
            self.items = list({item.event.id: item for item in reversed(upcoming)}.values())
            self.items.sort(key=lambda item: item.starts_at)
        else:
            self.items = upcoming[:24]
        self.table.setRowCount(len(self.items))
        for index, item in enumerate(self.items):
            values = [item.event.name, item.event.region, display_time(item.starts_at, self.context.prefs.timezone), countdown(item.starts_at, now)]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column==0:cell.setIcon(icon(event_icon(item.event)))
                cell.setToolTip(f"{value}\n{item.event.verification} • {item.event.verified_on}\n{item.event.notes}\nFuso da agenda: {item.event.schedule.timezone}")
                self.table.setItem(index, column, cell)
            self.table.setRowHeight(index, 48)
        suffix = " • HORÁRIOS FICTÍCIOS" if self.context.feed.demo else " • " + (self.context.feed.coverage or "origem não informada")
        self.status.setText('Agenda de demonstração' if self.context.feed.demo else 'Horários no seu fuso · agenda disponível offline')
        self.status.setToolTip(self.context.provider_status+suffix)
        self.panel_toggle.blockSignals(True)
        self.panel_toggle.setChecked(self.context.prefs.overlay.events_panel)
        self.panel_toggle.blockSignals(False)
        self.profile.blockSignals(True)
        known = self.context.prefs.agenda_profile
        expected = "reference-"+known.removeprefix("reference-")+"-v030" if known.startswith("reference-") else "latam-2026-10-11"
        selected = known if self.context.feed.release==expected else "custom"
        self.profile.setCurrentIndex(max(0,self.profile.findData(selected)))
        self.profile.blockSignals(False)

    def toggle_panel(self,enabled):
        self.context.prefs.overlay.events_panel=enabled
        self.context.save()

    def change_profile(self):
        key = self.profile.currentData()
        if key and key!="custom":
            try:
                self.context.select_agenda_profile(key)
            except (ValueError,OSError) as exc:
                self.status.setText(str(exc))

    def open_source(self):
        index = self.table.currentRow()
        if 0 <= index < len(self.items):
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            url = QUrl(self.items[index].event.source)
            if url.scheme() == "https" and url.host():
                QDesktopServices.openUrl(url)

    def tick(self):
        now = datetime.now(UTC)
        if self.items and self.items[0].starts_at < now:
            self.rebuild()
        for index, item in enumerate(self.items):
            self.table.item(index, 3).setText(countdown(item.starts_at, now))
        prefs = self.context.prefs
        if prefs.remote_auto_refresh and prefs.remote_events_url and (now-self.last_auto_refresh).total_seconds() >= prefs.remote_interval_minutes*60:
            self.refresh_remote(automatic=True)

    def import_json(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Importar agenda", "", "JSON (*.json)")
        if filename:
            try:
                self.context.import_events(Path(filename))
                self.context.prefs.agenda_profile = "custom"
                self.context.save()
            except Exception as exc:
                QMessageBox.warning(self, "Agenda não importada", str(exc))

    def refresh_remote(self, checked=False, automatic=False):
        if self.worker is not None:
            return
        url = self.context.prefs.remote_events_url if automatic else self.url.text().strip()
        try:
            RemoteJsonProvider(url)
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        self.context.prefs.remote_events_url = url
        self.context.save()
        self.last_auto_refresh = datetime.now(UTC)
        self.refresh_button.setEnabled(False)
        self.status.setText("Atualizando agenda… cache anterior preservado")
        self.worker = RefreshWorker(url)
        self.worker.loaded.connect(self.accept_remote)
        self.worker.failed.connect(self.remote_error)
        self.worker.finished.connect(self.cleanup_worker)
        self.worker.start()

    def accept_remote(self, feed):
        try:
            self.context.accept_feed(feed, f"Remoto atualizado {datetime.now():%H:%M} • cache offline")
            self.context.prefs.agenda_profile = "custom"
            self.context.save()
        except OSError as exc:
            self.remote_error(str(exc))

    def remote_error(self, message):
        self.context.provider_status = "Falha remota • usando cache local"
        self.status.setText(f"{self.context.provider_status}: {message}")

    def cleanup_worker(self):
        self.worker.deleteLater()
        self.worker = None
        self.refresh_button.setEnabled(True)

    def shutdown(self):
        if self.worker:
            self.worker.wait()
