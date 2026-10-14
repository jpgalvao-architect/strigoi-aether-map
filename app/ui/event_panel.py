# SPDX-License-Identifier: GPL-3.0-only
"""Floating agenda with a compact next event and an expandable calendar day."""
from datetime import UTC,datetime,timedelta
from PySide6.QtCore import QEvent,QPoint,Qt,QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout
from app.ui.localized_widgets import QFrame, QLabel, QToolButton, QWidget
from app.modules.events.day import day_events,local_time
from app.modules.events.service import countdown,occurrences
from app.ui.icons import icon,event_icon
from app.ui.widgets import label
from app.core.i18n import tr, clock, calendar_date
from app.ui.overlay_visibility import OverlayVisibilityMixin


class EventCard(QFrame):
    def __init__(self,item,parent=None):
        super().__init__(parent)
        self.item=item
        self.setObjectName('eventCard')
        box=QHBoxLayout(self);box.setContentsMargins(5,6,5,6);box.setSpacing(7)
        self.picture=label('');self.picture.setFixedSize(22,22)
        self.picture.setPixmap(icon(event_icon(item.event)).pixmap(22,22))
        box.addWidget(self.picture)
        copy=QVBoxLayout();copy.setSpacing(3)
        self.name=label(item.event.name,'eventName')
        self.name.setMinimumWidth(0)
        self.name.setAccessibleName(item.event.name)
        self.clock=label('','eventTime')
        self.remaining=label('','eventCountdown')
        self.remaining.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
        second=QHBoxLayout();second.setSpacing(4)
        second.addWidget(self.clock);second.addStretch();second.addWidget(self.remaining)
        copy.addWidget(self.name);copy.addLayout(second)
        box.addLayout(copy,1)
        self.setFixedHeight(52)
        self.setToolTip(item.event.name)

    def resizeEvent(self,event):
        self.name.setText(self.name.fontMetrics().elidedText(tr(self.item.event.name),Qt.TextElideMode.ElideRight,max(0,self.name.width())))
        super().resizeEvent(event)

    def refresh(self,now,timezone):
        start=self.item.starts_at
        when=local_time(start,timezone)
        today=local_time(now,timezone).date()
        prefix='' if when.date()==today else ('Amanhã · ' if when.date()==today+timedelta(days=1) else calendar_date(when)+' · ')
        self.clock.setText(prefix+clock(when))
        self.name.setText(self.name.fontMetrics().elidedText(tr(self.item.event.name),Qt.TextElideMode.ElideRight,max(0,self.name.width())))
        active=start<=now and self.item.event.duration_minutes is not None and now<start+timedelta(minutes=self.item.event.duration_minutes)
        passed=start<=now and not active
        state='past' if passed else ('active' if active else 'upcoming')
        if self.property('state')!=state:
            self.setProperty('state',state);self.style().unpolish(self);self.style().polish(self)
            for child in self.findChildren(QLabel):
                child.style().unpolish(child);child.style().polish(child)
        self.remaining.setText('Já começou' if passed else ('Em andamento' if active else countdown(start,now)))
        self.remaining.setToolTip('Horário de início' if passed else ('Evento em andamento' if active else 'Tempo até o início'))


class EventPanel(OverlayVisibilityMixin, QFrame):
    def __init__(self,context):
        super().__init__(None,Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool)
        self.context=context;self.shutting_down=False;self.drag=None
        self.cards=[];self.items=[];self.structure=None;self.initial_position=False
        self.setWindowTitle('Strigoi · Eventos')
        self.setObjectName('floatingAgenda')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(260)
        self.setStyleSheet("""
          QFrame#floatingAgenda { background: transparent; }
          QFrame#agendaSurface { background:rgba(17,23,30,226); border:1px solid #53616d; border-radius:3px; }
          QFrame#agendaHeader { background:rgba(10,14,19,230); border:0; border-bottom:1px solid #384652; }
          QLabel#panelTitle { color:#eef4fb; font-weight:600; font-size:13px; }
          QLabel#panelSubtitle { color:#a8bbc8; font-size:10px; }
          QToolButton { border:0; background:transparent; border-radius:2px; padding:2px; }
          QToolButton:hover { background:#2a3f4d; }
          QToolButton:focus { border:1px solid #a4dcdf; }
          QFrame#eventCard { background:transparent; border:0; border-bottom:1px solid #2c3b46; border-radius:0; }
          QFrame#eventCard[state="past"] QLabel { color:#7c8e9b; }
          QFrame#eventCard[state="active"] { background:rgba(35,82,81,80); }
          QLabel#eventName { color:#eaf0f8; font-size:12px; font-weight:600; }
          QLabel#eventTime { color:#aabfd2; font-size:10px; }
          QLabel#eventCountdown { color:#a5e0df; font-size:11px; font-weight:600; }
          QScrollArea { border:0; background:transparent; }
          QScrollArea QWidget#agendaList { background:transparent; }
        """)
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        self.surface=QFrame();self.surface.setObjectName('agendaSurface');outer.addWidget(self.surface)
        box=QVBoxLayout(self.surface);box.setContentsMargins(1,1,1,4);box.setSpacing(3)
        header=QFrame();header.setObjectName('agendaHeader')
        top=QHBoxLayout(header);top.setContentsMargins(7,3,4,3);top.setSpacing(4)
        moon=label('');moon.setPixmap(icon('moon').pixmap(14,14));top.addWidget(moon)
        self.heading=label('Eventos','panelTitle');top.addWidget(self.heading,1)
        from app.ui.event_selector import EventPicker
        self.event_selector=EventPicker(context,self);self.event_selector.setFixedSize(22,22)
        top.addWidget(self.event_selector)
        self.expand_button=QToolButton();self.expand_button.setFixedSize(22,22)
        self.expand_button.clicked.connect(self.toggle_expanded);top.addWidget(self.expand_button)
        close=QToolButton();close.setIcon(icon('close'));close.setFixedSize(22,22)
        close.setToolTip('Fechar painel');close.setAccessibleName('Fechar painel')
        close.clicked.connect(self.dismiss);top.addWidget(close)
        box.addWidget(header)
        self.subtitle=label('','panelSubtitle');box.addWidget(self.subtitle)
        self.subtitle.setContentsMargins(7,0,7,0)
        self.scroller=QScrollArea();self.scroller.setWidgetResizable(True)
        self.scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget=QWidget();self.list_widget.setObjectName('agendaList')
        self.list_box=QVBoxLayout(self.list_widget);self.list_box.setContentsMargins(4,0,4,0);self.list_box.setSpacing(0)
        self.scroller.setWidget(self.list_widget);box.addWidget(self.scroller)
        self.empty=label('Nenhum evento hoje.','panelSubtitle',True);box.addWidget(self.empty)
        self.footer=label('','panelSubtitle');self.footer.setContentsMargins(7,0,7,0);box.addWidget(self.footer)
        for widget in [moon,self.heading,header]:
            widget.installEventFilter(self)
        self.context.changed.connect(self.refresh);self.context.events_changed.connect(self.refresh)
        self.timer=QTimer(self);self.timer.setInterval(1000);self.timer.timeout.connect(self.refresh);self.timer.start()
        self.refresh()

    def refresh(self,now=None):
        if self.shutting_down or not self.context.prefs.overlay.events_panel:
            self.hide();return
        now=now or datetime.now(UTC)
        expanded=self.context.prefs.overlay.events_panel_expanded
        timezone=self.context.prefs.timezone
        selected=self.context.prefs.overlay.events_panel_event
        events=[e for e in self.context.feed.events if not selected or e.id==selected]
        daily=day_events(events,now,timezone)
        self.items=daily if expanded else occurrences(events,now)[:1]
        key=(id(self.context.feed),tuple(i.key for i in self.items),expanded,timezone,selected)
        if key!=self.structure:
            self.structure=key
            while self.list_box.count():
                self.list_box.takeAt(0).widget().deleteLater()
            self.cards=[EventCard(item) for item in self.items]
            for card in self.cards:self.list_box.addWidget(card)
            screen=QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
            max_height=max(130,min(312,screen.availableGeometry().height()-120))
            height=min(max_height,max(52,len(self.cards)*52))
            self.scroller.setFixedHeight(height if expanded else 52)
            self.adjustSize()
            self.fit_screen()
            if expanded:QTimer.singleShot(50,self.focus_upcoming)
        for card in self.cards:card.refresh(now,timezone)
        self.heading.setText('Eventos de hoje' if expanded else 'Eventos')
        self.subtitle.setVisible(expanded)
        self.footer.setVisible(expanded)
        self.subtitle.setText(calendar_date(local_time(now,timezone))+f' · {len(daily)} horários hoje')
        self.expand_button.setIcon(icon('chevron-up' if expanded else 'chevron-down'))
        action='Recolher painel' if expanded else 'Expandir horários de hoje'
        self.expand_button.setToolTip(action);self.expand_button.setAccessibleName(action)
        self.empty.setVisible(not self.items);self.scroller.setVisible(bool(self.items))
        self.empty.setText('Nenhum evento hoje.' if expanded else 'Nenhum evento agendado.')
        local=local_time(now,timezone);offset=local.strftime('%z')
        self.footer.setText(f'Horários locais · UTC{offset[:3]}:{offset[3:]}')
        self.adjustSize();self.fit_screen();self.show()

    def focus_upcoming(self):
        if self.shutting_down or not self.context.prefs.overlay.events_panel_expanded:return
        now=datetime.now(UTC)
        card=next((card for card in self.cards if card.item.starts_at>=now),None)
        if card:self.scroller.verticalScrollBar().setValue(card.y())

    def fit_screen(self):
        screen=QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        if not self.initial_position:
            saved=self.context.prefs.overlay.events_panel_position
            if saved:
                self.move(*saved)
                screen=QGuiApplication.screenAt(self.geometry().center()) or screen
            else:
                g=screen.availableGeometry();self.move(g.right()-self.width()-24,g.top()+40)
            self.initial_position=True
        g=screen.availableGeometry()
        self.move(max(g.left(),min(self.x(),g.right()-self.width()+1)),max(g.top(),min(self.y(),g.bottom()-self.height()+1)))

    def toggle_expanded(self):
        settings=self.context.prefs.overlay
        settings.events_panel_expanded=not settings.events_panel_expanded
        self.context.save()

    def eventFilter(self,watched,event):
        if event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.MouseMove,QEvent.Type.MouseButtonRelease):
            y=self.mapFromGlobal(event.globalPosition().toPoint()).y()
            if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton and y<34:
                self.drag=event.globalPosition().toPoint()-self.pos();return True
            if event.type()==QEvent.Type.MouseMove and self.drag is not None:
                self.move(event.globalPosition().toPoint()-self.drag);return True
            if event.type()==QEvent.Type.MouseButtonRelease and self.drag is not None:
                self.drag=None;self.fit_screen()
                self.context.prefs.overlay.events_panel_position=(self.x(),self.y())
                self.context.save();return True
        return super().eventFilter(watched,event)

    def dismiss(self):
        self.context.prefs.overlay.events_panel=False;self.context.save()

    def shutdown(self):
        self.shutting_down=True;self.timer.stop();self.hide();self.close()
