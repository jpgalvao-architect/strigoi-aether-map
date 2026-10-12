# SPDX-License-Identifier: GPL-3.0-only
"""Session-scoped passive helper lifecycle and bounded JSON event delivery."""
import json
import sqlite3
import sys
from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from app.infrastructure.storage import PACKAGE
from app.modules.combat.engine import CombatEngine
from app.modules.combat.history import CombatHistory

HELPER = PACKAGE / "assets/combat/strigoi-combat.exe"


class CombatService(QObject):
    changed = Signal()
    error = Signal(str)
    history_changed = Signal()
    run_started = Signal()
    MAX_BUFFER = 2 * 1024 * 1024

    def __init__(self, context):
        super().__init__()
        self.context = context
        self.engine = CombatEngine()
        try:
            self.history = CombatHistory(context.directory / "combat.sqlite")
        except (OSError, ValueError, sqlite3.Error):
            self.history = None
            context.messages.append("Histórico de combate indisponível; arquivo preservado")
        self.process = None
        self.buffer = bytearray()
        self.status = "Medição desligada"
        self.last_health = (0, 0, 0)
        self.draining = False
        self.closed = False
        self.protocol_ready = False
        self.auto_instances = False
        self.instance_timers = {}
        self.instance_floor = 0
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.changed)
        self.context.changed.connect(self.changed)
        self.checkpoint = QTimer(self)
        self.checkpoint.setInterval(10000)
        self.checkpoint.timeout.connect(self.save)

    def start(self, name=""):
        if self.process is not None:
            if self.engine.active:
                return False
            self.engine.start_run(name)
            self.auto_instances = True
            self.instance_timers.clear()
            self.instance_floor = 0
            self.changed.emit()
            return True
        if sys.platform != "win32" or not HELPER.is_file():
            self.status = "Coletor de combate indisponível"
            self.changed.emit()
            return False
        self.engine.start_run(name)
        self.auto_instances = True
        self.instance_timers = {}
        self.instance_floor = 0
        self.buffer.clear()
        self.last_health = (0, 0, 0)
        self.protocol_ready = False
        self.status = "Preparando leitura de combate"
        process = QProcess(self)
        self.process = process
        process.setProgram(str(HELPER))
        process.setArguments(["--live"])
        process.readyReadStandardOutput.connect(self.read)
        process.readyReadStandardError.connect(lambda: process.readAllStandardError())
        process.finished.connect(self.finished)
        process.errorOccurred.connect(self.process_error)
        process.start()
        self.timer.start()
        self.checkpoint.start()
        self.changed.emit()
        return True

    def process_error(self, _):
        self.status = "Falha ao abrir coletor de combate"
        self.engine.mark_partial("capture_error")
        if self.process and self.process.state() == QProcess.ProcessState.NotRunning:
            self.finished()
        self.changed.emit()

    def read(self):
        if self.process is None:
            return
        self.buffer.extend(bytes(self.process.readAllStandardOutput()))
        if len(self.buffer) > self.MAX_BUFFER:
            self.engine.mark_partial("ipc_overflow")
            self.status = "Leitura interrompida: fila excedida"
            self.stop()
            return
        if not self.draining:
            self.drain()

    def drain(self):
        self.draining = True
        for _ in range(500):
            end = self.buffer.find(b"\n")
            if end < 0:
                break
            line = bytes(self.buffer[:end])
            del self.buffer[:end + 1]
            try:
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ValueError("Invalid helper message")
                self.accept(message)
            except (ValueError, TypeError, KeyError, OverflowError):
                self.engine.mark_partial("invalid_event")
        if b"\n" in self.buffer:
            QTimer.singleShot(0, self.drain)
        else:
            self.draining = False

    def accept(self, message):
        if message.get("type") == "hello":
            if message.get("protocol") != 1 or message.get("saValidated") is not False:
                raise ValueError("Unsupported collector contract")
            self.protocol_ready = True
        elif message.get("type") == "event":
            if not self.protocol_ready:
                raise ValueError("Collector handshake missing")
            was_active = self.engine.active
            previous_map = self.engine.map_id
            previous_sequence = self.engine.last_sequence
            previous_session = self.engine.capture_session
            self.engine.process(message)
            if was_active and not self.engine.active:
                self.save()
                self.status = "Instância encerrada: mudança de mapa"
            if (self.auto_instances and (message["session"] != previous_session
                    or message["sequence"] > previous_sequence)):
                self.follow_instance(message, previous_map)
        elif message.get("type") == "status":
            code = message.get("code")
            self.status = {"missing_npcap": "Npcap necessário para medir dano",
                "WaitingForGame": "Aguardando conexão do jogo", "Starting": "Preparando leitura de combate",
                "Capturing": "Recebendo eventos · SA experimental", "Error": "Não foi possível ler a conexão do jogo",
                "Stopped": "Medição desligada"}.get(code, "Aguardando eventos de combate")
            if code == "Error":
                self.status = {
                    "multiple_clients": "Mais de um cliente conectado; mantenha apenas um para medir",
                    "adapter_not_found": "Conexão encontrada, mas o adaptador de captura está indisponível",
                    "npcap_load_failed": "Não foi possível carregar o Npcap; verifique a instalação",
                    "capture_failed": "Falha na captura pelo Npcap; reinicie a medição",
                }.get(message.get("reason"), self.status)
            if code in ("Error", "missing_npcap"):
                self.engine.mark_partial("capture_error")
        elif message.get("type") == "health":
            values = tuple(message.get(key, 0) for key in ("dropped", "gaps", "rejected"))
            if any(type(v) is not int or v < 0 for v in values):
                raise ValueError("Invalid capture health")
            if any(v > previous for v, previous in zip(values, self.last_health)):
                self.engine.mark_partial("capture_gap")
            self.last_health = values
            stamp = message.get("time_ms", 0)
            if type(stamp) is int and self.engine.current:
                self.engine.last_time = max(self.engine.last_time, stamp)

    def follow_instance(self, message, previous_map):
        payload, kind = message["payload"], message.get("kind")
        if kind == "ZoneChangedEvent" and not payload.get("IsTeleport"):
            zone = payload["MapId"]
            changed = previous_map is not None and zone != previous_map
            first_load_after_damage = previous_map is None and bool(self.engine.encounters)
            if changed or first_load_after_damage:
                if self.engine.active:
                    self.engine.stop_run("map_changed")
                    self.save()
                self.instance_timers.clear()
                self.instance_floor = 0
            if payload.get("IsDungeon") is True and not self.engine.active:
                self.begin_next_instance()
        elif kind == "InstanceTimerEvent" and payload.get("Kind") in (1, 2):
            zone, start, timer_kind = payload["MapId"], payload["StartMs"], payload["Kind"]
            if self.engine.map_id not in (None, zone) or start < self.instance_floor:
                return  # Delayed timers from a previous map/run cannot reset the current one.
            previous = self.instance_timers.get(timer_kind)
            if previous is not None and start <= previous:
                return  # Reloads, deaths and teleport packets repeat the same server deadline.
            next_entry = (timer_kind == 1 and previous is None
                          and start > self.instance_timers.get(2, start))
            if previous is not None or next_entry:
                self.engine.stop_run("new_instance")
                self.save()
                self.instance_timers.clear()
                self.instance_floor = start
                self.begin_next_instance()
            elif not self.engine.active:
                self.begin_next_instance()
            self.engine.map_id = zone
            self.instance_timers[timer_kind] = start

    def begin_next_instance(self):
        zone = self.engine.map_id
        self.engine.start_run()
        self.engine.map_id = zone
        self.run_started.emit()
        self.changed.emit()

    def summary(self):
        summary = self.engine.snapshot("instance")
        summary["attempts"] = [self.engine.snapshot(encounter_id=e.id) for e in self.engine.encounters]
        return summary

    def save(self):
        if not self.closed and self.history is not None:
            try:
                self.history.save(self.summary())
                self.history_changed.emit()
            except (OSError, ValueError, sqlite3.Error):
                self.error.emit("Não foi possível salvar o histórico de combate")

    def finished(self, *_):
        process = self.process
        if process is None:
            return
        self.read()
        # Consume all already received normalized events before finalizing.
        while b"\n" in self.buffer:
            self.drain()
        self.engine.stop_run("interrupted")
        self.auto_instances = False
        self.save()
        self.process = None
        process.deleteLater()
        self.timer.stop()
        self.checkpoint.stop()
        self.changed.emit()

    def stop(self):
        self.auto_instances = False
        self.instance_timers.clear()
        self.engine.stop_run()
        self.save()
        process = self.process
        if process:
            process.write(b"stop\n")
            if not process.waitForFinished(3000):
                process.kill()
                process.waitForFinished(1000)
        self.timer.stop()
        self.checkpoint.stop()
        self.changed.emit()

    def shutdown(self):
        self.stop()
        self.closed = True
        if self.history is not None:
            self.history.close()
