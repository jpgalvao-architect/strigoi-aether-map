# SPDX-License-Identifier: GPL-3.0-only
"""UI translation only. Model identifiers, coordinates and user text stay intact."""
import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError
from PySide6.QtCore import QLocale, QTranslator

LANGUAGES = {
    'pt_BR': 'Português (Brasil)',
    'en_US': 'English (United States)',
    'es-419': 'Español (Latinoamérica)',
}
DEFAULT_LANGUAGE = 'pt_BR'
_LANGUAGE_FILES = {
    'en_US': tuple(f'{prefix}en_US.json' for prefix in (
        '', 'combat_', 'quick_menu_', 'pets_', 'vigilia_', 'routine_', 'events_', 'routes_', 'siege_', 'live_sync_',
    )),
    'es-419': ('es-419.json', 'live_sync_es-419.json'),
}
_ASSETS = Path(__file__).resolve().parents[1] / 'assets/i18n'
_QT_CATALOGS = {'pt_BR': 'qtbase_pt_BR.qm', 'es-419': 'qtbase_es.qm'}
_language = DEFAULT_LANGUAGE
_qt_translator = None


class Verbatim(str):
    """Text supplied by a player, or already localized with explicit arguments."""


@lru_cache
def _catalog(code):
    entries = {}
    for filename in _LANGUAGE_FILES.get(code, ()):
        entries.update(json.loads((_ASSETS / filename).read_text(encoding='utf-8')))
    patterns = []
    fragments = {}
    for source, target in sorted(entries.items(), key=lambda item: -len(item[0])):
        if not source or source == target:
            continue
        if '{' in source:
            chunks = re.split(r'(\{[^{}]+\})', source)
            names = [part[1:-1] for part in chunks[1::2]]
            regex = ''.join('(.*?)' if index % 2 else re.escape(part) for index, part in enumerate(chunks))
            patterns.append((re.compile('^'+regex+'$', re.S), names, target))
        else:
            fragments[source] = target
    fragment_pattern = None
    if code == 'es-419':
        fragment_pattern = re.compile('|'.join(
            (r'(?<!\w)' if source[0].isalnum() else '') + re.escape(source)
            + (r'(?!\w)' if source[-1].isalnum() else '')
            for source in fragments
        ))
    return entries, patterns, fragments, fragment_pattern


def language():
    return _language


def suggested_language():
    """Existing setup and saved choices take precedence over system Spanish."""
    return 'es-419' if QLocale.system().language() == QLocale.Spanish else DEFAULT_LANGUAGE


def tr(text):
    if not isinstance(text, str) or isinstance(text, Verbatim) or _language == DEFAULT_LANGUAGE:
        return text
    return _translate(_language, text)


@lru_cache(maxsize=8192)
def _translate(code, text):
    entries, patterns, fragments, fragment_pattern = _catalog(code)
    if text in entries:
        return entries[text]
    if '\n' in text:
        return '\n'.join(_translate(code, line) for line in text.split('\n'))
    for pattern, names, target in patterns:
        found = pattern.match(text)
        if found:
            return target.format(**{
                name: _translate(code, value) for name, value in zip(names, found.groups())
            })
    if fragment_pattern is not None:
        return fragment_pattern.sub(lambda match: fragments[match.group()], text)
    # Preserve the existing English behavior for source notes assembled at runtime.
    for source, target in fragments.items():
        if source in text:
            text = text.replace(source, target)
    return text


def validation_text(error):
    if not isinstance(error, ValidationError):
        return str(error)
    issue = error.errors(include_url=False, include_context=False, include_input=False)[0]
    if issue['type'] == 'value_error':
        return issue['msg'].removeprefix('Value error, ')
    return 'Dados inválidos. Confira os campos e tente novamente.'


def set_language(value):
    global _language, _qt_translator
    if value not in LANGUAGES:
        raise ValueError('Unsupported interface language')
    _language = value
    QLocale.setDefault(QLocale(value))
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app:
        if _qt_translator is not None:
            app.removeTranslator(_qt_translator)
            _qt_translator.deleteLater()
            _qt_translator = None
        filename = _QT_CATALOGS.get(value)
        if filename is not None:
            translator = QTranslator(app)
            if translator.load(str(_ASSETS / filename)):
                _qt_translator = translator
                app.installTranslator(translator)
        from app.ui.localized_widgets import retranslate_widgets
        retranslate_widgets(app)


def clock(instant: datetime, *, seconds=False):
    if _language == 'en_US':
        return instant.strftime('%I:%M:%S %p' if seconds else '%I:%M %p').lstrip('0')
    return instant.strftime('%H:%M:%S' if seconds else '%H:%M')


def calendar_date(instant: datetime):
    return instant.strftime('%m/%d' if _language == 'en_US' else '%d/%m')
