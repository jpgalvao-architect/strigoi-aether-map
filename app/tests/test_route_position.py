# SPDX-License-Identifier: GPL-3.0-only
import cv2
import numpy as np
import pytest
from app.core.models import RouteSettings
from app.modules.routes.position import calibrate,locate,area_key
from app.modules.overlay.selection import CaptureArea
from app.modules.overlay.tracking import Registration
from app.modules.overlay.stencil import apply_route_stencil


def area(ratio=1):
    return CaptureArea(map_id='altgard',screen_name='test',screen_x=0,screen_y=0,screen_width=2560,
        screen_height=1440,pixel_ratio=ratio,x=2000,y=60,width=330,height=220,view_kind='minimap')


def frame(scale=1,rotation=0):
    image=np.full((220*scale,330*scale,3),35,np.uint8)
    shape=np.array([[0,-10],[7,9],[0,4],[-7,9]],np.float32)
    theta=np.deg2rad(rotation);matrix=np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
    vertices=np.rint((shape@matrix.T+[165,110])*scale).astype(np.int32)
    cv2.fillPoly(image,[vertices],(240,240,240))
    return image


@pytest.mark.parametrize('scale',[1,2])
def test_arrow_position_projects_physical_pixels_back_to_normalized_map(scale):
    image=frame(scale);a=area(scale)
    profile=RouteSettings(**calibrate(image,.5,.5),anchor_area=area_key(a))
    reg=Registration(np.array([[1000*scale,0,-335*scale],[0,1000*scale,-390*scale]],float),25,.95)
    result=locate(image,profile,reg,a)
    assert result and result[0].x==pytest.approx(.5,abs=.001) and result[0].y==pytest.approx(.5,abs=.003)
    assert 0<result[1]<=.006
    rotated=locate(frame(scale,90),profile,reg,a)
    assert rotated and rotated[0].x==pytest.approx(.5,abs=.004)
    assert locate(image,profile,reg,a.model_copy(update={'x':1999})) is None
    assert locate(np.full_like(image,35),profile,reg,a) is None
    assert locate(image,profile,Registration(np.zeros((2,3)),25,.95),a) is None


def test_non_arrow_cannot_be_calibrated_and_marker_ambiguity_fails_closed():
    image=frame();a=area();profile=RouteSettings(**calibrate(image,.5,.5),anchor_area=area_key(a))
    with pytest.raises(ValueError):calibrate(image,.1,.1)
    reg=Registration(np.array([[1000,0,-335],[0,1000,-390]],float),25,.95)
    # Identical second arrow close to the anchor must not be picked as the player.
    second=np.roll(image,19,axis=1)
    both=np.maximum(image,second)
    profile.anchor=(profile.anchor[0]+9.5/330,profile.anchor[1])
    assert locate(both,profile,reg,a) is None


def test_path_stencil_masks_strokes_without_erasing_the_bounding_rectangle():
    image=np.full((220,330,3),240,np.uint8);mask=np.full((220,330),255,np.uint8)
    reg=Registration(np.array([[330,0,0],[0,220,0]],float),25,.95)
    lines=[(((.1,.1),(.9,.1),(.9,.9)),False,True)]
    apply_route_stencil(image,mask,reg,lines,6,(.9,.9,2))
    assert mask[22,150]==0 and mask[110,297]==0
    assert mask[110,150]==255 and np.array_equal(image[110,150],[240]*3)
