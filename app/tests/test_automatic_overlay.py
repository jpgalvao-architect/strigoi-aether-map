# SPDX-License-Identifier: GPL-3.0-only
import numpy as np

from app.modules.overlay.automatic import AutomaticMapTracker
from app.modules.overlay.selection import CaptureArea
from app.modules.overlay.tracking import Registration


def areas(screen_name='test'):
    mini=CaptureArea(map_id='altgard',screen_name=screen_name,screen_x=0,screen_y=0,
        screen_width=1000,screen_height=700,pixel_ratio=1.,x=670,y=40,width=330,height=220,view_kind='minimap')
    full=mini.model_copy(update=dict(x=0,y=0,width=1000,height=700,view_kind='large'))
    return mini,full


def test_automatic_priority_and_return_to_minimap():
    mini,full=areas()
    registration=object()
    frames={'large':None,'minimap':registration}
    reads=[]
    class Tracker:
        def __init__(self):self.resets=0
        def observe(self,frame,now,**kwargs):return frame,'reference'
        def reset(self):self.resets+=1
    small,big=Tracker(),Tracker()
    automatic=AutomaticMapTracker(small,big,mini,full)
    def capture(area):
        reads.append(area.view_kind)
        return frames[area.view_kind],None
    assert automatic.observe(capture,0,minimum=18)[2]==mini
    reads.clear()
    automatic.observe(capture,.1,minimum=18)
    assert reads==['minimap']  # No full-screen capture at the minimap frame rate.
    frames['large']=registration;frames['minimap']=None
    result=automatic.observe(capture,.6,minimum=18)
    assert result[0] is registration and result[2]==full
    reads.clear()
    assert automatic.observe(capture,.62,minimum=18)[2]==full
    assert reads==['large']  # A missing minimap cannot hide the recognized full map.
    frames['large']=None;frames['minimap']=registration
    assert automatic.observe(capture,.64,minimum=18)[2]==mini
    assert small.resets==2
    frames['minimap']=None
    assert automatic.observe(capture,.66,minimum=18)[0] is None


def test_window_changes_geometry_and_requires_confirmation_in_each_mode(qapp,tmp_path):
    from app.services.context import AppContext
    from app.modules.overlay.service import OverlayService
    screen=qapp.primaryScreen();g=screen.geometry()
    mini=CaptureArea(map_id='altgard',screen_name=screen.name(),screen_x=g.x(),screen_y=g.y(),
        screen_width=g.width(),screen_height=g.height(),pixel_ratio=screen.devicePixelRatio(),
        x=100,y=40,width=330,height=220,view_kind='minimap')
    full=mini.model_copy(update=dict(x=0,y=0,width=g.width(),height=g.height(),view_kind='large'))
    service=OverlayService(AppContext(tmp_path))
    class Worker:
        def __init__(self):self.exclusions=[]
        def set_exclusion(self,*args):self.exclusions.append(args)
    worker=Worker();service.worker=worker
    service.context.prefs.overlay.enabled=True
    registration=Registration(np.array([[600.,0,0],[0,600.,0]]),40,.9)
    try:
        for area in [mini,full,mini]:
            service.on_registration(registration,{'area':area})
            assert not service.window.isVisible()
            service.on_registration(registration,{'area':area})
            assert service.window.isVisible()
            assert service.window.geometry().getRect()==(area.screen_x+area.x,area.screen_y+area.y,area.width,area.height)
            assert worker.exclusions[-1][2]==area.view_kind
            assert 'sem pontos desta camada' in service.status
        service.on_registration(None,{'area':mini})
        assert not service.window.isVisible() and service.window.registration is None
    finally:
        service.worker=None;service.stop();service.watchdog.stop()
