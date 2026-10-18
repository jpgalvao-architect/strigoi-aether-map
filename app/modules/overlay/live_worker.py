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
    minimap_preview = Signal(object,object)

    def __init__(self, area, map_image, minimum_matches, capture_hz=30):
        super().__init__()
        self.area = area.model_copy(deep=True)
        self.map_image = map_image
        self.minimum_matches = minimum_matches
        self.capture_hz = min(capture_hz,60 if area.view_kind=="minimap" else 30)
        self.full_area = self.area.model_copy(update=dict(x=0,y=0,width=area.screen_width,height=area.screen_height,view_kind="large")) if area.view_kind=="minimap" else None
        self.stop_event = threading.Event()
        self.paint_exclusion = None
        self._mask_lock = threading.Lock()
        self.route_exclusion=None
        self.route_tracking=False
        self.route_settings=None
        self.preview_requested=False

    def set_route_tracking(self,enabled,settings):
        with self._mask_lock:
            self.route_tracking=bool(enabled);self.route_settings=settings.model_copy(deep=True)

    def request_preview(self):
        with self._mask_lock:self.preview_requested=True

    def set_route_exclusion(self,registration,lines,kind,pen=6,target=None):
        with self._mask_lock:self.route_exclusion=(registration,lines,kind,pen,target) if registration else None

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
                last_mini=None;last_mini_at=0.;last_mini_game=None;next_position=0.
                from app.modules.overlay.foreground import ForegroundProbe
                probe=ForegroundProbe()
                def read_frame(area):
                    nonlocal last_mini,last_mini_at,last_mini_game
                    monitor=find_monitor(area,capture.monitors[1:])
                    roi=physical_region(area,monitor)
                    frame = np.asarray(capture.grab(roi))[:, :, :3].copy()
                    feature_mask=np.full(frame.shape[:2],255,dtype=np.uint8)
                    with self._mask_lock:
                        stencil = self.paint_exclusion
                        routes=self.route_exclusion
                        wants=self.route_tracking or self.preview_requested
                    if area.view_kind=='minimap' and wants:
                        last_mini=frame.copy();last_mini_at=time.perf_counter();last_mini_game=probe.game_foreground()
                    if stencil and stencil[2]==area.view_kind:
                        registration, points, _ = stencil
                        apply_stencil(frame, feature_mask, registration, points)
                    if routes and routes[2]==area.view_kind:
                        from app.modules.overlay.stencil import apply_route_stencil
                        apply_route_stencil(frame,feature_mask,routes[0],routes[1],routes[3],routes[4])
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
                    now=time.perf_counter()
                    metadata=dict(roi=roi,area=area,screen_name=area.screen_name,method=method,observed_at=now)
                    with self._mask_lock:enabled=self.route_tracking;profile=self.route_settings;preview=self.preview_requested
                    if (enabled or preview) and now>=next_position:
                        next_position=now+.2;game=probe.game_foreground()
                        metadata.update(player_read=True,player=None,game_key=(game.handle,game.pid) if game else None,player_observed_at=last_mini_at)
                        # No additional screen read. Never derive a position from the full-map centre.
                        if game and game==last_mini_game and now-last_mini_at<=.7 and area.view_kind=='minimap' and registration is not None and last_mini is not None:
                            from app.modules.routes.position import locate
                            metadata['player']=locate(last_mini,profile,registration,area) if enabled and profile else None
                            if preview and probe.game_foreground()==game:
                                with self._mask_lock:self.preview_requested=False
                                self.minimap_preview.emit(last_mini.copy(),area)
                    self.observed.emit(registration,metadata)
                    rate=min(self.capture_hz,30) if area.view_kind=="large" else self.capture_hz
                    period=1/rate if registration else .2
                    self.stop_event.wait(max(.001, period-(time.perf_counter()-started)))
        except InterruptedError:
            pass
        except Exception as exc:
            logging.getLogger(__name__).exception("Reconhecimento visual encerrado")
            self.failed.emit(str(exc))
