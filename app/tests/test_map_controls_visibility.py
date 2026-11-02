# SPDX-License-Identifier: GPL-3.0-only
from types import SimpleNamespace
import numpy as np
from app.services.context import AppContext
from app.ui.main_window import MainWindow
from app.ui.overlay_visibility import OverlayVisibility
from app.modules.overlay.tracking import Registration


def test_chips_require_confirmed_minimap_and_hide_with_menus_and_map_loss(qapp,tmp_path):
    main=MainWindow(AppContext(tmp_path));overlay=main.overlay;controls=main.map_controls
    gate=OverlayVisibility(main)
    gate.register(overlay.window,'map');gate.register(controls,'hud');gate.set_context(True)
    try:
        main.context.prefs.overlay.enabled=True;overlay.worker=object()
        controls.refresh();assert not controls.isVisible()
        overlay.capture_area=SimpleNamespace(view_kind='minimap')
        overlay.window.accept_registration(Registration(np.array([[100.,0,0],[0,100.,0]]),40,.9))
        overlay.matches=1;controls.refresh();assert not controls.isVisible()
        overlay.matches=2;controls.refresh();assert controls.isVisible()
        before=main.context.prefs.model_dump()
        for mode in ['menu','map']:
            gate.set_context(True,mode);controls.refresh();assert not controls.isVisible()
            gate.set_context(True,'play');assert controls.isVisible()
        gate.set_context(False);controls.refresh();assert not controls.isVisible()
        gate.set_context(True);assert controls.isVisible()
        assert main.context.prefs.model_dump()==before
        overlay.capture_area=SimpleNamespace(view_kind='large');controls.refresh()
        assert not controls.isVisible()
        overlay.capture_area=SimpleNamespace(view_kind='minimap');controls.refresh()
        assert controls.isVisible()
        controls.layers.menu_widget.show();assert controls.layers.menu_widget.isVisible()
        overlay.window.clear_registration();controls.refresh()
        assert not controls.isVisible() and not controls.layers.menu_widget.isVisible()
    finally:
        overlay.worker=None;gate.shutdown();main.close()
