# SPDX-License-Identifier: GPL-3.0-only
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.core.models import Dataset, EventFeed
from app.infrastructure.storage import PACKAGE, load_model


@pytest.fixture
def dataset():
    return load_model(PACKAGE / "tests/fixtures/demo-dataset.json", Dataset)


@pytest.fixture
def feed():
    return load_model(PACKAGE / "tests/fixtures/demo-events.json", EventFeed)


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    from app.ui.theme import apply_theme
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    yield app
