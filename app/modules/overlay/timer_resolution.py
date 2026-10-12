# SPDX-License-Identifier: GPL-3.0-only
"""Scoped Windows timer precision while a high-rate overlay is visible."""
import sys


class TimerResolution:
    def __init__(self):
        self.active=False
        self.library=None

    def enable(self):
        if self.active or sys.platform!='win32':
            return
        import ctypes
        try:
            library=ctypes.WinDLL('winmm')
            library.timeBeginPeriod.argtypes=[ctypes.c_uint]
            library.timeBeginPeriod.restype=ctypes.c_uint
            library.timeEndPeriod.argtypes=[ctypes.c_uint]
            library.timeEndPeriod.restype=ctypes.c_uint
            if library.timeBeginPeriod(1)==0:
                self.library=library
                self.active=True
        except OSError:
            pass

    def disable(self):
        if self.active:
            self.library.timeEndPeriod(1)
            self.active=False
            self.library=None
