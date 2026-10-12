# SPDX-License-Identifier: GPL-3.0-only
import cv2
import numpy as np
import pytest
from PySide6.QtCore import QRect

from app.infrastructure.storage import PACKAGE
from app.modules.overlay.tracking import MapRegistration,Registration
from app.modules.overlay.flow import FastMapTracker
from app.modules.overlay.cadence import FramePacer,SmoothRegistration


@pytest.fixture(scope='module')
def real_minimap():
    return cv2.imdecode(np.fromfile(PACKAGE/'tests/fixtures/user-minimap-terrain.png',dtype=np.uint8),cv2.IMREAD_COLOR)


@pytest.fixture(scope='module')
def minimap_reference():
    cv2.setRNGSeed(42)
    return MapRegistration(PACKAGE/'assets/maps/altgard-world.webp',minimap=True)


def test_user_minimap_recognized_with_distributed_support(minimap_reference,real_minimap):
    registration=minimap_reference.find(real_minimap,minimum=18)
    assert registration is not None and registration.inliers>=18
    # Independent investigation of the supplied terrain places this crop here.
    assert registration.matrix[0,0]==pytest.approx(9020,rel=.015)
    assert registration.matrix[0,2]==pytest.approx(-3665,abs=10)
    assert registration.matrix[1,2]==pytest.approx(-3510,abs=10)
    assert np.ptp(registration.support_points,axis=0)[0]>150


def test_minimap_rejects_uniform_or_unrelated_image(minimap_reference):
    assert minimap_reference.find(np.zeros((214,332,3),dtype=np.uint8),minimum=18) is None
    noise=np.random.default_rng(25).integers(0,255,(214,332,3),dtype=np.uint8)
    assert minimap_reference.find(noise,minimum=18) is None


def test_battlescar_minimap_with_quest_icons_and_vision_cone(minimap_reference):
    image=cv2.imdecode(np.fromfile(PACKAGE/'tests/fixtures/user-minimap-battlescar.png',dtype=np.uint8),cv2.IMREAD_COLOR)
    registration=minimap_reference.find(image,minimum=18)
    assert registration is not None and registration.inliers>=18
    assert registration.matrix[0,0]==pytest.approx(9020,rel=.015)
    assert registration.matrix[0,2]==pytest.approx(-5538,abs=12)
    assert registration.matrix[1,2]==pytest.approx(-2882,abs=12)
    assert np.ptp(registration.support_points,axis=0)[0]>200


def test_periodic_revalidation_with_marker_mask_needs_fresh_terrain(minimap_reference):
    image=cv2.imdecode(np.fromfile(PACKAGE/'tests/fixtures/user-minimap-battlescar.png',dtype=np.uint8),cv2.IMREAD_COLOR)
    tracker=FastMapTracker(minimap_reference)
    first,_=tracker.observe(image,0.,minimum=18)
    assert first is not None
    masked=image.copy();mask=np.full(image.shape[:2],255,dtype=np.uint8)
    cv2.circle(masked,(124,98),14,(128,128,128),-1)
    cv2.circle(mask,(124,98),17,0,-1)
    methods=[]
    for tick in range(1,14):
        registration,method=tracker.observe(masked,tick*.1,minimum=18,feature_mask=mask)
        assert registration is not None and registration.inliers>=18
        methods.append(method)
    assert methods.count('reference')>=2
    noise=np.random.default_rng(72).integers(0,255,image.shape,dtype=np.uint8)
    lost,_=tracker.observe(noise,2.,minimum=18,feature_mask=mask)
    assert lost is None and tracker.registration is None


def test_fast_visual_updates_follow_motion_and_stop_on_loss(minimap_reference,real_minimap):
    tracker=FastMapTracker(minimap_reference)
    first,method=tracker.observe(real_minimap,0.,minimum=18)
    assert first is not None and method=='reference'
    shifted=cv2.warpAffine(real_minimap,np.float32([[1,0,2],[0,1,1]]),(332,214))
    current,method=tracker.observe(shifted,.02,minimum=18)
    assert current is not None and method=='flow'
    a=first.project(.425,.402);b=current.project(.425,.402)
    assert b[0]-a[0]==pytest.approx(2,abs=.8)
    assert b[1]-a[1]==pytest.approx(1,abs=.8)
    lost,_=tracker.observe(np.zeros_like(real_minimap),.04,minimum=18)
    assert lost is None and tracker.registration is None


def test_240_target_skips_missed_frames_without_burst():
    pacer=FramePacer(240)
    redraws=sum(pacer.due(i/1000) for i in range(1000))
    assert 238<=redraws<=241
    assert pacer.due(4.)
    assert not pacer.due(4.)
    assert not pacer.due(4.001)


def test_interpolation_is_bounded_and_cleared_on_loss():
    smoother=SmoothRegistration()
    start=Registration(np.array([[100.,0,10],[0,100.,20]]),30,.9)
    finish=Registration(np.array([[100.,0,20],[0,100.,30]]),30,.9)
    smoother.accept(start,0)
    smoother.accept(finish,.1)
    assert smoother.at(.106).project(.5,.5)==pytest.approx((65,75))
    assert smoother.at(2.).project(.5,.5)==finish.project(.5,.5)
    smoother.clear()
    assert smoother.at(3.) is None


def test_full_map_start_uses_whole_screen_without_manual_selection(qapp,tmp_path,monkeypatch):
    from app.services.context import AppContext
    from app.ui.main_window import MainWindow
    from app.modules.overlay.selection import CaptureArea
    from app.infrastructure.storage import load_model
    window=MainWindow(AppContext(tmp_path))
    called=[]
    monkeypatch.setattr(window.overlay,'start',lambda:called.append(True))
    window.overlay_page.start()
    assert called
    area=load_model(__import__('pathlib').Path(window.context.prefs.overlay.capture_area),CaptureArea)
    assert area.x==0 and area.y==0 and area.width==area.screen_width and area.height==area.screen_height
    assert area.view_kind=='large'
    window.close()


def test_minimap_selection_is_separate_from_full_map(qapp,tmp_path):
    from app.services.context import AppContext
    from app.ui.main_window import MainWindow
    window=MainWindow(AppContext(tmp_path))
    page=window.overlay_page
    page.view_kind.setCurrentIndex(page.view_kind.findData('minimap'))
    page.screen=qapp.primaryScreen();page.main_window=window;page.was_visible=False
    page.accept_area(QRect(100,40,332,214))
    assert window.context.prefs.overlay.minimap_area
    assert not window.context.prefs.overlay.capture_area
    assert window.context.prefs.overlay.render_hz==240
    window.close()
