# SPDX-License-Identifier: GPL-3.0-only
"""Explicit, session-scoped audio capture with an independent detector worker."""
from dataclasses import dataclass
import logging
import os
import time
from typing import Iterable, Protocol
from PySide6.QtCore import QObject, QThread, Signal
from app.infrastructure.storage import PACKAGE


@dataclass(frozen=True)
class AudioFrame:
    pcm: bytes
    sample_rate: int
    channels: int
    timestamp: float
    discontinuity: bool = False


@dataclass(frozen=True)
class SonarDetection:
    confidence: float
    timestamp: float
    label: str = "possible_cube"


@dataclass(frozen=True)
class SonarLevel:
    level_db: float | None
    timestamp: float
    reset: bool = False


class LoopbackSource(Protocol):
    def frames(self) -> Iterable[AudioFrame]: ...
    def stop(self) -> None: ...


class CubeSoundDetector(Protocol):
    def analyze(self, frame: AudioFrame) -> SonarDetection | None: ...


class SonarWorker(QThread):
    detected = Signal(object)
    level_updated = Signal(object)
    status_changed = Signal(str)
    failed = Signal(str)

    def __init__(self, source, detector):
        super().__init__()
        self.source=source
        self.detector=detector

    def run(self):
        import numpy as np
        last_status=0.
        last_pcm=time.monotonic()
        last_notice=-float('inf')
        try:
            for frame in self.source.frames():
                if self.isInterruptionRequested():
                    break
                if frame.sample_rate!=48000 or frame.channels!=2:
                    raise ValueError('Formato de áudio incompatível')
                if frame.discontinuity:
                    self.detector.reset()
                    self.level_updated.emit(SonarLevel(None,frame.timestamp,True))
                pcm=np.frombuffer(frame.pcm,dtype='<f4').reshape(-1,2)
                if len(pcm):
                    last_pcm=time.monotonic()
                if time.monotonic()-last_status>=1.:
                    audible=len(pcm)>0 and float(np.mean(pcm*pcm))>1e-14
                    self.status_changed.emit('Ouvindo o jogo' if audible else 'Ouvindo · aguardando áudio do jogo')
                    last_status=time.monotonic()
                before=getattr(self.detector,'analysis_count',0)
                match=self.detector.push(pcm) if len(pcm) else None
                if getattr(self.detector,'analysis_count',0)!=before:
                    self.level_updated.emit(SonarLevel(self.detector.last_level_db,frame.timestamp))
                # An empty heartbeat means no new packet, not missing evidence.
                if not len(pcm) and time.monotonic()-last_pcm>1.:
                    self.detector.previous=None
                    self.detector.last_level_db=None
                    self.level_updated.emit(SonarLevel(None,frame.timestamp))
                if match is not None and time.monotonic()-last_notice>=15.:
                    last_notice=time.monotonic()
                    self.detected.emit(SonarDetection(match.score,frame.timestamp))
        except Exception as exc:
            if not self.isInterruptionRequested():
                logging.getLogger(__name__).exception('Captura do sonar encerrada')
                self.failed.emit(str(exc))
        finally:
            self.source.stop()


class SonarService(QObject):
    detected = Signal(object)
    level_updated = Signal(object)
    status_changed = Signal(str)
    active_changed = Signal(bool)

    def __init__(self, context=None):
        super().__init__()
        self.context=context
        self.worker=None
        self.active=False
        self.status='Desligado'
        self.level=None
        from app.modules.sonar.capture import HELPER
        self.available=os.name=='nt' and HELPER.is_file()

    def set_status(self, text):
        self.status=text
        self.status_changed.emit(text)

    def start(self, pid=None, *, source=None, detector=None):
        if self.worker is not None:
            return
        if source is None:
            if not self.available or not isinstance(pid,int) or pid<=0:
                raise ValueError('Selecione o aplicativo do jogo para iniciar o sonar')
            from app.modules.sonar.capture import ProcessLoopback
            source=ProcessLoopback(pid)
        if detector is None:
            import numpy as np
            from app.modules.sonar.detector import CubeDetector
            with np.load(PACKAGE/'assets/sonar/cube-reference.npz',allow_pickle=False) as reference:
                if int(reference['sample_rate'])!=48000:
                    raise ValueError('Referência de áudio incompatível')
                detector=CubeDetector(reference['pcm'],self.context.prefs.sonar_sensitivity if self.context else 'balanced')
        self.worker=SonarWorker(source,detector)
        self.worker.detected.connect(self.on_detection)
        self.worker.level_updated.connect(self.on_level)
        self.worker.status_changed.connect(self.on_status)
        self.worker.failed.connect(self.on_failure)
        self.worker.finished.connect(self.on_finished)
        self.active=True
        if self.context:
            self.context.prefs.sonar_enabled=True
            self.context.save()
        self.set_status('Preparando áudio do jogo…')
        self.active_changed.emit(True)
        self.worker.start()

    def on_detection(self, detection):
        if self.active and self.sender() is self.worker:
            self.detected.emit(detection)

    def on_level(self, reading):
        if self.active and self.sender() is self.worker:
            self.level=reading.level_db
            self.level_updated.emit(reading)

    def clear_level(self):
        self.level=None
        self.level_updated.emit(SonarLevel(None,time.monotonic(),True))

    def on_status(self, text):
        if self.active and self.sender() is self.worker:
            self.set_status(text)

    def on_failure(self, text):
        if self.sender() is self.worker:
            self.set_status('Áudio interrompido. Verifique se o jogo está aberto e inicie novamente.')

    def on_finished(self):
        if self.sender() is not self.worker:
            return
        worker=self.worker
        self.worker=None
        self.active=False
        self.clear_level()
        if self.context:
            self.context.prefs.sonar_enabled=False
            self.context.save()
        self.active_changed.emit(False)
        if not self.status.startswith('Áudio interrompido'):
            self.set_status('Desligado')
        worker.deleteLater()

    def stop(self):
        self.active=False
        self.clear_level()
        worker=self.worker
        if worker:
            worker.requestInterruption()
            worker.source.stop()
            worker.wait()
            self.worker=None
            worker.deleteLater()
        if self.context:
            self.context.prefs.sonar_enabled=False
            self.context.save()
        self.active_changed.emit(False)
        self.set_status('Desligado')
