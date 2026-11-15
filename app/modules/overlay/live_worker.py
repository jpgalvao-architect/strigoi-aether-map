# SPDX-License-Identifier: GPL-3.0-only
"""Selected-area capture and map registration, both owned by one worker."""
import logging
import threading
import time

from PySide6.QtCore import QThread, Signal

from app.modules.overlay.selection import find_monitor, physical_region
from app.modules.overlay.stencil import apply_stencil


class MapCandidates:
    """Track one map. Search one alternative at a time after losing terrain."""

    def __init__(self, make_tracker, *, retry=.25):
        self.make_tracker = make_tracker
        self.references = {}
        self.trackers = {}
        self.unavailable = set()
        self.order = ()
        self.active = self.pending = self.map_id = None
        self.retry = retry
        self.next_search = self.next_active = 0.
        self.cursor = 0

    def reset(self):
        for key in (self.active, self.pending):
            if key in self.trackers:
                self.trackers[key].reset()
        self.pending = self.map_id = None
        self.next_search = self.next_active = 0.

    def configure(self, references):
        order = tuple(references)
        if order == self.order:
            return
        images = dict(order)
        self.trackers = {key: tracker for key, tracker in self.trackers.items()
                         if key in images and self.references[key] == images[key]}
        if self.active not in self.trackers:
            self.active = None
        if self.pending not in self.trackers:
            self.pending = None
        self.map_id = None
        self.references = images
        self.order = order
        self.next_search = 0.
        self.cursor = 0

    def observe(self, frame, now, **kwargs):
        self.map_id = None
        if self.pending is not None:
            key, self.pending = self.pending, None
            registration, method = self.trackers[key].observe(frame, now, **kwargs)
            if registration is not None and method == 'reference':
                if self.active in self.trackers and self.active != key:
                    self.trackers[self.active].reset()
                self.active = self.map_id = key
                return registration, method
        if self.active in self.trackers and now >= self.next_active:
            registration, method = self.trackers[self.active].observe(frame, now, **kwargs)
            if registration is not None:
                self.map_id = self.active
                return registration, method
            self.next_active = now + self.retry
        if not self.order or now < self.next_search:
            return None, 'search'
        self.next_search = now + self.retry
        for _ in self.order:
            key, image = self.order[self.cursor]
            self.cursor = (self.cursor + 1) % len(self.order)
            if key != self.active and (key, image) not in self.unavailable:
                break
        else:
            return None, 'search'
        try:
            if key not in self.trackers:
                self.trackers[key] = self.make_tracker(image)
        except (OSError, ValueError):
            logging.getLogger(__name__).warning("Referência visual indisponível para %s", key)
            self.unavailable.add((key, image))
            return None, 'search'
        tracker = self.trackers[key]
        tracker.reset()
        registration, _ = tracker.observe(frame, now, **kwargs)
        if registration is not None:
            self.pending = key
            tracker.reset()  # A different frame must independently confirm the new region.
        return None, 'search'


class LiveMapWorker(QThread):
    observed = Signal(object, object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, area, minimum_matches, capture_hz=30, *, references=(), minimap_enabled=True):
        super().__init__()
        self.area = area.model_copy(deep=True)
        self.minimum_matches = minimum_matches
        self.capture_hz = min(capture_hz,60 if area.view_kind=="minimap" else 30)
        self.full_area = self.area.model_copy(update=dict(x=0,y=0,width=area.screen_width,height=area.screen_height,view_kind="large")) if area.view_kind=="minimap" else None
        self.stop_event = threading.Event()
        self.paint_exclusion = None
        self._mask_lock = threading.Lock()
        self.route_exclusion=None
        self.route_tracking=False
        self.references = references
        self.minimap_enabled = minimap_enabled
        self.capture_context = (True, 'play', 0)

    def set_references(self, references, minimap_enabled):
        with self._mask_lock:
            self.references = references
            self.minimap_enabled = minimap_enabled

    def set_capture_context(self, context):
        with self._mask_lock:
            self.capture_context = context

    def set_route_tracking(self,enabled):
        with self._mask_lock:self.route_tracking=bool(enabled)

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
            def candidates(minimap):
                def make_tracker(image):
                    return FastMapTracker(MapRegistration(
                        image, should_stop=self.stop_event.is_set, minimap=minimap,
                    ), interval=.75 if minimap else .6, flow_grace=.25 if minimap else 0.)
                return MapCandidates(make_tracker, retry=.25 if minimap else .45)

            tracker = candidates(self.area.view_kind == "minimap")
            automatic = None
            large = None
            if self.full_area:
                from app.modules.overlay.automatic import AutomaticMapTracker
                large = candidates(False)
                automatic = AutomaticMapTracker(tracker, large, self.area, self.full_area)
            if self.stop_event.is_set():
                return
            self.progress.emit("Procurando o mapa na área selecionada…")
            with mss.MSS() as capture:
                monitor = find_monitor(self.area, capture.monitors[1:])
                last_mini_shape=None;last_mini_at=0.;last_mini_game=None;next_position=0.
                from app.modules.overlay.foreground import ForegroundProbe
                probe=ForegroundProbe()
                generation = None

                def probe_large():
                    from app.modules.overlay.menu_monitor import fullscreen_close
                    roi = physical_region(self.full_area, monitor)
                    header = np.asarray(capture.grab({**roi, 'height': round(roi['height']*.08)}))[:, :, :3]
                    return fullscreen_close(header, roi['height'])

                def read_frame(area):
                    nonlocal last_mini_shape,last_mini_at,last_mini_game
                    roi=physical_region(area,monitor)
                    frame = np.asarray(capture.grab(roi))[:, :, :3].copy()
                    feature_mask=np.full(frame.shape[:2],255,dtype=np.uint8)
                    with self._mask_lock:
                        stencil = self.paint_exclusion
                        routes=self.route_exclusion
                        wants=self.route_tracking
                    if area.view_kind=='minimap' and wants:
                        last_mini_shape=frame.shape;last_mini_at=time.perf_counter();last_mini_game=probe.game_foreground()
                    if stencil and stencil[2]==area.view_kind:
                        registration, points, _ = stencil
                        apply_stencil(frame, feature_mask, registration, points)
                    if routes and routes[2]==area.view_kind:
                        from app.modules.overlay.stencil import apply_route_stencil
                        apply_route_stencil(frame,feature_mask,routes[0],routes[1],routes[3],routes[4])
                    return frame,feature_mask
                while not self.stop_event.is_set():
                    started = time.perf_counter()
                    with self._mask_lock:
                        active, mode, epoch = self.capture_context
                        refs = self.references
                        minimap_enabled = self.minimap_enabled
                    if epoch != generation:
                        tracker.reset()
                        if large is not None:
                            large.reset()
                        generation = epoch
                    if not active or mode == 'menu':
                        self.stop_event.wait(.25)
                        continue
                    tracker.configure(refs if minimap_enabled or self.area.view_kind == 'large' else ())
                    if large is not None:
                        large.configure(refs)
                    if automatic and minimap_enabled:
                        registration, method, area = automatic.observe(
                            read_frame, started, minimum=self.minimum_matches, large_only=mode == 'map',
                            probe_large=probe_large,
                        )
                        detected = large if area.view_kind == 'large' else tracker
                    else:
                        area, detected = (self.full_area, large) if automatic else (self.area, tracker)
                        frame, feature_mask = read_frame(area)
                        registration, method = detected.observe(
                            frame, started, minimum=self.minimum_matches, feature_mask=feature_mask,
                        )
                    area = area.model_copy(update={'map_id': detected.map_id or ''})
                    roi=physical_region(area,monitor)
                    now=time.perf_counter()
                    metadata=dict(roi=roi,area=area,screen_name=area.screen_name,method=method,observed_at=now,epoch=epoch)
                    with self._mask_lock:enabled=self.route_tracking
                    if enabled and now>=next_position:
                        next_position=now+.2;game=probe.game_foreground()
                        metadata.update(player_read=True,player=None,game_key=(game.handle,game.pid) if game else None,player_observed_at=last_mini_at)
                        # No additional screen read. Never derive a position from the full-map centre.
                        if game and game==last_mini_game and now-last_mini_at<=.7 and area.view_kind=='minimap' and registration is not None and last_mini_shape is not None:
                            from app.modules.routes.position import locate
                            metadata['player']=locate(last_mini_shape,registration,area)
                    self.observed.emit(registration,metadata)
                    rate=min(self.capture_hz,30) if area.view_kind=="large" else self.capture_hz
                    period=1/rate if registration else .2
                    self.stop_event.wait(max(.001, period-(time.perf_counter()-started)))
        except InterruptedError:
            pass
        except Exception as exc:
            logging.getLogger(__name__).exception("Reconhecimento visual encerrado")
            self.failed.emit(str(exc))
