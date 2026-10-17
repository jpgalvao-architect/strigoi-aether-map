# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path

from PySide6.QtWidgets import QVBoxLayout
from app.ui.localized_widgets import QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QMessageBox, QSpinBox, QWidget

from app.core.models import Preferences
from app.infrastructure.storage import atomic_json
from app.ui.widgets import button, label, page_header, row
from app.core.i18n import set_language


class SettingsPage(QWidget):
    def __init__(self, context, tray):
        super().__init__()
        self.context = context
        self.tray = tray
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 20, 26, 20)
        layout.addWidget(page_header("Do seu jeito", "Preferências salvas neste computador. As alterações de filtros são aplicadas imediatamente."))
        language_group=QGroupBox('Idioma')
        language_form=QFormLayout(language_group)
        self.language=QComboBox()
        self.language.addItem('Português (Brasil)','pt_BR')
        self.language.addItem('English (United States)','en_US')
        self.language.setCurrentIndex(self.language.findData(context.prefs.ui_language))
        language_form.addRow('Idioma do aplicativo',self.language)
        language_form.addRow(label('O idioma muda imediatamente. Sua seleção fica salva neste computador.','subtitle',True))
        self.language.currentIndexChanged.connect(self.choose_language)
        layout.addWidget(language_group)
        quick_group = QGroupBox("Controles durante o jogo")
        quick_form = QFormLayout(quick_group)
        self.quick_enabled = QCheckBox("Mostrar menu rápido de overlay")
        self.quick_enabled.setChecked(context.prefs.quick_menu.enabled)
        self.quick_enabled.toggled.connect(self.change_quick_menu)
        quick_form.addRow(self.quick_enabled)
        quick_form.addRow(label("Os overlays se ocultam ao sair do jogo ou abrir um menu reconhecido. A medição continua.", "subtitle", True))
        self.combat_automatic = QCheckBox("Medir combate automaticamente")
        self.combat_automatic.setChecked(context.prefs.combat.auto_capture)
        self.combat_automatic.toggled.connect(self.change_combat_automatic)
        quick_form.addRow(self.combat_automatic)
        layout.addWidget(quick_group)
        general = QGroupBox("Horário e dados")
        form = QFormLayout(general)
        self.timezone = QComboBox()
        self.timezone.setEditable(True)
        self.timezone.addItems(["local", "America/Fortaleza", "America/Sao_Paulo", "UTC", "America/New_York", "Europe/Lisbon", "Asia/Seoul"])
        self.timezone.setCurrentText(context.prefs.timezone)
        form.addRow("Fuso dos horários", self.timezone)
        self.auto = QCheckBox("Atualizar agenda online automaticamente")
        self.auto.setChecked(context.prefs.remote_auto_refresh)
        form.addRow(self.auto)
        self.interval = QSpinBox()
        self.interval.setRange(5, 1440)
        self.interval.setValue(context.prefs.remote_interval_minutes)
        self.interval.setSuffix(" min")
        form.addRow("Intervalo de atualização", self.interval)
        layout.addWidget(general)
        notifications = QGroupBox("Alertas de eventos")
        alert_layout = QVBoxLayout(notifications)
        self.enabled = QCheckBox("Habilitar notificações do sistema")
        self.enabled.setChecked(context.prefs.notifications.enabled)
        alert_layout.addWidget(self.enabled)
        self.leads = {}
        for lead in [5, 15, 30]:
            checkbox = QCheckBox(f"Avisar {lead} minutos antes")
            checkbox.setChecked(lead in context.prefs.notifications.lead_minutes)
            self.leads[lead] = checkbox
        alert_layout.addLayout(row(*self.leads.values()))
        self.kind_box = QWidget()
        self.kind_layout = QVBoxLayout(self.kind_box)
        self.kind_layout.setContentsMargins(0, 0, 0, 0)
        alert_layout.addWidget(self.kind_box)
        self.refresh_kinds()
        context.events_changed.connect(self.refresh_kinds)
        alert_layout.addWidget(label("Alertas exigem o app em execução. Ao fechar a janela, o app é encerrado. A entrega visual depende das configurações de notificações e Não Perturbe do Windows.", "subtitle", True))
        layout.addWidget(notifications)
        layout.addLayout(row(button("Salvar preferências", self.save, True), button("Testar notificação", self.test_notification)))
        layout.addLayout(row(button("Importar atlas JSON", self.import_dataset), button("Exportar preferências", self.export_preferences)))
        self.feedback = label("", "subtitle", True)
        layout.addWidget(self.feedback)
        layout.addWidget(label(f"Armazenamento local: {context.directory}", "subtitle", True))
        layout.addStretch()

    def change_quick_menu(self, enabled):
        self.context.prefs.quick_menu.enabled = enabled
        self.context.save()

    def change_combat_automatic(self, enabled):
        self.context.prefs.combat.auto_capture = enabled
        self.context.save()

    def refresh_kinds(self):
        while self.kind_layout.count():
            self.kind_layout.takeAt(0).widget().deleteLater()
        self.kinds = {}
        for kind in sorted({event.kind for event in self.context.calendar_events}):
            checkbox = QCheckBox(kind)
            checkbox.setChecked(kind not in self.context.prefs.notifications.disabled_kinds)
            self.kinds[kind] = checkbox
            self.kind_layout.addWidget(checkbox)

    def choose_language(self):
        selected=self.language.currentData()
        if selected not in ('pt_BR','en_US'):return
        self.context.prefs.ui_language=selected
        set_language(selected)
        self.context.save()

    def save(self):
        try:
            data = self.context.prefs.model_dump()
            data.update(timezone=self.timezone.currentText().strip(), ui_language=self.language.currentData(), remote_auto_refresh=self.auto.isChecked(), remote_interval_minutes=self.interval.value())
            data["notifications"] = {"enabled": self.enabled.isChecked(), "lead_minutes": [key for key, checkbox in self.leads.items() if checkbox.isChecked()], "disabled_kinds": {key for key, checkbox in self.kinds.items() if not checkbox.isChecked()}}
            self.context.prefs = Preferences.model_validate(data)
            self.context.save()
            self.feedback.setText("Preferências aplicadas.")
        except ValueError as exc:
            self.feedback.setText(f"Revise o fuso horário: {exc}")

    def test_notification(self):
        self.tray.notify("Strigoi está por perto", "Este é um alerta de teste do seu companion.")
        self.feedback.setText("Alerta de teste solicitado; confira a área de notificações do Windows.")

    def import_dataset(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Importar atlas", "", "JSON (*.json)")
        if filename:
            try:
                self.context.import_dataset(Path(filename))
                self.feedback.setText("Atlas validado e importado. O overlay foi desligado para revisão da calibração.")
            except Exception as exc:
                QMessageBox.warning(self, "Atlas não importado", str(exc))

    def export_preferences(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar preferências", "preferences.json", "JSON (*.json)")
        if filename:
            try:
                atomic_json(Path(filename), self.context.prefs)
                self.feedback.setText("Preferências exportadas.")
            except OSError as exc:
                self.feedback.setText(str(exc))
