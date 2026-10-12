# SPDX-License-Identifier: GPL-3.0-only
"""Atlas category preferences, also editable while the overlay is running."""
from app.ui.localized_widgets import QMenu, QToolButton
from PySide6.QtCore import Qt
from app.ui.icons import icon


class LayerPopup(QMenu):
    def mouseReleaseEvent(self,event):
        action=self.actionAt(event.position().toPoint())
        if event.button()==Qt.MouseButton.LeftButton and action and action.isCheckable():
            action.setChecked(not action.isChecked());event.accept();return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self,event):
        action=self.activeAction()
        if event.key()==Qt.Key.Key_Space and action and action.isCheckable():
            action.setChecked(not action.isChecked());event.accept();return
        super().keyPressEvent(event)


class AtlasLayerMenu(QToolButton):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.setText('Camadas do Atlas')
        self.setIcon(icon('atlas'))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolTip('A mesma seleção vale para o Atlas, minimapa e mapa grande')
        self.setAccessibleName('Camadas do Atlas e dos mapas do jogo')
        self.menu_widget = LayerPopup(self)
        self.setMenu(self.menu_widget)
        self.menu_widget.aboutToShow.connect(self.refresh)
        self.refresh()

    def refresh(self):
        self.menu_widget.clear()
        self.actions_by_category = {}
        used={p.resource_id for p in self.context.dataset.all_points}
        categories={r.category for r in self.context.dataset.resources if r.id in used}
        for category in self.context.dataset.categories:
            if category.id not in categories:
                continue
            action=self.menu_widget.addAction(category.name)
            action.setCheckable(True)
            action.setChecked(category.id not in self.context.prefs.disabled_categories)
            action.toggled.connect(lambda checked,key=category.id:self.choose(key,checked))
            self.actions_by_category[category.id]=action

    def choose(self, key, checked):
        disabled=self.context.prefs.disabled_categories
        disabled.discard(key) if checked else disabled.add(key)
        self.context.save()
