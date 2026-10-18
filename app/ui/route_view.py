# SPDX-License-Identifier: GPL-3.0-only
"""Native map editor; route points never modify the Atlas dataset."""
from PySide6.QtCore import Signal,QRectF,Qt,QPointF
from PySide6.QtGui import QColor,QPen,QPainterPath,QFont
from PySide6.QtWidgets import QGraphicsEllipseItem,QGraphicsSimpleTextItem
from app.modules.atlas.view import AtlasView


class RouteView(AtlasView):
    map_clicked=Signal(float,float)

    def __init__(self):
        super().__init__();self.editing=False;self.route_items=[];self._fit_route=None
        self.setBackgroundBrush(QColor('#171721'))

    def set_map(self,definition):
        self.route_items=[];self._fit_route=None;super().set_map(definition)

    def show_route(self,route):
        for item in self.route_items:self.scene().removeItem(item)
        self.route_items=[]
        if route is None or self.map is None:return
        for leg in route.legs:
            path=QPainterPath(QPointF(leg.vertices[0].x*self.map.width,leg.vertices[0].y*self.map.height))
            for v in leg.vertices[1:]:path.lineTo(v.x*self.map.width,v.y*self.map.height)
            pen=QPen(QColor('#a7e4cb'),2,Qt.SolidLine if leg.reviewed else Qt.DashLine);pen.setCosmetic(True)
            item=self.scene().addPath(path,pen);item.setZValue(3);self.route_items.append(item)
        for index,stop in enumerate(route.stops):
            item=QGraphicsEllipseItem(-10,-10,20,20)
            item.setFlag(item.GraphicsItemFlag.ItemIgnoresTransformations)
            item.setBrush(QColor('#a7e4cb' if index==0 else '#171721'));item.setPen(QPen(QColor('#a7e4cb'),1.5))
            item.setPos(stop.x*self.map.width,stop.y*self.map.height);item.setZValue(5)
            item.setToolTip(stop.name)
            text=QGraphicsSimpleTextItem(str(index+1),item);text.setFont(QFont('Segoe UI',9))
            text.setBrush(QColor('#101018' if index==0 else '#efedf7'))
            rect=text.boundingRect();text.setPos(-rect.width()/2,-rect.height()/2)
            self.scene().addItem(item);self.route_items.append(item)

    def fit_route(self,route):
        self._fit_route=route
        if not route or not self.map:return self.fit_map()
        points=[v for leg in route.legs for v in leg.vertices]
        xs=[p.x*self.map.width for p in points];ys=[p.y*self.map.height for p in points]
        rect=QRectF(min(xs),min(ys),max(30,max(xs)-min(xs)),max(30,max(ys)-min(ys)))
        margin=max(rect.width(),rect.height())*.18+20
        self.fitInView(rect.adjusted(-margin,-margin,margin,margin),Qt.KeepAspectRatio);self.zoom_level=1

    def zoom(self,delta):self._fit_route=None;super().zoom(delta)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self._fit_route:self.fit_route(self._fit_route)

    def mousePressEvent(self,event):
        if self.editing and self.map and event.button()==Qt.LeftButton:
            point=self.mapToScene(event.position().toPoint());x=point.x()/self.map.width;y=point.y()/self.map.height
            if 0<=x<=1 and 0<=y<=1:self.map_clicked.emit(x,y)
            event.accept();return
        self._fit_route=None;super().mousePressEvent(event)
