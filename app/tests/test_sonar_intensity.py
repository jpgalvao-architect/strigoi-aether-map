# SPDX-License-Identifier: GPL-3.0-only
"""Controlled reference/noise tests, not a claim of live distance or separation accuracy."""
import time
import threading
import numpy as np
import pytest
from PySide6.QtTest import QSignalSpy
from app.infrastructure.storage import PACKAGE
from app.modules.sonar.detector import CubeDetector
from app.modules.sonar.service import AudioFrame, SonarLevel, SonarWorker
from app.modules.sonar.service import SonarService
from app.ui.sonar_intensity import IntensityTrace
from app.ui.sonar_page import SonarAlert
from app.services.context import AppContext


@pytest.fixture(scope='module')
def reference():
    with np.load(PACKAGE/'assets/sonar/cube-reference.npz',allow_pickle=False) as data:
        return data['pcm'].copy()


def test_reference_level_follows_amplitude_not_normalized_match_score(reference):
    detector=CubeDetector(reference)
    audio=reference[:int(detector.rate*detector.window_seconds)]
    quiet=detector.match(audio*.01)
    loud=detector.match(audio*.02)
    assert quiet is not None and loud is not None
    assert loud.level_db-quiet.level_db==pytest.approx(20*np.log10(2),abs=.05)
    assert quiet.level_db==pytest.approx(20*np.log10(detector.reference_rms*.01),abs=.1)
    assert loud.score==pytest.approx(quiet.score,rel=.001)


def test_intensity_is_reference_projection_not_total_mixture_loudness(reference):
    detector=CubeDetector(reference)
    audio=reference[:int(detector.rate*detector.window_seconds)].astype(float)
    noise=np.random.default_rng(727).normal(0,.03,len(audio))
    quiet=detector.match(noise+audio*.02)
    louder_noise=detector.match(noise*2+audio*.02)
    assert quiet is not None and louder_noise is not None
    assert abs(quiet.level_db-louder_noise.level_db)<1.5


def test_steady_confirmed_level_updates_during_alert_cooldown_then_silence_clears(reference):
    detector=CubeDetector(reference)
    levels=[];alerts=[]
    # Reference aligned at time zero; two successive windows confirm the same sound.
    stereo=np.column_stack([reference*.02,-reference*.02])
    for i in range(0,len(stereo),4800):
        before=detector.analysis_count
        match=detector.push(stereo[i:i+4800])
        if match:alerts.append(match)
        if detector.analysis_count!=before and detector.last_level_db is not None:
            levels.append(detector.last_level_db)
    assert len(alerts)==1 and len(levels)>=3
    for _ in range(35):detector.push(np.zeros((4800,2),np.float32))
    assert detector.last_level_db is None
    detector.reset()
    assert detector.last_level_db is None and detector.analysis_count==0


def test_loud_unrelated_noise_never_has_a_confirmed_level(reference):
    detector=CubeDetector(reference)
    noise=np.random.default_rng(1727).normal(0,.15,(48000*4,2)).astype(np.float32)
    for i in range(0,len(noise),4800):
        assert detector.push(noise[i:i+4800]) is None
        assert detector.last_level_db is None


def test_worker_emits_levels_independently_of_notification_cooldown(qapp):
    class Detector:
        analysis_count=0;last_level_db=None;previous=None
        def reset(self):self.analysis_count=0;self.last_level_db=None
        def push(self, pcm):
            self.analysis_count+=1
            self.last_level_db=(-65.,-40.,None)[self.analysis_count-1]
            return None
    class Source:
        stopped=False
        def frames(self):
            for _ in range(3):
                yield AudioFrame(np.zeros((480,2),'<f4').tobytes(),48000,2,time.monotonic())
        def stop(self):self.stopped=True
    source=Source();worker=SonarWorker(source,Detector())
    levels=QSignalSpy(worker.level_updated);alerts=QSignalSpy(worker.detected)
    worker.run()
    assert [levels.at(i)[0].level_db for i in range(levels.count())]==[-65.,-40.,None]
    assert alerts.count()==0 and source.stopped


def test_trace_rejects_stale_nonfinite_levels_and_bounds_history():
    trace=IntensityTrace();trace.set_level(-60.,10.)
    assert trace.fraction(10.1)==pytest.approx(1/3)
    assert trace.fraction(12.)==0 and not trace.valid(12.)
    trace.set_level(float('nan'),13.)
    assert not trace.valid(13.)
    for i in range(200):trace.set_level(-40.,14+i*.35)
    assert len(trace.history)==96 and trace.fraction(14+199*.35)==pytest.approx(2/3)


def test_dismissed_alert_stays_hidden_when_intensity_changes(qapp,tmp_path):
    alert=SonarAlert(AppContext(tmp_path))
    try:
        alert.present();alert.update_level(SonarLevel(-40.,time.monotonic()))
        assert alert.isVisible() and alert.intensity.trace.level==-40
        alert.hide();alert.update_level(SonarLevel(-30.,time.monotonic()))
        assert not alert.isVisible()
        alert.update_level(SonarLevel(None,time.monotonic(),True))
        assert alert.intensity.trace.level is None and alert.intensity.display==0
        alert.present(test=True)
        assert not alert.intensity.isVisible()
    finally:alert.timer.stop();alert.close()


def test_stopping_resets_graph_and_rejects_queued_worker_levels(qapp,tmp_path):
    class Detector:
        analysis_count=0;last_level_db=None
        def push(self, pcm):
            self.analysis_count+=1;self.last_level_db=-40.
            return None
    class Source:
        def __init__(self):self.stopped=threading.Event()
        def frames(self):
            while not self.stopped.wait(.005):
                yield AudioFrame(np.zeros((480,2),'<f4').tobytes(),48000,2,time.monotonic())
        def stop(self):self.stopped.set()
    service=SonarService(AppContext(tmp_path));spy=QSignalSpy(service.level_updated)
    source=Source()
    try:
        service.start(source=source,detector=Detector())
        deadline=time.monotonic()+1.
        while service.level is None and time.monotonic()<deadline:
            time.sleep(.01);qapp.processEvents()
        assert service.level==-40.
        service.stop();qapp.processEvents()
        assert service.level is None and spy.at(spy.count()-1)[0].reset
        assert source.stopped.is_set()
    finally:service.stop()
