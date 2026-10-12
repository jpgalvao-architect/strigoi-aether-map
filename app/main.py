# SPDX-License-Identifier: GPL-3.0-only
"""Entrypoint. --smoke-test exercises startup and exits without any capture."""
import argparse
import logging
from pathlib import Path
import sys

from PySide6.QtCore import QLockFile, QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen
from app.ui.localized_widgets import QMessageBox

from app.bootstrap.logging_setup import configure_logging
from app.infrastructure.storage import PACKAGE, user_data_dir
from app.services.context import AppContext
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme
from app.core.i18n import tr, set_language


def main() -> int:
    parser = argparse.ArgumentParser(description="STRIGOI AETHER MAP")
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--screenshot", type=Path, help="Save the rendered app window, without capturing the desktop")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Strigoi Aether Map")
    app.setOrganizationName("Strigoi")
    apply_theme(app)
    directory = user_data_dir()
    configure_logging(directory)
    lock = QLockFile(str(directory / "app.lock"))
    if not lock.tryLock(0):
        QMessageBox.information(None, "Strigoi já está aberto", "Uma instância está usando este diretório de dados.")
        return 0
    splash = None
    try:
        context = AppContext(directory)
        set_language(context.prefs.ui_language)
    except Exception:
        logging.exception('Falha ao iniciar aplicação')
        lock.unlock()
        if args.smoke_test:raise
        QMessageBox.critical(None,'Não foi possível iniciar',f"Consulte o log em {directory / 'logs/strigoi.log'}")
        return 1
    if not args.smoke_test:
        pixmap = QPixmap(500, 280)
        pixmap.fill(Qt.GlobalColor.transparent)
        from PySide6.QtGui import QColor, QPainter
        from app.ui.mascot import MASCOT_PATH
        pixmap.fill(QColor("#191d2e"))
        painter = QPainter(pixmap)
        mascot = QPixmap(str(MASCOT_PATH)).scaled(180, 165, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap((500-mascot.width())//2, 10, mascot)
        painter.end()
        splash = QSplashScreen(pixmap)
        splash.showMessage(tr("STRIGOI AETHER MAP\nPreparando seu caderno de exploração…"), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, Qt.GlobalColor.white)
        splash.show()
        app.processEvents()
    try:
        window = MainWindow(context)
        window.show()
        if splash:
            splash.finish(window)
        def capture_window():
            if args.screenshot:
                args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                if not window.grab().save(str(args.screenshot)):
                    raise OSError("Não foi possível salvar screenshot da janela")
        if args.smoke_test:
            def smoke():
                try:
                    for index in range(window.stack.count()):
                        window.navigate(index)
                        app.processEvents()
                    window.navigate(0)
                    app.processEvents()
                    # Exercise frozen audio assets and imports without opening a stream.
                    import numpy as np
                    import subprocess
                    from app.modules.sonar.capture import HELPER
                    from app.modules.sonar.detector import CubeDetector
                    with np.load(PACKAGE/'assets/sonar/cube-reference.npz',allow_pickle=False) as reference:
                        assert int(reference['sample_rate'])==48000
                        detector=CubeDetector(reference['pcm'])
                        assert detector.match(reference['pcm'][:int(detector.rate*detector.window_seconds)]) is not None
                    assert not window.sonar.active and window.sonar.worker is None
                    assert window.combat.process is None
                    assert not window.combat_page.panel.isVisible()
                    if sys.platform=='win32':
                        result=subprocess.run([str(HELPER),'--version'],capture_output=True,text=True,
                            timeout=5,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
                        assert 'Strigoi Sonar Capture 1' in result.stdout
                        from app.modules.combat.service import HELPER as COMBAT_HELPER
                        combat_check=subprocess.run([str(COMBAT_HELPER),'--self-test'],capture_output=True,text=True,
                            timeout=10,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
                        assert 'SELF_TEST_OK' in combat_check.stdout
                        logging.info('SMOKE_COMBAT_OK: helper self-test, no live capture')
                    logging.info('SMOKE_SONAR_OK: reference, detector and helper checked without capture')
                    capture_window()
                    logging.info("SMOKE_OK: all %s pages rendered", window.stack.count())
                    window.close()
                    app.quit()
                except Exception:
                    logging.exception("SMOKE_FAILED")
                    window.close()
                    app.exit(1)
            QTimer.singleShot(800, smoke)
        elif args.screenshot:
            QTimer.singleShot(1000, capture_window)
        return app.exec()
    except Exception:
        logging.exception("Falha ao iniciar aplicação")
        if args.smoke_test:
            raise
        QMessageBox.critical(None, "Não foi possível iniciar", f"Consulte o log em {directory / 'logs/strigoi.log'}")
        return 1
    finally:
        lock.unlock()


if __name__ == "__main__":
    raise SystemExit(main())
