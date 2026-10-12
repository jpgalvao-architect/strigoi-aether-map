# SPDX-License-Identifier: GPL-3.0-only
import numpy as np
import pytest
import cv2

from app.modules.overlay.detector import Calibration, MapDetector, Rect, project
from app.modules.sonar.service import SonarService


@pytest.fixture
def calibrated(tmp_path):
    rng = np.random.default_rng(45)
    image = rng.integers(0, 255, (300, 400, 3), dtype=np.uint8)
    path = tmp_path / "reference.png"
    cv2.imencode(".png", image)[1].tofile(path)
    calibration = Calibration(map_id="vale-lunar", screen_width=400, screen_height=300, viewport=Rect(x=50,y=50,width=300,height=200), anchor=Rect(x=10,y=10,width=30,height=20), fingerprint=Rect(x=100,y=100,width=40,height=40), reference_image=str(path))
    return image, calibration


def test_detector_requires_both_patches(calibrated):
    image, calibration = calibrated
    detector = MapDetector(calibration, .96)
    assert detector.detect(image)[0]
    altered = image.copy()
    altered[100:140,100:140] = 0
    assert not detector.detect(altered)[0]
    assert not detector.detect(np.zeros_like(image))[0]
    assert not detector.detect(image[:200])[0]


def test_uniform_template_rejected(calibrated):
    image, calibration = calibrated
    image[10:30,10:40] = 128
    cv2.imencode(".png",image)[1].tofile(calibration.reference_image)
    with pytest.raises(ValueError, match="uniforme"):
        MapDetector(calibration, .96)


def test_viewport_projection_and_bounds():
    rect = Rect(x=120,y=80,width=800,height=400)
    assert project(0,0,rect) == (120,80)
    assert project(.5,.5,rect) == (520,280)
    assert project(1,1,rect) == (920,480)


def test_sonar_never_starts_capture():
    service = SonarService()
    assert not service.active and service.worker is None
    with pytest.raises(ValueError,match='Selecione'):
        service.start()
