# SPDX-License-Identifier: GPL-3.0-only
"""Small Atlas-layer controls shared by the two game maps."""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout
from app.ui.hud import HudSurface
from app.ui.localized_widgets import QToolButton
from app.ui.layer_menu import AtlasLayerMenu
from app.ui.icons import icon
from app.ui.widgets import label


class MapControls(HudSurface):
    def __init__(self, main):
        super().__init__(None,Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|
                         Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.WindowDoesNotAcceptFocus)
        self.main,self.context=main,main.context
        self.drag=None;self.closed=False
        self.setWindowTitle('Azphelumbra · Camadas')
        self.setFixedSize(280,38)
        box=QHBoxLayout(self);box.setContentsMargins(7,3,7,3);box.setSpacing(7)
        handle=label('⋮');handle.setToolTip('Arraste para mover');handle.installEventFilter(self);box.addWidget(handle)
        self.cubes=QToolButton();self.cubes.setText('Cubos ocultos');self.cubes.setIcon(icon('cube'))
        self.cubes.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.cubes.setCheckable(True);self.cubes.toggled.connect(self.toggle_cubes);box.addWidget(self.cubes)
        self.layers=AtlasLayerMenu(self.context,self);self.layers.setText('Coletas')
        self.layers.setIcon(icon('gatherables'));box.addWidget(self.layers)
        self.context.changed.connect(self.refresh);main.overlay.status_changed.connect(self.refresh)
        self.refresh()

    def refresh(self,*_):
        if self.closed:return
        cube_categories={r.category for r in self.context.dataset.resources
                         if any(p.resource_id==r.id for p in self.context.dataset.cubes)}
        self.cube_categories=cube_categories
        self.cubes.blockSignals(True)
        self.cubes.setChecked(bool(cube_categories-self.context.prefs.disabled_categories))
        self.cubes.blockSignals(False)
        self.cubes.setStyleSheet('color:#e6cc7d;' if self.cubes.isChecked() else 'color:#aaa8bd;')
        saved=self.context.prefs.overlay.controls_position
        screen=QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        area=screen.availableGeometry()
        if not hasattr(self,'positioned'):
            self.move(*(saved or (area.right()-self.width()-25,area.top()+340)))
            self.positioned=True
        self.move(max(area.left(),min(self.x(),area.right()-self.width()+1)),
                  max(area.top(),min(self.y(),area.bottom()-self.height()+1)))
        self.setVisible(self.context.prefs.overlay.enabled and self.main.overlay.worker is not None)

    def toggle_cubes(self,checked):
        disabled=self.context.prefs.disabled_categories
        disabled.difference_update(self.cube_categories) if checked else disabled.update(self.cube_categories)
        self.context.save()

    def eventFilter(self,watched,event):
        if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
            self.drag=event.globalPosition().toPoint()-self.pos();return True
        if event.type()==QEvent.Type.MouseMove and self.drag is not None:
            self.move(event.globalPosition().toPoint()-self.drag);return True
        if event.type()==QEvent.Type.MouseButtonRelease and self.drag is not None:
            self.drag=None;self.context.prefs.overlay.controls_position=(self.x(),self.y());self.context.save();return True
        return super().eventFilter(watched,event)

    def shutdown(self):
        self.closed=True;self.hide();self.close()
