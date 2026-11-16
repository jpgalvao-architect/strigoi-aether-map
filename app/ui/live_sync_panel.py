# SPDX-License-Identifier: GPL-3.0-only
"""Live Sync panels inside the Siege Command workspace."""
import secrets
from urllib.parse import urlencode

from PySide6.QtCore import QSignalBlocker, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QStackedWidget, QVBoxLayout

from app.core.i18n import Verbatim, language
from app.ui.localized_widgets import QComboBox, QDialog, QLineEdit, QMessageBox, QWidget
from app.ui.widgets import button, label

REPO = 'https://github.com/jpgalvao-architect/strigoi-aether-map/tree/main/backend/live-sync'
DEPLOY_URL = 'https://deploy.workers.cloudflare.com/?' + urlencode({'url': REPO})
GUIDE_URL = 'https://jpgalvao-architect.github.io/strigoi-aether-map/live-sync.html'


def open_url(url):
    return QDesktopServices.openUrl(QUrl(url))


class SetupDialog(QDialog):
    def __init__(self, sync, parent):
        super().__init__(parent)
        self.sync = sync
        self.key = secrets.token_hex(32)
        self.setWindowTitle('Configurar Live Sync')
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.addWidget(label('Configurar Live Sync', 'title', True))
        self.pages = QStackedWidget()
        layout.addWidget(self.pages)
        self.deploy_step()
        self.verify_step()
        self.status = label('', 'subtitle', True)
        layout.addWidget(self.status)
        layout.addWidget(button('Abrir guia de configuração', lambda: open_url(GUIDE_URL + '?' + urlencode({'lang': language()}))))
        layout.addWidget(button('Cancelar', self.reject))
        self.sync.pairing_done.connect(self.result)
        self.finished.connect(self.cleanup)

    def step(self, title, body):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 4)
        layout.setSpacing(10)
        layout.addWidget(label(title, 'section', True))
        layout.addWidget(label(body, 'subtitle', True))
        self.pages.addWidget(page)
        return layout

    def deploy_step(self):
        layout = self.step(
            '1 de 2 · Implantar na sua conta',
            'Entre na Cloudflare pelo navegador e escolha sua conta no plano Free. '
            'O assistente da Cloudflare cria o Worker e o armazenamento da sessão.',
        )
        layout.addWidget(label(
            'Copie a chave abaixo e cole no campo LIVE_SYNC_OWNER_KEY durante a implantação. '
            'Guarde essa chave para você.', 'subtitle', True,
        ))
        layout.addWidget(button('Copiar chave de vinculação', self.copy_key))
        layout.addWidget(button('Implantar na Cloudflare', self.deploy, primary=True))
        layout.addWidget(label('Se a Cloudflare pedir, conecte seu GitHub para copiar o modelo.', 'subtitle', True))
        layout.addWidget(button('Já tenho o endereço do Worker', lambda: self.move_to(1, existing=True)))

    def verify_step(self):
        layout = self.step(
            '2 de 2 · Verificar a conexão',
            'Depois da implantação, copie o endereço .workers.dev que a Cloudflare mostra e cole aqui.',
        )
        self.endpoint = QLineEdit()
        self.endpoint.setMaxLength(200)
        self.endpoint.setPlaceholderText(Verbatim('https://azphelumbra-live-sync.conta.workers.dev'))
        self.endpoint.setAccessibleName('Endereço do Worker')
        self.endpoint.returnPressed.connect(self.verify)
        layout.addWidget(self.endpoint)
        self.existing_key = QLineEdit()
        self.existing_key.setMaxLength(64)
        self.existing_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.existing_key.setPlaceholderText('Chave anterior, se já implantou (opcional)')
        self.existing_key.setAccessibleName('Chave de vinculação')
        self.existing_key.returnPressed.connect(self.verify)
        layout.addWidget(self.existing_key)
        self.verify_button = button('Verificar e vincular', self.verify, primary=True)
        layout.addWidget(self.verify_button)
        self.previous = button('Voltar à implantação', lambda: self.move_to(0))
        layout.addWidget(self.previous)

    def copy_key(self):
        QApplication.clipboard().setText(self.key)
        self.status.setText('Chave copiada. Cole no campo LIVE_SYNC_OWNER_KEY da Cloudflare.')

    def deploy(self):
        if open_url(DEPLOY_URL):
            self.move_to(1)
        else:
            self.status.setText('Não foi possível abrir o navegador.')

    def move_to(self, page, *, existing=False):
        self.status.clear()
        self.pages.setCurrentIndex(page)
        if page == 1:
            self.existing_key.setVisible(existing)
            self.endpoint.setFocus()

    def verify(self):
        if not self.verify_button.isEnabled():
            return
        try:
            endpoint = self.endpoint.text().strip()
            if '://' not in endpoint and endpoint.lower().rstrip('/').endswith('.workers.dev'):
                endpoint = 'https://' + endpoint
            previous_key = self.existing_key.text().strip() if self.existing_key.isVisible() else ''
            self.sync.pair(endpoint, previous_key or self.key)
        except ValueError as error:
            self.status.setText(str(error))
            return
        self.verify_button.setEnabled(False)
        self.previous.setEnabled(False)
        self.status.setText('Verificando implantação, armazenamento e canal de sincronização…')

    def result(self, error):
        if not error:
            self.accept()
            return
        self.status.setText(error)
        self.verify_button.setEnabled(True)
        self.previous.setEnabled(True)

    def cleanup(self):
        self.sync.pairing_done.disconnect(self.result)
        self.sync.cancel_pairing()
        clipboard = QApplication.clipboard()
        if clipboard.text() and clipboard.text() in {self.key, self.existing_key.text()}:
            clipboard.clear()
        self.existing_key.clear()
        self.key = ''


class LiveSyncPanel(QWidget):
    def __init__(self, sync, parent=None):
        super().__init__(parent)
        self.sync = sync
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.mode = QComboBox()
        self.mode.addItem('Desativado', 'off')
        self.mode.addItem('Hospedar sessão (Caller)', 'host')
        self.mode.addItem('Participar de sessão (Jogador)', 'player')
        layout.addWidget(self.mode)
        self.views = QStackedWidget()
        layout.addWidget(self.views)
        self.overlay_hint = label('Para ver a estratégia no jogo, ative Overlay de Reshanta acima.', 'subtitle', True)
        layout.addWidget(self.overlay_hint)
        off = self.page()
        off.addWidget(label('Compartilhe marcações táticas de Lower Reshanta durante a siege.', 'subtitle', True))
        self.host_page()
        self.player_page()
        self.state = label('', 'subtitle', True)
        self.message = label('', 'subtitle', True)
        layout.addWidget(self.state)
        layout.addWidget(self.message)
        layout.addStretch()
        self.mode.currentIndexChanged.connect(self.change_mode)
        sync.changed.connect(self.refresh)
        self.refresh()

    def page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(7)
        self.views.addWidget(widget)
        return layout

    def host_page(self):
        layout = self.page()
        self.cloud = label('', 'subtitle', True)
        self.host_session = label('', 'subtitle', True)
        self.dirty = label('', 'subtitle', True)
        self.configure_button = button('Configurar Cloudflare', self.configure, primary=True)
        self.create_button = button('Criar sessão', self.sync.create, primary=True)
        self.invite_button = button('Copiar convite', self.copy_invite)
        self.rotate_button = button('Gerar novo convite', self.rotate)
        self.publish_button = button('Publicar alterações', self.sync.publish, primary=True)
        self.close_button = button('Encerrar sessão', self.close_room)
        self.forget_button = button('Desconectar Cloudflare', self.sync.forget)
        for widget in (self.cloud, self.configure_button, self.create_button, self.host_session, self.dirty,
                       self.publish_button, self.invite_button, self.rotate_button, self.close_button,
                       self.forget_button):
            layout.addWidget(widget)
        layout.addStretch()

    def player_page(self):
        layout = self.page()
        self.invite_input = QLineEdit()
        self.invite_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.invite_input.setMaxLength(256)
        self.invite_input.setPlaceholderText('Cole o convite do caller')
        self.invite_input.setAccessibleName('Convite da sessão')
        self.invite_input.returnPressed.connect(self.join)
        self.player_session = label('', 'subtitle', True)
        self.join_button = button('Entrar na sessão', self.join, primary=True)
        self.leave_button = button('Sair da sessão', self.sync.leave)
        for widget in (self.invite_input, self.join_button, self.player_session, self.leave_button):
            layout.addWidget(widget)
        layout.addStretch()

    def confirm(self, text):
        return QMessageBox.question(self, 'Live Sync', text, QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No) == QMessageBox.Yes

    def change_mode(self, index):
        mode = self.mode.itemData(index)
        if mode == self.sync.mode:
            return
        if self.sync.publisher and not self.confirm(
            'Ao mudar de modo, você perde os controles da sessão. Encerre a sessão para desconectar todos agora. Mudar de modo?',
        ):
            with QSignalBlocker(self.mode):
                self.mode.setCurrentIndex(self.mode.findData(self.sync.mode))
            return
        self.invite_input.clear()
        self.sync.set_mode(mode)

    def configure(self):
        dialog = SetupDialog(self.sync, self)
        dialog.exec()
        dialog.deleteLater()

    def copy_invite(self):
        if self.sync.invite:
            QApplication.clipboard().setText(self.sync.invite.encode())
            self.sync.report(self.sync.state, 'Convite copiado.')

    def rotate(self):
        if self.confirm('Gerar um novo convite invalida o anterior e desconecta os jogadores. Continuar?'):
            self.sync.rotate()

    def close_room(self):
        if self.confirm('Encerrar a sessão e desconectar os jogadores?'):
            self.sync.close_room()

    def join(self):
        try:
            self.sync.join(self.invite_input.text())
        except ValueError as error:
            self.sync.report(self.sync.state, str(error))
        else:
            if self.sync.invite:
                self.invite_input.clear()

    def refresh(self):
        sync = self.sync
        self.views.setCurrentIndex(self.mode.findData(sync.mode))
        room = sync.invite
        paired = sync.owner is not None
        hosting = room is not None and sync.publisher is not None
        joining = room is not None and not hosting
        self.cloud.setText('Cloudflare verificada e vinculada.' if paired else 'Cloudflare ainda não vinculada.')
        self.configure_button.setVisible(not paired)
        self.create_button.setVisible(paired and not hosting)
        self.create_button.setEnabled(not sync.busy)
        self.forget_button.setVisible(paired and not hosting)
        self.forget_button.setEnabled(not sync.busy)
        self.host_session.setVisible(hosting)
        self.dirty.setVisible(hosting)
        if hosting:
            self.host_session.setText(f'Sessão {room.session[:6].upper()} · {sync.participants} online · versão {sync.version}')
            self.dirty.setText('Alterações locais pendentes.' if sync.dirty else 'Estratégia local publicada.')
        for widget in (self.invite_button, self.publish_button, self.rotate_button, self.close_button):
            widget.setVisible(hosting)
            widget.setEnabled(not sync.busy)
        self.publish_button.setEnabled(not sync.busy and sync.dirty)
        self.invite_input.setVisible(not joining)
        self.join_button.setVisible(not joining)
        self.player_session.setVisible(joining)
        self.overlay_hint.setVisible(joining)
        self.leave_button.setVisible(joining)
        if joining:
            self.player_session.setText(f'Sessão {room.session[:6].upper()} · versão recebida {sync.version}')
        self.state.setText(sync.state)
        self.message.setText(sync.feedback)
        self.state.setVisible(bool(sync.state))
        self.message.setVisible(bool(sync.feedback))
