# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout
from app.ui.localized_widgets import QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QMessageBox, QSpinBox, QWidget

from app.ui.calibration_dialog import CalibrationDialog
from app.ui.widgets import button, label, page_header, row


class OverlayPage(QWidget):
    def __init__(self, context, service):
        super().__init__()
        self.context = context
        self.service = service
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 20, 26, 20)
        layout.addWidget(page_header("Overlay experimental", "Uma camada visual externa, opcional e desligada a cada abertura do app."))
        layout.addWidget(label("O MVP reconhece uma posição e um zoom fixos do mapa grande. Mudanças de enquadramento exigem nova calibração. Não há detecção universal do AION 2 nem validação com o cliente real nesta versão.", "badge", True))
        group = QGroupBox("Captura e marcadores")
        form = QFormLayout(group)
        prefs = context.prefs.overlay
        self.maps = QComboBox()
        self.refresh_maps()
        self.monitor = QSpinBox()
        self.monitor.setRange(1, 16)
        self.monitor.setValue(prefs.monitor)
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(.1, 1)
        self.opacity.setSingleStep(.1)
        self.opacity.setValue(prefs.opacity)
        self.scale = QDoubleSpinBox()
        self.scale.setRange(.5, 3)
        self.scale.setSingleStep(.1)
        self.scale.setValue(prefs.scale)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(.8, 1)
        self.threshold.setSingleStep(.01)
        self.threshold.setValue(prefs.threshold)
        for title, widget in [("Mapa calibrado", self.maps), ("Monitor (ordem MSS)", self.monitor), ("Opacidade", self.opacity), ("Escala dos marcadores", self.scale), ("Confiança mínima", self.threshold)]:
            form.addRow(title, widget)
        layout.addWidget(group)
        self.calibration = label("", "subtitle", True)
        layout.addWidget(self.calibration)
        self.status = label("Desligado", "eyebrow", True)
        service.status_changed.connect(self.status.setText)
        layout.addWidget(self.status)
        self.calibrate_button = button("Calibrar com screenshot", self.calibrate)
        self.enable_button = button("Ativar nesta sessão", self.activate, True)
        layout.addLayout(row(self.calibrate_button, self.enable_button, button("Desligar captura", self.deactivate)))
        layout.addWidget(label("A calibração salva uma cópia local da imagem escolhida. A captura ao vivo fica apenas na memória, sem gravação ou upload. Escolha referências sem marcadores, para que o próprio overlay não interfira na detecção. Use janela sem bordas; fullscreen exclusivo pode impedir a captura.", "subtitle", True))
        layout.addStretch()
        context.changed.connect(self.refresh)
        self.refresh()

    def refresh_maps(self):
        self.maps.clear()
        for definition in self.context.dataset.maps:
            self.maps.addItem(definition.name, definition.id)
        self.maps.setCurrentIndex(max(0, self.maps.findData(self.context.prefs.overlay.map_id)))
        self.dataset_identity = self.context.dataset

    def refresh(self):
        if self.dataset_identity is not self.context.dataset:
            self.refresh_maps()
        active = self.context.prefs.overlay.enabled
        for widget in [self.maps, self.monitor, self.opacity, self.scale, self.threshold, self.calibrate_button, self.enable_button]:
            widget.setEnabled(not active)
        path = self.context.prefs.overlay.calibration
        self.calibration.setText("Calibração local: " + (Path(path).name if path else "ainda não configurada"))

    def save_fields(self):
        prefs = self.context.prefs.overlay
        prefs.map_id = self.maps.currentData()
        prefs.monitor = self.monitor.value()
        prefs.opacity = self.opacity.value()
        prefs.scale = self.scale.value()
        prefs.threshold = self.threshold.value()
        self.context.save()

    def calibrate(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Screenshot do monitor inteiro, com mapa aberto", "", "Imagens (*.png *.jpg *.jpeg)")
        if filename:
            try:
                self.save_fields()
                dialog = CalibrationDialog(Path(filename), self.maps.currentData(), self.context.directory, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.context.prefs.overlay.calibration = dialog.result_path
                    self.context.save()
            except Exception as exc:
                QMessageBox.warning(self, "Calibração indisponível", str(exc))

    def activate(self):
        try:
            self.save_fields()
            self.service.start()
        except Exception as exc:
            self.status.setText(str(exc))

    def deactivate(self):
        self.service.stop()
        self.context.save()
