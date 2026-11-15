# SPDX-License-Identifier: GPL-3.0-only
"""Exclude painted symbols, including height arrows, from terrain evidence."""
import math


def apply_route_stencil(frame,feature_mask,registration,lines,width,target=None):
    import cv2
    import numpy as np
    for vertices,_,_ in lines:
        points=np.rint([registration.project(x,y) for x,y in vertices]).astype(np.int32).reshape(-1,1,2)
        if len(points)<2:continue
        # Mask only the narrow strokes, not the path's bounding rectangle.
        cv2.polylines(frame,[points],False,(128,128,128),max(3,round(width)))
        cv2.polylines(feature_mask,[points],False,0,max(3,round(width)))
    if target:
        x,y=registration.project(*target[:2]);radius=round(13*width/6)
        cv2.circle(frame,(round(x),round(y)),radius,(128,128,128),-1)
        cv2.circle(feature_mask,(round(x),round(y)),radius,0,-1)


def apply_stencil(frame, feature_mask, registration, points):
    import cv2
    import numpy as np
    if not points:
        return
    xy = np.asarray([(point[0], point[1], 1.) for point in points])
    projected = xy @ registration.matrix.T
    extents = np.asarray([max(point[2], 2.3*point[4]+.8*point[5]+2)
                          if len(point) > 5 and point[3] in ('cube-up', 'cube-down') else point[2]
                          for point in points])
    h, w = frame.shape[:2]
    visible = np.flatnonzero((projected[:, 0] >= -extents) & (projected[:, 0] < w+extents)
                            & (projected[:, 1] >= -extents) & (projected[:, 1] < h+extents))
    for index in visible:
        point = points[index]
        radius = point[2]
        shape = point[3] if len(point) > 3 else 'circle'
        px, py = projected[index]
        if shape == 'badge':
            cx, cy = round(px), round(py)
            for left, top, right, bottom in point[4]:
                cv2.rectangle(frame, (cx+left,cy+top), (cx+right,cy+bottom), (128,128,128), -1)
                cv2.rectangle(feature_mask, (cx+left,cy+top), (cx+right,cy+bottom), 0, -1)
            continue
        base = point[4] if len(point) > 4 else radius
        pen = point[5] if len(point) > 5 else 2
        cx, cy = round(px), round(py)
        for image, color in ((frame, (128,128,128)), (feature_mask, 0)):
            if shape.startswith('cube') or shape == 'diamond':
                vertices = ([(cx,cy-radius),(cx+.9*radius,cy-.55*radius),(cx+.9*radius,cy+.55*radius),
                             (cx,cy+radius),(cx-.9*radius,cy+.55*radius),(cx-.9*radius,cy-.55*radius)]
                            if shape.startswith('cube') else
                            [(cx,cy-radius),(cx+radius,cy),(cx,cy+radius),(cx-radius,cy)])
                cv2.fillConvexPoly(image, np.rint(vertices).astype(np.int32), color)
            else:
                cv2.circle(image, (cx,cy), radius, color, -1)
            if shape in ('cube-up', 'cube-down'):
                direction = -1 if shape == 'cube-up' else 1
                vertices = [(cx+1.3*base,cy), (cx+1.8*base,cy+direction*.6*base), (cx+2.3*base,cy)]
                # Qt's square caps reach farther diagonally than OpenCV's round caps.
                width = math.ceil(pen*1.6+3)
                cv2.fillConvexPoly(image, np.rint(vertices).astype(np.int32), color)
                cv2.polylines(image, [np.rint(vertices).astype(np.int32)], False, color, width)
                cv2.line(image, (round(cx+1.8*base),round(cy+direction*.6*base)),
                         (round(cx+1.8*base),round(cy-direction*.6*base)), color, width)
