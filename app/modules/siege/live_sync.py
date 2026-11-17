# SPDX-License-Identifier: GPL-3.0-only
"""Opt-in Qt client. The receiver's strategy lives only in memory."""
import hmac
import json
import random
import secrets
import time
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWebSockets import QWebSocket

from app.modules.siege.live_sync_credentials import PairingStore
from app.modules.siege.live_sync_protocol import (
    IncompatibleCatalogue, Invite, KEY, MAX_BYTES, digest, endpoint_url, read_snapshot, sign, snapshot_bytes,
    version_notice,
)

ERRORS = {
    401: 'A chave ou o convite não é mais válido.',
    403: 'Esta ação não é permitida nesta sessão.',
    410: 'Sessão encerrada ou expirada.',
    413: 'A estratégia excede 512 KiB.',
    422: 'O servidor recusou o formato da estratégia.',
    429: 'Limite temporário atingido. Tente novamente em instantes.',
}


@dataclass(frozen=True)
class Reply:
    status: int
    body: bytes
    version: bytes
    etag: bytes

    def object(self):
        value = json.loads(self.body)
        if not isinstance(value, dict):
            raise ValueError
        return value


class LiveSync(QObject):
    changed = Signal()
    pairing_done = Signal(str)

    def __init__(self, siege, directory, parent=None):
        super().__init__(parent)
        self.siege = siege
        self.store = PairingStore(directory)
        self.owner = self.store.load()
        self.network = QNetworkAccessManager(self)
        self.mode = 'off'
        self.generation = 0
        self.setup_generation = 0
        self.setup_socket = None
        self.socket = None
        self.replies = set()
        self.invite = None
        self.publisher = None
        self.pending_room = None
        self.pending_reader = None
        self.version = 0
        self.checksum = None
        self.wanted = 0
        self.wanted_hash = None
        self.participants = 0
        self.attempt = 0
        self.busy = False
        self.fetching = False
        self.status_pending = False
        self.waiting_pong = False
        self.state = ''
        self.feedback = ''
        self.reconnect = self.timer(self.open_room, single=True)
        self.fetch_delay = self.timer(self.fetch_snapshot, single=True)
        self.watchdog = self.timer(self.keepalive)
        self.presence = self.timer(self.refresh_host)
        self.dirty_delay = self.timer(self.changed.emit, single=True)
        siege.changed.connect(self.local_changed)

    def timer(self, callback, *, single=False):
        timer = QTimer(self)
        timer.setSingleShot(single)
        timer.timeout.connect(callback)
        return timer

    def local_changed(self):
        if self.publisher:
            self.dirty_delay.start(150)

    @property
    def dirty(self):
        if not self.publisher:
            return False
        try:
            return digest(snapshot_bytes(self.siege.exportable_preset())) != self.checksum
        except ValueError:
            return True

    def report(self, state, feedback=''):
        self.state, self.feedback = state, feedback
        self.changed.emit()

    def request(self, url, callback, *, method='GET', key=None, body=None, headers=None, pairing=False):
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.ManualRedirectPolicy)
        request.setTransferTimeout(9000)
        if key:
            request.setRawHeader(b'Authorization', b'Bearer ' + key.encode('ascii'))
        for name, value in (headers or {}).items():
            request.setRawHeader(name, value)
        if body is not None:
            request.setRawHeader(b'Content-Type', b'application/json')
        reply = self.network.sendCustomRequest(request, method.encode('ascii'), body or b'')
        generation = self.setup_generation if pairing else self.generation
        self.replies.add(reply)
        reply.setReadBufferSize(MAX_BYTES + 1)
        buffer = bytearray()
        exceeded = False

        def read():
            nonlocal exceeded
            if exceeded:
                return
            buffer.extend(bytes(reply.readAll()))
            if len(buffer) > MAX_BYTES:
                exceeded = True
                reply.abort()

        def finish():
            if reply not in self.replies:
                return
            self.replies.remove(reply)
            # Drain the final chunk without aborting an already finished reply.
            buffer.extend(bytes(reply.readAll()))
            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0
            if exceeded or len(buffer) > MAX_BYTES:
                status = 413
            elif status in (200, 201, 204, 304) and reply.error() != reply.NetworkError.NoError:
                status = 0
            result = Reply(status, bytes(buffer), bytes(reply.rawHeader('X-Siege-Version')),
                           bytes(reply.rawHeader('ETag')))
            reply.deleteLater()
            if generation == (self.setup_generation if pairing else self.generation):
                callback(result)

        deadline = QTimer(reply)
        deadline.setSingleShot(True)
        deadline.timeout.connect(reply.abort)
        reply.readyRead.connect(read)
        reply.finished.connect(finish)
        deadline.start(12000)

    def set_mode(self, mode):
        if mode != self.mode:
            self.mode = mode
            self.cancel_pairing()
            self.reset_room()
            self.report('')

    def reset_room(self):
        self.generation += 1
        self.drop_socket()
        for timer in (self.reconnect, self.fetch_delay, self.presence, self.dirty_delay):
            timer.stop()
        self.invite = self.publisher = self.pending_room = self.pending_reader = None
        self.fetching = self.busy = self.status_pending = False
        self.version = self.wanted = self.participants = self.attempt = 0
        self.checksum = self.wanted_hash = None
        self.siege.set_session_preset(None)

    def shutdown(self):
        self.cancel_pairing()
        self.reset_room()
        for reply in tuple(self.replies):
            reply.abort()

    def leave(self):
        self.reset_room()
        self.report('Desconectado.')

    def forget(self):
        if self.invite or self.busy:
            return
        try:
            self.store.remove()
        except OSError:
            self.report('Erro.', 'Não foi possível remover a vinculação do Windows.')
            return
        self.owner = None
        self.report('Desconectado.')

    def cancel_pairing(self):
        self.setup_generation += 1
        self.discard_setup_socket()

    def discard_setup_socket(self):
        socket, self.setup_socket = self.setup_socket, None
        if socket:
            socket.abort()
            socket.deleteLater()

    def pair(self, endpoint, owner):
        endpoint = endpoint_url(endpoint)
        if self.mode != 'host' or self.invite or not KEY.fullmatch(owner):
            raise ValueError('Use a chave de vinculação criada pelo Azphelumbra.')
        self.cancel_pairing()

        def health(reply):
            try:
                info = reply.object()
            except (ValueError, UnicodeError):
                info = {}
            if reply.status != 200 or info.get('protocol') != 1:
                self.pairing_done.emit('O endereço ainda não responde como Live Sync. Confira a implantação.')
            elif info.get('configured') is not True:
                self.pairing_done.emit('Falta a chave de vinculação na Cloudflare. Confira o campo LIVE_SYNC_OWNER_KEY.')
            else:
                self.verify_websocket(endpoint, owner)

        self.request(endpoint + '/v1/health', health, pairing=True)

    def verify_websocket(self, endpoint, owner):
        nonce = secrets.token_hex(32)
        expected = sign(owner, 'setup-v1:' + nonce)
        socket = self.setup_socket = self.new_socket()
        deadline = QTimer(socket)
        deadline.setSingleShot(True)

        def finish(error):
            if socket is not self.setup_socket:
                return
            self.discard_setup_socket()
            self.pairing_done.emit(error)

        def message(text):
            if socket is not self.setup_socket:
                return
            try:
                result = json.loads(text)
                proof = result.get('proof') if isinstance(result, dict) else None
                valid = (isinstance(proof, str) and KEY.fullmatch(proof)
                         and result.get('type') == 'ready' and result.get('protocol') == 1
                         and hmac.compare_digest(proof, expected))
            except ValueError:
                valid = False
            if not valid:
                finish('A chave do Worker difere da chave de vinculação deste assistente.')
                return
            try:
                self.store.save(endpoint, owner)
            except OSError:
                finish('Não foi possível guardar a chave com segurança no Windows.')
                return
            self.owner = endpoint, owner
            self.report('Cloudflare pronta para hospedar.')
            finish('')

        unavailable = 'O canal de sincronização do Worker está indisponível. Confira a implantação e tente novamente.'
        deadline.timeout.connect(lambda: finish(unavailable))
        socket.errorOccurred.connect(lambda _error: finish(unavailable))
        socket.disconnected.connect(lambda: finish(unavailable))
        socket.textMessageReceived.connect(message)
        deadline.start(10000)
        self.open_socket(socket, endpoint, '/v1/setup/' + nonce)

    def new_socket(self):
        socket = QWebSocket(parent=self)
        socket.setMaxAllowedIncomingMessageSize(2048)
        socket.setMaxAllowedIncomingFrameSize(2048)
        return socket

    @staticmethod
    def open_socket(socket, endpoint, path, key=None):
        request = QNetworkRequest(QUrl('wss' + endpoint[5:] + path))
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.ManualRedirectPolicy)
        if key:
            request.setRawHeader(b'Authorization', b'Bearer ' + key.encode('ascii'))
        socket.open(request)

    def room_request(self, callback, *, suffix='', method='GET', body=None, headers=None):
        invite = self.invite
        self.request(f'{invite.endpoint}/v1/sessions/{invite.session}{suffix}', callback, method=method,
                     key=self.publisher or invite.reader, body=body, headers=headers)

    def create(self):
        if self.mode != 'host' or not self.owner or self.invite or self.busy:
            return
        endpoint, owner = self.owner
        if not self.pending_room:
            self.pending_room = (secrets.token_hex(16), secrets.token_hex(32), secrets.token_hex(32))
        session, reader, publisher = self.pending_room
        now = time.time_ns() // 1_000_000
        proof = sign(owner, f'create-v1:{session}:{now}:{reader}:{publisher}')
        self.busy = True
        self.report('Conectando…')

        def created(reply):
            self.busy = False
            try:
                if reply.status not in (200, 201):
                    raise ValueError
                self.version, self.checksum = version_notice(reply.object())
            except ValueError:
                if reply.status in (401, 409, 410):
                    self.pending_room = None
                self.report('Erro.', self.error(reply))
                return
            self.pending_room = None
            self.invite = Invite(endpoint, session, reader)
            self.publisher = publisher
            self.presence.start(12000)
            self.open_room()

        self.request(f'{endpoint}/v1/sessions/{session}', created, method='POST', key=proof,
                     body=json.dumps({'reader': reader, 'publisher': publisher, 'time': now}).encode('ascii'))

    def join(self, text):
        if self.mode != 'player' or self.invite:
            return
        invite = Invite.parse(text)
        self.reset_room()
        self.invite = invite
        self.report('Conectando…')
        self.fetch_snapshot(initial=True)

    def drop_socket(self):
        self.watchdog.stop()
        self.waiting_pong = False
        socket, self.socket = self.socket, None
        if socket:
            socket.abort()
            socket.deleteLater()

    def keepalive(self):
        if not self.socket:
            return
        if self.waiting_pong:
            self.lost_socket()
        else:
            self.waiting_pong = True
            self.socket.ping()
            self.watchdog.start(25000)

    def open_room(self):
        if not self.invite or self.socket:
            return
        socket = self.socket = self.new_socket()
        self.waiting_pong = True
        self.watchdog.start(18000)
        socket.textMessageReceived.connect(lambda text: self.notice(text) if socket is self.socket else None)
        socket.pong.connect(lambda *_: self.acknowledge() if socket is self.socket else None)
        socket.disconnected.connect(lambda: self.lost_socket() if socket is self.socket else None)
        socket.errorOccurred.connect(lambda _: self.lost_socket() if socket is self.socket else None)
        invite = self.invite
        self.open_socket(socket, invite.endpoint, f'/v1/sessions/{invite.session}/watch', self.publisher or invite.reader)

    def acknowledge(self):
        self.waiting_pong = False
        self.watchdog.start(25000)

    def notice(self, text):
        try:
            data = json.loads(text)
            kind = data.get('type') if isinstance(data, dict) else None
            if kind in ('closed', 'revoked'):
                self.terminal(410 if kind == 'closed' else 401)
                return
            if kind != 'version':
                raise ValueError
            version, checksum = version_notice(data)
        except ValueError:
            self.lost_socket()
            return
        recovering = self.attempt != 0
        self.attempt = 0
        self.acknowledge()
        if self.publisher:
            self.update_host(data, version, checksum)
            if not self.busy:
                self.report('Conectado.', self.feedback if not recovering else '')
            return
        if version > self.wanted:
            self.wanted, self.wanted_hash = version, checksum
        if self.version < self.wanted:
            self.report('Sincronizando…')
            if not self.fetch_delay.isActive() and not self.fetching:
                # Spread each publication's fan-out across clients.
                spread = data.get('spread')
                ceiling = spread if type(spread) is int and 3500 <= spread <= 10000 else 3500
                self.fetch_delay.start(random.randint(150, ceiling))
        else:
            self.report('Atualizado.' if self.version else 'Aguardando a primeira publicação.')

    def lost_socket(self):
        self.drop_socket()
        if not self.invite or self.reconnect.isActive():
            return
        self.attempt += 1
        base = 2000 if self.publisher else 4000
        upper = min(30_000, base * 2 ** min(self.attempt - 1, 4))
        self.reconnect.start(random.randint(upper // 2, upper))
        if not self.busy:
            self.report('Reconectando…', 'A última estratégia recebida continua visível.' if self.version and not self.publisher else '')
        if self.publisher:
            self.refresh_host()
        else:
            self.fetch_delay.stop()
            if self.attempt >= 2 and not self.fetching:
                # A successful WebSocket returns the current version. Probe HTTP only
                # after repeated failures to distinguish an expired or revoked invite.
                self.fetch_delay.start(random.randint(upper // 2, upper))

    def terminal(self, status):
        self.reset_room()
        self.report('Sessão encerrada.' if status == 410 else 'Desconectado.', ERRORS[status])

    @staticmethod
    def error(reply):
        return ERRORS.get(reply.status, 'Não foi possível comunicar com o Worker. Tente novamente.')

    def fetch_snapshot(self, initial=False):
        if not self.invite or self.publisher or self.fetching:
            return
        self.fetching = True
        headers = {b'If-None-Match': f'"{self.checksum}"'.encode('ascii')} if self.checksum else {}
        self.room_request(lambda reply: self.accept_snapshot(reply, initial), suffix='/snapshot', headers=headers)

    def accept_snapshot(self, reply, initial):
        self.fetching = False
        if reply.status in (401, 403, 410):
            self.terminal(reply.status)
            return
        if initial and (reply.status in (0, 429) or reply.status >= 500):
            self.lost_socket()
            return
        try:
            if reply.status == 200:
                if not reply.version.isdigit() or len(reply.version) > 10:
                    raise ValueError
                version = int(reply.version)
                checksum = digest(reply.body)
                # A proxy can weaken an ETag during transfer encoding. The
                # checksum must still match the full body and any socket notice.
                etag = reply.etag.removeprefix(b'W/')
                if (not version or etag != f'"{checksum}"'.encode('ascii')
                        or (version == self.wanted and self.wanted_hash != checksum)
                        or (version == self.version and self.checksum != checksum)):
                    raise ValueError
                if version > self.version:
                    preset = read_snapshot(reply.body)
                    self.version, self.checksum = version, checksum
                    self.siege.set_session_preset(preset)
            elif reply.status not in (204, 304):
                raise ValueError
        except IncompatibleCatalogue:
            self.reset_room()
            self.report('Erro.', 'O catálogo da sessão exige uma versão mais recente do Azphelumbra.')
            return
        except (ValueError, UnicodeError, RecursionError):
            if initial:
                self.reset_room()
                self.report('Erro.', self.error(reply) if reply.status != 200 else 'O Worker retornou uma estratégia inválida.')
            elif self.socket:
                self.report('Sincronizando…', 'Não foi possível obter a versão publicada. Tentando novamente.')
                self.fetch_delay.start(random.randint(1300, 4000))
            return
        if initial:
            self.open_room()
        elif self.socket and not self.waiting_pong:
            self.report('Sincronizando…' if self.version < self.wanted else
                        'Atualizado.' if self.version else 'Aguardando a primeira publicação.')
        if self.version < self.wanted:
            self.fetch_delay.start(random.randint(700, 1600))

    def update_host(self, data, version, checksum):
        if version >= self.version:
            self.version, self.checksum = version, checksum
        count = data.get('participants')
        if type(count) is int and 0 <= count <= 2500:
            self.participants = count

    def refresh_host(self):
        if not self.invite or not self.publisher or self.busy or self.status_pending:
            return
        self.status_pending = True

        def finished(reply):
            self.status_pending = False
            if reply.status in (401, 410):
                self.terminal(reply.status)
                return
            if reply.status == 200:
                try:
                    data = reply.object()
                    self.update_host(data, *version_notice(data))
                    self.changed.emit()
                except ValueError:
                    pass

        self.room_request(finished)

    def publish(self):
        if not self.publisher or not self.invite or self.busy:
            return
        try:
            body = snapshot_bytes(self.siege.exportable_preset())
            if len(body) > MAX_BYTES:
                self.report(self.state, ERRORS[413])
                return
            read_snapshot(body)
        except ValueError:
            self.report(self.state, 'A estratégia local não pôde ser validada.')
            return
        version = self.version
        self.busy = True
        self.report('Publicando…')

        def check_catalogue(reply):
            self.busy = False
            try:
                supported = reply.status == 200 and reply.object().get('ring_catalogue') == 1
            except (ValueError, UnicodeError):
                supported = False
            if not supported:
                self.report('Conectado.' if self.socket else 'Reconectando…',
                            'Atualize o Worker para publicar o catálogo de anéis.' if reply.status == 200
                            else self.error(reply))
                return
            self.host_action('PUT', '/snapshot', body, {b'X-Base-Version': str(version).encode('ascii')},
                             'Estratégia publicada.')

        self.request(self.invite.endpoint + '/v1/health', check_catalogue)

    def rotate(self):
        if not self.publisher or not self.invite or self.busy:
            return
        if not self.pending_reader:
            self.pending_reader = secrets.token_hex(32)
        self.host_action('PUT', '/invite', self.pending_reader.encode('ascii'), None, 'Novo convite pronto.')

    def close_room(self):
        if self.publisher and self.invite and not self.busy:
            self.host_action('DELETE', '', None, None, '')

    def host_action(self, method, suffix, body, headers, success):
        self.busy = True
        self.report('Publicando…' if suffix == '/snapshot' else 'Conectando…')

        def completed(reply):
            self.busy = False
            if reply.status in (401, 410) or (method == 'DELETE' and reply.status == 204):
                self.terminal(410 if method == 'DELETE' and reply.status == 204 else reply.status)
                return
            if reply.status in (200, 409):
                try:
                    data = reply.object()
                    self.update_host(data, *version_notice(data))
                except ValueError:
                    self.report('Erro.', self.error(reply))
                    return
                if reply.status == 409:
                    self.report('Conectado.', 'A versão publicada mudou. Confira e clique em Publicar novamente.')
                    return
                if suffix == '/invite':
                    self.invite = Invite(self.invite.endpoint, self.invite.session, self.pending_reader)
                    self.pending_reader = None
                self.report('Conectado.' if self.socket else 'Reconectando…', success)
            else:
                self.report('Erro.', self.error(reply))

        self.room_request(completed, suffix=suffix, method=method, body=body, headers=headers)
