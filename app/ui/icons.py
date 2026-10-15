# SPDX-License-Identifier: GPL-3.0-only
"""Original vector icons shared by navigation, resource lists and event cards."""
from functools import lru_cache
from app.infrastructure.storage import PACKAGE
from PySide6.QtGui import QIcon, QPainter, QPixmap, QColor
from PySide6.QtCore import Qt


@lru_cache(maxsize=32)
def icon(name):
    path=PACKAGE/'assets/icons'/f'{name}.svg'
    return QIcon(str(path if path.is_file() else PACKAGE/'assets/icons/events.svg'))


def event_icon(event):
    text=(event.kind+' '+event.id+' '+event.name).casefold()
    for keys,name in [(['reset'],'reset'),(['shugo'],'shugo'),(['fenda','rift'],'rift'),
                      (['executor','nahma','guardian','chefe','boss'],'boss'),
                      (['cerco','siege'],'siege'),(['invas','invasion'],'invasion')]:
        if any(key in text for key in keys):return name
    return 'events'


@lru_cache(maxsize=32)
def navigation_icon(name):
    source=icon(name).pixmap(64,64)
    tinted=QPixmap(source.size());tinted.fill(Qt.GlobalColor.transparent)
    painter=QPainter(tinted);painter.drawPixmap(0,0,source)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(),QColor('#c2b2fc'));painter.end()
    return QIcon(tinted)
