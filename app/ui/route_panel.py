# SPDX-License-Identifier: GPL-3.0-only
"""Fio/Guia: a compact route HUD, independent of capture and navigation state."""
from PySide6.QtCore import Qt,QEvent,QTimer,QSize
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout,QVBoxLayout,QMenu,QSizePolicy,QLayout
from app.ui.localized_widgets import QToolButton
from app.ui.hud import HudSurface
from app.ui.widgets import label
from app.ui.icons import icon
from app.core.i18n import tr


class RoutePanel(HudSurface):
    def __init__(self,main):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.WindowDoesNotAcceptFocus)
        self.main=main;self.context=main.context;self.service=main.routes;self.drag=None;self.positioned=False
        self.setWindowTitle('Azphelumbra · Rotas');self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedWidth(303);self.setObjectName('routeHud')
        self.setStyleSheet(self.styleSheet()+'''QFrame#routeHud{border:0;background:transparent;}
            QLabel{font-size:11px;background:transparent;border:0;}
            QLabel#routeCount{color:#a7e4cb;} QLabel#routeCaption{font-size:10px;color:#aaa8bd;}
            QToolButton{border:0;background:transparent;padding:2px;color:#c2b2fc;}
            QToolButton:hover{background:#302943;}''')
        box=QHBoxLayout(self);box.setContentsMargins(8,4,6,4);box.setSpacing(6)
        box.setSizeConstraint(QLayout.SetNoConstraint)
        picture=label('');picture.setPixmap(icon('routes').pixmap(17,17));box.addWidget(picture)
        copy=QVBoxLayout();copy.setSpacing(2);self.name=label('');self.name.setTextFormat(Qt.PlainText)
        self.name.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        self.detail=label('','routeCaption');self.detail.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        copy.addWidget(self.name);copy.addWidget(self.detail);box.addLayout(copy,1)
        self.count=label('','routeCount');box.addWidget(self.count)
        self.pause_button=QToolButton();self.pause_button.setFixedSize(24,26);self.pause_button.clicked.connect(self.service.pause);box.addWidget(self.pause_button)
        self.menu_button=QToolButton();self.menu_button.setText('···');self.menu_button.setFixedSize(24,26)
        self.menu_button.setToolTip('Opções da rota');self.menu_button.setAccessibleName('Opções da rota');box.addWidget(self.menu_button)
        self.menu_button.clicked.connect(self.menu)
        for target in (picture,self.name,self.detail):target.installEventFilter(self)
        self.service.changed.connect(self.refresh);self.context.changed.connect(self.refresh)
        self.timer=QTimer(self);self.timer.setInterval(1000);self.timer.timeout.connect(self.refresh);self.timer.start()
        self.refresh()

    def refresh(self,*_):
        service=self.service;prefs=self.context.prefs.routes
        if not service.active or not prefs.panel_visible:self.hide();return
        guide=prefs.panel_style=='guide';self.detail.setVisible(guide);self.setFixedHeight(54 if guide else 38)
        resources={r.id:r.name for r in self.context.atlas_dataset.resources}
        name=' + '.join(resources.get(r,r) for r in service.route.resources) or service.route.name
        self.name.setText(self.name.fontMetrics().elidedText(name,Qt.ElideRight,max(25,self.name.width())))
        self.name.setToolTip(name)
        if service.complete:status='Volta concluída'
        elif service.paused:status='Rota pausada'
        elif not service.position:status='Aguardando minimapa'
        elif service.current==len(service.route.stops):status='Voltando ao início'
        else:status='Próxima parada'
        self.detail.setText(status);self.setToolTip(tr(status)+'\n'+tr(service.status))
        self.count.setText(tr('Retorno') if service.current==len(service.route.stops) and not service.complete
            else f'{min(service.current+1,len(service.route.stops))} / {len(service.route.stops)}')
        self.pause_button.setIcon(icon('play' if service.paused else 'pause'));self.pause_button.setIconSize(QSize(12,12))
        self.pause_button.setEnabled(not service.complete)
        self.pause_button.setToolTip('Retomar rota' if service.paused else 'Pausar rota')
        self.pause_button.setAccessibleName('Retomar rota' if service.paused else 'Pausar rota')
        self.fit_screen();self.show()

    def menu(self):
        menu=QMenu(self)
        for text,callback in [('Pular parada',self.service.skip),('Repetir rota',lambda:self.service.start(self.service.route)),
            ('Alternar Fio / Guia',self.toggle_style),('Abrir Rotas',lambda:self.main.quick_menu.open_page('routes')),
            ('Ocultar guia',self.hide_guide),('Encerrar rota',self.service.stop)]:
            action=menu.addAction(tr(text));action.triggered.connect(callback)
        menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))

    def toggle_style(self):
        prefs=self.context.prefs.routes;prefs.panel_style='guide' if prefs.panel_style=='strip' else 'strip';self.context.save()

    def hide_guide(self):self.context.prefs.routes.panel_visible=False;self.context.save()

    def fit_screen(self):
        screen=QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        if not self.positioned:
            saved=self.context.prefs.routes.panel_position;area=self.main.overlay.capture_area
            if saved:self.move(*saved)
            elif area:
                self.move(area.screen_x+area.x,area.screen_y+area.y+area.height+9)
                controls=getattr(self.main,'map_controls',None)
                if controls and controls.isVisible() and controls.geometry().intersects(self.geometry()):self.move(self.x(),controls.geometry().bottom()+8)
            else:
                bounds=screen.availableGeometry();self.move(bounds.right()-self.width()-22,bounds.top()+365)
            self.positioned=True;screen=QGuiApplication.screenAt(self.geometry().center()) or screen
        bounds=screen.availableGeometry();self.move(max(bounds.left(),min(self.x(),bounds.right()-self.width()+1)),max(bounds.top(),min(self.y(),bounds.bottom()-self.height()+1)))

    def eventFilter(self,watched,event):
        if event.type()==QEvent.MouseButtonPress and event.button()==Qt.LeftButton:self.drag=event.globalPosition().toPoint()-self.pos();return True
        if event.type()==QEvent.MouseMove and self.drag is not None:self.move(event.globalPosition().toPoint()-self.drag);return True
        if event.type()==QEvent.MouseButtonRelease and self.drag is not None:
            self.drag=None;self.fit_screen();self.context.prefs.routes.panel_position=(self.x(),self.y());self.context.save();return True
        return super().eventFilter(watched,event)

    def shutdown(self):self.timer.stop();self.hide();self.close()
