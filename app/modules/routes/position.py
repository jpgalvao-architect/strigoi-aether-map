# SPDX-License-Identifier: GPL-3.0-only
"""User-confirmed minimap arrow geometry; no assumption about the ROI centre."""
import hashlib
import math
import json
from app.modules.routes.models import Vertex


def area_key(area):
    return hashlib.sha256(json.dumps(area.model_dump(mode='json'),sort_keys=True).encode()).hexdigest()


def contours(frame):
    import cv2
    import numpy as np
    low=frame.min(axis=2);high=frame.max(axis=2)
    mask=((low>=185)&(high-low<=55)).astype(np.uint8)*255
    rows,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    h,w=frame.shape[:2];factor=max(.5,min(w/330,h/220))
    result=[]
    for contour in rows:
        area=cv2.contourArea(contour);x,y,cw,ch=cv2.boundingRect(contour)
        if not 5*factor**2<=area<=750*factor**2 or not 4*factor<=max(cw,ch)<=42*factor:continue
        if not .25<cw/ch<4 or len(contour)<4:continue
        moments=cv2.moments(contour)
        if moments['m00']<=0:continue
        cx,cy=moments['m10']/moments['m00'],moments['m01']/moments['m00']
        result.append((contour,cx,cy,area,cw,ch))
    return result


def calibrate(frame,u,v):
    import cv2
    if not 0<=u<=1 or not 0<=v<=1:raise ValueError('Clique dentro do minimapa.')
    h,w=frame.shape[:2];x,y=u*w,v*h
    rows=[r for r in contours(frame) if cv2.pointPolygonTest(r[0],(x,y),True)>=-5]
    if len(rows)!=1:raise ValueError('Clique no centro da seta branca do seu personagem, sem outros ícones sobre ela.')
    contour,cx,cy,area,cw,ch=rows[0]
    contour=cv2.approxPolyDP(contour,.6,True).reshape(-1,2)
    if not 4<=len(contour)<=96:raise ValueError('A seta não está nítida. Aproxime o minimapa e tente novamente.')
    size=max(cw,ch)
    return dict(anchor=(cx/w,cy/h),arrow_shape=[((float(px)-cx)/size,(float(py)-cy)/size) for px,py in contour],arrow_area=area/(w*h))


def locate(frame,settings,registration,area):
    import cv2
    import numpy as np
    if settings.anchor is None or settings.anchor_area!=area_key(area) or len(settings.arrow_shape)<4:return None
    h,w=frame.shape[:2];u,v=settings.anchor
    template=np.array(settings.arrow_shape,dtype=np.float32).reshape(-1,1,2)
    matches=[]
    for contour,x,y,size,cw,ch in contours(frame):
        # Follow-mode minimaps keep the confirmed anchor in the same place.
        if abs(x/w-u)>.035 or abs(y/h-v)>.035:continue
        ratio=size/(w*h)
        if not settings.arrow_area*.6<=ratio<=settings.arrow_area*1.6:continue
        # Compare the same prepared outlines. Raw thin/ragged contours have very
        # different Hu moments from their approximation, even in the same frame.
        prepared=cv2.approxPolyDP(contour,.6,True)
        score=cv2.matchShapes(template,prepared,cv2.CONTOURS_MATCH_I1,0)
        if score<.10:matches.append((score,x,y,max(cw,ch)))
    matches.sort()
    if not matches or len(matches)>1 and matches[1][0]-matches[0][0]<.025:return None
    score,x,y,size=matches[0]
    matrix=np.vstack([registration.matrix,[0,0,1]])
    if not np.isfinite(matrix).all() or abs(np.linalg.det(matrix[:2,:2]))<1e-8:return None
    point=np.linalg.solve(matrix,np.array([x,y,1.]))
    if not np.isfinite(point).all() or not all(0<=p<=1 for p in point[:2]):return None
    scale=math.sqrt(abs(np.linalg.det(matrix[:2,:2])))
    radius=min(.006,max(.00002,max(4,size*.5)/scale))
    return Vertex(x=float(point[0]),y=float(point[1])),radius
