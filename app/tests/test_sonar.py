# SPDX-License-Identifier: GPL-3.0-only
import threading
import time
import numpy as np
import pytest
from PySide6.QtTest import QSignalSpy
from app.infrastructure.storage import PACKAGE,atomic_json
from app.core.models import Preferences
from app.modules.sonar.detector import CubeDetector
from app.modules.sonar.service import SonarService,SonarWorker,AudioFrame
from app.services.context import AppContext


@pytest.fixture(scope='module')
def reference():
    with np.load(PACKAGE/'assets/sonar/cube-reference.npz',allow_pickle=False) as data:
        assert int(data['sample_rate'])==48000
        return data['pcm'].copy()


def analyze(reference,audio,sensitivity='balanced',chunk=4800):
    detector=CubeDetector(reference,sensitivity)
    hits=[]
    for i in range(0,len(audio),chunk):
        match=detector.push(audio[i:i+chunk])
        if match:hits.append((detector.samples_seen/detector.rate,match))
    return detector,hits


@pytest.mark.parametrize('snr,chunk,channel',[(-20,4800,'opposite'),(-30,1024,'opposite'),(-20,4800,'right_only')])
def test_quiet_reference_in_noise_and_opposite_phase_channels(reference,snr,chunk,channel):
    rng=np.random.default_rng(7838+chunk)
    noise=rng.normal(0,.03,48000*9).astype(np.float32)
    gain=.03/np.sqrt(np.mean(reference**2))*10**(snr/20)
    audio=noise.copy();audio[48000:48000+len(reference)]+=reference*gain
    stereo=np.column_stack([audio,-audio]) if channel=='opposite' else np.column_stack([np.zeros_like(audio),-audio])
    detector,hits=analyze(reference,stereo,chunk=chunk)
    assert len(hits)==1 # consensus, then cooldown, despite opposite channel phases
    assert 3.25<hits[0][0]<7.5 and hits[0][1].templates>=2
    assert len(detector.buffer)<=round(detector.rate*detector.window_seconds)


@pytest.mark.parametrize('kind',['silence','noise','tones','reverse'])
def test_controls_do_not_emit_alerts(reference,kind):
    t=np.arange(48000*9)/48000
    if kind=='silence':audio=np.zeros(len(t),dtype=np.float32)
    elif kind=='noise':audio=np.random.default_rng(847).normal(0,.03,len(t)).astype(np.float32)
    elif kind=='tones':audio=(.03*np.sin(2*np.pi*1680*t)+.03*np.sin(2*np.pi*3530*t)).astype(np.float32)
    else:audio=np.resize(reference[::-1],len(t))
    _,hits=analyze(reference,np.column_stack([audio,audio]),sensitivity='sensitive')
    assert hits==[]


def test_capture_never_resumes_from_saved_preference(qapp,tmp_path):
    atomic_json(tmp_path/'preferences.json',Preferences(sonar_enabled=True,sonar_process_name='AION2.exe'))
    context=AppContext(tmp_path)
    service=SonarService(context)
    assert not context.prefs.sonar_enabled
    assert service.worker is None and not service.active
    assert context.prefs.sonar_process_name=='AION2.exe'


def test_stop_releases_worker_and_prevents_late_detections(qapp,tmp_path,reference):
    class Source:
        def __init__(self):self.stopped=threading.Event()
        def frames(self):
            while not self.stopped.wait(.01):
                yield AudioFrame(np.zeros((480,2),'<f4').tobytes(),48000,2,time.monotonic())
        def stop(self):self.stopped.set()
    source=Source();context=AppContext(tmp_path);service=SonarService(context)
    spy=QSignalSpy(service.detected)
    service.start(source=source,detector=CubeDetector(reference))
    qapp.processEvents();service.stop();qapp.processEvents()
    assert source.stopped.is_set() and service.worker is None
    assert not service.active and not context.prefs.sonar_enabled and spy.count()==0


def test_bad_pcm_is_rejected_and_reset_discards_history(reference):
    detector=CubeDetector(reference)
    with pytest.raises(ValueError):detector.push(np.array([[float('nan'),0]],np.float32))
    detector.previous=(0.,1.);detector.samples_seen=2000
    detector.reset()
    assert detector.previous is None and detector.samples_seen==0 and len(detector.buffer)==0


def test_empty_pipe_heartbeat_does_not_erase_temporal_confirmation(qapp):
    from app.modules.sonar.detector import Match
    class Detector:
        previous=None
        def reset(self):self.previous=None
        def push(self,pcm):
            confirmed=self.previous is not None
            self.previous=(0.,1.)
            return Match(12.,0.,2) if confirmed else None
    class Source:
        stopped=False
        def frames(self):
            for data in [np.zeros((480,2),'<f4').tobytes(),b'',np.zeros((480,2),'<f4').tobytes()]:
                yield AudioFrame(data,48000,2,time.monotonic())
        def stop(self):self.stopped=True
    source=Source();worker=SonarWorker(source,Detector());spy=QSignalSpy(worker.detected)
    worker.run()
    assert spy.count()==1 and source.stopped


def test_discontinuity_does_not_bypass_alert_cooldown(qapp):
    from app.modules.sonar.detector import Match
    class Detector:
        def reset(self):pass
        def push(self,pcm):return Match(12.,0.,2)
    class Source:
        def frames(self):
            for _ in range(3):
                yield AudioFrame(np.zeros((480,2),'<f4').tobytes(),48000,2,time.monotonic(),True)
        def stop(self):pass
    worker=SonarWorker(Source(),Detector());spy=QSignalSpy(worker.detected)
    worker.run()
    assert spy.count()==1
