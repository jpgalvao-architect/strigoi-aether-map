# SPDX-License-Identifier: GPL-3.0-only
"""User-operated transparent selection window; no screenshot or directory workflow."""
from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from app.ui.localized_widgets import QWidget


class ScreenSelection(QWidget):
    chosen = Signal(object)
    cancelled = Signal()

    def __init__(self, screen):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(screen.geometry())
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.begin = None
        self.end = None
        self.finished = False

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(10, 15, 30, 115))
        p.setPen(QColor('#eff1f7'))
        p.drawText(24, 40, "STRIGOI • Arraste sobre a área visível do mapa. Esc cancela.")
        if self.begin is not None and self.end is not None:
            box = QRect(self.begin, self.end).normalized().intersected(self.rect())
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.fillRect(box, Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            p.setPen(QPen(QColor('#91dedf'), 2))
            p.drawRect(box)
            p.drawText(box.topLeft(), f"{box.width()} × {box.height()} • solte para confirmar")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin = self.end = event.position().toPoint()
            self.update()

    def mouseMoveEvent(self, event):
        if self.begin is not None:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.begin is None or event.button() != Qt.MouseButton.LeftButton:
            return
        box = QRect(self.begin, event.position().toPoint()).normalized().intersected(self.rect())
        self.finished = True
        self.hide()
        if box.width() >= 80 and box.height() >= 80:
            self.chosen.emit(box)
        else:
            self.cancelled.emit()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def closeEvent(self, event):
        if not self.finished:
            self.finished = True
            self.cancelled.emit()
        event.accept()
