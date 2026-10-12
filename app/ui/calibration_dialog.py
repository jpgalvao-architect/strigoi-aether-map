# SPDX-License-Identifier: GPL-3.0-only
"""Manual calibration from a screenshot supplied by the user, without game access."""
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QVBoxLayout
from app.ui.localized_widgets import QDialog

from app.infrastructure.storage import atomic_json
from app.modules.overlay.detector import Calibration, MapDetector, Rect
from app.ui.widgets import button, label, row


class SelectionView(QGraphicsView):
    selected = Signal(object)

    def __init__(self, image):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.scene().addPixmap(image)
        self.scene().setSceneRect(QRectF(image.rect()))
        self.start_point = None
        self.rubber = None
        self.setMinimumSize(600, 360)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = self.mapToScene(event.position().toPoint())
            if self.rubber:
                self.scene().removeItem(self.rubber)
            self.rubber = self.scene().addRect(QRectF(self.start_point, self.start_point), QPen(QColor("#91dedf"), 3))

    def mouseMoveEvent(self, event):
        if self.start_point is not None:
            end = self.mapToScene(event.position().toPoint())
            self.rubber.setRect(QRectF(self.start_point, end).normalized().intersected(self.sceneRect()))

    def mouseReleaseEvent(self, event):
        if self.start_point is not None:
            self.selected.emit(self.rubber.rect())
            self.start_point = None


class CalibrationDialog(QDialog):
    STEPS = ["1 / 3 · Arraste sobre a área exata do mapa completo (sem bordas).", "2 / 3 · Selecione um detalhe fixo da janela do mapa, fora dos marcadores (título, moldura).", "3 / 3 · Selecione um detalhe interno do mapa (terreno/texto), distinto do anterior e sem marcadores."]

    def __init__(self, source: Path, map_id: str, directory: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibrar viewport • experimental")
        self.resize(1000, 720)
        self.source = source
        self.map_id = map_id
        self.directory = directory
        self.result_path = ""
        image = QPixmap(str(source))
        if image.isNull() or image.width() > 16000 or image.height() > 16000:
            raise ValueError("Screenshot inválido ou muito grande")
        self.image = image
        self.selections = []
        self.current = None
        layout = QVBoxLayout(self)
        layout.addWidget(label("Use uma captura do monitor inteiro, na resolução nativa. O mapa deve estar enquadrado exatamente como o atlas. A calibração serve para uma região, posição e zoom fixos.", "subtitle", True))
        self.instruction = label(self.STEPS[0], "eyebrow", True)
        layout.addWidget(self.instruction)
        self.view = SelectionView(image)
        self.view.selected.connect(self.select)
        layout.addWidget(self.view, 1)
        self.error = label("", "subtitle", True)
        layout.addWidget(self.error)
        self.next_button = button("Confirmar seleção", self.advance, True)
        self.next_button.setEnabled(False)
        layout.addLayout(row(button("Recomeçar", self.reset), self.next_button, button("Cancelar", self.reject)))

    def select(self, rectangle):
        self.current = rectangle
        self.next_button.setEnabled(rectangle.width() >= 12 and rectangle.height() >= 12)

    def reset(self):
        self.selections = []
        self.instruction.setText(self.STEPS[0])
        self.next_button.setEnabled(False)

    def advance(self):
        rectangle = self.current
        self.selections.append(Rect(x=int(rectangle.x()), y=int(rectangle.y()), width=int(rectangle.width()), height=int(rectangle.height())))
        self.next_button.setEnabled(False)
        if len(self.selections) < 3:
            self.instruction.setText(self.STEPS[len(self.selections)])
            return
        try:
            base = self.directory / "calibration"
            base.mkdir(exist_ok=True)
            stem = uuid4().hex
            image_path = base / f"{stem}.png"
            if not self.image.save(str(image_path), "PNG"):
                raise OSError("Não foi possível salvar a referência")
            calibration = Calibration(map_id=self.map_id, screen_width=self.image.width(), screen_height=self.image.height(), viewport=self.selections[0], anchor=self.selections[1], fingerprint=self.selections[2], reference_image=str(image_path))
            MapDetector(calibration, .96)
            path = base / f"{stem}.json"
            atomic_json(path, calibration)
            self.result_path = str(path)
            self.accept()
        except Exception as exc:
            self.error.setText(str(exc))
            self.reset()
