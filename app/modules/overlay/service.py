# SPDX-License-Identifier: GPL-3.0-only
"""Optional capture worker and independent, input-transparent Qt window."""
import logging
import math
import threading
import time

from PySide6.QtCore import QObject, QPointF, QRect, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QRegion, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from app.core.models import MapLocation
from app.infrastructure.storage import load_model, resolve_map_image
from app.modules.atlas.view import marker_path
from app.modules.atlas.heights import point_marker_shape
from app.modules.gatherables.service import FilterQuery, filter_points
from app.modules.overlay.badges import Badge, label_indices
from app.modules.overlay.detector import Calibration, MapDetector, project
from app.ui.overlay_visibility import OverlayVisibilityMixin


class CaptureWorker(QThread):
    detected = Signal(bool, float, object)
    failed = Signal(str)

    def __init__(self, calibration, settings):
        super().__init__()
        self.calibration = calibration
        self.settings = settings.model_copy(deep=True)
        self.stop_event = threading.Event()

    def run(self):
        try:
            import mss
            import numpy as np
            detector = MapDetector(self.calibration, self.settings.threshold)
            with mss.mss() as capture:
                if self.settings.monitor >= len(capture.monitors):
                    raise ValueError("Monitor indisponível")
                monitor = dict(capture.monitors[self.settings.monitor])
                while not self.stop_event.is_set():
                    frame = np.asarray(capture.grab(monitor))
                    matched, confidence = detector.detect(frame)
                    self.detected.emit(matched, confidence, monitor)
                    self.stop_event.wait(.5)
        except Exception as exc:
            logging.getLogger(__name__).exception("Overlay encerrado")
            self.failed.emit(str(exc))


class OverlayWindow(OverlayVisibilityMixin, QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.markers = []
        self.drawings = ()
        self._projected_drawings = ()
        self._drawing_registration = None
        self.scale = 1.0
        self.viewport = None
        self.ratio = 1.0
        self.calibration = None
        self.registration = None
        self.capture_area = None
        from app.modules.overlay.cadence import FramePacer,SmoothRegistration
        from app.modules.overlay.timer_resolution import TimerResolution
        self.timer_resolution=TimerResolution()
        self.pacer=FramePacer(60)
        self.smoothing=SmoothRegistration()
        self.draw_timer=QTimer(self)
        self.draw_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.draw_timer.setSingleShot(True)
        self.draw_timer.timeout.connect(self.schedule_frame)
        self.paint_count=0
        self.paint_hz=0.
        self.scheduled_frames=0
        self.timer_fires=0
        self.rate_started=time.perf_counter()
        self.dirty_region=QRegion()
        self._visible_markers=[]
        self._visible_labels=set()
        self._symbols={}
        self._coordinates=None
        self._marker_identity=None
        self._frame_signature=None
        self.badge_symbols=set()
        self.route_lines=()
        self.route_target=None

    def set_render_rate(self,hz):
        if self.pacer.hz!=hz:
            self.pacer.hz=hz
            self.pacer.deadline=0.
            self.request_frame()

    def request_frame(self):
        if self.isVisible() and self.registration is not None:
            delay=max(0,math.ceil((self.pacer.deadline-time.perf_counter())*1000))
            if not self.draw_timer.isActive() or delay<self.draw_timer.remainingTime():
                self.draw_timer.start(delay)

    def invalidate_frame(self):
        self._frame_signature=None
        if self.registration is None:
            self.update()  # Fixed-reference mode has no interpolation timer.
        else:
            self.request_frame()

    def clear_registration(self):
        self.registration=None
        self._drawing_registration=None
        self._projected_drawings = ()
        self.smoothing.clear()
        self.draw_timer.stop()
        self.dirty_region=QRegion()
        self._visible_markers=[]
        self._visible_labels=set()
        self._frame_signature=None

    def accept_registration(self,registration):
        self.registration=registration
        if self.smoothing.accept(registration,time.perf_counter()):
            self.request_frame()

    def schedule_frame(self):
        self.timer_fires+=1
        now=time.perf_counter()
        if not self.isVisible() or self.registration is None:
            self.draw_timer.stop()
            return
        if not self.pacer.due(now):
            self.request_frame()
            return
        self.scheduled_frames+=1
        registration=self.smoothing.at(now) or self.registration
        self._drawing_registration=registration
        # Clear and redraw only icon rectangles, including their previous positions.
        current=QRect()
        radius=self.paint_radius()
        visible=self.visible_markers(registration,radius)
        labels=self.marker_labels(visible)
        from app.modules.routes.drawing import project_lines,bounds
        routes=project_lines(self.route_lines,registration,self.ratio)
        target=registration.project(*self.route_target[:2]) if self.route_target else None
        signature=(self.scale,self.ratio,self.width(),self.height(),radius,
            tuple((round(px*4),round(py*4),color,shape,index in labels)
                  for index,(px,py,color,shape) in enumerate(visible)),
            tuple((tuple((round(x*4),round(y*4)) for x,y in vertices),reviewed,active) for vertices,reviewed,active in routes),
            (round(target[0]/self.ratio*4),round(target[1]/self.ratio*4),self.route_target[2]) if target else None,
            (self.drawings, tuple(round(value*4) for value in registration.matrix.flat)) if self.drawings else ())
        if not self.smoothing.settled(now):
            self.request_frame()
        if signature==self._frame_signature:
            return
        self._frame_signature=signature
        self._visible_markers=visible
        self._visible_labels=labels
        self._projected_drawings = self.project_drawings(registration)
        for px,py,_,_ in visible:
            rectangle=QRect(round(px)-radius,round(py)-radius,radius*2+1,radius*2+1)
            current=rectangle if current.isNull() else current.united(rectangle)
        route_bounds=bounds(routes).intersected(self.rect())
        if target:
            circle=QRect(round(target[0]/self.ratio)-12,round(target[1]/self.ratio)-12,25,25).intersected(self.rect())
            route_bounds=circle if route_bounds.isNull() else route_bounds.united(circle)
        if not route_bounds.isNull():current=route_bounds if current.isNull() else current.united(route_bounds)
        current=QRegion(current)
        for drawing in self._projected_drawings:
            current |= QRegion(drawing.bounds().toAlignedRect().intersected(self.rect()))
        dirty=self.dirty_region.united(current)
        self.dirty_region=current
        if not dirty.isEmpty():
            # Qt coalesces invalidations; a stationary map needs no ongoing paints.
            self.update(dirty)

    def project_drawings(self, registration):
        if not self.drawings:
            return ()
        from app.modules.siege.drawing import project_drawing, registration_transform
        transform = registration_transform(registration, self.ratio)
        projected = (project_drawing(drawing, color, transform) for drawing, color in self.drawings)
        return tuple(drawing for drawing in projected if drawing.bounds().toAlignedRect().intersects(self.rect()))

    def visible_markers(self,registration,radius=0):
        # Project in one array operation; do not construct thousands of NumPy
        # vectors and union a growing, fragmented QRegion for every frame.
        import numpy as np
        if self._marker_identity is not self.markers:
            self._marker_identity=self.markers
            self._coordinates=np.array([(x,y,1.) for x,y,_,_ in self.markers],dtype=float).reshape(-1,3)
        positions=self._coordinates@registration.matrix.T/self.ratio
        indices=np.flatnonzero((positions[:,0]>=-radius)&(positions[:,0]<self.width()+radius)&
                              (positions[:,1]>=-radius)&(positions[:,1]<self.height()+radius))
        return [(float(positions[i,0]),float(positions[i,1]),self.markers[i][2],self.markers[i][3]) for i in indices]

    def effective_scale(self):
        mini=self.capture_area is not None and self.capture_area.view_kind=='minimap'
        return self.scale * (2.0 if mini else 1.0)

    def shape_radius(self,shape):
        mini=self.capture_area is not None and self.capture_area.view_kind=='minimap'
        return 6 if shape.startswith('cube') and not mini else 4

    def badge_zoom(self):
        return self.scale * (1.3 if self.capture_area and self.capture_area.view_kind=='minimap' else 1.)

    def marker_labels(self, visible):
        if not self.badge_symbols:
            return set()
        badges = [(index,x,y,shape) for index,(x,y,_,shape) in enumerate(visible) if isinstance(shape, Badge)]
        shown = label_indices([(x,y,shape) for _,x,y,shape in badges], self.badge_zoom(), QRectF(self.rect()))
        return {badges[index][0] for index in shown}

    def paint_radius(self):
        # Includes arrows, outlines and antialiasing; the cube stays at its coordinate.
        return math.ceil(max(10*self.effective_scale()+2,
            (self.shape_radius('cube')*2.3+.65)*self.effective_scale()+2,
            max((badge.radius(self.badge_zoom()) for badge in self.badge_symbols), default=0)))

    def symbol(self,color,shape,draw_label=True):
        mini=self.capture_area is not None and self.capture_area.view_kind=='minimap'
        key=(color,shape,self.scale,self.ratio,mini,draw_label)
        if key not in self._symbols:
            scale=self.effective_scale()
            size=round(20*scale)+4
            if isinstance(shape, Badge):
                size=2*shape.radius(self.badge_zoom())
            elif shape in ('cube-up','cube-down'):
                size=max(size,2*math.ceil((2.3*self.shape_radius(shape)+.65)*scale+2))
            pixmap=QPixmap(round(size*self.ratio),round(size*self.ratio))
            pixmap.setDevicePixelRatio(self.ratio)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter=QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            logical=pixmap.deviceIndependentSize()
            painter.translate(logical.width()/2,logical.height()/2)
            if isinstance(shape, Badge):
                shape.paint(painter,color,self.badge_zoom(),draw_label)
            else:
                painter.scale(scale,scale)
                painter.setPen(QPen(QColor('#e7ffff'),1.3))
                painter.setBrush(QColor(color))
                painter.drawPath(marker_path(shape,self.shape_radius(shape)))
            painter.end()
            # Bound cache growth after many scale/DPI changes.
            if len(self._symbols)>256:self._symbols.clear()
            self._symbols[key]=pixmap
        return self._symbols[key]

    def showEvent(self,event):
        if self.registration:
            self.timer_resolution.enable()
            self.rate_started=time.perf_counter();self.paint_count=0
            self.request_frame()
        super().showEvent(event)

    def hideEvent(self,event):
        self.draw_timer.stop()
        self.timer_resolution.disable()
        self.paint_hz=0.
        super().hideEvent(event)

    def paintEvent(self, event):
        now=time.perf_counter()
        self.paint_count+=1
        elapsed=now-self.rate_started
        if elapsed>=1:
            self.paint_hz=self.paint_count/elapsed
            self.paint_count=0;self.rate_started=now
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.registration:
            registration=getattr(self,'_drawing_registration',None) or self.registration
            from app.modules.routes.drawing import paint_lines,project_lines
            drawings = self._projected_drawings if self._drawing_registration else self.project_drawings(registration)
            for drawing in drawings:
                drawing.paint(painter)
            paint_lines(painter,project_lines(self.route_lines,registration,self.ratio))
            visible=self._visible_markers if getattr(self,'_drawing_registration',None) else self.visible_markers(registration)
            labels=self._visible_labels if getattr(self,'_drawing_registration',None) else self.marker_labels(visible)
            for index,(px,py,color,shape) in enumerate(visible):
                pixmap=self.symbol(color,shape,index in labels)
                painter.drawPixmap(QPointF(px-pixmap.deviceIndependentSize().width()/2,py-pixmap.deviceIndependentSize().height()/2),pixmap)
            if self.route_target:
                x,y=registration.project(*self.route_target[:2]);x/=self.ratio;y/=self.ratio
                painter.setOpacity(1);painter.setBrush(QColor('#171721'));painter.setPen(QPen(QColor('#a7e4cb'),1.5))
                painter.drawEllipse(QPointF(x,y),10,10)
                painter.drawText(QRect(round(x)-10,round(y)-10,21,21),Qt.AlignCenter,str(self.route_target[2]))
            return
        for x, y, color, shape in self.markers:
            if self.registration:
                registration=getattr(self,"_drawing_registration",None) or self.registration
                px, py = registration.project(x, y)
            elif self.viewport:
                px, py = project(x, y, self.viewport)
            else:
                continue
            if self.capture_area:
                # The Qt window covers exactly the selected area, clipping hidden map points.
                if not 0 <= px/self.ratio < self.width() or not 0 <= py/self.ratio < self.height():
                    continue
            pixmap=self.symbol(color,shape)
            painter.drawPixmap(QPointF(px/self.ratio-pixmap.deviceIndependentSize().width()/2,
                py/self.ratio-pixmap.deviceIndependentSize().height()/2),pixmap)


class OverlayService(QObject):
    status_changed = Signal(str)

    def __init__(self, context):
        super().__init__()
        self.context = context
        self.window = OverlayWindow()
        self.worker = None
        self.siege_only = False
        self.capture_context = (True, 'play', 0)
        self.missing_region_since = None
        self.calibration = None
        self.capture_area = None
        self.last_result = 0.0
        self.matches = 0
        self.detection_started = False
        self.last_report=0.
        self.observation_count=0
        self.observation_hz=0.
        self.observation_since=time.perf_counter()
        self.status = "Desligado"
        self.watchdog = QTimer(self)
        self.watchdog.setInterval(250)
        self.watchdog.timeout.connect(self.check_stale)
        self.watchdog.start()
        context.changed.connect(self.sync)
        context.siege.changed.connect(self.sync)

    def attach_routes(self,routes):
        self.routes=routes;routes.changed.connect(self.sync_routes)
        self.status_changed.connect(lambda *_:routes.lose_position() if not self.window.registration else None)

    def sync_routes(self):
        routes=getattr(self,'routes',None)
        map_id = self.context.map_location.display_id
        active_map = bool(map_id and not self.siege_only and self.context.prefs.overlay.enabled)
        lines=routes.drawing(map_id) if routes and active_map else ()
        point=routes.target if routes and active_map and routes.active and routes.route.map_id==map_id else None
        target=(point.x,point.y,routes.current%len(routes.route.stops)+1) if point else None
        if target!=self.window.route_target:
            self.window.route_target=target;self.window.invalidate_frame()
        if lines!=self.window.route_lines:
            self.window.route_lines=lines;self.window.invalidate_frame()
        if self.worker and hasattr(self.worker,'set_route_tracking'):
            route_tracking = self.context.prefs.overlay.enabled and bool(routes and routes.active)
            key = (id(self.worker), route_tracking)
            if key != getattr(self, '_route_profile_key', None):
                self.worker.set_route_tracking(route_tracking)
                self._route_profile_key = key
            if self.window.registration and self.capture_area:
                self.worker.set_route_exclusion(self.window.registration,lines,self.capture_area.view_kind,6*self.window.ratio,target)
            else:self.worker.set_route_exclusion(None,(),self.context.prefs.overlay.map_view)

    def set_status(self, status):
        if status != self.status:
            self.status = status
            self.status_changed.emit(status)

    def start(self):
        if self.worker is not None and not self.siege_only:
            return
        from pathlib import Path
        settings = self.context.prefs.overlay
        if settings.tracking_mode == "dynamic":
            self.start_dynamic()
            return
        definition = next((m for m in self.context.exploration_dataset.maps if m.id == settings.map_id), None)
        if definition is None:
            raise ValueError("Selecione um mapa com uma referência visual disponível.")
        if not definition.supports_overlay:
            raise ValueError("Este mapa precisa de reconhecimento dinâmico. Selecione sua área na tela.")
        if not settings.calibration:
            raise ValueError("Calibre o overlay antes de ativar")
        calibration = load_model(Path(settings.calibration), Calibration)
        if calibration.map_id != settings.map_id:
            raise ValueError("A calibração pertence a outro mapa")
        MapDetector(calibration, settings.threshold)  # Validate before creating a worker.
        if self.siege_only:
            self.stop()
        self.calibration = calibration
        self.worker = CaptureWorker(calibration, settings)
        self.worker.detected.connect(self.on_detection)
        self.worker.failed.connect(self.on_error)
        self.last_result = time.perf_counter()
        self.matches = 0
        settings.enabled = True
        settings.resume_enabled = True
        self.sync()
        self.worker.start()
        self.set_status("Aguardando referências visuais")
        self.context.save()

    def start_dynamic(self):
        from pathlib import Path
        from app.modules.overlay.selection import CaptureArea
        settings = self.context.prefs.overlay
        area_path=settings.minimap_area if settings.map_view=="minimap" else settings.capture_area
        if not area_path:
            raise ValueError("Clique em Selecionar área na tela antes de ativar")
        area = load_model(Path(area_path), CaptureArea)
        if area.view_kind!=settings.map_view:
            raise ValueError("A seleção pertence a outro modo de mapa. Selecione novamente.")
        screens = [s for s in QApplication.screens() if s.name()==area.screen_name]
        if len(screens)!=1:
            raise ValueError("Monitor não encontrado. Selecione a área novamente.")
        self.begin_dynamic(area.on_screen(screens[0]))

    def selected_minimap(self, map_id):
        from pathlib import Path
        from app.modules.overlay.selection import CaptureArea
        try:
            path = self.context.prefs.overlay.minimap_area
            if path:
                area = load_model(Path(path), CaptureArea)
                screen = next((s for s in QApplication.screens() if s.name() == area.screen_name), None)
                if screen is not None and area.view_kind == 'minimap':
                    return area.on_screen(screen).model_copy(update={'map_id': map_id})
        except (OSError, ValueError):
            pass
        return None

    def references(self):
        settings = self.context.prefs.overlay
        preferred = settings.fallback_map_id or settings.map_id
        maps = self.context.exploration_dataset.maps
        refs = []
        for definition in maps:
            try:
                image = resolve_map_image(definition.image)
                if image.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'} and image.is_file():
                    refs.append((definition.id, image))
            except ValueError:
                continue
        return tuple(sorted(refs, key=lambda entry: entry[0] != preferred))

    def start_siege(self):
        from app.modules.overlay.selection import CaptureArea
        definition = self.context.siege.definition
        if self.worker or definition is None or not self.context.siege.state.overlay.map_markers:
            return
        area = self.selected_minimap(definition.id)
        if area is None:
            screen = QApplication.primaryScreen()
            if screen is None:
                return
            geom = screen.geometry()
            area = CaptureArea(map_id=definition.id, screen_name=screen.name(),
                               screen_x=geom.x(), screen_y=geom.y(), screen_width=geom.width(),
                               screen_height=geom.height(), pixel_ratio=screen.devicePixelRatio(),
                               x=0, y=0, width=geom.width(), height=geom.height())
        self.begin_dynamic(area, siege_only=True)

    def stop_general(self):
        if not self.siege_only:
            self.stop()
        self.start_siege()

    def refresh_siege_layer(self):
        if self.siege_only and not self.context.siege.state.overlay.map_markers:
            self.stop()
        else:
            self.start_siege()
        self.sync()

    def begin_dynamic(self, area, *, siege_only=False):
        from app.modules.overlay.live_worker import LiveMapWorker
        settings = self.context.prefs.overlay
        references = self.references()
        if not references:
            raise ValueError("Nenhum mapa com referência visual está disponível.")
        if not siege_only and area.view_kind == 'large':
            mini = self.selected_minimap('')
            if mini and mini.screen_name == area.screen_name:
                area = mini
        area = area.model_copy(update={'map_id': ''})
        if self.siege_only:
            self.stop()
        self.siege_only = siege_only
        self.capture_area = area
        self.window.capture_area = area
        self.window.clear_registration()
        self.window.viewport = None
        self.window.ratio = area.pixel_ratio
        self.window.setGeometry(area.screen_x+area.x, area.screen_y+area.y, area.width, area.height)
        self.worker = LiveMapWorker(area, settings.minimum_matches, settings.capture_hz,
                                    references=references, minimap_enabled=self.minimap_enabled())
        self.worker.set_capture_context(self.capture_context)
        self.worker.observed.connect(self.on_registration)
        self.worker.failed.connect(self.on_error)
        self.worker.progress.connect(self.on_progress)
        self.last_result = time.perf_counter()
        self.matches = 0
        self.detection_started = False
        self.last_report=0.;self.observation_count=0;self.observation_hz=0.;self.observation_since=time.perf_counter()
        if not siege_only:
            settings.enabled = True
            settings.resume_enabled = True
        self.sync()
        self.worker.start()
        self.set_status("Preparando reconhecimento do mapa…")
        if not siege_only:
            self.context.save()

    def minimap_enabled(self):
        return (self.siege_only or self.context.prefs.overlay.map_view == 'minimap'
                or self.context.siege.state.overlay.map_markers)

    def update_location(self, display_id=None, view=None, *, clear_region=False, observe_minimap=False):
        region = self.context.map_location.region_id
        if observe_minimap and display_id:
            region = display_id
            self.missing_region_since = None
        elif observe_minimap:
            now = time.monotonic()
            if self.missing_region_since is None:
                self.missing_region_since = now
            clear_region |= now-self.missing_region_since >= 1.2
        else:
            self.missing_region_since = None
        updated = MapLocation(None if clear_region else region, display_id, view)
        if updated != self.context.map_location:
            self.context.set_map_location(updated)
            self.sync()

    def set_capture_context(self, active, mode):
        if (active, mode) == self.capture_context[:2]:
            return
        self.capture_context = (active, mode, self.capture_context[2]+1)
        if self.worker and hasattr(self.worker, 'set_capture_context'):
            self.worker.set_capture_context(self.capture_context)
        if not active or mode == 'menu':
            self.matches = 0
            self.window.hide()
            self.window.clear_registration()
            self.update_location()
            if self.worker is not None:
                self.set_status("Captura pausada")

    def on_registration(self, registration, metadata):
        if not (self.context.prefs.overlay.enabled or self.siege_only) or not self.current_worker_signal():
            return
        if metadata.get('epoch', self.capture_context[2]) != self.capture_context[2]:
            return
        observed_area=metadata.get("area")
        if observed_area is not None and observed_area!=self.capture_area:
            self.matches=0
            self.last_report=0.
            self.window.hide()
            self.window.clear_registration()
            self.capture_area=observed_area
            self.window.capture_area=observed_area
            self.window.ratio=observed_area.pixel_ratio
            self.window.setGeometry(observed_area.screen_x+observed_area.x,observed_area.screen_y+observed_area.y,observed_area.width,observed_area.height)
            self.observation_count=0;self.observation_hz=0.;self.observation_since=time.perf_counter()
            self.update_location()
        self.last_result = time.perf_counter()
        self.observation_count+=1
        elapsed=self.last_result-self.observation_since
        if elapsed>=1:
            self.observation_hz=self.observation_count/elapsed
            self.observation_count=0;self.observation_since=self.last_result
        self.detection_started = True
        if self.capture_area:
            area = self.capture_area
            screens = [s for s in QApplication.screens() if s.name()==area.screen_name]
            if len(screens)!=1:
                self.on_error("Monitor desconectado. Selecione a área novamente.")
                return
            screen = screens[0]
            g = screen.geometry()
            if (g.x(),g.y(),g.width(),g.height())!=(area.screen_x,area.screen_y,area.screen_width,area.screen_height) or abs(screen.devicePixelRatio()-area.pixel_ratio)>.01:
                self.refresh_screen()
                return
        area = self.capture_area
        if registration is None or area is None or not area.map_id:
            self.update_location(observe_minimap=bool(area and area.view_kind == 'minimap'))
            self.observation_hz=0.
            self.observation_count=0
            self.observation_since=self.last_result
            self.matches = 0
            self.window.clear_registration()
            self.window.hide()
            if self.worker:
                self.worker.set_exclusion(None, [])
            self.set_status("Mapa não identificado")
            return
        self.matches += 1
        self.window.accept_registration(registration)
        if self.matches < 2:
            self.window.hide()
            self.set_status("Confirmando reconhecimento…")
            return
        self.update_location(area.map_id, area.view_kind, observe_minimap=area.view_kind == 'minimap')
        if self.window.markers or self.window.drawings or self.window.route_target or self.window.route_lines:
            self.window.show()
        else:
            self.window.hide()
        self.set_exclusion(registration)
        self.sync_routes()
        routes=getattr(self,'routes',None)
        if routes and metadata.get('player_read'):
            reading=metadata.get('player') if area.view_kind == 'minimap' else None
            map_id = self.context.map_location.region_id
            routes.observe(reading[0] if reading else None,map_id=map_id,
                game=metadata.get('game_key'),observed_at=metadata.get('player_observed_at',metadata['observed_at']),radius=reading[1] if reading else .001)
        if self.last_result-self.last_report>=.5:
            self.last_report=self.last_result
            name="Minimapa" if self.capture_area and self.capture_area.view_kind=="minimap" else "Mapa"
            visible = len(self.window.visible_markers(registration))
            points=f"{visible} posições possíveis de cubos" if visible and self.context.prefs.overlay.layers=='cubes' else (f"{visible} pontos desta camada" if visible else "sem pontos desta camada no recorte")
            self.set_status(f"{name} reconhecido • {points} • {registration.inliers} detalhes")

    def stop(self):
        self.siege_only = False
        self.context.prefs.overlay.enabled = False
        self.observation_hz=0.
        self.window.hide()
        self.window.clear_registration()
        self.matches = 0
        if self.worker:
            self.worker.stop_event.set()
            self.worker.wait()  # Capture owns no event-loop dependencies.
            self.worker.deleteLater()
            self.worker = None
        self.capture_area = None
        self.window.capture_area = None
        self.context.set_map_location(MapLocation())
        self.missing_region_since = None
        self.set_status("Desligado")

    def current_worker_signal(self):
        return self.sender() is None or self.sender() is self.worker

    def on_progress(self, message):
        if (self.context.prefs.overlay.enabled or self.siege_only) and self.current_worker_signal():
            self.set_status(message)

    def set_exclusion(self, registration):
        # Mask only symbols whose footprint can overlap this capture.
        window = self.window
        scale = window.effective_scale() * window.ratio
        zoom, ratio = window.badge_zoom(), window.ratio
        key = (id(window.markers), scale, zoom, ratio)
        if key != getattr(self, '_exclusion_key', None):
            points = []
            for x, y, _, shape in window.markers:
                if isinstance(shape, Badge):
                    radius = math.ceil(shape.radius(zoom)*ratio)+2
                    rectangles = tuple(
                        (math.floor(rect.left()*ratio)-2, math.floor(rect.top()*ratio)-2,
                         math.ceil(rect.right()*ratio)+2, math.ceil(rect.bottom()*ratio)+2)
                        for rect in shape.layout(zoom)[:2] if not rect.isEmpty()
                    )
                    points.append((x, y, radius, 'badge', rectangles))
                else:
                    base = window.shape_radius(shape)
                    extent = base*(1.3 if shape in ('leaf', 'wood') else 1)+.8
                    points.append((x, y, math.ceil(extent*scale)+2, shape, base*scale, 1.3*scale))
            self._exclusion_key = key
            self._exclusion_points = points
            self._exclusion_markers = window.markers
        if self.capture_area:
            view_kind = self.capture_area.view_kind
            self.worker.set_exclusion(registration, self._exclusion_points, view_kind)
            if hasattr(self.worker, 'set_drawing_exclusion'):
                stencil = tuple(drawing.stencil(ratio) for drawing in window.project_drawings(registration))
                self.worker.set_drawing_exclusion(stencil, view_kind)
        else:
            self.worker.set_exclusion(registration, self._exclusion_points)

    def sync(self):
        self.sync_routes()
        prefs = self.context.prefs
        if not (prefs.overlay.enabled or self.siege_only):
            if self.worker is not None:
                self.stop()
            return
        dataset = self.context.atlas_dataset
        from app.modules.siege.models import MAP_ID
        map_id = self.context.map_location.display_id
        siege = self.context.siege
        if self.worker and hasattr(self.worker, 'set_references'):
            self.worker.set_references(self.references(), self.minimap_enabled())
        exploration = bool(map_id and prefs.overlay.enabled and (
            prefs.overlay.map_view != 'large' or self.context.map_location.view == 'large'
        ))
        drawings = ()
        if map_id == MAP_ID:
            from app.modules.siege.markers import markers_for
            tactical = siege.state.overlay.map_markers
            markers = markers_for(siege, dataset, tactical=tactical, exploration=exploration) if siege.definition else []
            if tactical and siege.definition:
                from app.modules.siege.drawing import visible_drawings
                drawings = visible_drawings(siege.preset)
        elif exploration:
            resources = {r.id: r for r in dataset.resources}
            categories = {c.id: c for c in dataset.categories}
            points = filter_points(dataset, prefs, FilterQuery(map_id=map_id, overlay=True))
            markers = [(p.x, p.y, categories[resources[p.resource_id].category].color,
                point_marker_shape(p,categories[resources[p.resource_id].category].icon)) for p in points]
        else:
            markers = []
        self.window.markers = markers
        self.window.drawings = drawings
        self.window.badge_symbols = {shape for _,_,_,shape in markers if isinstance(shape, Badge)}
        self.window.scale = prefs.overlay.scale
        self.window.set_render_rate(prefs.overlay.render_hz)
        self.window.setWindowOpacity(prefs.overlay.opacity)
        self.window.invalidate_frame()
        if self.capture_area and self.worker:
            self.worker.capture_hz=prefs.overlay.capture_hz
        if self.capture_area and self.worker and self.window.registration:
            self.set_exclusion(self.window.registration)

    def on_detection(self, matched, confidence, monitor):
        if not self.context.prefs.overlay.enabled or not self.current_worker_signal():
            return
        self.last_result = time.perf_counter()
        self.matches = self.matches + 1 if matched else 0
        if self.matches < 2:
            self.window.hide()
            self.update_location()
            self.set_status(f"Aguardando mapa • confiança {max(0, confidence):.0%}")
            return
        # Map physical capture pixels to Qt logical coordinates using the selected screen.
        screens = QApplication.screens()
        candidates = [s for s in screens if s.geometry().x() == monitor["left"] and s.geometry().y() == monitor["top"] and abs(s.geometry().width()*s.devicePixelRatio()-monitor["width"]) < 3 and abs(s.geometry().height()*s.devicePixelRatio()-monitor["height"]) < 3]
        if len(candidates) != 1:
            self.window.hide()
            self.set_status("Monitor/DPI incompatível • overlay oculto")
            return
        screen = candidates[0]
        self.window.setGeometry(screen.geometry())
        self.window.ratio = screen.devicePixelRatio()
        self.window.viewport = self.calibration.viewport
        self.window.registration = None
        self.update_location(self.calibration.map_id, 'large')
        self.window.show()
        self.window.update()
        self.set_status(f"Mapa detectado • confiança {confidence:.0%}")

    def check_stale(self):
        if self.capture_area and (not self.detection_started or not self.capture_context[0]
                                  or self.capture_context[1] == 'menu'):
            return
        if self.worker and time.perf_counter()-self.last_result > 1.5:
            self.window.hide()
            self.window.clear_registration()
            if self.capture_area:
                self.worker.set_exclusion(None,[])
            self.matches = 0
            self.update_location(clear_region=True)
            self.set_status("Captura sem resposta • overlay oculto")

    def refresh_screen(self):
        siege_only = self.siege_only
        self.stop()
        try:
            if siege_only:
                self.start_siege()
            else:
                self.start()
        except (OSError, ValueError) as exc:
            self.context.save()
            self.set_status(f"Indisponível: {exc}")

    def on_error(self, message):
        if not self.current_worker_signal():
            return
        self.stop()
        self.context.save()
        self.set_status(f"Indisponível: {message}")
