# SPDX-License-Identifier: GPL-3.0-only
import cv2
import numpy as np
import pytest
from app.core.models import RouteSettings
from app.modules.routes.position import locate
from app.modules.overlay.selection import CaptureArea
from app.modules.overlay.tracking import Registration
from app.modules.overlay.stencil import apply_route_stencil


def area(ratio=1):
    return CaptureArea(map_id='altgard',screen_name='test',screen_x=0,screen_y=0,screen_width=2560,
        screen_height=1440,pixel_ratio=ratio,x=2000,y=60,width=330,height=220,view_kind='minimap')


@pytest.mark.parametrize('scale',[1,1.5,2])
def test_fixed_center_projects_to_map_without_manual_profile_or_arrow(scale):
    a=area(scale);shape=(round(220*scale),round(330*scale),3)
    reg=Registration(np.array([[1000*scale,0,-335*scale],[0,1000*scale,-390*scale]],float),25,.95)
    point,radius=locate(shape,reg,a)
    assert point.x==pytest.approx(.5) and point.y==pytest.approx(.5)
    assert 0<radius<=.006
    # The frame may contain a compass, quest icons or our own stop number.
    # Pixels and legacy arrow calibration are deliberately not inputs.
    assert locate(shape,reg,a)==(point,radius)
    assert locate(shape,None,a) is None
    assert locate(shape,reg,a.model_copy(update={'view_kind':'large'})) is None
    assert locate((40,40,3),reg,a) is None
    assert locate(shape,Registration(np.zeros((2,3)),25,.95),a) is None
    assert locate(shape,Registration(np.full((2,3),np.nan),25,.95),a) is None
    assert locate(shape,Registration(np.array([[1,0,10000],[0,1,10000]],float),25,.95),a) is None


def test_path_stencil_masks_strokes_without_erasing_the_bounding_rectangle():
    image=np.full((220,330,3),240,np.uint8);mask=np.full((220,330),255,np.uint8)
    reg=Registration(np.array([[330,0,0],[0,220,0]],float),25,.95)
    lines=[(((.1,.1),(.9,.1),(.9,.9)),False,True)]
    apply_route_stencil(image,mask,reg,lines,6,(.9,.9,2))
    assert mask[22,150]==0 and mask[110,297]==0
    assert mask[110,150]==255 and np.array_equal(image[110,150],[240]*3)
