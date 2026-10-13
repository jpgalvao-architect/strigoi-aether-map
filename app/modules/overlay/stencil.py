# SPDX-License-Identifier: GPL-3.0-only
"""Exclude painted symbols, including height arrows, from terrain evidence."""
import math


def apply_stencil(frame, feature_mask, registration, points):
    import cv2
    import numpy as np
    for point in points:
        x, y, radius = point[:3]
        shape = point[3] if len(point) > 3 else 'circle'
        base = point[4] if len(point) > 4 else radius
        pen = point[5] if len(point) > 5 else 2
        px, py = registration.project(x, y)
        extent = max(radius, 2.3*base+pen*.8+2) if shape in ('cube-up', 'cube-down') else radius
        if not (-extent <= px < frame.shape[1]+extent and -extent <= py < frame.shape[0]+extent):
            continue
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
