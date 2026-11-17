# SPDX-License-Identifier: GPL-3.0-only
import os
from contextlib import suppress
from multiprocessing import get_context
from time import monotonic
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QImage
from PySide6.QtNetwork import QNetworkRequest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.infrastructure.storage import atomic_json
from app.modules.siege.live_sync import LiveSync, Reply
from app.modules.siege.live_sync_credentials import PairingStore
from app.modules.siege.live_sync_protocol import Invite, digest, endpoint_url, read_snapshot, snapshot_bytes
from app.modules.siege.drawing import visible_drawings
from app.modules.siege.markers import markers_for
from app.modules.siege.models import Coordinate, Ring, RingCatalogue, RingPosition
from app.modules.siege.service import SiegeService
from app.ui.live_sync_panel import LiveSyncPanel, SetupDialog

FAKE_ENDPOINT = 'https://azphelumbra-live-sync.test-account.workers.dev'


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize('address', [
    'http://test.account.workers.dev', 'https://127.0.0.1', 'https://host.workers.dev',
    'https://host.account.workers.dev:443', 'https://host.account.workers.dev.evil.net',
    'https://user@host.account.workers.dev', 'https://host.account.workers.dev/path',
    'https://host.account.workers.dev?q=1', 'https://host.account.workers.dev#data',
])
def test_invite_rejects_unsafe_endpoints(address):
    with pytest.raises(ValueError):
        endpoint_url(address)
    invalid = Invite(address, 'c' * 32, 'b' * 64)
    with pytest.raises(ValueError):
        Invite.parse(invalid.encode())


def test_invite_has_only_reader_credentials():
    invite = Invite(FAKE_ENDPOINT, 'c' * 32, 'b' * 64)
    assert Invite.parse(invite.encode()) == invite


def test_wizard_is_opt_in(app, tmp_path, monkeypatch):
    sync = LiveSync(SiegeService(tmp_path), tmp_path)
    network = []
    monkeypatch.setattr(sync, 'request', lambda *args, **kwargs: network.append(args))
    panel = LiveSyncPanel(sync)
    assert not network and sync.mode == 'off'
    panel.mode.setCurrentIndex(1)
    assert not network and sync.owner is None
    setup = SetupDialog(sync, panel)
    assert setup.key and setup.pages.count() == 2
    setup.reject()
    assert not network
    sync.shutdown()


def test_pairing_storage_is_encrypted(tmp_path):
    if os.name != 'nt':
        pytest.skip('Windows DPAPI only')
    key = 'b' * 64
    store = PairingStore(tmp_path)
    store.save(FAKE_ENDPOINT, key)
    assert store.load() == (FAKE_ENDPOINT, key)
    assert key not in store.path.read_text()
    store.remove()
    assert store.load() is None


def test_shared_preset_keeps_local_state(app, tmp_path):
    siege = SiegeService(tmp_path)
    local = siege.preset
    siege.add_marker('Local', Coordinate(x=0.2, y=0.4))
    before = siege.path.read_bytes()
    atlas = SimpleNamespace(resources=[], points=[])
    assert "Local" in {badge.text for _, _, _, badge in markers_for(siege, atlas)}
    strategy = read_snapshot(snapshot_bytes(local))
    siege.set_session_preset(strategy)
    assert strategy == siege.session_preset
    assert siege.preset != strategy
    assert "Local" not in {badge.text for _, _, _, badge in markers_for(siege, atlas, shared=siege.session_preset)}
    siege.set_session_preset(None)
    assert siege.path.read_bytes() == before


@pytest.mark.parametrize('matches', [True, False])
def test_weak_snapshot_etag_still_requires_matching_checksum(app, tmp_path, monkeypatch, matches):
    siege = SiegeService(tmp_path)
    sync = LiveSync(siege, tmp_path)
    monkeypatch.setattr(sync, 'open_room', lambda: None)
    body = snapshot_bytes(siege.exportable_preset())
    checksum = digest(body) if matches else '0' * 64
    sync.accept_snapshot(Reply(200, body, b'1', f'W/"{checksum}"'.encode('ascii')), initial=True)
    assert sync.version == (1 if matches else 0)
    assert (siege.session_preset is not None) is matches
    sync.shutdown()


class LoopbackSync(LiveSync):
    """Route only this test's public-looking URI to the isolated local Worker."""
    def request(self, url, *args, **kwargs):
        assert url.startswith(FAKE_ENDPOINT)
        return super().request(url.replace(FAKE_ENDPOINT, 'http://127.0.0.1:8976', 1), *args, **kwargs)

    @staticmethod
    def open_socket(socket, endpoint, path, key=None):
        assert endpoint == FAKE_ENDPOINT
        request = QNetworkRequest(QUrl('ws://127.0.0.1:8976' + path))
        if key:
            request.setRawHeader(b'Authorization', b'Bearer ' + key.encode('ascii'))
        socket.open(request)


def wait_for(predicate, seconds=10):
    end = monotonic() + seconds
    while not predicate() and monotonic() < end:
        QTest.qWait(25)
    assert predicate()


@pytest.mark.skipif(os.getenv('AZPHELUMBRA_LIVE_SYNC_LOCAL_TEST') != '1', reason='requires isolated Wrangler on port 8976')
def test_qt_client_and_local_worker(app, tmp_path):
    host = LoopbackSync(SiegeService(tmp_path / 'host'), tmp_path / 'host')
    player = LoopbackSync(SiegeService(tmp_path / 'player'), tmp_path / 'player')
    player.siege.add_marker('Local', Coordinate(x=0.2, y=0.2))
    local_bytes = player.siege.path.read_bytes()
    try:
        host.set_mode('host')
        pairing = []
        host.pairing_done.connect(pairing.append)
        host.pair(FAKE_ENDPOINT, 'b' * 64)
        wait_for(lambda: bool(pairing))
        assert pairing[-1] and host.owner is None
        host.pair(FAKE_ENDPOINT, 'a' * 64)
        wait_for(lambda: len(pairing) == 2)
        assert pairing[-1] == '' and host.owner
        host.create()
        wait_for(lambda: host.state == 'Conectado.')
        player.set_mode('player')
        player.join(host.invite.encode())
        wait_for(lambda: player.state == 'Aguardando a primeira publicação.')
        host.siege.add_marker('Strategy', Coordinate(x=0.5, y=0.5))
        for kind in ('rectangle', 'ellipse', 'arrow'):
            host.siege.add_drawing(kind, Coordinate(x=0.4, y=0.4), Coordinate(x=0.6, y=0.6))
        assert host.dirty and player.version == 0 and player.siege.session_preset is None
        host.publish()
        wait_for(lambda: player.version == 1)
        assert not host.dirty
        assert player.siege.session_preset == host.siege.exportable_preset()
        old = player.siege.session_preset
        player.lost_socket()
        assert player.siege.session_preset is old
        player.reconnect.stop()
        QTest.qWait(1600)
        host.siege.add_marker('New', Coordinate(x=0.65, y=0.65))
        host.publish()
        wait_for(lambda: host.version == 2)
        player.open_room()
        wait_for(lambda: player.version == 2)
        # Leaving reveals the still untouched local file, including all personal pins.
        player.leave()
        assert player.siege.session_preset is None
        assert player.siege.path.read_bytes() == local_bytes
        player.join(host.invite.encode())
        wait_for(lambda: player.version == 2 and player.state == 'Atualizado.')
        host.rotate()
        wait_for(lambda: player.invite is None and not host.busy)
        player.join(host.invite.encode())
        wait_for(lambda: player.version == 2 and player.state == 'Atualizado.')
        host.close_room()
        wait_for(lambda: not player.invite and not host.invite)
        assert player.siege.path.read_bytes() == local_bytes
    finally:
        if host.invite and not host.busy:
            host.close_room()
            wait_for(lambda: not host.invite)
        host.shutdown()
        player.shutdown()


def live_sync_player(pipe, directory):
    app = QApplication([])
    siege = SiegeService(directory)
    client = LoopbackSync(siege, directory)
    siege.add_marker('Personal', Coordinate(x=.2, y=.2))
    siege.edit_preset(layers=siege.preset.layers | {'TransitRings'})
    siege.set_ring_alias('ring-reshanta-293952', 'Nome pessoal')
    original = siege.path.read_bytes()
    client.set_mode('player')
    try:
        while True:
            if not pipe.poll():
                QTest.qWait(25)
                continue
            command, payload = pipe.recv()
            if command == 'stop':
                return
            if command == 'join':
                client.join(payload)
            elif command == 'offline':
                client.lost_socket()
                client.reconnect.stop()
                client.fetch_delay.stop()
            elif command == 'online':
                client.open_room()
            elif command == 'leave':
                client.leave()
            elif command != 'state':
                raise ValueError('Unknown player command')
            preset = siege.session_preset
            atlas = SimpleNamespace(resources=[], points=[])
            markers = markers_for(siege, atlas, shared=preset)
            pipe.send({
                'version': client.version,
                'pins': {badge.text: (x, y) for x, y, _, badge in markers if not badge.ring},
                'rings': {badge.text: (x, y) for x, y, _, badge in markers if badge.ring},
                'shapes': [drawing.kind for drawing, _ in visible_drawings(preset or siege.preset)],
                'preserved': siege.path.read_bytes() == original,
                'connected': client.socket is not None,
            })
    finally:
        client.shutdown()
        pipe.close()
        app.quit()


@pytest.mark.skipif(os.getenv('AZPHELUMBRA_LIVE_SYNC_LOCAL_TEST') != '1', reason='requires isolated Wrangler on port 8976')
def test_live_sync_between_independent_processes(app, tmp_path, monkeypatch):
    from app.services.context import AppContext
    from app.ui import siege_page

    monkeypatch.setattr(siege_page, 'LiveSync', LoopbackSync)
    host_context = AppContext(tmp_path / 'host')
    siege = host_context.siege
    ring_point = Coordinate(x=.67, y=.33)
    flight_ring = Ring(
        ring_id='ring-reshanta-293952', zone_id='fixture', category='transit',
        display_name='Flight Circle', source='Controlled test',
        position=RingPosition(map_position=ring_point, status='verified', source='Controlled test'),
    )
    catalogue = RingCatalogue(map_frame=siege.data.map_frame, rings=[flight_ring])
    atomic_json(tmp_path / 'catalogue.json', catalogue)
    siege.import_catalogue(tmp_path / 'catalogue.json')
    siege.edit_preset(layers=siege.preset.layers | {'TransitRings'})
    image = QImage(32, 32, QImage.Format_RGB32)
    image.fill(QColor('#172435'))
    assert image.save(str(siege.map_path))
    siege._set_map()
    page = siege_page.SiegePage(host_context, lambda _: None, lambda: None, lambda: True)
    page.resize(1120, 760)
    page.show()
    app.processEvents()
    page.section.setCurrentIndex(page.section.findData('live'))
    panel = page.live_panel
    panel.mode.setCurrentIndex(panel.mode.findData('host'))
    view = page.board.view
    view.fit_full()
    host = page.live_sync
    context = get_context('spawn')
    pipe, player_pipe = context.Pipe()
    player_directory = tmp_path / 'player'
    atomic_json(player_directory / 'siege-ring-catalogue.json', catalogue)
    player = context.Process(target=live_sync_player, args=(player_pipe, player_directory))
    player.start()
    player_pipe.close()

    def ask(command, payload=None):
        pipe.send((command, payload))
        wait_for(pipe.poll)
        return pipe.recv()

    def at_version(version):
        state = ask('state')
        assert state['preserved']
        return state if state['version'] == version else None

    def sync_version(version):
        deadline = monotonic() + 12
        while monotonic() < deadline:
            state = at_version(version)
            if state is not None:
                return state
            QTest.qWait(50)
        pytest.fail(f'Player never received revision {version}')

    try:
        host.pair(FAKE_ENDPOINT, 'a' * 64)
        wait_for(lambda: host.owner is not None)
        host.create()
        wait_for(lambda: host.state == 'Conectado.')
        removed = siege.add_marker('Remove me', Coordinate(x=.3, y=.3))
        wait_for(panel.publish_button.isEnabled)
        panel.publish_button.click()
        wait_for(lambda: host.version == 1)
        ask('join', host.invite.encode())
        first = sync_version(1)
        assert 'Remove me' in first['pins'] and 'Personal' not in first['pins']
        assert first['rings'] == {'BF3': (.67, .33)}
        tools = page.editor.quick_toolbar.buttons
        center = view.mapFromScene(view._at(Coordinate(x=.5, y=.5)))
        tools['pin'].click()
        assert tools['pin'].isChecked()
        QTest.mouseClick(view.viewport(), Qt.LeftButton, pos=center)
        pin = page.editor.selected_marker()
        assert pin and pin.name == 'Pin 1'
        siege.edit_marker('objective-p1', position=Coordinate(x=.4, y=.6))
        for shape in ('arrow', 'ellipse', 'rectangle'):
            tools[shape].click()
            assert tools[shape].isChecked()
            start = view.mapFromScene(view._at(Coordinate(x=.35, y=.38)))
            end = view.mapFromScene(view._at(Coordinate(x=.6, y=.57)))
            QTest.mousePress(view.viewport(), Qt.LeftButton, pos=start)
            QTest.mouseMove(view.viewport(), end)
            QTest.mouseRelease(view.viewport(), Qt.LeftButton, pos=end)
            assert tools['select'].isChecked()
        siege.delete_marker(removed.id)
        page.show_editor()
        editor = page.editor
        editor.items.setCurrentIndex(editor.items.findData(f'ring:{flight_ring.ring_id}'))
        editor.ring_name.setText('Entrada Norte')
        QTest.keyClick(editor.ring_name, Qt.Key_Return)
        assert any(item.badge.text == 'Entrada Norte' for item in view.badges if item.badge.ring)
        page.section.setCurrentIndex(page.section.findData('live'))
        QTest.qWait(1600)
        assert ask('state') == first
        assert panel.publish_button.isEnabled()
        panel.publish_button.click()
        second = sync_version(2)
        assert second['pins']['P1'] == (.4, .6)
        assert second['pins']['Pin 1'] == (pin.position.x, pin.position.y)
        assert 'Remove me' not in second['pins']
        assert set(second['shapes']) == {'arrow', 'ellipse', 'rectangle'}
        assert second['rings'] == {'Entrada Norte': (.67, .33)}
        offline = ask('offline')
        assert offline['version'] == 2 and not offline['connected']
        siege.set_ring_alias(flight_ring.ring_id, '')
        for version in (3, 4):
            QTest.qWait(1600)
            siege.add_marker(f'Revision {version}', Coordinate(x=.65, y=.65))
            host.publish()
            wait_for(lambda: host.version == version)
        assert ask('state') == offline
        ask('online')
        reconnected = sync_version(4)
        assert 'Revision 4' in reconnected['pins']
        assert reconnected['rings'] == {'BF3': (.67, .33)}
        local = ask('leave')
        assert 'Personal' in local['pins'] and local['preserved']
        assert local['rings'] == {'Nome pessoal': (.67, .33)}
    finally:
        if host.invite and not host.busy:
            host.close_room()
            wait_for(lambda: not host.invite)
        page.shutdown()
        page.close()
        if player.is_alive():
            with suppress(OSError):
                pipe.send(('stop', None))
            player.join(3)
        if player.is_alive():
            player.terminate()
            player.join()
        pipe.close()
