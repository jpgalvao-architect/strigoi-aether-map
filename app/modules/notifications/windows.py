# SPDX-License-Identifier: GPL-3.0-only
"""Qt uses the OS tray notification integration; app UI provides a fallback."""
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class DesktopNotifications(QObject):
    fallback = Signal(str)

    def __init__(self, icon: QIcon, window):
        super().__init__(window)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("STRIGOI AETHER MAP")
        menu = QMenu(window)
        action = QAction("Abrir Strigoi", menu)
        action.triggered.connect(window.showNormal)
        menu.addAction(action)
        action = QAction("Sair", menu)
        action.triggered.connect(window.close)
        menu.addAction(action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: window.showNormal() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def notify(self, title: str, message: str):
        from app.core.i18n import tr
        title,message=tr(title),tr(message)
        if self.tray.isVisible() and QSystemTrayIcon.supportsMessages():
            self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 10000)
        self.fallback.emit(f"{title} • {message}")
