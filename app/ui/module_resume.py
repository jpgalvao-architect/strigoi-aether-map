# SPDX-License-Identifier: GPL-3.0-only
"""Restore requested modules when the game becomes available; previews never run this."""
import time
from PySide6.QtCore import QObject,QTimer
from app.modules.sonar.capture import processes
from app.modules.overlay.foreground import GAME_NAMES


class ModuleResume(QObject):
    def __init__(self,main):
        super().__init__(main)
        self.main=main;self.closed=False;self.next_map=0.;self.next_sonar=0.
        self.timer=QTimer(self);self.timer.setInterval(5000)
        self.timer.timeout.connect(self.refresh);self.timer.start()
        QTimer.singleShot(0,self.refresh)

    def refresh(self):
        if self.closed:return
        main=self.main;prefs=main.context.prefs;now=time.monotonic()
        maps=prefs.overlay.resume_enabled and main.overlay.worker is None
        sonar=prefs.sonar_resume and not main.sonar.active
        if not maps and not sonar:return
        try:games=[p for p in processes() if p.name.casefold() in GAME_NAMES]
        except OSError:return
        if not games:
            if maps:main.overlay.set_status('Aguardando o jogo para retomar o overlay')
            if sonar:main.sonar.set_status('Aguardando o jogo para retomar o sonar')
            return
        page=main.overlay_page
        if maps and now>=self.next_map and not page._selection_pending:
            self.next_map=now+15
            if prefs.overlay.map_view=='minimap' and not page.minimap_ready():
                main.overlay.set_status('Selecione o minimapa para retomar o overlay')
            else:page.start()
        if sonar and now>=self.next_sonar and main.sonar.available:
            self.next_sonar=now+15
            preferred=prefs.sonar_process_name.casefold()
            game=next((p for p in games if p.name.casefold()==preferred),games[0])
            main.sonar_page.refresh_processes()
            index=main.sonar_page.process.findData(game.pid)
            if index>=0:
                main.sonar_page.process.setCurrentIndex(index)
                main.sonar_page.start()
        main.quick_menu.refresh()

    def shutdown(self):
        self.closed=True;self.timer.stop()
