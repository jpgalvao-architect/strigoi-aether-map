# SPDX-License-Identifier: GPL-3.0-only
from datetime import UTC, datetime
import logging

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QIcon
from app.ui.mascot import MascotWidget, AVATAR_PATH
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QStackedWidget, QVBoxLayout
from app.ui.localized_widgets import QFrame, QMainWindow, QPushButton, QWidget

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
from app.ui.icons import icon as ui_icon
from app.core.i18n import set_language, language, tr


class MainWindow(QMainWindow):
    def __init__(self, context, *, runtime=False):
        super().__init__()
        self.context = context
        set_language(context.prefs.ui_language)
        self.setWindowTitle("STRIGOI AETHER MAP • AION 2 Companion App")
        self.resize(1380, 900)
        self.setMinimumSize(1120, 780)
        icon = QIcon(str(AVATAR_PATH))
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
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(228)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 22, 16, 18)
        side.setSpacing(7)
        brand = MascotWidget(compact=True)
        brand.setFixedSize(74, 67)
        side.addWidget(brand, 0, Qt.AlignmentFlag.AlignHCenter)
        logo = label("S T R I G O I")
        logo.setStyleSheet("font-size: 23px; font-weight: 700;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side.addWidget(logo)
        subtitle = label("A E T H E R  M A P", "eyebrow")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side.addWidget(subtitle)
        game = label("AION 2 Companion App", "subtitle")
        game.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side.addWidget(game)
        side.addSpacing(24)
        self.nav = []
        entries=[('Início','home'),('Atlas','atlas'),('Coletas','gatherables'),('Cubos ocultos','cube'),('Eventos','events'),('Configurações','settings'),('Overlay','overlay'),('Sonar','sonar'),('Combate','combat'),('Donate','donate'),('Sobre','about')]
        for index, (text, name) in enumerate(entries):
            entry = QPushButton(text)
            entry.setIcon(ui_icon(name))
            entry.setIconSize(QSize(22,22))
            entry.setAccessibleName(text)
            entry.setObjectName("nav")
            entry.setCheckable(True)
            entry.setCursor(Qt.CursorShape.PointingHandCursor)
            entry.clicked.connect(lambda checked, number=index: self.navigate(number))
            side.addWidget(entry)
            self.nav.append(entry)
        side.addStretch()
        side.addWidget(label("Seu caderno de exploração.", "subtitle", True))
        side.addWidget(label(f"v{__version__}", "subtitle"))
        root_layout.addWidget(sidebar)
        main = QVBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        root_layout.addLayout(main, 1)
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
        self.pages = [self.dashboard, self.atlas, self.catalog, self.cubes, self.events, self.settings, self.overlay_page, self.sonar_page, self.combat_page, self.donate, self.about_page()]
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
        if runtime:
            QTimer.singleShot(0, self.combat.enable_automatic)

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
        self.stack.setCurrentIndex(index)
        for number, entry in enumerate(self.nav):
            entry.setChecked(number == index)

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
        layout.addWidget(page_header("Pequeno guardião. Grandes descobertas.", "STRIGOI AETHER MAP / AION 2 Companion App"))
        mascot = MascotWidget()
        mascot.setFixedSize(220, 200)
        layout.addWidget(mascot)
        frame, body = card()
        body.addWidget(label(f"STRIGOI AETHER MAP · {__version__}", "eyebrow"))
        body.addWidget(label("Seu companheiro de exploração em AION 2. Organize coletas, encontre locais de cubos e acompanhe os eventos do dia.", wrap=True))
        body.addWidget(label("Suas visitas e preferências ficam neste computador. Mapas e agenda funcionam offline.", "subtitle", True))
        body.addWidget(label("Os mapas indicam locais possíveis; confirme a presença dos objetos no jogo. A agenda usa o perfil selecionado em Eventos.", "subtitle", True))
        body.addWidget(label('Como o aplicativo funciona', 'eyebrow'))
        body.addWidget(label('O Strigoi funciona ao lado do AION 2. Os marcadores, o painel de eventos e os avisos do Sonar aparecem em janelas externas de overlay sobre o jogo. Para acompanhar o mapa, o app analisa a imagem da tela; o Sonar recebe o áudio do aplicativo pelo Windows. O Atlas e a agenda consultam dados locais.', 'subtitle', True))
        body.addWidget(label('Não injetamos código nas DLLs do jogo, não alteramos seus arquivos e não lemos sua memória. Os overlays são desenhados pelo próprio Strigoi, fora do processo do AION 2.', 'subtitle', True))
        body.addWidget(label('O módulo experimental de Combate também pode ler passivamente o tráfego recebido pela conexão do jogo, usando Npcap. Com a medição automática habilitada, a leitura começa ao abrir o Strigoi e aguarda o jogo. Você pode desativá-la nas Configurações. Pacotes brutos não são gravados nem enviados. O placar apresenta dano observado e identifica dados parciais.', 'subtitle', True))
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
        self.quick_menu.shutdown()
        self.combat_page.shutdown()
        self.combat.shutdown()
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
