# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from app.infrastructure.storage import atomic_json
from app.core.models import Preferences
from app.services.context import AppContext
from app.ui.main_window import MainWindow


def test_all_pages_and_shared_preferences(qapp, tmp_path):
    context = AppContext(tmp_path)
    window = MainWindow(context)
    window.show()
    qapp.processEvents()
    assert window.overlay.worker is None
    assert not window.overlay.window.isVisible()
    for index in range(window.stack.count()):
        window.navigate(index)
        qapp.processEvents()
        assert window.stack.currentIndex() == index
    window.navigate(1)
    checkbox = window.atlas.checks["traces"]
    QTest.mouseClick(checkbox, Qt.MouseButton.LeftButton)
    qapp.processEvents()
    assert "traces" in context.prefs.disabled_categories
    assert not window.cubes.context.prefs.overlay.enabled
    point = context.dataset.cubes[0]
    window.cubes.select_point(point)
    window.cubes.toggle_visit()
    assert point.id in context.prefs.visited
    window.atlas.search.setText("nonexistent material")
    assert len(window.atlas.view._markers) == 0
    window.atlas.search.clear()
    window.atlas.view.zoom(2)
    assert window.atlas.view.zoom_level == 2
    window.atlas.view.fit_map()
    assert window.atlas.view.zoom_level == 0
    window.close()
    reloaded = AppContext(tmp_path)
    assert "traces" in reloaded.prefs.disabled_categories
    assert point.id in reloaded.prefs.visited


def test_capture_consent_resets_at_start(qapp, tmp_path):
    prefs = Preferences()
    prefs.overlay.enabled = True
    atomic_json(tmp_path / "preferences.json", prefs)
    context = AppContext(tmp_path)
    assert not context.prefs.overlay.enabled


def test_invalid_import_preserves_data(qapp, tmp_path):
    context = AppContext(tmp_path)
    previous = context.dataset
    source = tmp_path / "bad.json"
    source.write_text('{"maps": []}', encoding="utf-8")
    import pytest
    with pytest.raises(ValueError):
        context.import_dataset(source)
    assert context.dataset is previous


def test_import_copies_external_map_and_stops_overlay(qapp, tmp_path):
    from PySide6.QtGui import QColor, QImage
    context = AppContext(tmp_path / "user-data")
    image_path = tmp_path / "custom.png"
    image = QImage(400, 300, QImage.Format.Format_RGB32)
    image.fill(QColor("#314054"))
    assert image.save(str(image_path))
    dataset = context.dataset.model_copy(deep=True)
    dataset.maps[0].image = "custom.png"
    source = tmp_path / "custom.json"
    atomic_json(source, dataset)
    context.prefs.overlay.enabled = True
    context.import_dataset(source)
    copied = Path(context.dataset.maps[0].image)
    assert copied != image_path and copied.is_file()
    assert copied.read_bytes() == image_path.read_bytes()
    assert not context.prefs.overlay.enabled


def test_overlay_disappears_and_stale_watchdog(qapp, tmp_path, monkeypatch):
    import time
    from app.modules.overlay.service import OverlayService
    context = AppContext(tmp_path)
    service = OverlayService(context)
    context.prefs.overlay.enabled = True
    service.window.show()
    service.on_detection(False, .1, {})
    assert not service.window.isVisible()
    service.window.show()
    service.worker = object()
    service.last_result = time.monotonic()-3
    service.check_stale()
    assert not service.window.isVisible()
    service.worker = None
    service.stop()
    service.watchdog.stop()
