# SPDX-License-Identifier: GPL-3.0-only
"""Shared visual tokens and Qt styling."""
import os
from pathlib import Path
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette

COLORS = {"background": "#10121f", "surface": "#191d2e", "accent": "#91dedf", "muted": "#9ba5bd"}
STYLE = """
QWidget { color: #eff1f7; font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow, QDialog { background: #10121f; }
QFrame#sidebar { background: #151828; border-right: 1px solid #2b3046; }
QFrame#card { background: #191d2e; border: 1px solid #30364c; border-radius: 14px; }
QFrame#hero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #282240,stop:1 #193640); border: 1px solid #434363; border-radius: 18px; }
QLabel { background: transparent; }
QLabel#title { font-size: 29px; font-weight: 700; }
QLabel#subtitle { color: #9ba5bd; font-size: 13px; }
QLabel#eyebrow { color: #91dedf; font-size: 11px; font-weight: 700; letter-spacing: 2px; }
QLabel#number { font-size: 31px; font-weight: 700; color: #c6b9f0; }
QLabel#badge { color: #ddc58e; background: #302c2c; border-radius: 8px; padding: 7px 12px; font-size: 11px; }
QLabel#banner { color: #d4c7a1; background: #252431; padding: 8px 16px; border-bottom: 1px solid #3c3745; }
QPushButton { background: #252b40; border: 1px solid #3a425c; border-radius: 8px; padding: 9px 15px; font-weight: 600; }
QPushButton:hover { background: #333b55; border-color: #687894; }
QPushButton:pressed { background: #41425e; }
QPushButton:disabled { color: #626d84; background: #202437; }
QPushButton#primary { background: #91dedf; border-color: #91dedf; color: #15252d; }
QPushButton#primary:hover { background: #aff0ed; }
QPushButton#nav { text-align: left; border: 0; background: transparent; padding: 12px 16px; color: #a9b2c9; font-weight: 500; }
QPushButton#nav:checked { color: #d4f6f2; background: #2a3347; border-left: 3px solid #91dedf; }
QPushButton#nav:hover { background: #232a3d; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: #111727; border: 1px solid #3a435a; border-radius: 7px; padding: 7px 10px; selection-background-color: #465478; min-height: 20px; }
QComboBox::drop-down { border: 0; width: 22px; }
QComboBox QAbstractItemView { background: #22293c; selection-background-color: #3c4862; }
QCheckBox { spacing: 9px; padding: 5px 0; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #68738e; background: #151b2b; }
QCheckBox::indicator:checked { background: #91dedf; border: 3px solid #405a69; }
QGroupBox { border: 1px solid #343b52; border-radius: 10px; margin-top: 16px; padding: 16px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QTableWidget { background: #151b2b; alternate-background-color: #1a2032; border: 1px solid #30364c; border-radius: 9px; gridline-color: #293249; selection-background-color: #35445d; }
QTableWidget::item { padding: 8px; }
QHeaderView::section { background: #242c41; color: #aab9cf; padding: 10px; border: 0; border-bottom: 1px solid #3a455c; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { width: 9px; background: #141928; }
QScrollBar::handle:vertical { background: #3b465f; border-radius: 4px; min-height: 26px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QTabWidget::pane { border: 0; }
QStatusBar { color: #9ba5bd; background: #151828; }
QToolTip { color: #e9eff5; background: #242c40; border: 1px solid #64738d; padding: 7px; }
QMenu { background: #20273b; border: 1px solid #3a435a; }
QMenu::item { padding: 8px 22px; }
QMenu::item:selected { background: #3b465c; }
"""


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
    for role, color in [(QPalette.ColorRole.Window, "#10121f"), (QPalette.ColorRole.Base, "#151b2b"), (QPalette.ColorRole.WindowText, "#eff1f7"), (QPalette.ColorRole.Text, "#eff1f7"), (QPalette.ColorRole.Button, "#252b40"), (QPalette.ColorRole.ButtonText, "#eff1f7"), (QPalette.ColorRole.Highlight, "#3b536a")]:
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(STYLE)
