# SPDX-License-Identifier: GPL-3.0-only
"""UI translation only: model identifiers, coordinates and user notes stay intact."""
import json
import re
from functools import lru_cache
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QLocale

_language = 'pt_BR'
_qt_translator = None
_catalog = json.loads((Path(__file__).resolve().parents[1]/'assets/i18n/en_US.json').read_text(encoding='utf-8'))
_catalog.update(json.loads((Path(__file__).resolve().parents[1]/'assets/i18n/combat_en_US.json').read_text(encoding='utf-8')))
_patterns = []
_fragments = sorted(((a,b) for a,b in _catalog.items() if a and '{' not in a), key=lambda pair:len(pair[0]),reverse=True)
for source, target in _catalog.items():
    if '{' in source:
        chunks = re.split(r'(\{[^{}]+\})', source)
        names = [part[1:-1] for part in chunks if part.startswith('{') and part.endswith('}')]
        regex = ''.join('(.*?)' if part.startswith('{') and part.endswith('}') else re.escape(part) for part in chunks)
        _patterns.append((re.compile('^'+regex+'$', re.S), names, target))


def language():
    return _language


def tr(text):
    if not isinstance(text, str) or _language != 'en_US':
        return text
    return _translate(text)


@lru_cache(maxsize=8192)
def _translate(text):
    if text in _catalog:
        return _catalog[text]
    for pattern, names, target in _patterns:
        found = pattern.match(text)
        if found:
            for name, value in zip(names, found.groups()):
                target = target.replace('{'+name+'}', tr(value))
            return target
    # Fragments in multi-line details and verified source notes.
    for source, target in _fragments:
        if source in text:
            text = text.replace(source, target)
    return text


def set_language(value):
    global _language, _qt_translator
    if value not in ('pt_BR', 'en_US'):
        raise ValueError('Unsupported interface language')
    _language = value
    _translate.cache_clear()
    QLocale.setDefault(QLocale(value))
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app:
        from PySide6.QtCore import QTranslator
        if _qt_translator is not None:
            app.removeTranslator(_qt_translator)
            _qt_translator=None
        if value=='pt_BR':
            _qt_translator=QTranslator(app)
            if _qt_translator.load(str(Path(__file__).resolve().parents[1]/'assets/i18n/qtbase_pt_BR.qm')):
                app.installTranslator(_qt_translator)
        from app.ui.localized_widgets import retranslate_widgets
        retranslate_widgets(app)


def clock(instant: datetime):
    return instant.strftime('%I:%M %p').lstrip('0') if _language == 'en_US' else instant.strftime('%H:%M')


def calendar_date(instant: datetime):
    return instant.strftime('%m/%d') if _language == 'en_US' else instant.strftime('%d/%m')
