# SPDX-License-Identifier: GPL-3.0-only
"""Compact Siege Command HUD and its optional Windows shortcut."""
import ctypes
from ctypes import wintypes
import os
import re

from PySide6.QtCore import QAbstractNativeEventFilter, QEvent, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QHBoxLayout, QSizePolicy, QVBoxLayout

from app.core.i18n import tr
from app.ui.hud import HudSurface
from app.ui.widgets import label

FLAGS = Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
HOTKEY_ID = 0xA270
WM_HOTKEY = 0x0312
MODIFIER = {'alt': 0x0001, 'ctrl': 0x0002, 'shift': 0x0004}


def shortcut(value):
    if not value:
        return None
    words = value.lower().split('+')
    match = re.fullmatch(r'f([1-9]|1[0-2])', words[-1])
    modifiers = words[:-1]
    if (match is None or not {'alt', 'ctrl'} & set(modifiers)
            or set(modifiers) - MODIFIER.keys() or len(set(modifiers)) != len(modifiers)):
        raise ValueError(tr('Use Ctrl ou Alt com F1–F12. Limpe o campo para desativar o atalho.'))
    key = int(match[1])
    mask = sum(MODIFIER[word] for word in modifiers)
    name = '+'.join([*(m.title() for m in ('ctrl', 'alt', 'shift') if m in modifiers), f'F{key}'])
    return name, mask | 0x4000, 0x6F + key  # MOD_NOREPEAT, VK_F1..VK_F12


class SiegeHotkeys(QAbstractNativeEventFilter):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.registered = False
        self.attempt = None
        self.user32 = ctypes.WinDLL('user32', use_last_error=True) if os.name == 'nt' else None
        if self.user32:
            self.user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            QApplication.instance().installNativeEventFilter(self)

    def sync(self, active):
        prefs = self.controller.service.state.overlay
        requested = prefs.hud_shortcut if active else ''
        if self.user32 is None or requested == self.attempt:
            return
        self.clear()
        self.attempt = requested
        try:
            parsed = shortcut(requested)
        except ValueError:
            return
        if parsed:
            name, mask, key = parsed
            self.registered = bool(self.user32.RegisterHotKey(None, HOTKEY_ID, mask, key))
            if not self.registered:
                self.controller.main.statusBar().showMessage(f'{tr("Atalho ocupado")} · {name}', 6000)

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) in (b'windows_generic_MSG', b'windows_dispatcher_MSG') and self.registered:
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                self.controller.toggle_hud()
                return True, 0
        return False, 0

    def clear(self):
        if self.registered:
            self.user32.UnregisterHotKey(None, HOTKEY_ID)
            self.registered = False

    def shutdown(self):
        self.clear()
        if self.user32:
            QApplication.instance().removeNativeEventFilter(self)


class SiegeHud(HudSurface):
    def __init__(self, controller):
        super().__init__(None, FLAGS | Qt.WindowDoesNotAcceptFocus)
        self.controller = controller
        self.service = controller.service
        self.drag = None
        self.saved_position = None
        self.positioned = False
        self.locked = False
        self.setWindowTitle('Azphelumbra · Siege Command')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(3)
        header = QHBoxLayout()
        self.title = label('Siege Command', 'subtitle')
        self.title.setCursor(Qt.SizeAllCursor)
        self.title.installEventFilter(self)
        header.addWidget(self.title, 1)
        layout.addLayout(header)
        self.call_label = label('', '', True)
        layout.addWidget(self.call_label)
        self.detail = label('', 'subtitle', True)
        for caption in (self.title, self.call_label, self.detail):
            caption.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(self.detail)

    def refresh(self):
        overlay = self.service.state.overlay
        call = self.service.call
        self.call_label.setText(self.service.call_text() or 'Aguardando call')
        self.call_label.setStyleSheet(
            f'font-size:{round(17*overlay.scale)}px;font-weight:700;color:#eee6ff;')
        ring = self.service.rings.get(call.ring_id)
        code = self.service.callsign(ring) if ring else None
        detail = tr(f'Ponto {call.objective}') if call.objective else ''
        objective = self.service.objectives.get(call.objective)
        if objective and objective.status == 'reference':
            detail += ' · ' + tr('Referência visual')
        self.detail.setText('  /  '.join(part for part in (call.sector, code, detail) if part))
        self.setFixedWidth(round(274 * overlay.scale))
        self.setWindowOpacity(overlay.opacity)
        if self.locked != overlay.locked:
            self.locked = overlay.locked
            self.setWindowFlag(Qt.WindowTransparentForInput, overlay.locked)
        self.adjustSize()
        if not self.positioned or self.saved_position != overlay.position:
            self.saved_position = overlay.position
            screen = QGuiApplication.primaryScreen().availableGeometry()
            self.move(*(overlay.position or (screen.left()+20, screen.top()+screen.height()//3+58)))
            self.positioned = True
        self.clamp()

    def clamp(self):
        screen = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(max(area.left(), min(self.x(), area.right()-self.width()+1)),
                  max(area.top(), min(self.y(), area.bottom()-self.height()+1)))

    def eventFilter(self, watched, event):
        if watched is self.title and not self.locked:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self.drag = event.globalPosition().toPoint() - self.pos()
                return True
            if event.type() == QEvent.MouseMove and self.drag is not None:
                self.move(event.globalPosition().toPoint() - self.drag)
                return True
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton and self.drag is not None:
                self.drag = None
                self.clamp()
                self.controller.change_overlay(position=(self.x(), self.y()))
                return True
        return super().eventFilter(watched, event)


class SiegeOverlay:
    def __init__(self, main, *, runtime):
        self.main = main
        self.service = main.context.siege
        self.hud = SiegeHud(self)
        self.hotkeys = SiegeHotkeys(self) if runtime else None
        self.service.changed.connect(self.refresh)
        self.refresh()

    def bind_visibility(self, gate):
        gate.register(self.hud, 'hud')
        gate.context_changed.connect(self.sync_keys)

    def sync_keys(self, active, mode):
        if self.hotkeys is not None:
            self.hotkeys.sync(active and mode == 'play')

    def configure_shortcut(self, hud_key):
        hud = shortcut(hud_key)
        if self.hotkeys is None and os.name != 'nt':
            raise ValueError(tr('Atalhos no jogo disponíveis no Windows.'))
        self.service.update_overlay(hud_shortcut=hud[0] if hud else '')
        return 'Atalho do HUD salvo.'

    def change_overlay(self, **changes):
        try:
            self.service.update_overlay(**changes)
        except (OSError, ValueError) as error:
            self.main.statusBar().showMessage(str(error), 6000)

    def toggle_hud(self):
        self.change_overlay(visible=not self.service.state.overlay.visible)

    def refresh(self):
        self.hud.refresh()
        self.hud.setVisible(self.service.state.overlay.visible)
        gate = getattr(self.main, 'overlay_visibility', None)
        if gate:
            self.sync_keys(gate.active, gate.mode)

    def shutdown(self):
        if self.hotkeys:
            self.hotkeys.shutdown()
        self.hud.hide()
        self.hud.close()
