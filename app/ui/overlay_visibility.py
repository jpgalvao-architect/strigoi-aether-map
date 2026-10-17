# SPDX-License-Identifier: GPL-3.0-only
"""Transient visibility policy, separate from module preferences and capture."""
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QWidget


class OverlayVisibilityMixin:
    def setVisible(self, visible):
        self._overlay_wanted = bool(visible)
        gate = getattr(self, '_visibility_gate', None)
        if gate and getattr(self, '_overlay_role', '') == 'alert' and not gate.allows('alert'):
            self._overlay_wanted = False  # Never replay a notification heard while away.
        self.apply_overlay_visibility()

    def show(self):
        self.setVisible(True)

    def hide(self):
        self.setVisible(False)

    def apply_overlay_visibility(self):
        gate = getattr(self, '_visibility_gate', None)
        allowed = gate is None or gate.allows(self._overlay_role)
        visible = getattr(self, '_overlay_wanted', False) and allowed
        if self.isVisible() != visible:
            QWidget.setVisible(self, visible)


class OverlayVisibility(QObject):
    def __init__(self, main, probe=None):
        super().__init__(main)
        from app.modules.overlay.foreground import ForegroundProbe
        self.main = main
        self.probe = probe or ForegroundProbe()
        self.windows = []
        self.game = None
        self.generation = 0
        self.mode = 'play'
        self.active = False
        self.closed = False
        self.timer = QTimer(self); self.timer.setInterval(100)
        self.timer.timeout.connect(self.poll)
        self.worker = None

    def register(self, window, role='hud'):
        window._overlay_wanted = window.isVisible()
        window._visibility_gate = self
        window._overlay_role = role
        self.windows.append(window)
        window.apply_overlay_visibility()

    def allows(self, role):
        return self.active and (self.mode == 'play' or role == 'map' and self.mode == 'map')

    def set_context(self, active, mode='play'):
        self.active, self.mode = bool(active), mode
        if not self.active or mode != 'play':
            for popup in self.associated_popups(): popup.hide()
        for window in self.windows:
            if not self.allows(window._overlay_role) and window._overlay_role == 'alert':
                window._overlay_wanted = False
            window.apply_overlay_visibility()

    def associated_popups(self):
        result=[]
        for widget in QApplication.topLevelWidgets():
            if not widget.isVisible() or widget in self.windows: continue
            parent=widget.parentWidget()
            while parent is not None:
                if parent in self.windows:
                    result.append(widget);break
                parent=parent.parentWidget()
        return result

    def start(self):
        from app.modules.overlay.menu_monitor import MenuMonitor
        self.worker = MenuMonitor(self.probe)
        self.worker.observed.connect(self.on_menu)
        self.worker.pet_observed.connect(self.on_pet)
        self.worker.boss_observed.connect(self.on_boss)
        self.worker.start()
        self.timer.start(); self.poll()

    def poll(self):
        if self.closed:
            return
        owned = {int(window.winId()) for window in self.windows if window.isVisible()}
        owned.update(int(popup.winId()) for popup in self.associated_popups())
        game = self.probe.game_foreground(owned, self.game)
        if game is None:
            if self.game is not None: self.generation += 1
            self.game = None
            if self.worker: self.worker.set_game(None)
            self.set_context(False)
            return
        changed = self.game != game
        if changed: self.generation += 1
        self.game = game
        self.main.context.boss_timer.set_game((game.handle,game.pid))
        if self.worker: self.worker.set_game((game, self.generation))
        if self.worker:self.worker.set_pet_scope(self.main.pets.screen_scope())
        if self.worker:self.worker.set_boss_scope(self.main.context.boss_timer.screen_scope())
        self.set_context(True, 'play' if changed else self.mode)

    def on_pet(self,job,scope,reading):
        if self.closed or not self.active or job!=(self.game,self.generation):return
        self.main.pets.from_screen(scope,reading)

    def on_boss(self,job,scope,reading,captured):
        if self.closed or not self.active or job!=(self.game,self.generation):return
        self.main.context.boss_timer.accept(scope,reading,captured)

    def on_menu(self, job, mode):
        if self.closed or job != (self.game, self.generation) or not self.active:
            return  # Late recognition never brings overlays back over another app.
        # Confirmed full-map registration also supplies the exception for markers.
        overlay = self.main.overlay
        if mode == 'fullscreen' and overlay.window.registration is not None and overlay.capture_area is not None:
            import time
            if overlay.capture_area.view_kind == 'large' and time.perf_counter()-overlay.last_result < .8:
                mode = 'map'
        if mode == 'fullscreen': mode = 'menu'
        self.set_context(True, mode)

    def shutdown(self):
        self.closed = True; self.timer.stop(); self.set_context(False)
        if self.worker:
            self.worker.stop(); self.worker.wait(3000)
            self.worker = None
