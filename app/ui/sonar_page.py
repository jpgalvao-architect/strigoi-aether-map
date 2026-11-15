# SPDX-License-Identifier: GPL-3.0-only
"""Accessible visual cue for a sound that may be difficult to hear."""
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from app.ui.localized_widgets import QComboBox, QDialog, QWidget, QToolButton
from app.core.i18n import Verbatim, clock, tr
from app.modules.sonar.capture import processes
from app.ui.icons import icon
from app.ui.widgets import button, card, label, page_header, row
from app.ui.hud import HudSurface


ALERT_TITLE = 'Cubo oculto detectado!'
ALERT_DETAIL = 'Há um cubo nas proximidades.'
ALERT_DURATION_MS = 8000


class SonarAlert(HudSurface):
    def __init__(self, context):
        super().__init__(None,Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|
                         Qt.WindowType.Tool|Qt.WindowType.WindowDoesNotAcceptFocus)
        self.context=context
        self.drag=None
        self.testing=False
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle('Azphelumbra · Sonar')
        self.setFixedWidth(350)
        layout=QHBoxLayout(self)
        layout.setContentsMargins(12,10,9,10); layout.setSpacing(9)
        picture=label('');picture.setPixmap(icon('cube').pixmap(38,38))
        layout.addWidget(picture)
        copy=QVBoxLayout()
        self.title=label(ALERT_TITLE)
        self.title.setStyleSheet('font-size:13px;font-weight:600;')
        self.detail=label(ALERT_DETAIL,'subtitle',True)
        copy.addWidget(self.title);copy.addWidget(self.detail)
        layout.addLayout(copy,1)
        close=QToolButton();close.setIcon(icon('close'));close.setFixedSize(30,30)
        close.setAccessibleName('Dispensar aviso do sonar');close.setToolTip('Dispensar aviso')
        close.clicked.connect(self.hide)
        layout.addWidget(close)
        for widget in [picture,self.title,self.detail]:widget.installEventFilter(self)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.hide)

    def present(self,test=False):
        self.testing=test
        self.title.setText('Teste do aviso do sonar' if test else ALERT_TITLE)
        self.detail.setText('Este é apenas um teste visual.' if test else ALERT_DETAIL)
        screens=QGuiApplication.screens()
        screen=screens[min(len(screens)-1,self.context.prefs.overlay.monitor-1)]
        g=screen.availableGeometry()
        self.adjustSize()
        position=self.context.prefs.sonar_alert_position
        if position:self.move(*position)
        else:self.move(g.center().x()-self.width()//2,g.top()+40)
        screen=QGuiApplication.screenAt(self.geometry().center()) or screen
        g=screen.availableGeometry()
        self.move(max(g.left(),min(self.x(),g.right()-self.width()+1)),max(g.top(),min(self.y(),g.bottom()-self.height()+1)))
        self.show()
        if self.isVisible():
            self.timer.start(ALERT_DURATION_MS)

    def keep_visible(self):
        if self.isVisible() and not self.testing:
            self.timer.start(ALERT_DURATION_MS)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def eventFilter(self,watched,event):
        if not self.isWindow(): return super().eventFilter(watched,event)
        if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
            self.drag=event.globalPosition().toPoint()-self.pos();return True
        if event.type()==QEvent.Type.MouseMove and self.drag is not None:
            self.move(event.globalPosition().toPoint()-self.drag);return True
        if event.type()==QEvent.Type.MouseButtonRelease and self.drag is not None:
            self.drag=None
            self.context.prefs.sonar_alert_position=(self.x(),self.y());self.context.save();return True
        return super().eventFilter(watched,event)


class SonarPage(QWidget):
    def __init__(self,context,service,alert):
        super().__init__()
        self.context,self.service,self.alert=context,service,alert
        layout=QVBoxLayout(self);layout.setContentsMargins(26,20,26,20)
        layout.addWidget(page_header('Sonar de cubos','Uma pista visual para o som dos cubos ocultos.'))
        frame,body=card()
        body.addWidget(label('Ouvir o jogo','eyebrow'))
        body.addWidget(label('Selecione o aplicativo do AION 2. O sonar analisa somente o áudio desse aplicativo, sem usar o microfone.','subtitle',True))
        self.process=QComboBox();self.process.setAccessibleName('Aplicativo do jogo')
        self.refresh_button=button('Atualizar aplicativos',self.refresh_processes)
        body.addLayout(row(self.process,self.refresh_button))
        self.sensitivity=QComboBox()
        self.sensitivity.addItem('Equilibrada','balanced');self.sensitivity.addItem('Alta · pode gerar mais avisos','sensitive')
        self.sensitivity.setCurrentIndex(self.sensitivity.findData(context.prefs.sonar_sensitivity))
        self.sensitivity.currentIndexChanged.connect(self.save_sensitivity)
        body.addLayout(row(label('Sensibilidade'),self.sensitivity))
        self.status=label('Desligado','eyebrow',True);body.addWidget(self.status)
        self.confirmed = False
        self.presence=label('Cubo não detectado','subtitle');body.addWidget(self.presence)
        self.start_button=button('Ativar sonar',self.start,True)
        self.stop_button=button('Parar sonar',service.stop)
        body.addLayout(row(self.start_button,self.stop_button,button('Testar aviso visual',self.test_notice)))
        body.addWidget(label('O aviso indica um som compatível, sem revelar posição ou distância. A detecção pode falhar em meio a outros efeitos.','subtitle',True))
        body.addWidget(label('O áudio é analisado neste computador e não é gravado. Sua escolha de ativação fica salva; o sonar aguarda o jogo para retomar.','subtitle',True))
        layout.addWidget(frame)
        self.last_notice = None
        self.last_detection=label('Nenhum aviso nesta sessão.','subtitle',True)
        layout.addWidget(self.last_detection)
        layout.addStretch()
        service.status_changed.connect(self.status.setText)
        service.active_changed.connect(self.refresh_active)
        context.changed.connect(lambda:self.stop_button.setEnabled(service.active or context.prefs.sonar_resume))
        service.detected.connect(self.show_detection)
        service.confirmation_updated.connect(self.show_confirmation)
        self.refresh_processes();self.refresh_active(False)

    def test_notice(self):
        gate=getattr(self.alert,'_visibility_gate',None)
        if gate is None or gate.allows('alert'):
            self.alert.present(test=True)
            return
        # A preview belongs to the app window; it is never an always-on-top HUD.
        dialog=QDialog(self);dialog.setWindowTitle('Teste do aviso do sonar')
        body=QVBoxLayout(dialog)
        preview=SonarAlert(self.context)
        preview.setParent(dialog);preview.setWindowFlags(Qt.WindowType.Widget)
        preview.testing=True;preview.title.setText('Teste do aviso do sonar')
        preview.detail.setText('Este é apenas um teste visual.')
        for close in preview.findChildren(QToolButton):close.clicked.connect(dialog.accept)
        body.addWidget(preview);preview.show()
        body.addWidget(button('Fechar',dialog.accept))
        dialog.exec();preview.timer.stop();dialog.deleteLater()

    def refresh_processes(self):
        current=self.process.currentData()
        self.process.clear();self.process.addItem('Selecione o aplicativo do jogo',None)
        try:
            items=processes()
            for item in items:self.process.addItem(Verbatim(f'{item.name} · {item.pid}'),item.pid)
            index=self.process.findData(current)
            if index<=0:
                preferred=self.context.prefs.sonar_process_name
                index=next((i+1 for i,p in enumerate(items) if p.name==preferred),0)
                if not index:index=next((i+1 for i,p in enumerate(items) if 'aion' in p.name.casefold()),0)
            self.process.setCurrentIndex(index)
        except OSError:
            self.status.setText('Não foi possível listar os aplicativos. Tente atualizar.')

    def save_sensitivity(self):
        self.context.prefs.sonar_sensitivity=self.sensitivity.currentData()
        self.context.save()

    def refresh_active(self,active):
        self.presence.setVisible(active)
        if not active:
            self.alert.hide()
        for widget in [self.process,self.refresh_button,self.sensitivity,self.start_button]:widget.setEnabled(not active)
        self.stop_button.setEnabled(active or self.context.prefs.sonar_resume)

    def start(self):
        try:
            pid=self.process.currentData()
            if pid is None:raise ValueError('Abra o jogo, atualize a lista e selecione seu aplicativo.')
            name=self.process.currentText().rsplit(' · ',1)[0]
            if not any(p.pid==pid and p.name==name for p in processes()):
                raise ValueError('Esse aplicativo foi encerrado. Atualize a lista e selecione o jogo novamente.')
            self.context.prefs.sonar_process_name=name
            self.context.save()
            self.service.start(pid)
        except (ValueError,OSError,RuntimeError) as exc:
            self.status.setText(str(exc))

    def retranslate(self):
        super().retranslate()
        self.refresh_notice()

    def refresh_notice(self):
        if self.last_notice is not None:
            self.last_detection.setText(Verbatim(
                tr('Último aviso às {time} · cubo oculto detectado.').format(time=clock(self.last_notice, seconds=True))
            ))

    def show_detection(self, detection):
        self.last_notice = datetime.now()
        self.refresh_notice()
        self.alert.present()

    def show_confirmation(self, confirmed):
        if confirmed != self.confirmed:
            self.confirmed = confirmed
            self.presence.setText('Cubo detectado' if confirmed else 'Cubo não detectado')
        if confirmed:
            self.alert.keep_visible()
