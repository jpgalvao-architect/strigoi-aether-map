# SPDX-License-Identifier: GPL-3.0-only
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from app.ui.localized_widgets import QFrame, QLabel, QPushButton, QWidget


def label(text: str, role: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    if role:
        widget.setObjectName(role)
    return widget


def button(text: str, callback, primary: bool = False) -> QPushButton:
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        widget.setObjectName("primary")
    widget.clicked.connect(callback)
    return widget


def card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(10)
    return frame, layout


def page_header(title: str, subtitle: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 12)
    layout.setSpacing(5)
    layout.addWidget(label(title, "title"))
    layout.addWidget(label(subtitle, "subtitle", True))
    return widget


def row(*widgets) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(12)
    for widget in widgets:
        layout.addWidget(widget)
    return layout
