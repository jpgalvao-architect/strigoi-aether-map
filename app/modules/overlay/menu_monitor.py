# SPDX-License-Identifier: GPL-3.0-only
"""Local, transient recognition of game menu headers; never hooks input."""
import base64
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import unicodedata
from PySide6.QtCore import QThread, Signal
from app.infrastructure.storage import PACKAGE

MENU_TITLES = {'settings', 'inventory', 'skills', 'character', 'quest', 'quests',
    'abyss', 'legion', 'crafting', 'ranking', 'rankings', 'shop', 'mail', 'storage',
    'configuracoes', 'inventario', 'habilidades', 'personagem', 'missoes',
    'abismo', 'legiao', 'fabricacao', 'classificacao', 'loja', 'correio', 'armazem'}


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.lower()) if not unicodedata.combining(c)).strip(' :·.-')


def classify_lines(lines, width, height, full_close=False):
    for line in lines:
        text = normalized(line.get('text',''))
        x,y,h = line.get('x',0),line.get('y',0),line.get('height',0)
        if h < 12: continue
        if x < width*.35 and y < height*.12 and (text.startswith('map:') or text.startswith('mapa:')):
            return 'map'
        if text in MENU_TITLES and y < height*.45 and not (x > width*.8 and y < height*.3):
            return 'menu'
    return 'fullscreen' if full_close else 'play'


def fullscreen_close(frame, full_height=None):
    """A large neutral X at the game's full-screen menu close-button position."""
    import cv2
    import numpy as np
    h,w = frame.shape[:2]
    small = cv2.resize(frame,(1024,max(1,round(h*1024/w))))
    height = round((full_height or h)*1024/w)
    crop = small[round(height*.015):round(height*.065),round(1024*.963):round(1024*.993)]
    if min(crop.shape[:2]) < 8: return False
    neutral = np.max(crop,axis=2)-np.min(crop,axis=2)<35
    gray = cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(np.where(neutral,gray,0).astype('uint8'),60,140)
    lines = cv2.HoughLinesP(edges,1,np.pi/180,threshold=7,minLineLength=9,maxLineGap=3)
    if lines is None: return False
    positive=[];negative=[]
    for x1,y1,x2,y2 in lines.reshape(-1,4):
        if abs(x2-x1)<8 or not .65 <= abs((y2-y1)/(x2-x1)) <= 1.5: continue
        target=positive if (x2-x1)*(y2-y1)>0 else negative
        target.append(((x1+x2)/2,(y1+y2)/2))
    return any(abs(x-a)<5 and abs(y-b)<5 for x,y in positive for a,b in negative)


class WindowsOCR:
    def __init__(self):
        self.child = None; self.closed = False
        self.responses = queue.Queue(maxsize=2)
        self.lock = threading.Lock()

    def start(self):
        executable=Path(os.environ.get('WINDIR','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
        with self.lock:
            if self.closed: return False
            self.child=subprocess.Popen([str(executable),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                '-File',str(PACKAGE/'assets/overlay/menu-ocr.ps1')], stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW,bufsize=0)
            child=self.child
        def read():
            try:
                while line:=child.stdout.readline(65536):
                    self.responses.put(json.loads(line.decode('utf-8')),timeout=1)
            except (OSError,ValueError,queue.Full): pass
        threading.Thread(target=read,daemon=True).start()
        return True

    def recognize(self, image):
        import cv2
        if self.closed: return []
        try:
            if self.child is None and not self.start(): return []
            ok,data=cv2.imencode('.png',image)
            if not ok: return []
            message=json.dumps({'png':base64.b64encode(data).decode('ascii')}).encode('ascii')+b'\n'
            self.child.stdin.write(message);self.child.stdin.flush()
            result=self.responses.get(timeout=3)
            if not result.get('available'):
                self.close();return []
            return result.get('lines',[])[:200]
        except (OSError,ValueError,queue.Empty):
            self.close();return []

    def close(self):
        with self.lock:
            self.closed=True
            child=self.child
            if child and child.poll() is None:
                try: child.kill()
                except OSError: pass
        if child:
            try: child.wait(timeout=1)
            except subprocess.TimeoutExpired: pass


class MenuMonitor(QThread):
    observed = Signal(object,str)

    def __init__(self, probe):
        super().__init__()
        self.probe=probe;self.job=None
        self.lock=threading.Lock();self.stopped=threading.Event()
        self.ocr=WindowsOCR()

    def set_game(self, job):
        with self.lock: self.job=job

    def stop(self):
        self.stopped.set();self.ocr.close()

    def run(self):
        import cv2
        import mss
        import numpy as np
        try:
            with mss.MSS() as capture:
                while not self.stopped.is_set():
                    with self.lock: job=self.job
                    if job is not None:
                        game,_=job
                        if self.probe.game_foreground() == game:
                            frame=np.asarray(capture.grab(dict(left=game.left,top=game.top,width=game.width,height=round(game.height*.45))))[:,:,:3].copy()
                            # No image/text is saved or logged. Capture only the active game.
                            if self.probe.game_foreground() == game:
                                close=fullscreen_close(frame,game.height)
                                # Cross geometry needs the original full-frame aspect ratio.
                                if close: self.observed.emit(job,'fullscreen')
                                width=min(1920,game.width);height=round(game.height*width/game.width)
                                image=cv2.resize(frame,(width,round(height*.45)))
                                lines=self.ocr.recognize(image)
                                self.observed.emit(job,classify_lines(lines,width,height,close))
                    self.stopped.wait(.65)
        except (OSError,ValueError,mss.ScreenShotError):
            pass  # Foreground gating remains active if visual recognition is unavailable.
        finally: self.ocr.close()
