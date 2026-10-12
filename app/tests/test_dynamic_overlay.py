# SPDX-License-Identifier: GPL-3.0-only
from datetime import UTC, datetime
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest

from app.core.models import Dataset,EventFeed
from app.infrastructure.storage import PACKAGE,load_model
from app.modules.events.service import occurrences
from app.modules.overlay.selection import CaptureArea,find_monitor,physical_region
from app.modules.overlay.tracking import MapRegistration,Registration


@pytest.fixture(scope='module')
def terrain():
    image=cv2.imdecode(np.fromfile(PACKAGE/'assets/maps/altgard-world.webp',dtype=np.uint8),cv2.IMREAD_GRAYSCALE)
    return cv2.resize(image,(1500,1500),interpolation=cv2.INTER_AREA)


@pytest.fixture(scope='module')
def tracker(terrain):
    cv2.setRNGSeed(42)
    return MapRegistration(terrain)


def test_registration_follows_crop_pan_and_zoom(tracker,terrain):
    for crop in [(200,300,1000,900),(400,400,900,900),(500,550,800,800)]:
        x,y,w,h=crop
        frame=cv2.resize(terrain[y:y+h,x:x+w],(900,700),interpolation=cv2.INTER_LINEAR)
        # Real maps keep aspect ratio. Use a uniformly scaled viewport and clipped terrain.
        scale=900/w
        frame=cv2.resize(terrain,None,fx=scale,fy=scale,interpolation=cv2.INTER_LINEAR)
        frame=frame[round(y*scale):round(y*scale)+min(700,round(h*scale)),round(x*scale):round(x*scale)+900]
        registration=tracker.find(frame,minimum=18)
        assert registration is not None
        for mx,my in [(.5,.5),(.4,.6)]:
            px,py=registration.project(mx,my)
            assert px==pytest.approx((1500*mx-x)*scale,abs=4)
            assert py==pytest.approx((1500*my-y)*scale,abs=4)


def test_registration_rejects_closed_wrong_or_uniform_map(tracker):
    assert tracker.find(np.zeros((600,900),dtype=np.uint8)) is None
    random=np.random.default_rng(15).integers(0,255,(600,900),dtype=np.uint8)
    assert tracker.find(random) is None
    different=cv2.imdecode(np.fromfile(PACKAGE/'assets/maps/verteron-world.webp',dtype=np.uint8),cv2.IMREAD_GRAYSCALE)
    different=cv2.resize(different,(900,900),interpolation=cv2.INTER_AREA)
    assert tracker.find(different) is None


def test_geometry_negative_monitor_and_mixed_dpi():
    area=CaptureArea(map_id='altgard',screen_name='left',screen_x=-1920,screen_y=0,screen_width=1280,screen_height=720,
        pixel_ratio=1.5,x=100,y=50,width=500,height=400)
    monitors=[dict(left=-1920,top=0,width=1920,height=1080),dict(left=0,top=0,width=2560,height=1440)]
    monitor=find_monitor(area,monitors)
    assert physical_region(area,monitor)==dict(left=-1770,top=75,width=750,height=600)
    with pytest.raises(ValueError,match='mudou'):
        find_monitor(area,[dict(left=-1920,top=0,width=1280,height=720)])


def test_live_selection_stores_only_bounds(qapp,tmp_path):
    from app.services.context import AppContext
    from app.ui.main_window import MainWindow
    window=MainWindow(AppContext(tmp_path))
    page=window.overlay_page
    page.screen=qapp.primaryScreen()
    page.main_window=window
    page.was_visible=False
    page.accept_area(QRect(30,40,400,300))
    path=Path(window.context.prefs.overlay.capture_area)
    data=json.loads(path.read_text(encoding='utf-8'))
    assert (data['x'],data['y'],data['width'],data['height'])==(30,40,400,300)
    assert not list((tmp_path/'calibration').glob('*.png'))
    assert window.context.prefs.overlay.tracking_mode=='dynamic'
    window.close()


def test_screen_selection_escape_and_drag(qapp):
    from app.ui.screen_selection import ScreenSelection
    screen=qapp.primaryScreen()
    selector=ScreenSelection(screen)
    chosen=[];cancelled=[]
    selector.chosen.connect(chosen.append)
    selector.cancelled.connect(lambda:cancelled.append(True))
    selector.show()
    QTest.mousePress(selector,Qt.MouseButton.LeftButton,pos=QPoint(20,20))
    QTest.mouseRelease(selector,Qt.MouseButton.LeftButton,pos=QPoint(320,220))
    assert len(chosen)==1 and not cancelled
    again=ScreenSelection(screen)
    again.cancelled.connect(lambda:cancelled.append(True))
    again.show()
    QTest.keyClick(again,Qt.Key.Key_Escape)
    assert len(cancelled)==1


def test_overlay_hides_on_first_lost_registration(qapp,tmp_path):
    from app.services.context import AppContext
    from app.modules.overlay.service import OverlayService
    service=OverlayService(AppContext(tmp_path))
    class Worker:
        def set_exclusion(self,*args):pass
    service.worker=Worker()
    service.context.prefs.overlay.enabled=True
    registration=Registration(np.array([[600.,0,0],[0,600.,0]]),40,.9)
    service.on_registration(registration,{})
    assert not service.window.isVisible()
    service.on_registration(registration,{})
    assert service.window.isVisible()
    service.on_registration(None,{})
    assert not service.window.isVisible() and service.window.registration is None
    service.worker=None
    service.watchdog.stop()
    service.stop()


def test_sa_profile_uses_explicit_rule_zone():
    feed=load_model(PACKAGE/'data/profiles/reference-sa.json',EventFeed)
    event={e.id:e for e in feed.events}
    now=datetime(2026,10,12,tzinfo=UTC)
    siege=occurrences([event['reference-sa-artifact-siege']],now)[0]
    assert siege.starts_at==datetime(2026,10,12,21,tzinfo=UTC) # 18h SA, as published by this project
    reset=occurrences([event['reference-sa-daily-reset']],now)[0]
    assert reset.starts_at==datetime(2026,10,12,12,tzinfo=UTC) # 09h SA, project profile
    rift=occurrences([event['reference-sa-rift']],now)[0]
    assert rift.starts_at==now


def test_gathering_coords_match_licensed_source():
    dataset=load_model(PACKAGE/'data/dataset.json',Dataset)
    for name,count in [('altgard',2692),('verteron',2733)]:
        source=json.loads((PACKAGE.parent/f'data-sources/object-sets/{name}.json').read_text(encoding='utf-8'))
        nodes={n['id']:n for n in source['nodes'] if n['categoryId'].startswith('gathering-')}
        points=[p for p in dataset.points if p.map_id==name and p.id.startswith('gather-')]
        assert len(points)==count
        for point in points:
            node=nodes[point.id.removeprefix('gather-')]
            assert point.x==node['x']/100 and point.y==node['y']/100
            assert point.resource_id==node['categoryId'].removeprefix('gathering-')


def test_alternative_sa_profile_survives_restart(qapp,tmp_path):
    from app.services.context import AppContext
    context=AppContext(tmp_path)
    context.select_agenda_profile('curated-sa')
    assert len(context.feed.events)==9
    restarted=AppContext(tmp_path)
    assert restarted.prefs.agenda_profile=='curated-sa'
    assert restarted.feed==context.feed


def test_event_panel_does_not_reopen_when_app_saves_at_shutdown(qapp,tmp_path):
    from app.services.context import AppContext
    from app.ui.event_panel import EventPanel
    context=AppContext(tmp_path)
    context.prefs.overlay.events_panel=True
    panel=EventPanel(context)
    assert panel.isVisible()
    panel.shutdown()
    context.save()
    assert not panel.isVisible()
