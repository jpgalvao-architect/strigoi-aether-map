# SPDX-License-Identifier: GPL-3.0-only
"""Stationary overlays must sleep; frequency choices persist and apply live."""
from types import SimpleNamespace
import numpy as np
import pytest

from app.core.models import OverlaySettings
from app.modules.overlay.cadence import FramePacer
from app.modules.overlay.service import OverlayWindow
from app.modules.overlay.tracking import Registration


@pytest.mark.parametrize('hz',[30,60,75,120,144,165,240,360])
def test_selected_rate_is_a_ceiling_without_catchup_bursts(hz):
    pacer=FramePacer(hz)
    assert abs(sum(pacer.due(i/10000) for i in range(10000))-hz)<=1
    assert pacer.due(10) and not pacer.due(10)


def test_legacy_rate_preserved_and_lighter_new_defaults():
    assert OverlaySettings().render_hz==60
    assert OverlaySettings().capture_hz==30
    for hz in (30,75,120,144,165,240,360):
        original=OverlaySettings(render_hz=hz,capture_hz=60)
        assert OverlaySettings.model_validate_json(original.model_dump_json())==original


def test_duplicate_observations_do_not_restart_interpolation():
    from app.modules.overlay.cadence import SmoothRegistration
    smoother=SmoothRegistration()
    initial=Registration(np.array([[100.,0,0],[0,100.,0]]),40,.9)
    target=Registration(initial.matrix+np.array([[0,0,20],[0,0,0]]),40,.9)
    smoother.accept(initial,0)
    smoother.accept(target,1.)
    assert not smoother.accept(target,1.006)
    assert smoother.at(1.006).project(0,0)==pytest.approx((10,0))
    assert smoother.settled(1.013)


def test_static_map_sleeps_and_pan_filter_style_redraw_without_ghosts(qapp,monkeypatch):
    import app.modules.overlay.service as module
    now=[1.]
    monkeypatch.setattr(module.time,'perf_counter',lambda:now[0])
    window=OverlayWindow();window.resize(200,100)
    window.markers=[(.2,.2,'#e6c576','cube')]
    registration=Registration(np.array([[100.,0,0],[0,100.,0]]),40,.9)
    draws=[]
    monkeypatch.setattr(window,'update',lambda *args:draws.append(args))
    def frame():
        window.draw_timer.stop()  # Emulate the single-shot timer firing.
        now[0]+=.1
        window.schedule_frame()
    try:
        window.show()
        window.accept_registration(registration);frame()
        assert len(draws)==1 and not window.draw_timer.isActive()
        for _ in range(20):
            window.accept_registration(registration);frame()
        assert len(draws)==1 and not window.draw_timer.isActive()
        old=window.dirty_region
        shifted=Registration(registration.matrix+np.array([[0,0,20],[0,0,0]]),40,.9)
        window.accept_registration(shifted);frame()
        assert len(draws)==2
        assert draws[-1][0].contains(old.boundingRect())
        assert window._visible_markers[0][0]==40
        window.scale=2;window.invalidate_frame();frame()
        assert len(draws)==3
        previous=window.dirty_region
        window.markers=[];window.invalidate_frame();frame()
        assert len(draws)==4 and window._visible_markers==[]
        assert draws[-1][0].contains(previous.boundingRect())
        window.hide();window.accept_registration(registration)
        assert not window.draw_timer.isActive()
    finally:window.close()


def test_controls_visible_live_and_persisted_in_both_languages(qapp,tmp_path):
    from app.services.context import AppContext
    from app.ui.main_window import MainWindow
    from app.core.i18n import set_language
    context=AppContext(tmp_path)
    context.prefs.overlay.render_hz=240
    context.prefs.overlay.map_view='minimap'
    window=MainWindow(context)
    page=window.overlay_page
    try:
        window.show();window.navigate(6);qapp.processEvents()
        assert page.render_rate.isVisible() and page.capture_rate.isVisible()
        assert not page.advanced.isVisible() and page.render_rate.value()==240
        context.prefs.overlay.enabled=True
        worker=SimpleNamespace(capture_hz=60)
        window.overlay.worker=worker
        window.overlay.capture_area=object()
        page.refresh()
        assert page.capture_rate.isEnabled() and page.render_rate.isEnabled()
        page.render_rate.setValue(75);page.capture_rate.setValue(20)
        assert window.overlay.window.pacer.hz==75 and worker.capture_hz==20
        assert AppContext(tmp_path).prefs.overlay.render_hz==75
        assert AppContext(tmp_path).prefs.overlay.capture_hz==20
        set_language('en_US')
        assert page.render_rate.value()==75 and page.capture_rate.value()==20
        assert page.render_rate.toolTip().startswith('Marker drawing limit.')
        page.refresh_rates()
        assert page.rates.text().startswith('Visual limit: 75 Hz')
    finally:
        window.overlay.worker=None;window.overlay.capture_area=None
        context.prefs.overlay.enabled=False
        window.close();set_language('pt_BR')
