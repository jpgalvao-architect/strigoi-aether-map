# SPDX-License-Identifier: GPL-3.0-only
"""Optional capture worker and independent, input-transparent Qt window."""
import logging
import math
import threading
import time

from PySide6.QtCore import QObject, QPointF, QRect, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QRegion, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from app.infrastructure.storage import load_model, resolve_map_image
from app.modules.atlas.view import marker_path
from app.modules.atlas.heights import point_marker_shape
from app.modules.gatherables.service import FilterQuery, filter_points
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
        self._symbols={}
        self._coordinates=None
        self._marker_identity=None
        self._frame_signature=None

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
        self.smoothing.clear()
        self.draw_timer.stop()
        self.dirty_region=QRegion()
        self._visible_markers=[]
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
        signature=(self.scale,self.ratio,self.width(),self.height(),radius,
            tuple((round(px*4),round(py*4),color,shape) for px,py,color,shape in visible))
        if not self.smoothing.settled(now):
            self.request_frame()
        if signature==self._frame_signature:
            return
        self._frame_signature=signature
        self._visible_markers=visible
        for px,py,_,_ in visible:
            rectangle=QRect(round(px)-radius,round(py)-radius,radius*2+1,radius*2+1)
            current=rectangle if current.isNull() else current.united(rectangle)
        current=QRegion(current)
        dirty=self.dirty_region.united(current)
        self.dirty_region=current
        if not dirty.isEmpty():
            # Qt coalesces invalidations; a stationary map needs no ongoing paints.
            self.update(dirty)

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

    def paint_radius(self):
        # Includes arrows, outlines and antialiasing; the cube stays at its coordinate.
        return math.ceil(max(10*self.effective_scale()+2,
            (self.shape_radius('cube')*2.3+.65)*self.effective_scale()+2))

    def symbol(self,color,shape):
        mini=self.capture_area is not None and self.capture_area.view_kind=='minimap'
        key=(color,shape,self.scale,self.ratio,mini)
        if key not in self._symbols:
            scale=self.effective_scale()
            size=round(20*scale)+4
            if shape in ('cube-up','cube-down'):
                size=max(size,2*math.ceil((2.3*self.shape_radius(shape)+.65)*scale+2))
            pixmap=QPixmap(round(size*self.ratio),round(size*self.ratio))
            pixmap.setDevicePixelRatio(self.ratio)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter=QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            logical=pixmap.deviceIndependentSize()
            painter.translate(logical.width()/2,logical.height()/2)
            painter.scale(scale,scale)
            painter.setPen(QPen(QColor('#e7ffff'),1.3))
            painter.setBrush(QColor(color))
            painter.drawPath(marker_path(shape,self.shape_radius(shape)))
            painter.end()
            # Bound cache growth after many scale/DPI changes.
            if len(self._symbols)>100:self._symbols.clear()
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
            visible=self._visible_markers if getattr(self,'_drawing_registration',None) else self.visible_markers(registration)
            for px,py,color,shape in visible:
                pixmap=self.symbol(color,shape)
                painter.drawPixmap(QPointF(px-pixmap.deviceIndependentSize().width()/2,py-pixmap.deviceIndependentSize().height()/2),pixmap)
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

    def set_status(self, status):
        if status != self.status:
            self.status = status
            self.status_changed.emit(status)

    def start(self):
        if self.worker is not None:
            return
        from pathlib import Path
        settings = self.context.prefs.overlay
        definition = next(m for m in self.context.dataset.maps if m.id == settings.map_id)
        if settings.tracking_mode == "dynamic":
            self.start_dynamic(definition)
            return
        if not definition.supports_overlay:
            raise ValueError("Este mapa precisa de reconhecimento dinâmico. Selecione sua área na tela.")
        if not settings.calibration:
            raise ValueError("Calibre o overlay antes de ativar")
        calibration = load_model(Path(settings.calibration), Calibration)
        if calibration.map_id != settings.map_id:
            raise ValueError("A calibração pertence a outro mapa")
        MapDetector(calibration, settings.threshold)  # Validate before creating a worker.
        self.calibration = calibration
        self.worker = CaptureWorker(calibration, settings)
        self.worker.detected.connect(self.on_detection)
        self.worker.failed.connect(self.on_error)
        self.last_result = time.perf_counter()
        self.matches = 0
        settings.enabled = True
        self.sync()
        self.worker.start()
        self.set_status("Aguardando referências visuais")
        self.context.save()

    def start_dynamic(self, definition):
        from pathlib import Path
        from app.modules.overlay.selection import CaptureArea
        from app.modules.overlay.live_worker import LiveMapWorker
        settings = self.context.prefs.overlay
        area_path=settings.minimap_area if settings.map_view=="minimap" else settings.capture_area
        if not area_path:
            raise ValueError("Clique em Selecionar área na tela antes de ativar")
        area = load_model(Path(area_path), CaptureArea)
        if area.map_id != settings.map_id:
            raise ValueError("A área foi selecionada para outro mapa. Selecione-a novamente.")
        if area.view_kind!=settings.map_view:
            raise ValueError("A seleção pertence a outro modo de mapa. Selecione novamente.")
        screens = [s for s in QApplication.screens() if s.name()==area.screen_name]
        if len(screens)!=1:
            raise ValueError("Monitor não encontrado. Selecione a área novamente.")
        screen = screens[0]
        geometry = screen.geometry()
        if (geometry.x(),geometry.y(),geometry.width(),geometry.height()) != (area.screen_x,area.screen_y,area.screen_width,area.screen_height) or abs(screen.devicePixelRatio()-area.pixel_ratio)>.01:
            raise ValueError("Resolução ou escala mudou. Selecione a área novamente.")
        image = resolve_map_image(definition.image)
        if image.suffix.lower()==".svg":
            raise ValueError("O reconhecimento dinâmico precisa de um mapa raster com terreno.")
        self.capture_area = area
        self.window.capture_area = area
        self.window.clear_registration()
        self.window.viewport = None
        self.window.ratio = area.pixel_ratio
        self.window.setGeometry(area.screen_x+area.x, area.screen_y+area.y, area.width, area.height)
        self.worker = LiveMapWorker(area, image, settings.minimum_matches,settings.capture_hz)
        self.worker.observed.connect(self.on_registration)
        self.worker.failed.connect(self.on_error)
        self.worker.progress.connect(lambda message: self.set_status(message) if settings.enabled else None)
        self.last_result = time.perf_counter()
        self.matches = 0
        self.detection_started = False
        self.last_report=0.;self.observation_count=0;self.observation_hz=0.;self.observation_since=time.perf_counter()
        settings.enabled = True
        self.sync()
        self.worker.start()
        self.set_status("Preparando reconhecimento do mapa…")
        self.context.save()

    def on_registration(self, registration, metadata):
        if not self.context.prefs.overlay.enabled:
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
                self.on_error("Monitor ou escala mudou. Selecione a área novamente.")
                return
        if registration is None:
            self.observation_hz=0.
            self.observation_count=0
            self.observation_since=self.last_result
            self.matches = 0
            self.window.clear_registration()
            self.window.hide()
            if self.worker:
                self.worker.set_exclusion(None, [])
            self.set_status("Mapa não reconhecido • marcadores ocultos")
            return
        self.matches += 1
        self.window.accept_registration(registration)
        if self.matches < 2:
            self.window.hide()
            self.set_status("Confirmando reconhecimento…")
            return
        self.window.show()
        radius = round((7*self.window.scale+2)*self.window.ratio)
        self.set_exclusion(registration,radius)
        if self.last_result-self.last_report>=.5:
            self.last_report=self.last_result
            name="Minimapa" if self.capture_area and self.capture_area.view_kind=="minimap" else "Mapa"
            w,h=self.window.width()*self.window.ratio,self.window.height()*self.window.ratio
            visible=sum(0<=px<w and 0<=py<h for px,py in (registration.project(x,y) for x,y,_,_ in self.window.markers))
            points=f"{visible} posições possíveis de cubos" if visible and self.context.prefs.overlay.layers=='cubes' else (f"{visible} pontos desta camada" if visible else "sem pontos desta camada no recorte")
            self.set_status(f"{name} reconhecido • {points} • {registration.inliers} detalhes")

    def stop(self):
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
        self.set_status("Desligado")

    def set_exclusion(self,registration,radius):
        # Mask the painted silhouette, preserving terrain between dense candidates.
        scale=self.window.effective_scale()*self.window.ratio
        points=[(x,y,math.ceil((self.window.shape_radius(shape)*(1.3 if shape in ('leaf','wood') else 1)+.8)*scale)+2,shape,
                 self.window.shape_radius(shape)*scale,1.3*scale)
                for x,y,_,shape in self.window.markers]
        if self.capture_area:
            self.worker.set_exclusion(registration,points,self.capture_area.view_kind)
        else:
            self.worker.set_exclusion(registration,points)

    def sync(self):
        if not self.context.prefs.overlay.enabled:
            if self.worker:
                self.stop()
            return
        prefs = self.context.prefs
        dataset = self.context.atlas_dataset
        resources = {r.id: r for r in dataset.resources}
        categories = {c.id: c for c in dataset.categories}
        points = filter_points(dataset, prefs, FilterQuery(map_id=prefs.overlay.map_id, overlay=True))
        self.window.markers = [(p.x, p.y, categories[resources[p.resource_id].category].color,
            point_marker_shape(p,categories[resources[p.resource_id].category].icon)) for p in points]
        self.window.scale = prefs.overlay.scale
        self.window.set_render_rate(prefs.overlay.render_hz)
        self.window.setWindowOpacity(prefs.overlay.opacity)
        self.window.invalidate_frame()
        if self.capture_area and self.worker:
            self.worker.capture_hz=prefs.overlay.capture_hz
        if self.capture_area and self.worker and self.window.registration:
            radius = round((7*self.window.scale+2)*self.window.ratio)
            self.set_exclusion(self.window.registration,radius)

    def on_detection(self, matched, confidence, monitor):
        if not self.context.prefs.overlay.enabled:
            return
        self.last_result = time.perf_counter()
        self.matches = self.matches + 1 if matched else 0
        if self.matches < 2:
            self.window.hide()
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
        self.window.show()
        self.window.update()
        self.set_status(f"Mapa detectado • confiança {confidence:.0%}")

    def check_stale(self):
        if self.capture_area and not self.detection_started:
            return
        if self.worker and time.perf_counter()-self.last_result > 1.5:
            self.window.hide()
            self.window.clear_registration()
            if self.capture_area:
                self.worker.set_exclusion(None,[])
            self.matches = 0
            self.set_status("Captura sem resposta • overlay oculto")

    def on_error(self, message):
        self.stop()
        self.context.save()
        self.set_status(f"Indisponível: {message}")
