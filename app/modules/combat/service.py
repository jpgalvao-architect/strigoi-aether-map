# SPDX-License-Identifier: GPL-3.0-only
"""Session-scoped passive helper lifecycle and bounded JSON event delivery."""
import json
import sqlite3
import sys
import os
from pathlib import Path
from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from app.infrastructure.storage import PACKAGE
from app.modules.combat.engine import CombatEngine
from app.modules.combat.arenas import arena_mode, timer_matches_map
from app.modules.combat.history import CombatHistory
from app.services.game_feed import GameFeedService

HELPER = PACKAGE / "assets/combat/strigoi-combat.exe"


class CombatService(QObject):
    changed = Signal()
    error = Signal(str)
    history_changed = Signal()
    run_started = Signal()
    MAX_BUFFER = 2 * 1024 * 1024

    def __init__(self, context, feed=None):
        super().__init__()
        self.context = context
        self.engine = CombatEngine()
        try:
            self.history = CombatHistory(context.directory / "combat.sqlite")
        except (OSError, ValueError, sqlite3.Error):
            self.history = None
            context.messages.append("Histórico de combate indisponível; arquivo preservado")
        self.feed = feed or GameFeedService()
        self.feed.message.connect(self.from_feed)
        self.feed.ended.connect(self.finished)
        self.status = "Medição desligada"
        self.last_health = (0, 0, 0)
        self.draining = False
        self.closed = False
        self.protocol_ready = False
        self.auto_instances = False
        self.instance_timers = {}
        self.instance_floor = 0
        self.runtime = False
        self.in_instance = False
        self.watchdog = QTimer(self)
        self.watchdog.setInterval(5000)
        self.watchdog.timeout.connect(self.ensure_automatic)
        context.changed.connect(self.ensure_automatic)
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.changed)
        self.context.changed.connect(self.changed)
        self.checkpoint = QTimer(self)
        self.checkpoint.setInterval(10000)
        self.checkpoint.timeout.connect(self.save)

    @property
    def process(self):
        return self.feed.process

    @process.setter
    def process(self, value):
        self.feed.process = value

    def from_feed(self, message):
        if 'combat' not in self.feed.consumers:
            return
        if message.get('type') == 'feed_quality':
            if message.get('reason') not in ('pet_record_rejected','routine_record_rejected'):
                self.engine.mark_partial(message.get('reason','capture_gap'))
            return
        try:
            self.accept(message)
        except (ValueError, TypeError, KeyError, OverflowError):
            self.engine.mark_partial('invalid_event')

    def enable_automatic(self):
        self.runtime = True
        self.watchdog.start()
        self.ensure_automatic()

    def ensure_automatic(self):
        if self.closed or not self.runtime:
            return
        if not self.context.prefs.combat.auto_capture:
            if 'combat' in self.feed.consumers or (self.process is not None and not self.feed.consumers):
                self.stop()
            self.status = "Medição automática desativada"
        elif self.process is None or (self.feed.consumers and 'combat' not in self.feed.consumers):
            if sys.platform != "win32" or not HELPER.is_file():
                self.status = "Coletor de combate indisponível"
            elif not (Path(os.environ.get("WINDIR", "C:/Windows")) / "System32/Npcap/wpcap.dll").is_file():
                self.status = "Npcap necessário para medir dano"
            else:
                self.start()
        self.changed.emit()

    def start(self, name=""):
        if self.process is not None and self.engine.active and 'combat' in self.feed.consumers:
            return False
        if sys.platform != "win32" or not HELPER.is_file():
            self.status = "Coletor de combate indisponível"
            self.changed.emit()
            return False
        self.in_instance = False
        self.engine.start_run(name)
        self.auto_instances = True
        self.instance_timers = {}
        self.instance_floor = 0
        self.last_health = (0, 0, 0)
        self.protocol_ready = self.feed.protocol_ready
        self.status = "Preparando leitura de combate"
        self.feed.acquire('combat')
        self.timer.start()
        self.checkpoint.start()
        self.changed.emit()
        return True

    def process_error(self, _):
        self.feed.process_error(_)

    def read(self):
        self.feed.read()

    def drain(self):
        self.feed.drain()

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
            if (code in ("Stopped", "Error", "missing_npcap")
                    or message.get("reset_zone") is True
                    or (code == "WaitingForGame" and "reset_zone" not in message)):
                self.in_instance = False
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
        was_inside = self.in_instance
        payload, kind = message["payload"], message.get("kind")
        recognized = payload.get("IsDungeon") is True or arena_mode(payload.get("MapId")) is not None
        if kind == "ZoneChangedEvent" and payload.get("IsTeleport") and recognized:
            self.in_instance = True  # A fresh reload can restore context after reconnect.
        if kind == "ZoneChangedEvent" and not payload.get("IsTeleport"):
            zone = payload["MapId"]
            changed = previous_map is not None and zone != previous_map
            first_load_after_damage = previous_map is None and bool(self.engine.encounters)
            if changed or previous_map is None:
                self.in_instance = recognized
            elif recognized:
                self.in_instance = True
            if changed or first_load_after_damage:
                if self.engine.active:
                    self.engine.stop_run("map_changed")
                    self.save()
                self.instance_timers.clear()
                self.instance_floor = 0
            if recognized and (not self.engine.active or
                    self.engine.pvp != (arena_mode(zone) is not None)):
                if self.engine.active:
                    self.engine.stop_run("mode_changed")
                    self.save()
                self.begin_next_instance()
        elif kind == "InstanceTimerEvent" and payload.get("Kind") in (1, 2):
            zone, start, timer_kind = payload["MapId"], payload["StartMs"], payload["Kind"]
            current_map = self.engine.map_id
            if (current_map is not None and not timer_matches_map(current_map, zone)) or start < self.instance_floor:
                return  # Delayed timers from a previous map/run cannot reset the current one.
            previous = self.instance_timers.get(timer_kind)
            if previous is not None and start <= previous:
                if start == previous and not self.in_instance:
                    self.in_instance = True
                    self.changed.emit()  # Current timer restores context, never restarts statistics.
                return  # Reloads, deaths and teleport packets repeat the same server deadline.
            self.in_instance = True  # Valid kind 1/2 denotes an instance, not a boss timer.
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
            self.engine.map_id = current_map if current_map is not None else zone
            self.instance_timers[timer_kind] = start
        if self.in_instance != was_inside:
            self.changed.emit()

    def begin_next_instance(self):
        zone = self.engine.map_id
        mode = arena_mode(zone)
        if mode is not None:
            # A world/dungeon party is not evidence of the next arena's team.
            self.engine.roster = set()
            self.engine.roster_jobs = {}
            self.engine.roster_complete = False
        self.engine.start_run(pvp=mode is not None, team_pvp=mode == "5v5")
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
        if not self.engine.active and not self.auto_instances:
            return
        self.engine.stop_run("interrupted")
        self.in_instance = False
        self.auto_instances = False
        self.save()
        self.timer.stop()
        self.checkpoint.stop()
        self.changed.emit()

    def stop(self):
        self.in_instance = False
        self.auto_instances = False
        self.instance_timers.clear()
        self.engine.stop_run()
        self.save()
        self.feed.release('combat')
        self.timer.stop()
        self.checkpoint.stop()
        self.changed.emit()

    def shutdown(self):
        self.runtime = False
        self.watchdog.stop()
        self.stop()
        self.closed = True
        if self.history is not None:
            self.history.close()
