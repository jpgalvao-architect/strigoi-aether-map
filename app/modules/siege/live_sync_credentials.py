# SPDX-License-Identifier: GPL-3.0-only
"""Protect the caller's pairing key with the current Windows account."""
import base64
import ctypes
import json
import sys
from ctypes import wintypes

from app.infrastructure.storage import atomic_json
from app.modules.siege.live_sync_protocol import KEY, endpoint_url


class _Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(value, encrypt):
    if sys.platform != 'win32':
        raise OSError('Windows credential storage is unavailable.')
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32')
    free = kernel.LocalFree
    free.argtypes = [wintypes.HLOCAL]
    free.restype = wintypes.HLOCAL
    operation = crypt.CryptProtectData if encrypt else crypt.CryptUnprotectData
    operation.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p,
                          ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
    operation.restype = wintypes.BOOL
    source_buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
    source = _Blob(len(value), source_buffer)
    output = _Blob()
    if not operation(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise OSError('Windows credential storage failed.')
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        ctypes.memset(output.data, 0, output.size)
        free(output.data)


class PairingStore:
    def __init__(self, directory):
        self.path = directory / 'live-sync-connection.json'

    def load(self):
        try:
            if self.path.stat().st_size > 8192:
                return None
            data = json.loads(self.path.read_text(encoding='utf-8'))
            key = _dpapi(base64.b64decode(data['credential'], validate=True), False).decode('ascii')
            if KEY.fullmatch(key):
                return endpoint_url(data['endpoint']), key
        except (OSError, KeyError, TypeError, ValueError):
            pass
        return None

    def save(self, endpoint, key):
        encrypted = _dpapi(key.encode('ascii'), True)
        atomic_json(self.path, {'endpoint': endpoint, 'credential': base64.b64encode(encrypted).decode('ascii')})

    def remove(self):
        self.path.unlink(missing_ok=True)
