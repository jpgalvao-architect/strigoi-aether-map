# SPDX-License-Identifier: GPL-3.0-only
"""Two compact HUD layouts; switching style never changes the measured data."""
from PySide6.QtCore import QEvent,Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout,QVBoxLayout,QLayout
from app.core.i18n import tr,language
from app.modules.routine.models import RESOURCES
from app.ui.hud import HudSurface
from app.ui.identity import emblem_icon
from app.ui.icons import icon
from app.ui.localized_widgets import QFrame,QToolButton,QWidget
from app.ui.widgets import label


class RoutinePanel(HudSurface):
    def __init__(self,context,service,open_routine):
        flags=(Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|
               Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.WindowDoesNotAcceptFocus)
        super().__init__(None,flags)
        self.context,self.service,self.open_routine=context,service,open_routine
        self.closed=False;self.drag=None;self.structure=None;self.initial_position=False
        self.saved_position=context.prefs.routine.panel_position
        self.setWindowTitle('Azphelumbra · Rotina')
        self.setObjectName('routinePanel')
        self.setStyleSheet(self.styleSheet()+'''
            QFrame#routinePanel{background:transparent;border:0;}
            QFrame#routineRow{border:0;border-bottom:1px solid #302a38;background:transparent;}
            QLabel{font-size:11px;background:transparent;border:0;}
            QLabel#routineValue{font-size:12px;color:#e5c48b;font-weight:600;}
            QLabel#routineCaption{color:#aaa8bd;}
            QToolButton{padding:2px;min-height:0;border:0;background:transparent;color:#bdb0d2;}
            QToolButton:hover{background:#302943;}
        ''')
        self.body=QVBoxLayout(self);self.body.setContentsMargins(1,1,1,1);self.body.setSpacing(0)
        self.body.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        context.changed.connect(self.refresh);service.changed.connect(self.refresh)
        service.status_changed.connect(self.refresh)
        self.refresh()

    def tool(self,name,tip,callback):
        widget=QToolButton();widget.setIcon(icon(name));widget.setFixedSize(22,22)
        widget.setToolTip(tip);widget.setAccessibleName(tip);widget.clicked.connect(callback)
        return widget

    def refresh(self,*_):
        if self.closed:return
        prefs=self.context.prefs.routine
        if not prefs.panel_visible:self.hide();return
        key=self.service.profile_key or self.service.store.collection.last_profile
        profile=self.service.store.collection.profiles.get(key)
        structure=(prefs.panel_style,prefs.panel_expanded,prefs.panel_locked,tuple(prefs.pinned),
                   key,profile.model_dump_json() if profile else '',self.service.fresh,
                   language())
        if structure!=self.structure:
            self.structure=structure
            while self.body.count():
                widget=self.body.takeAt(0).widget()
                if widget:widget.hide();widget.setParent(None);widget.deleteLater()
            strip=prefs.panel_style=='strip'
            content=QWidget();box=QVBoxLayout(content);box.setContentsMargins(0,0,0,0);box.setSpacing(0)
            self.body.addWidget(content)
            header=QFrame();head=QHBoxLayout(header);head.setContentsMargins(6,2,3,2);head.setSpacing(3)
            mark=label('');mark.setPixmap(emblem_icon().pixmap(16,16));head.addWidget(mark)
            heading=label('' if strip else 'Rotina');head.addWidget(heading,0 if strip else 1)
            caption=profile.character if profile else tr('Aguardando leitura')
            if profile and not strip:
                title=tr('Rotina')+' · '+profile.character
                heading.setText(heading.fontMetrics().elidedText(title,Qt.TextElideMode.ElideRight,110))
                heading.setToolTip(title)
            header.setToolTip(tr('Rotina')+' · '+caption)
            for widget in (header,mark,heading):widget.installEventFilter(self)
            if strip:
                resources=prefs.pinned if prefs.panel_expanded else prefs.pinned[:1]
                for resource in resources:
                    title,_,_=RESOURCES[resource]
                    reading=self.service.store.reading(key,resource)
                    item=label(tr('Básica' if resource=='odyle' else 'Recarga')+' '+(str(reading.value) if reading else '—'))
                    item.setObjectName('routineValue' if reading else 'routineCaption')
                    item.setContentsMargins(6,0,6,0)
                    item.setToolTip(tr(title)+' · '+self.service.profile_status(key))
                    head.addWidget(item)
                if not resources:head.addWidget(label('Sem itens fixados','routineCaption'))
            head.addWidget(self.tool('layout','Trocar estilo',self.toggle_style))
            head.addWidget(self.tool('lock' if prefs.panel_locked else 'unlock',
                'Destravar posição' if prefs.panel_locked else 'Travar posição',self.toggle_locked))
            head.addWidget(self.tool('chevron-up' if prefs.panel_expanded else 'chevron-down',
                'Recolher Rotina' if prefs.panel_expanded else 'Expandir Rotina',self.toggle_expanded))
            box.addWidget(header)
            if not strip and prefs.panel_expanded:
                for resource in prefs.pinned:
                    row=QFrame();row.setObjectName('routineRow');row.setFixedHeight(29)
                    line=QHBoxLayout(row);line.setContentsMargins(8,2,8,2);line.setSpacing(7)
                    picture=label('');picture.setPixmap(icon('energy').pixmap(14,14));line.addWidget(picture)
                    line.addWidget(label('Odyle' if resource=='odyle' else 'Recarregada'),1)
                    reading=self.service.store.reading(key,resource)
                    value=label(str(reading.value) if reading else '—','routineValue');line.addWidget(value)
                    row.setToolTip(tr(RESOURCES[resource][0])+' · '+tr(self.service.profile_status(key)))
                    box.addWidget(row)
            if not strip:
                footer=QFrame();bottom=QHBoxLayout(footer);bottom.setContentsMargins(7,0,3,0);bottom.setSpacing(4)
                bottom.addWidget(label(self.service.profile_status(key),'routineCaption'),1)
                bottom.addWidget(self.tool('chevron-right','Abrir Panorama',self.open_routine));box.addWidget(footer)
            else:
                head.addWidget(self.tool('chevron-right','Abrir Panorama',self.open_routine))
            if strip:
                self.setFixedSize(max(220,min(420,content.sizeHint().width()+2)),34)
            else:self.setFixedSize(220,29+(29*len(prefs.pinned) if prefs.panel_expanded else 0)+24)
        self.setWindowOpacity(prefs.panel_opacity)
        if prefs.panel_position!=self.saved_position:
            self.saved_position=prefs.panel_position;self.initial_position=False
        self.fit_screen();self.show()

    def fit_screen(self):
        screen=QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        if not self.initial_position:
            saved=self.context.prefs.routine.panel_position
            if saved is not None:self.move(*saved)
            else:
                area=screen.availableGeometry();self.move(area.left()+22,area.top()+275)
            self.initial_position=True
            screen=QGuiApplication.screenAt(self.geometry().center()) or screen
        area=screen.availableGeometry()
        self.move(max(area.left(),min(self.x(),area.right()-self.width()+1)),
                  max(area.top(),min(self.y(),area.bottom()-self.height()+1)))

    def toggle_style(self):
        prefs=self.context.prefs.routine;prefs.panel_style='strip' if prefs.panel_style=='pulse' else 'pulse'
        self.context.save()

    def toggle_expanded(self):
        prefs=self.context.prefs.routine;prefs.panel_expanded=not prefs.panel_expanded;self.context.save()

    def toggle_locked(self):
        prefs=self.context.prefs.routine;prefs.panel_locked=not prefs.panel_locked;self.context.save()

    def eventFilter(self,watched,event):
        if self.context.prefs.routine.panel_locked:return super().eventFilter(watched,event)
        if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
            self.drag=event.globalPosition().toPoint()-self.pos();return True
        if event.type()==QEvent.Type.MouseMove and self.drag is not None:
            self.move(event.globalPosition().toPoint()-self.drag);return True
        if event.type()==QEvent.Type.MouseButtonRelease and self.drag is not None:
            self.drag=None;self.fit_screen()
            self.context.prefs.routine.panel_position=(self.x(),self.y());self.context.save();return True
        return super().eventFilter(watched,event)

    def shutdown(self):
        self.closed=True;self.hide();self.close()
