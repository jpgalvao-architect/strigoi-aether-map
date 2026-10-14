# SPDX-License-Identifier: GPL-3.0-only
"""Class ids follow the helper's GameClass contract; unknown values stay neutral."""
from app.core.i18n import tr
from app.ui.icons import icon
from app.infrastructure.storage import PACKAGE
from PySide6.QtGui import QIcon
from functools import lru_cache

# These are normalized enum values, not the game's raw wire ids.
CLASSES = {
    1: ("gladiator", "Gladiador"), 2: ("templar", "Templário"),
    3: ("ranger", "Patrulheiro"), 4: ("assassin", "Assassino"),
    5: ("sorcerer", "Feiticeiro"), 6: ("elementalist", "Elementalista"),
    7: ("cleric", "Clérigo"), 8: ("chanter", "Cantor"),
    9: ("brawler", "Lutador"),
}


@lru_cache(maxsize=16, typed=True)
def class_icon(job):
    entry = CLASSES.get(job) if type(job) is int else None
    path = PACKAGE/'assets/icons/classes'/f'{entry[0] if entry else "unknown"}.png'
    return QIcon(str(path)) if path.is_file() else icon("classes/unknown")


def class_label(job):
    entry = CLASSES.get(job) if type(job) is int else None
    return tr(entry[1] if entry else "Classe não identificada")
