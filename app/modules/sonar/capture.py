# SPDX-License-Identifier: GPL-3.0-only
"""Bounded pipe protocol to our native, external process-loopback helper."""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
import struct
import subprocess
import threading
import time
from app.infrastructure.storage import PACKAGE

HELPER=PACKAGE/'assets/sonar/sonar-capture.exe'


@dataclass(frozen=True)
class Process:
    pid: int
    name: str


def processes():
    if os.name!='nt':
        return []
    class Entry(ctypes.Structure):
        _fields_=[('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),
                  ('th32ProcessID',wintypes.DWORD),('th32DefaultHeapID',ctypes.c_size_t),
                  ('th32ModuleID',wintypes.DWORD),('cntThreads',wintypes.DWORD),
                  ('th32ParentProcessID',wintypes.DWORD),('pcPriClassBase',wintypes.LONG),
                  ('dwFlags',wintypes.DWORD),('szExeFile',wintypes.WCHAR*260)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    snapshot=kernel.CreateToolhelp32Snapshot(2,0)
    if snapshot==ctypes.c_void_p(-1).value:
        raise OSError('Não foi possível listar os aplicativos')
    result=[]
    try:
        entry=Entry();entry.dwSize=ctypes.sizeof(entry)
        valid=kernel.Process32FirstW(snapshot,ctypes.byref(entry))
        while valid:
            if entry.th32ProcessID and entry.th32ProcessID!=os.getpid():
                result.append(Process(entry.th32ProcessID,entry.szExeFile))
            valid=kernel.Process32NextW(snapshot,ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    return sorted(result,key=lambda p:('aion' not in p.name.lower(),p.name.lower(),p.pid))


class ProcessLoopback:
    def __init__(self,pid):
        self.pid=pid
        self.child=None
        self.lock=threading.Lock()
        self.stopped=threading.Event()

    def read_exact(self,length):
        data=bytearray()
        while len(data)<length:
            part=self.child.stdout.read(length-len(data))
            if not part:
                return None
            data.extend(part)
        return bytes(data)

    def frames(self):
        from app.modules.sonar.service import AudioFrame
        if os.name!='nt' or not HELPER.is_file():
            raise RuntimeError('Captura de áudio indisponível nesta instalação')
        with self.lock:
            if self.stopped.is_set():
                return
            self.child=subprocess.Popen([str(HELPER),'--pid',str(self.pid)],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,bufsize=0)
        try:
            header=self.read_exact(20)
            if header is None:
                error=self.child.stderr.read(4096).decode('utf-8',errors='replace').strip()
                raise RuntimeError('Não foi possível iniciar o áudio: '+error)
            if header[:8]!=b'STRSA001' or struct.unpack('<III',header[8:])!=(48000,2,4):
                raise RuntimeError('Formato de áudio inesperado')
            while not self.stopped.is_set():
                packet=self.read_exact(8)
                if packet is None:
                    if not self.stopped.is_set():
                        raise RuntimeError('O aplicativo encerrou ou a captura de áudio foi interrompida')
                    break
                count,flags=struct.unpack('<II',packet)
                if count>48000:
                    raise RuntimeError('Pacote de áudio inválido')
                pcm=self.read_exact(count*8) if count else b''
                if pcm is None:
                    raise RuntimeError('Captura de áudio interrompida')
                yield AudioFrame(pcm,48000,2,time.monotonic(),bool(flags&1))
        finally:
            self.stop()
            for pipe in [self.child.stdin,self.child.stdout,self.child.stderr]:
                if pipe is not None:
                    pipe.close()

    def stop(self):
        self.stopped.set()
        with self.lock:
            child=self.child
            if child is None:
                return
            if child.poll() is None:
                try:
                    child.stdin.close()
                except (OSError,ValueError):
                    pass
                try:
                    child.wait(timeout=1.)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    child.wait(timeout=3.)
