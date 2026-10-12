# SPDX-License-Identifier: GPL-3.0-only
"""Display Aether, the app's original Asmodian-inspired mascot."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from app.ui.localized_widgets import QWidget

from app.infrastructure.storage import PACKAGE

MASCOT_PATH = PACKAGE / "assets/aether-asmodian-v2.png"
AVATAR_PATH = PACKAGE / "assets/aether-avatar-v2.png"


class MascotWidget(QWidget):
    def __init__(self, parent=None, compact=False):
        super().__init__(parent)
        self.pixmap = QPixmap(str(AVATAR_PATH if compact else MASCOT_PATH))
        self.setAccessibleName("Aether, o pequeno guardião do atlas")
        self.setToolTip("Aether · seu companheiro de exploração")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        size = self.pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        painter.drawPixmap((self.width()-size.width())//2, (self.height()-size.height())//2,
                           size.width(), size.height(), self.pixmap)
