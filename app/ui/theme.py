# SPDX-License-Identifier: GPL-3.0-only
"""Shared visual tokens and Qt styling."""
import os
from pathlib import Path
from app.infrastructure.storage import PACKAGE
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette

COLORS = {"background": "#101018", "surface": "#171721", "accent": "#c2b2fc", "muted": "#aaa8bd"}
STYLE = """
QWidget { color: #eeedf8; font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow, QDialog { background: #101018; }
QFrame#sidebar { background: #14141d; border-right: 1px solid #30303e; }
QFrame#sessionInspector { background:#171721; border-right:1px solid #30303e; }
QFrame#sessionBar { background:#101018; border-bottom:1px solid #30303e; }
QFrame#divider { background:#30303e; border:0; }
QLabel#sessionTitle {font-size:18px;font-weight:600;}
QLabel#sectionTitle {font-size:12px;font-weight:600;}
QLabel#sessionState {font-size:10px;color:#aaa8bd;}
QFrame#card { background: #171721; border: 1px solid #30303e; border-radius: 6px; }
QFrame#hero { background: #1c1928; border: 1px solid #393048; border-radius: 6px; }
QLabel { background: transparent; }
QLabel#title { font-size: 23px; font-weight: 600; }
QLabel#subtitle { color: #aaa8bd; font-size: 12px; }
QLabel#eyebrow { color: #c2b2fc; font-size: 10px; font-weight: 600; letter-spacing: 1px; }
QLabel#number { font-size: 26px; font-weight: 600; color: #eeedf8; }
QLabel#badge { color: #ddc58e; background: #302c2c; border-radius: 8px; padding: 7px 12px; font-size: 11px; }
QLabel#banner { color: #d4c7a1; background: #252431; padding: 8px 16px; border-bottom: 1px solid #3c3745; }
QPushButton { background: #22222e; border: 1px solid #393545; border-radius: 5px; padding: 8px 13px; font-weight: 500; }
QPushButton:hover { background: #302943; border-color: #8875ad; }
QPushButton:pressed { background: #3f3457; }
QPushButton:disabled { color: #626d84; background: #202437; }
QPushButton#primary { background: #c2b2fc; border-color: #c2b2fc; color: #231940; }
QPushButton#primary:hover { background: #d2c6ff; }
QPushButton#quiet {background:transparent;border:0;text-align:left;padding:4px 0;color:#c2b2fc;}
QToolButton#nav,QToolButton#sectionNav {background:transparent;border:0;border-radius:5px;padding:5px;color:#aaa8bd;}
QToolButton#nav:hover,QToolButton#sectionNav:hover {background:#22222e;}
QToolButton#nav:checked,QToolButton#sectionNav:checked {background:#302943;color:#e1d6ff;border-left:2px solid #c2b2fc;}
QToolButton#sectionNav {text-align:left;font-size:12px;}
QPushButton#nav { text-align: left; border: 0; background: transparent; padding: 12px 16px; color: #a9b2c9; font-weight: 500; }
QPushButton#nav:checked { color: #d4f6f2; background: #2a3347; border-left: 3px solid #91dedf; }
QPushButton#nav:hover { background: #232a3d; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: #111727; border: 1px solid #3a435a; border-radius: 7px; padding: 7px 10px; selection-background-color: #465478; min-height: 20px; }
QComboBox::drop-down { border: 0; width: 22px; }
QComboBox QAbstractItemView { background: #22293c; selection-background-color: #3c4862; }
QCheckBox { spacing: 9px; padding: 5px 0; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #68738e; background: #151b2b; }
QCheckBox::indicator:checked { background: #c2b2fc; border: 3px solid #625178; }
QCheckBox#moduleSwitch::indicator {width:27px;height:15px;border-radius:8px;background:#302e3b;border:2px solid #464051;}
QCheckBox#moduleSwitch::indicator:checked {background:#b8a2ee;border-color:#c2b2fc;}
QGroupBox { border: 1px solid #343b52; border-radius: 10px; margin-top: 16px; padding: 16px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QTableWidget { background: #15151f; alternate-background-color: #1a1925; border: 1px solid #30303e; border-radius: 5px; gridline-color: #272533; selection-background-color: #302943; }
QTableWidget::item { padding: 8px; }
QHeaderView::section { background: #1c1b28; color: #aaa8bd; padding: 9px; border: 0; border-bottom: 1px solid #30303e; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { width: 9px; background: #141928; }
QScrollBar::handle:vertical { background: #3b465f; border-radius: 4px; min-height: 26px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QTabWidget::pane { border: 0; }
QStatusBar { color: #aaa8bd; background: #14141d; font-size:11px; }
QToolTip { color: #e9eff5; background: #242c40; border: 1px solid #64738d; padding: 7px; }
QMenu { background: #20273b; border: 1px solid #3a435a; }
QMenu::item { padding: 8px 22px; }
QMenu::item:selected { background: #3b465c; }
"""

STYLE += '''
QCheckBox#moduleSwitch::indicator {width:32px;height:18px;border:0;background:transparent;image:url(OFF_IMAGE);}
QCheckBox#moduleSwitch::indicator:checked {border:0;background:transparent;image:url(ON_IMAGE);}
'''.replace('OFF_IMAGE',(PACKAGE/'assets/icons/switch-off.svg').as_posix()).replace('ON_IMAGE',(PACKAGE/'assets/icons/switch-on.svg').as_posix())


def apply_theme(app):
    # The Windows offscreen platform does not enumerate installed fonts reliably.
    if app.platformName() == "offscreen":
        font_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ["segoeui.ttf", "segoeuib.ttf", "seguisym.ttf"]:
            if (font_dir / name).exists():
                QFontDatabase.addApplicationFont(str(font_dir / name))
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")
    palette = QPalette()
    for role, color in [(QPalette.ColorRole.Window, "#101018"), (QPalette.ColorRole.Base, "#15151f"), (QPalette.ColorRole.WindowText, "#eeedf8"), (QPalette.ColorRole.Text, "#eeedf8"), (QPalette.ColorRole.Button, "#22222e"), (QPalette.ColorRole.ButtonText, "#eeedf8"), (QPalette.ColorRole.Highlight, "#302943")]:
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(STYLE)
