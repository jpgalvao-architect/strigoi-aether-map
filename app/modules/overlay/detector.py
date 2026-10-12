# SPDX-License-Identifier: GPL-3.0-only
"""Conservative fixed-viewport detector; no process access or input observation."""
from pathlib import Path

from pydantic import Field, model_validator

from app.core.models import Model


class Rect(Model):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(ge=12)
    height: int = Field(ge=12)


class Calibration(Model):
    map_id: str
    screen_width: int = Field(ge=100)
    screen_height: int = Field(ge=100)
    viewport: Rect
    anchor: Rect
    fingerprint: Rect
    reference_image: str

    @model_validator(mode="after")
    def within_screen(self):
        for rect in [self.viewport, self.anchor, self.fingerprint]:
            if rect.x + rect.width > self.screen_width or rect.y + rect.height > self.screen_height:
                raise ValueError("Seleção fora da imagem")
        a, b = self.anchor, self.fingerprint
        viewport = self.viewport
        if b.x < viewport.x or b.y < viewport.y or b.x+b.width > viewport.x+viewport.width or b.y+b.height > viewport.y+viewport.height:
            raise ValueError("A referência de terreno deve ficar dentro do viewport")
        if not (a.x+a.width <= b.x or b.x+b.width <= a.x or a.y+a.height <= b.y or b.y+b.height <= a.y):
            raise ValueError("As duas referências não podem se sobrepor")
        return self


def project(x: float, y: float, viewport: Rect) -> tuple[float, float]:
    return viewport.x + x*viewport.width, viewport.y + y*viewport.height


class MapDetector:
    def __init__(self, calibration: Calibration, threshold: float):
        import cv2
        import numpy as np
        self.calibration = calibration
        self.threshold = threshold
        path = Path(calibration.reference_image)
        image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None or image.shape[:2] != (calibration.screen_height, calibration.screen_width):
            raise ValueError("Imagem de referência ausente ou incompatível")
        self.templates = []
        for rect in [calibration.anchor, calibration.fingerprint]:
            patch = image[rect.y:rect.y+rect.height, rect.x:rect.x+rect.width]
            gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
            if gray.std() < 12:
                raise ValueError("Referência visual uniforme demais. Selecione detalhes/texto do mapa.")
            self.templates.append(gray)

    def detect(self, image) -> tuple[bool, float]:
        import cv2
        if image.shape[:2] != (self.calibration.screen_height, self.calibration.screen_width):
            return False, 0.0
        scores = []
        for rect, template in zip([self.calibration.anchor, self.calibration.fingerprint], self.templates):
            roi = image[rect.y:rect.y+rect.height, rect.x:rect.x+rect.width, :3]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            score = float(cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)[0, 0])
            # An absolute difference gate also rejects inverted/brightness-shifted lookalikes.
            difference = float(cv2.absdiff(gray, template).mean())
            scores.append(score if difference <= 22 else 0.0)
        confidence = min(scores)
        return confidence >= self.threshold, confidence
