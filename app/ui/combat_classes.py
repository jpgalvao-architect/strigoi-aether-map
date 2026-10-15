# SPDX-License-Identifier: GPL-3.0-only
"""Class ids follow the helper's GameClass contract; unknown values stay neutral."""
from app.core.i18n import tr
from app.ui.icons import icon
from app.infrastructure.storage import PACKAGE
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt
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


# Approved visual palette, kept separate from the unmodified official silhouettes.
CLASS_COLORS = {1:'#ed8c80', 2:'#cbbced', 3:'#6ed3c0', 4:'#8bdc85',
                5:'#8bbcf4', 6:'#f1a561', 7:'#e6cc7d', 8:'#dda2d9', 9:'#d8ae83'}


def class_color(job):
    return CLASS_COLORS.get(job, '#aaa8bd') if type(job) is int else '#aaa8bd'


@lru_cache(maxsize=64)
def colored_class_icon(job):
    """Tint the original alpha silhouette, cached once per class."""
    source = class_icon(job).pixmap(64,64)
    pixmap = QPixmap(source.size())
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.drawPixmap(0,0,source)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(class_color(job)))
    painter.end()
    return QIcon(pixmap)
