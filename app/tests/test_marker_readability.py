# SPDX-License-Identifier: GPL-3.0-only
from types import SimpleNamespace
import numpy as np
import pytest
from PySide6.QtGui import QImage
from app.modules.atlas.heights import height_levels, point_marker_shape
from app.modules.overlay.service import OverlayWindow, OverlayService
from app.modules.overlay.stencil import apply_stencil
from app.modules.overlay.tracking import Registration
from app.services.context import AppContext


def test_height_flags_are_only_supplied_levels_with_unchanged_coordinates():
    records=height_levels()
    assert len(records)==1241
    for level in ('up','down'):
        ident,record=next((k,v) for k,v in records.items() if v['level']==level)
        point=SimpleNamespace(id=ident,map_id=record['map_id'],resource_id='cube-spawns',x=record['x'],y=record['y'])
        assert point_marker_shape(point,'cube')=='cube-'+level
        point.x+=.01
        assert point_marker_shape(point,'cube')=='cube'
        point.x=record['x'];point.resource_id='cubes'
        assert point_marker_shape(point,'cube')=='cube'
    assert point_marker_shape(SimpleNamespace(resource_id='custom',id='missing'),'cube')=='cube'


@pytest.mark.parametrize('shape',['circle','diamond','leaf','wood','star','cube','cube-up','cube-down'])
def test_minimap_doubles_all_symbols_without_changing_projection(qapp,shape):
    window=OverlayWindow()
    try:
        window.resize(200,100);window.ratio=1.5
        window.capture_area=SimpleNamespace(view_kind='minimap')
        window.markers=[(.25,.25,'#e6c576',shape)]
        assert window.effective_scale()==2
        pixmap=window.symbol('#e6c576',shape)
        assert pixmap.devicePixelRatio()==1.5
        registration=Registration(np.array([[600.,0,0],[0,300.,0]]),40,.9)
        assert window.visible_markers(registration)[0][:2]==pytest.approx((100,50))
        assert pixmap.deviceIndependentSize().width()/2<=window.paint_radius()
        window.capture_area=SimpleNamespace(view_kind='large')
        assert window.effective_scale()==1
        assert window.visible_markers(registration)[0][:2]==pytest.approx((100,50))
    finally:window.close()


@pytest.mark.parametrize('shape',['cube-up','cube-down','leaf','wood','star','diamond','circle','cube'])
@pytest.mark.parametrize('mini,ratio,scale',[(True,1.5,1),(True,2,3),(False,1.5,1)])
def test_stencil_covers_the_actual_painted_symbol_including_arrow(qapp,tmp_path,shape,mini,ratio,scale):
    service=OverlayService(AppContext(tmp_path))
    worker=SimpleNamespace(set_exclusion=lambda registration,points,*args:setattr(worker,'points',points))
    service.worker=worker
    window=service.window
    window.capture_area=SimpleNamespace(view_kind='minimap' if mini else 'large')
    window.ratio=ratio;window.scale=scale
    window.markers=[(0,0,'#e6c576',shape)]
    registration=Registration(np.array([[0.,0,150],[0,0,150]]),40,.9)
    try:
        service.set_exclusion(registration,0)
        pixmap=window.symbol('#e6c576',shape)
        image=pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        rgba=np.frombuffer(image.constBits(),dtype=np.uint8).reshape(image.height(),image.bytesPerLine())
        alpha=rgba[:,:image.width()*4].reshape(image.height(),image.width(),4)[:,:,3]
        frame=np.zeros((300,300,3),dtype=np.uint8);mask=np.full((300,300),255,np.uint8)
        apply_stencil(frame,mask,registration,worker.points)
        x,y=150-image.width()//2,150-image.height()//2
        patch=mask[y:y+image.height(),x:x+image.width()]
        assert patch.shape==alpha.shape
        missing=np.argwhere((alpha>15)&(patch!=0))
        assert len(missing)==0, f'Unmasked painted pixels: {missing[:8].tolist()}, count={len(missing)}'
        assert mask[20,20]==255
    finally:
        service.worker=None;service.stop();service.watchdog.stop();window.close()
