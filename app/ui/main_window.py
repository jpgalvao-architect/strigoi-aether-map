# SPDX-License-Identifier: GPL-3.0-only
from datetime import UTC, datetime
import logging

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QIcon
from app.ui.mascot import MascotWidget, AVATAR_PATH
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QStackedWidget, QVBoxLayout
from app.ui.localized_widgets import QFrame, QMainWindow, QPushButton, QToolButton, QWidget
from app.ui.identity import emblem_icon

from app import __version__
from app.infrastructure.storage import PACKAGE
from app.modules.events.service import occurrences
from app.modules.notifications.windows import DesktopNotifications
from app.modules.overlay.service import OverlayService
from app.ui.atlas_page import AtlasPage
from app.ui.catalog_page import CatalogPage
from app.ui.dashboard import Dashboard
from app.ui.event_panel import EventPanel
from app.ui.events_page import EventsPage
from app.ui.live_overlay_page import LiveOverlayPage
from app.ui.settings_page import SettingsPage
from app.ui.widgets import card, label, page_header
from app.ui.icons import navigation_icon as ui_icon
from app.core.i18n import set_language, language, tr


class MainWindow(QMainWindow):
    def __init__(self, context, *, runtime=False):
        super().__init__()
        self.context = context
        set_language(context.prefs.ui_language)
        self.setWindowTitle("Azphelumbra • AION 2 Companion")
        self.resize(1380, 900)
        self.setMinimumSize(1120, 780)
        icon = emblem_icon()
        self.setWindowIcon(icon)
        self.notifications = DesktopNotifications(icon, self)
        self.notifications.fallback.connect(lambda text: self.statusBar().showMessage(text, 20000))
        self.overlay = OverlayService(context)
        self.event_panel = EventPanel(context)
        from app.modules.sonar.service import SonarService
        from app.ui.sonar_page import SonarAlert, SonarPage
        from app.ui.donate_page import DonatePage
        self.sonar = SonarService(context)
        self.sonar_alert = SonarAlert(context)
        from app.modules.combat.service import CombatService
        from app.ui.combat_page import CombatPage
        self.combat = CombatService(context)
        from app.modules.pets.service import PetService
        from app.ui.pets_page import PetsPage
        self.pets = PetService(context, self.combat.feed)
        from app.modules.routine.service import RoutineService
        from app.ui.routine_page import RoutinePage
        self.routine = RoutineService(context,self.combat.feed)
        context.pets = self.pets
        self.pets.sync_map_preferences()
        self.pets.changed.connect(self.pets.sync_map_preferences)
        self.pets.changed.connect(context.changed.emit)
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(58)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(7, 14, 7, 12)
        side.setSpacing(6)
        brand = label(''); brand.setPixmap(emblem_icon().pixmap(38,38)); brand.setToolTip('Azphelumbra')
        side.addWidget(brand,0,Qt.AlignmentFlag.AlignHCenter)
        side.addSpacing(14)
        entries=[('Início','home'),('Atlas','atlas'),('Coletas','gatherables'),('Cubos ocultos','cube'),('Eventos','events'),('Configurações','settings'),('Overlay','overlay'),('Sonar','sonar'),('Combate','combat'),('Donate','donate'),('Sobre','about'),('Pets','pets'),('Rotina','routine')]
        self.page_indices = {name:index for index, (_, name) in enumerate(entries)}
        self.nav = [None]*len(entries)
        # Stable page identities preserve shortcuts and existing integrations.
        for index in [0,1,11,12,7,8,4,5,9,10,2,3,6]:
            text, name = entries[index]
            entry = QToolButton(); entry.setText(text)
            entry.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            entry.setIcon(ui_icon(name))
            entry.setIconSize(QSize(22,22))
            entry.setAccessibleName(text)
            entry.setObjectName("nav")
            entry.setFixedSize(42,42)
            entry.setToolTip(text)
            entry.setCheckable(True)
            entry.setCursor(Qt.CursorShape.PointingHandCursor)
            entry.clicked.connect(lambda checked, key=name: self.navigate(key))
            if index in (5,): side.addStretch()
            if index not in (2,3,6): side.addWidget(entry)
            self.nav[index] = entry
        root_layout.addWidget(sidebar)
        main = QVBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        root_layout.addLayout(main, 1)
        session_bar = QFrame(); session_bar.setObjectName('sessionBar')
        strip = QHBoxLayout(session_bar); strip.setContentsMargins(20,10,20,10)
        strip.addWidget(label('A Z P H E L U M B R A', 'eyebrow'))
        strip.addStretch(); strip.addWidget(label('AION 2 Companion','subtitle'))
        strip.addWidget(label(f'v{__version__}','subtitle')); main.addWidget(session_bar)
        self.banner = label("", "banner", True)
        main.addWidget(self.banner)
        self.stack = QStackedWidget()
        main.addWidget(self.stack, 1)
        self.dashboard = Dashboard(context, self.overlay, self.navigate)
        self.atlas = AtlasPage(context)
        self.catalog = CatalogPage(context)
        self.cubes = AtlasPage(context, cubes_only=True)
        self.events = EventsPage(context)
        self.settings = SettingsPage(context, self.notifications)
        self.overlay_page = LiveOverlayPage(context, self.overlay)
        self.sonar_page = SonarPage(context, self.sonar, self.sonar_alert)
        self.donate = DonatePage()
        self.combat_page = CombatPage(context, self.combat)
        self.pets_page = PetsPage(context, self.pets, self.show_pet_farm)
        self.routine_page = RoutinePage(context,self.routine)
        self.pages = [self.dashboard, self.atlas, self.catalog, self.cubes, self.events, self.settings, self.overlay_page, self.sonar_page, self.combat_page, self.donate, self.about_page(), self.pets_page,self.routine_page]
        for page in self.pages:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            self.stack.addWidget(scroll)
        self.navigate(0)
        context.changed.connect(self.refresh_banner)
        context.events_changed.connect(self.refresh_banner)
        context.error.connect(lambda message: self.statusBar().showMessage(message, 20000))
        self.refresh_banner()
        self.statusBar().showMessage("Pronto para explorar")
        self.alert_timer = QTimer(self)
        self.alert_timer.timeout.connect(self.check_alerts)
        self.alert_timer.start(1000)
        if context.messages:
            self.statusBar().showMessage(" / ".join(context.messages), 30000)
        from app.ui.quick_menu import QuickMenu
        self.quick_menu = QuickMenu(self, runtime=runtime)
        from app.ui.session_inspector import SessionInspector
        self.inspector = SessionInspector(self)
        root_layout.insertWidget(1,self.inspector)
        for index in (2,3,6):
            entry=self.nav[index]; entry.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            entry.setFixedSize(170,32); entry.setObjectName('sectionNav')
            self.inspector.explore.addWidget(entry)
        context.changed.connect(self.inspector.refresh)
        context.events_changed.connect(self.inspector.refresh)
        self.combat.changed.connect(self.inspector.refresh)
        self.sonar.active_changed.connect(self.inspector.refresh)
        self.overlay.status_changed.connect(self.inspector.refresh)
        self.alert_timer.timeout.connect(self.inspector.refresh)
        self.inspector.refresh()
        from app.ui.pet_panel import PetPanel
        self.pet_panel = PetPanel(context,self.pets,lambda: self.quick_menu.open_page('pets'))
        from app.ui.map_controls import MapControls
        self.map_controls=MapControls(self)
        from app.ui.routine_panel import RoutinePanel
        self.routine_panel=RoutinePanel(context,self.routine,lambda:self.quick_menu.open_page('routine'))
        self.overlay_visibility = None
        if runtime:
            from app.ui.overlay_visibility import OverlayVisibility
            self.overlay_visibility = OverlayVisibility(self)
            for window, role in [(self.overlay.window, 'map'), (self.event_panel, 'hud'),
                                 (self.combat_page.panel, 'hud'), (self.sonar_alert, 'alert'),
                                 (self.pet_panel, 'hud'),
                                 (self.routine_panel, 'hud'),
                                 (self.map_controls, 'map'),
                                 (self.quick_menu, 'hud'), (self.quick_menu.panel, 'hud')]:
                self.overlay_visibility.register(window, role)
            self.overlay_visibility.start()
            QTimer.singleShot(0, self.combat.enable_automatic)
            QTimer.singleShot(0, self.pets.enable_automatic)
            QTimer.singleShot(0, self.routine.enable_automatic)

    def refresh_banner(self):
        self.banner.setVisible(self.context.dataset.demo or self.context.feed.demo)
        if self.context.dataset.demo or self.context.feed.demo:
            areas = []
            if self.context.dataset.demo:
                areas.append("mapas e pontos fictícios")
            if self.context.feed.demo:
                areas.append("horários fictícios")
            self.banner.setText("DEMONSTRAÇÃO   /   " + " · ".join(areas) + "   /   Sem dados oficiais do jogo")
        else:
            self.banner.setText(self.context.dataset.coverage or "BASE LOCAL / Origem e compatibilidade não informadas")

    def navigate(self, index):
        if isinstance(index, str):
            index = self.page_indices[index]
        self.stack.setCurrentIndex(index)
        for number, entry in enumerate(self.nav):
            entry.setChecked(number == index)

    def show_pet_farm(self, pet_id):
        candidates = self.pets.farm.by_pet.get(pet_id, [])
        maps = {m.id for m in self.context.atlas_dataset.maps}
        site = next((s for s in candidates if s.map_id == self.context.prefs.map_id),
                    next((s for s in candidates if s.map_id in maps), None))
        if site is None:
            return
        self.context.prefs.map_id = site.map_id
        self.context.prefs.overlay.map_id = site.map_id
        self.context.prefs.pets.focus_id = pet_id
        self.context.prefs.pets.map_filter = 'all'
        self.context.prefs.disabled_categories.discard('pets')
        self.pets.sync_map_preferences()
        self.context.save()
        self.atlas.resource.setCurrentIndex(self.atlas.resource.findData(f'pet-{pet_id}'))
        self.navigate('atlas')

    def check_alerts(self):
        try:
            now = datetime.now(UTC)
            items = occurrences(self.context.feed.events, now, days=1)
            for item, lead in self.context.alerts.due(items, self.context.prefs.notifications, now):
                prefix = "[DEMO] " if self.context.feed.demo else ""
                self.notifications.notify(prefix + item.event.name, f"Começa em {lead} min • {item.event.region}")
        except (OSError, ValueError):
            logging.getLogger(__name__).exception("Falha ao processar alertas")
            self.statusBar().showMessage("Falha ao persistir alertas. Consulte os logs.", 10000)

    def about_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.addWidget(page_header("Pequeno guardião. Grandes descobertas.", "Azphelumbra / AION 2 Companion"))
        mascot = MascotWidget()
        mascot.setFixedSize(220, 200)
        layout.addWidget(mascot)
        frame, body = card()
        body.addWidget(label(f"Azphelumbra · {__version__}", "eyebrow"))
        body.addWidget(label("Seu companheiro de exploração em AION 2. Organize coletas, encontre locais de cubos e acompanhe os eventos do dia.", wrap=True))
        body.addWidget(label("Suas visitas e preferências ficam neste computador. Mapas e agenda funcionam offline.", "subtitle", True))
        body.addWidget(label("Os mapas indicam locais possíveis; confirme a presença dos objetos no jogo. A agenda usa o perfil selecionado em Eventos.", "subtitle", True))
        body.addWidget(label('Como o aplicativo funciona', 'eyebrow'))
        body.addWidget(label('O Azphelumbra funciona ao lado do AION 2. Os marcadores, o painel de eventos e os avisos do Sonar aparecem em janelas externas de overlay sobre o jogo. Para acompanhar o mapa, o app analisa a imagem da tela; o Sonar recebe o áudio do aplicativo pelo Windows. O Atlas e a agenda consultam dados locais.', 'subtitle', True))
        body.addWidget(label('Não injetamos código nas DLLs do jogo, não alteramos seus arquivos e não lemos sua memória. Os overlays são desenhados pelo próprio Azphelumbra, fora do processo do AION 2.', 'subtitle', True))
        body.addWidget(label('Combate, Pets e Rotina podem ler passivamente os dados recebidos pela conexão do jogo, usando Npcap. Cada módulo permite desativar sua leitura automática e todos compartilham a mesma captura. Pacotes brutos não são gravados nem enviados. O placar apresenta dano observado e identifica dados parciais. A Rotina guarda os saldos de Odyle recebidos do jogo por personagem.', 'subtitle', True))
        body.addWidget(label('Acessibilidade auditiva', 'eyebrow'))
        body.addWidget(label('O Sonar foi desenvolvido exclusivamente como recurso de acessibilidade para auxiliar pessoas surdas ou com deficiência auditiva a encontrar cubos ocultos com mais facilidade. Ele transforma uma pista sonora do jogo em um aviso visual, reduzindo a dependência da audição durante a exploração.', 'subtitle', True))
        body.addWidget(label('O aviso indica um som compatível com a referência e pode falhar. Não confirma a presença nem informa a posição exata do cubo.', 'subtitle', True))
        from app.ui.widgets import button
        body.addWidget(button('Fontes e créditos',self.open_credits))
        body.addWidget(button('Termos de uso e licença',self.open_terms))
        layout.addWidget(frame)
        layout.addStretch()
        return widget

    def open_credits(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        # Docs live beside the source package or the portable executable.
        import sys
        from pathlib import Path
        root=Path(sys.executable).parent if getattr(sys,'frozen',False) else PACKAGE.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(root/'docs/SOURCES.md')))

    def open_terms(self):
        from app.ui.localized_widgets import QDialog
        from PySide6.QtWidgets import QTextBrowser, QDialogButtonBox
        dialog=QDialog(self)
        dialog.setWindowTitle('Termos de uso e licença')
        dialog.resize(760,600)
        layout=QVBoxLayout(dialog)
        document=QTextBrowser()
        document.setPlainText((PACKAGE/f'assets/legal/terms-{language()}.txt').read_text(encoding='utf-8-sig'))
        layout.addWidget(document)
        from app.ui.widgets import button
        layout.addWidget(button('Fechar',dialog.accept))
        dialog.exec()

    def closeEvent(self, event):
        if self.overlay_visibility: self.overlay_visibility.shutdown()
        self.quick_menu.shutdown()
        self.pet_panel.shutdown()
        self.routine_panel.shutdown()
        self.map_controls.shutdown()
        self.combat_page.shutdown()
        self.combat.shutdown()
        self.pets.shutdown()
        self.routine.shutdown()
        self.combat.feed.shutdown()
        self.alert_timer.stop()
        self.overlay.stop()
        self.sonar.stop()
        self.sonar_alert.timer.stop()
        self.sonar_alert.close()
        self.overlay_page.shutdown()
        self.event_panel.shutdown()
        self.events.shutdown()
        self.context.save()
        self.notifications.tray.hide()
        super().closeEvent(event)
