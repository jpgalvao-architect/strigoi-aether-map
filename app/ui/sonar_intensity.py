# SPDX-License-Identifier: GPL-3.0-only
"""Small, ephemeral trace of confirmed reference-component levels, not distance."""
from collections import deque
import math
import time
from PySide6.QtCore import QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from app.ui.localized_widgets import QWidget
from app.ui.widgets import label


class IntensityTrace:
    def __init__(self):
        self.history=deque(maxlen=96)
        self.level=None
        self.updated=-float('inf')

    def set_level(self, level, now):
        self.level=float(level) if level is not None and math.isfinite(level) else None
        self.updated=now
        self.history.append((now,self.fraction(now) if self.level is not None else None))

    def valid(self, now):
        return self.level is not None and 0 <= now-self.updated <= 1.2

    def fraction(self, now):
        if not self.valid(now):
            return 0.
        return max(0.,min(1.,(self.level+80)/60))


class IntensityCanvas(QWidget):
    def __init__(self, meter, compact):
        super().__init__(meter)
        self.meter=meter
        self.setFixedHeight(48 if compact else 76)

    def paintEvent(self, event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w=max(1,self.width()-2)
        bar=QRectF(1,1,w,9)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#111a28'));painter.drawRoundedRect(bar,4,4)
        if self.meter.display>0:
            painter.setBrush(QColor('#edcb81' if self.meter.display>=.7 else '#93dedf'))
            painter.drawRoundedRect(QRectF(1,1,w*self.meter.display,9),4,4)
        top,bottom=20,self.height()-3
        painter.setPen(QPen(QColor('#344254'),1))
        painter.drawLine(1,bottom,self.width()-1,bottom)
        now=time.monotonic()
        path=QPainterPath();connected=False;previous=None
        for stamp,value in self.meter.trace.history:
            if stamp<now-15:
                continue
            if value is None:
                connected=False;previous=stamp;continue
            x=1+w*max(0.,min(1.,(stamp-(now-15))/15))
            y=bottom-(bottom-top)*value
            if not connected or previous is None or stamp-previous>1.2:
                path.moveTo(x,y)
            else:path.lineTo(x,y)
            connected=True;previous=stamp
        painter.setPen(QPen(QColor('#93dedf'),1.6));painter.drawPath(path)


class SonarIntensity(QWidget):
    def __init__(self, compact=False):
        super().__init__()
        self.trace=IntensityTrace()
        self.display=0.
        self.last_tick=time.monotonic()
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(3)
        header=QHBoxLayout()
        header.addWidget(label('Intensidade do som','subtitle'),1)
        self.state=label('Aguardando sinal','subtitle');header.addWidget(self.state)
        layout.addLayout(header)
        self.canvas=IntensityCanvas(self,compact);layout.addWidget(self.canvas)
        legend=QHBoxLayout()
        legend.addWidget(label('Fraco','subtitle'));legend.addStretch()
        legend.addWidget(label('Forte','subtitle'));layout.addLayout(legend)
        self.setAccessibleName('Intensidade estimada do som reconhecido')
        self.setToolTip('A barra acompanha o som reconhecido. O volume do jogo influencia a leitura; não indica distância em metros.')
        self.timer=QTimer(self);self.timer.setInterval(100);self.timer.timeout.connect(self.tick)

    def set_level(self, level):
        self.trace.set_level(level,time.monotonic())
        self.tick()

    def clear(self):
        self.trace=IntensityTrace();self.display=0.
        self.last_tick=time.monotonic();self.state.setText('Aguardando sinal');self.canvas.update()

    def tick(self):
        now=time.monotonic()
        target=self.trace.fraction(now)
        elapsed=max(0.,now-self.last_tick);self.last_tick=now
        self.display+=(target-self.display)*(1-math.exp(-elapsed/.3))
        text=('Aguardando sinal' if not self.trace.valid(now) else
              'Fraco' if target<.33 else 'Moderado' if target<.7 else 'Forte')
        self.state.setText(text)
        self.canvas.update()

    def showEvent(self,event):
        self.last_tick=time.monotonic();self.timer.start();self.tick()
        super().showEvent(event)

    def hideEvent(self,event):
        self.timer.stop();super().hideEvent(event)
