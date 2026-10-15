# SPDX-License-Identifier: GPL-3.0-only
"""Small external module launcher; hiding panels never changes capture state."""
from pathlib import Path
from PySide6.QtCore import Qt, QPoint, QSize, QRectF
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QColor, QPen
from PySide6.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout
from app.ui.localized_widgets import QFrame, QToolButton, QCheckBox
from app.ui.widgets import label
from app.ui.icons import icon
from app.ui.mascot import AVATAR_PATH
from app.infrastructure.storage import PACKAGE
from app.ui.overlay_visibility import OverlayVisibilityMixin


FLAGS = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
         Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)


class LauncherButton(QToolButton):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.press = None
        self.dragging = False
        self.setIcon(QIcon(str(AVATAR_PATH)))
        self.setIconSize(QSize(40, 40))
        self.setFixedSize(52, 52)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Menu rápido · clique para abrir, arraste para mover")
        self.setAccessibleName("Menu rápido do Strigoi")
        self.clicked.connect(owner.toggle_panel)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.press = event.globalPosition().toPoint()
            self.origin = self.owner.pos()
            self.dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.press is not None:
            delta = event.globalPosition().toPoint() - self.press
            if delta.manhattanLength() >= QApplication.startDragDistance():
                self.dragging = True
            if self.dragging:
                self.owner.move(self.origin + delta)
                self.owner.place_panel()
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        dragged = self.dragging
        self.press = None
        self.dragging = False
        if dragged:
            self.setDown(False)
            self.owner.fit_screen()
            self.owner.save_position()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class MenuPanel(OverlayVisibilityMixin, QFrame):
    def paintEvent(self, event):
        # Translucent top-level windows need an explicit painted surface.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#53616d"), 1))
        painter.setBrush(QColor(17, 24, 32, 242))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 7, 7)


class QuickMenu(OverlayVisibilityMixin, QFrame):
    def __init__(self, main, *, runtime=False):
        super().__init__(None, FLAGS)
        self.main, self.context = main, main.context
        self.runtime = runtime
        self.closed = False
        self.setWindowTitle("Strigoi · Menu rápido")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(52, 52)
        self.setObjectName("quickLauncher")
        box = QVBoxLayout(self); box.setContentsMargins(0, 0, 0, 0)
        self.launcher = LauncherButton(self); box.addWidget(self.launcher)
        self.setStyleSheet("QToolButton{background:#151c25;border:1px solid #94dcdf;border-radius:12px;} QToolButton:hover{background:#263644;}")
        self.panel = MenuPanel(None, FLAGS)
        self.panel.setWindowTitle("Strigoi · Controles rápidos")
        self.panel.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.panel.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.panel.setFixedWidth(288)
        self.panel.setObjectName("quickPanel")
        self.panel.setStyleSheet("""
            QFrame#quickPanel{background:transparent;border:0;}
            QLabel{border:0;color:#edf4fa;font-size:12px;}
            QLabel#quickStatus{color:#9fb8c7;font-size:10px;}
            QToolButton{border:0;padding:4px;background:transparent;}
            QToolButton:hover{background:#293b49;}
            QCheckBox{background:transparent;border:0;padding:0;}
            QCheckBox::indicator{width:32px;height:18px;border:0;background:transparent;image:url(OFF_IMAGE);}
            QCheckBox::indicator:checked{image:url(ON_IMAGE);}
        """.replace("OFF_IMAGE", (PACKAGE/"assets/icons/switch-off.svg").as_posix())
              .replace("ON_IMAGE", (PACKAGE/"assets/icons/switch-on.svg").as_posix()))
        body = QVBoxLayout(self.panel); body.setContentsMargins(10, 8, 10, 8); body.setSpacing(7)
        header = QHBoxLayout(); header.addWidget(label("STRIGOI"), 1)
        close = QToolButton(); close.setIcon(icon("chevron-left")); close.setToolTip("Recolher menu rápido")
        close.clicked.connect(self.panel.hide); header.addWidget(close); body.addLayout(header)
        self.switches, self.states = {}, {}
        for key, title, symbol, callback in [
            ("sonar", "Sonar", "sonar", self.toggle_sonar),
            ("maps", "Mapa + minimapa", "atlas", self.toggle_maps),
            ("combat", "Painel de combate", "combat", self.toggle_combat),
            ("events", "Painel de eventos", "events", self.toggle_events),
            ("pets", "Painel de pets", "pets", self.toggle_pets),
        ]:
            line = QHBoxLayout(); line.setContentsMargins(0, 5, 0, 5); line.setSpacing(9)
            picture = label(""); picture.setPixmap(icon(symbol).pixmap(22, 22)); line.addWidget(picture)
            copy = QVBoxLayout(); copy.setSpacing(2); copy.addWidget(label(title))
            state = label("", "quickStatus"); copy.addWidget(state); line.addLayout(copy, 1)
            switch = QCheckBox(); switch.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            switch.setAccessibleName(title); switch.setToolTip(title); switch.toggled.connect(callback)
            line.addWidget(switch); body.addLayout(line)
            self.switches[key], self.states[key] = switch, state
        footer = QHBoxLayout()
        self.note = label("", "quickStatus", True); footer.addWidget(self.note, 1)
        gear = QToolButton(); gear.setIcon(icon("settings")); gear.setToolTip("Abrir Configurações")
        gear.clicked.connect(lambda: self.open_page('settings')); footer.addWidget(gear); body.addLayout(footer)
        self.feedback = label("", "quickStatus", True); self.feedback.hide(); body.addWidget(self.feedback)
        position = self.context.prefs.quick_menu.position
        if position is not None:
            self.move(*position)
        else:
            area = QGuiApplication.primaryScreen().availableGeometry()
            self.move(area.left()+18, area.top()+area.height()//3)
        self.fit_screen()
        self.context.changed.connect(self.refresh)
        main.sonar.active_changed.connect(self.refresh)
        main.overlay.status_changed.connect(self.refresh)
        main.combat.changed.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        if self.closed:
            return
        visible = self.runtime and self.context.prefs.quick_menu.enabled
        if not visible:
            self.panel.hide()
        self.setVisible(visible)
        values = {"sonar": self.main.sonar.active,
                  "maps": self.context.prefs.overlay.enabled and self.main.overlay.worker is not None,
                  "combat": self.context.prefs.combat.panel_visible,
                  "pets": self.context.prefs.pets.panel_visible,
                  "events": self.context.prefs.overlay.events_panel}
        for key, checked in values.items():
            switch = self.switches[key]; switch.blockSignals(True)
            switch.setChecked(bool(checked)); switch.blockSignals(False)
            if key == "combat" and checked and not self.main.combat.in_instance:
                self.states[key].setText("Aguardando instância")
                continue
            self.states[key].setText(("Visível" if checked else "Oculto") if key in ("combat", "events", "pets")
                                     else ("Ativo" if checked else "Desligado"))
        self.note.setText("Ocultar o placar mantém a medição ativa" if self.context.prefs.combat.auto_capture
                          else "Medição automática desativada")

    def toggle_panel(self):
        if self.panel.isVisible():
            self.panel.hide()
        else:
            self.feedback.hide(); self.refresh(); self.panel.adjustSize(); self.place_panel(); self.panel.show()

    def place_panel(self):
        area = (QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()).availableGeometry()
        x = self.x()+self.width()+8
        if x+self.panel.width() > area.right()+1:
            x = self.x()-self.panel.width()-8
        x = max(area.left(), min(x, area.right()-self.panel.width()+1))
        y = max(area.top(), min(self.y(), area.bottom()-self.panel.height()+1))
        self.panel.move(x, y)

    def fit_screen(self):
        screen = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(max(area.left(), min(self.x(), area.right()-self.width()+1)),
                  max(area.top(), min(self.y(), area.bottom()-self.height()+1)))
        self.place_panel()

    def save_position(self):
        self.context.prefs.quick_menu.position = (self.x(), self.y())
        self.context.save()

    def open_page(self, index):
        self.panel.hide(); self.main.navigate(index)
        self.main.showNormal(); self.main.raise_(); self.main.activateWindow()

    def toggle_sonar(self, enabled):
        if enabled:
            self.main.sonar_page.refresh_processes(); self.main.sonar_page.start()
            if not self.main.sonar.active:
                self.open_page('sonar')
        else:
            self.main.sonar.stop()
        self.refresh()

    def toggle_maps(self, enabled):
        if enabled:
            saved = self.context.prefs.overlay.minimap_area
            if not saved or not Path(saved).is_file():
                self.open_page(6)
                self.main.overlay_page.status.setText("Selecione a área do minimapa para usar os dois mapas")
            else:
                page = self.main.overlay_page
                page.view_kind.setCurrentIndex(page.view_kind.findData("minimap"))
                page.start()
                if not self.context.prefs.overlay.enabled:
                    self.open_page(6)
        else:
            self.main.overlay_page.stop()
        self.refresh()

    def toggle_combat(self, visible):
        self.main.combat_page.set_panel(visible)
        self.refresh()

    def toggle_events(self, visible):
        self.context.prefs.overlay.events_panel = visible
        self.context.save()
        self.refresh()

    def toggle_pets(self, visible):
        self.context.prefs.pets.panel_visible = visible
        self.context.save()
        self.refresh()

    def shutdown(self):
        self.closed = True
        self.panel.close(); self.close()
