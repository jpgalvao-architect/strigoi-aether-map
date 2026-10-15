# SPDX-License-Identifier: GPL-3.0-only
"""One bounded passive helper connection shared by independent modules."""
import json
import os
from pathlib import Path
import sys

from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from app.infrastructure.storage import PACKAGE

HELPER = PACKAGE/'assets/combat/strigoi-combat.exe'


class GameFeedService(QObject):
    message = Signal(dict)
    ended = Signal()
    MAX_BUFFER = 2 * 1024 * 1024

    def __init__(self, parent=None):
        super().__init__(parent)
        self.consumers = set()
        self.process = None
        self.buffer = bytearray()
        self.protocol_ready = False
        self.session = None
        self.sequence = 0
        self.health = (0, 0, 0)
        self.stopping = False
        self.draining = False
        self.closed = False
        self.retry = QTimer(self)
        self.retry.setInterval(5000)
        self.retry.timeout.connect(self.ensure_running)

    def acquire(self, consumer):
        if self.closed or consumer not in ('combat','pets'):
            return False
        self.consumers.add(consumer)
        self.retry.start()
        self.ensure_running()
        return True

    def release(self, consumer):
        self.consumers.discard(consumer)
        if not self.consumers:
            self.retry.stop()
            self.stop()

    def ensure_running(self):
        if self.closed or not self.consumers or self.process is not None:
            return
        if sys.platform != 'win32' or not HELPER.is_file():
            self.message.emit({'type':'status','code':'Error','reason':'helper_unavailable'})
            return
        if not (Path(os.environ.get('WINDIR','C:/Windows'))/'System32/Npcap/wpcap.dll').is_file():
            self.message.emit({'type':'status','code':'missing_npcap'})
            return
        self.buffer.clear()
        self.protocol_ready = False
        self.session, self.sequence = None, 0
        self.health = (0, 0, 0)
        self.stopping = False
        process = QProcess(self)
        self.process = process
        process.setProgram(str(HELPER))
        process.setArguments(['--live'])
        process.readyReadStandardOutput.connect(self.read)
        process.readyReadStandardError.connect(lambda: process.readAllStandardError())
        process.errorOccurred.connect(self.process_error)
        process.finished.connect(self.finished)
        process.start()

    def accept(self, message):
        if not isinstance(message, dict):
            raise ValueError('Invalid helper envelope')
        kind = message.get('type')
        if kind == 'hello':
            if message.get('protocol') != 1 or message.get('saValidated') is not False:
                raise ValueError('Unsupported helper contract')
            self.protocol_ready = True
        elif kind == 'event':
            if not self.protocol_ready:
                raise ValueError('Missing helper handshake')
            session, sequence, stamp = (message.get(key) for key in ('session','sequence','time_ms'))
            if not isinstance(session,str) or not session or len(session)>100:
                raise ValueError('Invalid event session')
            if type(sequence) is not int or sequence < 1 or type(stamp) is not int or stamp < 0:
                raise ValueError('Invalid event counters')
            if not isinstance(message.get('payload'),dict) or not isinstance(message.get('kind'),str):
                raise ValueError('Invalid event content')
            if self.session is not None and session != self.session:
                raise ValueError('Unexpected session inside helper generation')
            if sequence <= self.sequence:
                return False
            gap = sequence != self.sequence+1
            self.session, self.sequence = session, sequence
            if gap:
                self.message.emit({'type':'feed_quality','reason':'event_gap'})
        elif kind == 'health':
            values = tuple(message.get(key, 0) for key in ('dropped','gaps','pets_rejected'))
            if any(type(v) is not int or v < 0 for v in values):
                raise ValueError('Invalid capture health')
            if any(v > old for v, old in zip(values[:2],self.health[:2])):
                self.message.emit({'type':'feed_quality','reason':'capture_gap'})
            if values[2] > self.health[2]:
                self.message.emit({'type':'feed_quality','reason':'pet_record_rejected'})
            self.health = values
        elif kind != 'status':
            raise ValueError('Unknown helper message')
        self.message.emit(message)
        return True

    def read(self):
        if self.process is None:
            return
        self.buffer.extend(bytes(self.process.readAllStandardOutput()))
        if len(self.buffer)>self.MAX_BUFFER:
            self.buffer.clear()
            self.message.emit({'type':'feed_quality','reason':'ipc_overflow'})
            self.stop()
            return
        if not self.draining:
            self.drain()

    def drain(self):
        self.draining = True
        for _ in range(500):
            end = self.buffer.find(b'\n')
            if end < 0:
                break
            line = bytes(self.buffer[:end]); del self.buffer[:end+1]
            try:
                self.accept(json.loads(line))
            except (ValueError, TypeError, KeyError, OverflowError):
                self.message.emit({'type':'feed_quality','reason':'invalid_event'})
        if b'\n' in self.buffer:
            QTimer.singleShot(0,self.drain)
        else:
            self.draining = False

    def process_error(self, _):
        self.message.emit({'type':'status','code':'Error','reason':'capture_failed'})
        if self.process and self.process.state()==QProcess.ProcessState.NotRunning:
            self.finished()

    def finished(self, *_):
        process = self.process
        if process is None:
            return
        self.read()
        while b'\n' in self.buffer:
            self.drain()
        if self.buffer:
            self.buffer.clear()
            self.message.emit({'type':'feed_quality','reason':'incomplete_event'})
        self.process = None
        self.protocol_ready = False
        process.deleteLater()
        self.ended.emit()

    def stop(self):
        if self.stopping:
            return
        process = self.process
        if process:
            self.stopping = True
            process.write(b'stop\n')
            if not process.waitForFinished(3000):
                process.kill();process.waitForFinished(1000)
            self.stopping = False

    def shutdown(self):
        self.closed = True
        self.consumers.clear()
        self.retry.stop()
        self.stop()
