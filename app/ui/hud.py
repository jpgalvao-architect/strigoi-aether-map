# SPDX-License-Identifier: GPL-3.0-only
"""Shared quiet, rounded HUD surface; no animations or polling timers."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from app.ui.localized_widgets import QFrame
from app.ui.overlay_visibility import OverlayVisibilityMixin

HUD_STYLE = '''
QLabel {background:transparent; border:0; color:#eeedf8; font-size:12px;}
QLabel#subtitle {color:#aaa8bd;font-size:11px;}
QToolButton {background:transparent;border:0;border-radius:4px;padding:2px;color:#bbb0d7;}
QToolButton:hover {background:#302943;}
QToolButton:focus {border:1px solid #c2b2fc;}
QScrollArea {background:transparent;border:0;}
QWidget#hudList {background:transparent;border:0;}
'''


class HudSurface(OverlayVisibilityMixin, QFrame):
    def __init__(self, parent=None, flags=Qt.WindowType.Widget):
        super().__init__(parent, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(HUD_STYLE)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#484052'), 1))
        painter.setBrush(QColor(21, 20, 30, 245))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5), 9, 9)
