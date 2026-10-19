# SPDX-License-Identifier: GPL-3.0-only
"""Project the fixed center of a recognized follow-mode minimap into the atlas."""
import math
from app.modules.routes.models import Vertex


def locate(frame_shape,registration,area):
    import numpy as np
    # A full map can be panned. Its center must never become a player position.
    if area.view_kind!='minimap' or registration is None or len(frame_shape)<2:return None
    h,w=frame_shape[:2]
    if h<=0 or w<=0 or abs(w-area.width*area.pixel_ratio)>2 or abs(h-area.height*area.pixel_ratio)>2:return None
    matrix=np.vstack([registration.matrix,[0,0,1]])
    if not np.isfinite(matrix).all() or abs(np.linalg.det(matrix[:2,:2]))<1e-8:return None
    point=np.linalg.solve(matrix,np.array([w/2,h/2,1.]))
    if not np.isfinite(point).all() or not all(0<=p<=1 for p in point[:2]):return None
    scale=math.sqrt(abs(np.linalg.det(matrix[:2,:2])))
    radius=min(.006,max(.00002,8*area.pixel_ratio/scale))
    return Vertex(x=float(point[0]),y=float(point[1])),radius
