# SPDX-License-Identifier: GPL-3.0-only
"""Selected-area capture and map registration, both owned by one worker."""
import logging
import threading
import time

from PySide6.QtCore import QThread, Signal

from app.modules.overlay.selection import find_monitor, physical_region
from app.modules.overlay.stencil import apply_stencil


class LiveMapWorker(QThread):
    observed = Signal(object, object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, area, map_image, minimum_matches, capture_hz=60):
        super().__init__()
        self.area = area.model_copy(deep=True)
        self.map_image = map_image
        self.minimum_matches = minimum_matches
        self.capture_hz = min(capture_hz,60 if area.view_kind=="minimap" else 30)
        self.full_area = self.area.model_copy(update=dict(x=0,y=0,width=area.screen_width,height=area.screen_height,view_kind="large")) if area.view_kind=="minimap" else None
        self.stop_event = threading.Event()
        self.paint_exclusion = None
        self._mask_lock = threading.Lock()

    def set_exclusion(self, registration, points, view_kind=None):
        # A recent marker stencil is masked out of the next frame, preventing
        # the overlay's own icons from supplying visual matching evidence.
        with self._mask_lock:
            self.paint_exclusion = (registration, list(points), view_kind or self.area.view_kind) if registration else None

    def run(self):
        try:
            import mss
            import numpy as np
            from app.modules.overlay.tracking import MapRegistration
            from app.modules.overlay.flow import FastMapTracker
            self.progress.emit("Preparando reconhecimento do terreno…")
            reference = MapRegistration(self.map_image, should_stop=self.stop_event.is_set,minimap=self.area.view_kind=="minimap")
            tracker = FastMapTracker(reference)
            automatic=None
            if self.full_area:
                from app.modules.overlay.automatic import AutomaticMapTracker
                self.progress.emit("Preparando troca automática para o mapa grande…")
                large=FastMapTracker(MapRegistration(self.map_image,should_stop=self.stop_event.is_set))
                automatic=AutomaticMapTracker(tracker,large,self.area,self.full_area)
            if self.stop_event.is_set():
                return
            self.progress.emit("Procurando o mapa na área selecionada…")
            with mss.MSS() as capture:
                monitor = find_monitor(self.area, capture.monitors[1:])
                def read_frame(area):
                    monitor=find_monitor(area,capture.monitors[1:])
                    roi=physical_region(area,monitor)
                    frame = np.asarray(capture.grab(roi))[:, :, :3].copy()
                    feature_mask=np.full(frame.shape[:2],255,dtype=np.uint8)
                    with self._mask_lock:
                        stencil = self.paint_exclusion
                    if stencil and stencil[2]==area.view_kind:
                        registration, points, _ = stencil
                        apply_stencil(frame, feature_mask, registration, points)
                    return frame,feature_mask
                while not self.stop_event.is_set():
                    started = time.perf_counter()
                    if automatic:
                        registration,method,area=automatic.observe(read_frame,started,minimum=self.minimum_matches)
                    else:
                        area=self.area
                        frame,feature_mask=read_frame(area)
                        registration,method=tracker.observe(frame,started,minimum=self.minimum_matches,feature_mask=feature_mask)
                    roi=physical_region(area,monitor)
                    self.observed.emit(registration, dict(roi=roi,area=area,screen_name=area.screen_name,method=method,observed_at=time.perf_counter()))
                    rate=min(self.capture_hz,30) if area.view_kind=="large" else self.capture_hz
                    period=1/rate if registration else .2
                    self.stop_event.wait(max(.001, period-(time.perf_counter()-started)))
        except InterruptedError:
            pass
        except Exception as exc:
            logging.getLogger(__name__).exception("Reconhecimento visual encerrado")
            self.failed.emit(str(exc))
