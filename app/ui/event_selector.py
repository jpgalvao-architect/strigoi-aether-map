# SPDX-License-Identifier: GPL-3.0-only
"""One persisted event choice shared by the page and floating agenda."""
from app.ui.localized_widgets import QComboBox, QMenu, QToolButton
from app.ui.icons import icon, event_icon


class EventSelector(QComboBox):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.setAccessibleName('Evento do painel flutuante')
        self.setToolTip('Escolha o evento acompanhado no painel')
        self.currentIndexChanged.connect(self.choose)
        context.changed.connect(self.refresh)
        context.events_changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        selected = self.context.prefs.overlay.events_panel_event
        self.blockSignals(True)
        self.clear()
        self.addItem('Automático · próximo evento', '')
        for event in self.context.feed.events:
            if event.enabled:
                self.addItem(icon(event_icon(event)), event.name, event.id)
        index = self.findData(selected)
        if index < 0:
            self.addItem('Evento indisponível nesta agenda', selected)
            index = self.count()-1
        self.setCurrentIndex(index)
        self.blockSignals(False)

    def choose(self):
        self.context.prefs.overlay.events_panel_event = self.currentData() or ''
        self.context.save()


class EventPicker(QToolButton):
    """Small header control; the full event list only opens on demand."""
    def __init__(self,context,parent=None):
        super().__init__(parent)
        self.context=context
        self.setIcon(icon('events'))
        self.setAccessibleName('Escolher evento do painel')
        self.setToolTip('Escolher evento')
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu_widget=QMenu(self)
        self.menu_widget.setStyleSheet('QMenu {background:#17202b;color:#eaf0f8;border:1px solid #465966;padding:4px;} QMenu::item {padding:7px 20px;} QMenu::item:selected {background:#2a3f4d;}')
        self.setMenu(self.menu_widget)
        self.menu_widget.aboutToShow.connect(self.refresh)
        context.changed.connect(self.refresh)
        context.events_changed.connect(self.refresh)
        self.refresh()

    def currentData(self):
        return self.context.prefs.overlay.events_panel_event

    def refresh(self):
        self.menu_widget.clear()
        self.actions_by_event={}
        selected=self.currentData()
        choices=[('', 'Automático · próximo evento', 'events')]
        choices.extend((e.id,e.name,event_icon(e)) for e in self.context.feed.events if e.enabled)
        for key,title,picture in choices:
            action=self.menu_widget.addAction(icon(picture),title)
            action.setCheckable(True);action.setChecked(key==selected)
            action.triggered.connect(lambda checked=False,value=key:self.choose(value))
            self.actions_by_event[key]=action
        if selected and selected not in self.actions_by_event:
            unavailable=self.menu_widget.addAction('Evento escolhido indisponível nesta agenda')
            unavailable.setEnabled(False)

    def choose(self,key):
        self.context.prefs.overlay.events_panel_event=key
        self.context.save()
