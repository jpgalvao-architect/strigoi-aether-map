# SPDX-License-Identifier: GPL-3.0-only
import numpy as np
import pytest
from app.modules.overlay.tracking import Registration
from app.modules.overlay.service import OverlayWindow


def test_visible_candidate_projection_uses_physical_pixels_and_rebuilds_after_filtering(qapp):
    window=OverlayWindow()
    window.resize(200,100)
    window.ratio=1.5
    window.markers=[(.25,.25,'#e6c576','cube'),(.75,.75,'#e6c576','cube')]
    registration=Registration(np.array([[600.,0,0],[0,300.,0]]),40,.9)
    try:
        visible=window.visible_markers(registration)
        assert len(visible)==1
        assert visible[0][:2]==pytest.approx((100,50))
        # The 2D projection is culled in logical window bounds after DPI conversion.
        window.markers=[(.125,.125,'#e6c576','cube')]
        assert window.visible_markers(registration)[0][:2]==pytest.approx((50,25))
        window.markers=[]
        assert window.visible_markers(registration)==[]
    finally:window.close()


def test_cached_symbol_is_native_resolution_and_invalidates_for_dpi_and_scale(qapp):
    window=OverlayWindow()
    try:
        window.ratio=1.5
        symbol=window.symbol('#e6c576','cube')
        assert symbol.devicePixelRatio()==1.5
        assert symbol.width()==36 and symbol.deviceIndependentSize().width()==24
        assert window.symbol('#e6c576','cube') is symbol
        from types import SimpleNamespace
        window.capture_area=SimpleNamespace(view_kind='minimap')
        compact=window.symbol('#e6c576','cube')
        assert compact is not symbol and compact.toImage()!=symbol.toImage()
        window.capture_area=None
        window.scale=2
        scaled=window.symbol('#e6c576','cube')
        assert scaled is not symbol and scaled.width()==66
        window.ratio=1
        assert window.symbol('#e6c576','cube').width()==44
    finally:window.close()
