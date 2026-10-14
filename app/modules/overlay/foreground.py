# SPDX-License-Identifier: GPL-3.0-only
"""Read foreground ownership and physical client bounds through Windows APIs."""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
import time
from pathlib import PureWindowsPath

GAME_NAMES = {'aion2.exe', 'aion2-win64-shipping.exe'}


@dataclass(frozen=True)
class GameWindow:
    handle: int
    pid: int
    left: int
    top: int
    width: int
    height: int


class ForegroundProbe:
    def __init__(self):
        self.names = {}
        self.available = os.name == 'nt'
        if not self.available: return
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.user.GetForegroundWindow.restype = wintypes.HWND
        self.user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user.IsIconic.argtypes = [wintypes.HWND]
        self.user.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]

    def process_name(self, pid):
        now = time.monotonic()
        if pid in self.names and now-self.names[pid][0] < 2:
            return self.names[pid][1]
        handle = self.kernel.OpenProcess(0x1000, False, pid)  # Query only; no VM read/write rights.
        name = ''
        if handle:
            try:
                text = ctypes.create_unicode_buffer(32768); size = wintypes.DWORD(len(text))
                if self.kernel.QueryFullProcessImageNameW(handle, 0, text, ctypes.byref(size)):
                    name = PureWindowsPath(text.value).name.lower()
            finally: self.kernel.CloseHandle(handle)
        self.names = {key: value for key,value in self.names.items() if now-value[0] < 2}
        self.names[pid] = (now,name)
        return name

    def game_foreground(self, owned=(), previous=None):
        if not self.available: return None
        try:
            handle = int(self.user.GetForegroundWindow() or 0)
            if handle in owned and previous is not None:
                handle = previous.handle
            if not handle or self.user.IsIconic(handle) or not self.user.IsWindowVisible(handle):
                return None
            pid = wintypes.DWORD(); self.user.GetWindowThreadProcessId(handle, ctypes.byref(pid))
            if self.process_name(pid.value) not in GAME_NAMES: return None
            rectangle = wintypes.RECT(); origin = wintypes.POINT()
            if not self.user.GetClientRect(handle, ctypes.byref(rectangle)) or not self.user.ClientToScreen(handle, ctypes.byref(origin)):
                return None
            width,height = rectangle.right-rectangle.left, rectangle.bottom-rectangle.top
            if not (320 <= width <= 16384 and 200 <= height <= 16384): return None
            return GameWindow(handle,pid.value,origin.x,origin.y,width,height)
        except (OSError, ValueError):
            return None
