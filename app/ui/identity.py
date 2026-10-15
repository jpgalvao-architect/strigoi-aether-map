# SPDX-License-Identifier: GPL-3.0-only
"""Vigília identity. Storage and protocol names remain stable across upgrades."""
from app.infrastructure.storage import PACKAGE
from PySide6.QtGui import QIcon

PRODUCT = 'Azphelumbra'
EMBLEM = PACKAGE / 'assets/azphelumbra-emblem.png'


def emblem_icon():
    return QIcon(str(EMBLEM))
