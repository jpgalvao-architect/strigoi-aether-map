# SPDX-License-Identifier: GPL-3.0-only
"""Small projected polylines shared by Atlas and the existing overlay painter."""
from PySide6.QtCore import QPointF,QRect,Qt
from PySide6.QtGui import QColor,QPainterPath,QPen


def project_lines(lines,registration,ratio):
    return tuple((tuple((px/ratio,py/ratio) for px,py in (registration.project(x,y) for x,y in vertices)),reviewed,active)
                 for vertices,reviewed,active in lines)


def bounds(lines):
    result=QRect()
    for points,_,_ in lines:
        if not points:continue
        xs,ys=zip(*points)
        rect=QRect(int(min(xs))-8,int(min(ys))-8,int(max(xs)-min(xs))+17,int(max(ys)-min(ys))+17)
        result=rect if result.isNull() else result.united(rect)
    return result


def paint_lines(painter,lines):
    painter.save()
    for points,reviewed,active in lines:
        if len(points)<2:continue
        path=QPainterPath(QPointF(*points[0]))
        for point in points[1:]:path.lineTo(QPointF(*point))
        pen=QPen(QColor('#a7e4cb'),3 if active else 1.8,
            Qt.PenStyle.SolidLine if reviewed else Qt.PenStyle.DashLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap);pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen);painter.setOpacity(1 if active else .55);painter.drawPath(path)
    painter.restore()
