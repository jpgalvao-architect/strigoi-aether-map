# SPDX-License-Identifier: GPL-3.0-only
"""Favorite collection progress; no unverified live-NPC or distance claims."""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout

from app.core.i18n import language, tr
from app.infrastructure.storage import PACKAGE
from app.ui.icons import icon
from app.ui.localized_widgets import QFrame, QToolButton, QWidget
from app.ui.overlay_visibility import OverlayVisibilityMixin
from app.ui.pets_page import progress_caption
from app.ui.widgets import label
from app.ui.hud import HudSurface


class PetPanel(HudSurface):
    def __init__(self, context, service, open_collection):
        flags = (Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
                 Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
        super().__init__(None, flags)
        self.context, self.service = context, service
        self.open_collection = open_collection
        self.drag = None
        self.closed = False
        self.initial_position = False
        self.saved_position = context.prefs.pets.panel_position
        self.structure = None
        self.setWindowTitle('Azphelumbra · Pets')
        self.setObjectName('petPanel')
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(250)
        self.setStyleSheet('''
            QFrame#petPanel{background:transparent;border:0;}
            QFrame#petHeader{background:transparent;border:0;border-bottom:1px solid #30303e;}
            QFrame#petRow{background:transparent;border:0;border-bottom:1px solid #30303e;}
            QLabel{border:0;color:#edf4fb;background:transparent;font-size:11px;}
            QLabel#petProgress{color:#c2b2fc;font-size:10px;}
            QToolButton{background:transparent;border:0;padding:3px;color:#afc4d4;}
            QToolButton:hover{background:#293b49;}
            QScrollArea,QWidget#petList{border:0;background:transparent;}
        ''')
        layout = QVBoxLayout(self); layout.setContentsMargins(1,1,1,3); layout.setSpacing(2)
        header = QFrame(); header.setObjectName('petHeader')
        top = QHBoxLayout(header); top.setContentsMargins(6,2,3,2); top.setSpacing(3)
        picture = label(''); picture.setPixmap(icon('pets').pixmap(16,16)); top.addWidget(picture)
        self.heading = label('Pets favoritos'); top.addWidget(self.heading,1)
        self.lock = QToolButton(); self.lock.setFixedSize(22,22)
        self.lock.clicked.connect(self.toggle_locked); top.addWidget(self.lock)
        self.expand = QToolButton(); self.expand.setFixedSize(22,22)
        self.expand.clicked.connect(self.toggle_expanded); top.addWidget(self.expand)
        close = QToolButton(); close.setFixedSize(22,22); close.setIcon(icon('close'))
        close.setToolTip('Fechar painel'); close.clicked.connect(self.dismiss); top.addWidget(close)
        layout.addWidget(header)
        self.scroller = QScrollArea(); self.scroller.setWidgetResizable(True)
        self.scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget = QWidget(); self.list_widget.setObjectName('petList')
        self.rows = QVBoxLayout(self.list_widget); self.rows.setContentsMargins(4,0,4,0); self.rows.setSpacing(0)
        self.scroller.setWidget(self.list_widget); layout.addWidget(self.scroller)
        self.empty = label('Favorite um pet na coleção para acompanhá-lo aqui.', '', True)
        self.empty.setContentsMargins(7,5,7,5); layout.addWidget(self.empty)
        footer = QHBoxLayout(); footer.setContentsMargins(6,0,4,0)
        self.count = label(''); footer.addWidget(self.count,1)
        open_button = QToolButton(); open_button.setText('Abrir coleção')
        open_button.clicked.connect(open_collection); footer.addWidget(open_button); layout.addLayout(footer)
        for widget in (header,picture,self.heading): widget.installEventFilter(self)
        context.changed.connect(self.refresh); service.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        if self.closed or not self.context.prefs.pets.panel_visible:
            self.hide(); return
        prefs = self.context.prefs.pets
        pets = self.service.store.select(favorites=True)
        key = (self.service.store.collection.active_profile,
               tuple((p.id,self.service.entry(p.id).model_dump_json()) for p in pets),
               tuple(self.service.progress_status(p.id) for p in pets),
               tuple(self.service.gain_count(p.id) for p in pets),
               prefs.panel_expanded,language())
        if key != self.structure:
            self.structure = key
            while self.rows.count():
                item = self.rows.takeAt(0)
                widget=item.widget()
                if widget:widget.hide();widget.setParent(None);widget.deleteLater()
            for pet in pets:
                entry = self.service.entry(pet.id)
                row = QFrame(); row.setObjectName('petRow'); row.setFixedHeight(55)
                box = QHBoxLayout(row); box.setContentsMargins(3,4,3,4); box.setSpacing(7)
                portrait = label(''); portrait.setFixedSize(43,43)
                portrait.setPixmap(QPixmap(str(PACKAGE/'assets'/pet.portrait)).scaled(
                    43,43,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
                box.addWidget(portrait)
                copy = QVBoxLayout(); copy.setSpacing(2)
                name = label(pet.name); name.setToolTip(pet.name)
                name.setText(name.fontMetrics().elidedText(pet.name,Qt.TextElideMode.ElideRight,175))
                copy.addWidget(name)
                progress = entry.progress
                caption = tr(progress_caption(entry)) if progress and progress.level is not None else ''
                if progress and progress.souls is not None:
                    caption += (' · ' if caption else '')+(tr('{almas}/{total} almas').format(almas=progress.souls,total=progress.required)
                        if progress.required else tr(f'{progress.souls} almas'))
                state=self.service.progress_status(pet.id)
                gains=self.service.gain_count(pet.id)
                if gains and state not in ('Sincronizado','Leitura desta captura'):
                    caption=tr('+{count} almas nesta captura').format(count=gains)
                elif caption and state not in ('Sincronizado','Leitura desta captura'):
                    caption+=' · '+tr({'Registro manual':'Manual','Registro salvo':'Salvo'}.get(state,'Aguardando leitura'))
                if not caption:caption=tr('Abra os detalhes no jogo')
                detail = label(caption,'petProgress')
                total=tr(progress_caption(entry))
                if progress and progress.souls is not None:total+=' · '+tr('{count} almas').format(count=progress.souls)
                detail.setToolTip(total+'\n'+tr(state)+'\n'+tr('Os ganhos desta captura não são o total da coleção.'))
                if gains:detail.setToolTip(detail.toolTip()+'\n'+tr('+{count} almas nesta captura').format(count=gains))
                copy.addWidget(detail); box.addLayout(copy,1)
                self.rows.addWidget(row)
            self.rows.addStretch()
        self.scroller.setVisible(bool(pets)); self.empty.setVisible(not pets)
        self.scroller.setFixedHeight(55*min(len(pets),3 if prefs.panel_expanded else 1))
        self.count.setText(f'{len(pets)} favoritos')
        self.expand.setIcon(icon('chevron-up' if prefs.panel_expanded else 'chevron-down'))
        self.expand.setToolTip('Recolher painel' if prefs.panel_expanded else 'Expandir favoritos')
        self.lock.setIcon(icon('lock' if prefs.panel_locked else 'unlock'))
        self.lock.setToolTip('Destravar posição' if prefs.panel_locked else 'Travar posição')
        self.setWindowOpacity(prefs.panel_opacity)
        if prefs.panel_position != self.saved_position:
            self.saved_position = prefs.panel_position; self.initial_position = False
        self.adjustSize(); self.fit_screen(); self.show()

    def fit_screen(self):
        screen = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        if not self.initial_position:
            saved = self.context.prefs.pets.panel_position
            if saved is not None:
                self.move(*saved)
                screen = QGuiApplication.screenAt(self.geometry().center()) or screen
            else:
                area = screen.availableGeometry(); self.move(area.left()+22,area.top()+180)
            self.initial_position = True
        area = screen.availableGeometry()
        self.move(max(area.left(),min(self.x(),area.right()-self.width()+1)),
                  max(area.top(),min(self.y(),area.bottom()-self.height()+1)))

    def toggle_expanded(self):
        prefs = self.context.prefs.pets; prefs.panel_expanded = not prefs.panel_expanded
        self.context.save()

    def toggle_locked(self):
        prefs = self.context.prefs.pets; prefs.panel_locked = not prefs.panel_locked
        self.context.save()

    def eventFilter(self, watched, event):
        if self.context.prefs.pets.panel_locked:
            return super().eventFilter(watched,event)
        if event.type() == QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
            self.drag = event.globalPosition().toPoint()-self.pos(); return True
        if event.type() == QEvent.Type.MouseMove and self.drag is not None:
            self.move(event.globalPosition().toPoint()-self.drag); return True
        if event.type() == QEvent.Type.MouseButtonRelease and self.drag is not None:
            self.drag = None; self.fit_screen()
            self.context.prefs.pets.panel_position = (self.x(),self.y()); self.context.save(); return True
        return super().eventFilter(watched,event)

    def dismiss(self):
        self.context.prefs.pets.panel_visible = False; self.context.save()

    def shutdown(self):
        self.closed = True; self.hide(); self.close()
