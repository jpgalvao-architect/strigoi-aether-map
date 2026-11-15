# SPDX-License-Identifier: GPL-3.0-only
"""Controlled reference/noise tests, not a claim of live distance or separation accuracy."""
import numpy as np
import pytest
from app.infrastructure.storage import PACKAGE
from app.modules.sonar.detector import CubeDetector


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
