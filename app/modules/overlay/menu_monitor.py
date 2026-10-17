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
    'abismo', 'legiao', 'fabricacao', 'classificacao', 'loja', 'correio', 'armazem',
    'battlefield', 'campo de batalha'}


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.lower()) if not unicodedata.combining(c)).strip(' :·.-')


def classify_lines(lines, width, height, full_close=False, header_rule=False):
    if pet_menu(lines,width,height):return 'menu'
    for line in lines:
        text = normalized(line.get('text',''))
        x,y,h = line.get('x',0),line.get('y',0),line.get('height',0)
        if h < 12: continue
        if x < width*.35 and y < height*.12 and (text.startswith('map:') or text.startswith('mapa:')):
            return 'map'
        if text in MENU_TITLES and h>=18 and x<width*.35 and y<height*.12:
            return 'menu'
    if full_close and header_rule and tabbed_menu(lines,width,height):return 'menu'
    # Gameplay HUD and scenery can contain the same crossing diagonals as a
    # close button. Geometry alone is not evidence that a menu is open.
    return 'play'


def tabbed_menu(lines,width,height):
    """Menu chrome needs a large title and two aligned, separated text tabs."""
    def letters(line):return sum(c.isalpha() for c in line.get('text',''))>=3
    titles=[line for line in lines if letters(line) and line.get('height',0)>=max(12,height*.018)
        and 0<=line.get('x',width)<width*.32 and 0<=line.get('y',height)<height*.06]
    if not titles:return False
    tabs=[line for line in lines if letters(line) and line.get('height',0)>=max(7,height*.009)
        and width*.19<line.get('x',0)<width*.85 and height*.055<line.get('y',0)<height*.095]
    return any(abs(a['y']-b['y'])<height*.012 and abs(a['x']-b['x'])>width*.08
        for a in tabs for b in tabs)


def fullscreen_header_rule(frame,full_height):
    """Long menu header separator; city scenery alone must not hide the HUD."""
    import cv2
    import numpy as np
    h,w=frame.shape[:2]
    small=cv2.resize(frame,(1024,max(1,round(h*1024/w))))
    height=round(full_height*1024/w)
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY).astype('int16')
    band=np.abs(np.diff(gray,axis=0))[round(height*.075):round(height*.12),51:973]
    return bool(band.size and np.any(np.mean(band>=3,axis=1)>=.75))


def pet_menu(lines,width,height):
    title=any(normalized(line.get('text',''))=='pets' and line.get('height',0)>=18
              and line.get('x',width)<width*.18 and line.get('y',height)<height*.12 for line in lines)
    tabs=any(normalized(line.get('text','')) in ('genus insight','pet info','pet insight')
             and line.get('x',0)>width*.4 and line.get('y',height)<height*.45 for line in lines)
    return title and tabs


class MenuConsensus:
    """Changing scene text or one missed title cannot toggle the HUD."""
    def __init__(self):self.mode='play';self.candidate=None;self.count=0

    def observe(self,mode):
        if mode is None:self.candidate=None;self.count=0;return self.mode
        if mode==self.mode:self.candidate=None;self.count=0;return self.mode
        self.count=self.count+1 if self.candidate==mode else 1
        self.candidate=mode
        if self.count>=(3 if mode=='play' else 2):
            self.mode=mode;self.candidate=None;self.count=0
        return self.mode


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
    pet_observed = Signal(object,object,object)
    boss_observed = Signal(object,object,object,object)

    def __init__(self, probe):
        super().__init__()
        self.probe=probe;self.job=None
        self.lock=threading.Lock();self.stopped=threading.Event()
        self.ocr=WindowsOCR()
        self.pet_scope=None
        self.boss_scope=None

    def set_boss_scope(self,scope):
        with self.lock:self.boss_scope=scope

    def set_pet_scope(self,scope):
        with self.lock:self.pet_scope=scope

    def set_game(self, job):
        with self.lock: self.job=job

    def stop(self):
        self.stopped.set();self.ocr.close()

    def run(self):
        import cv2
        import mss
        import numpy as np
        from app.modules.pets.screen import PetScreenReader,ReadingConsensus
        from app.modules.events.boss_timer import read_gartua,BossConsensus
        from datetime import UTC,datetime
        from app.modules.pets.models import PetCatalogue
        from app.infrastructure.storage import load_model
        reader=PetScreenReader(self.ocr,load_model(PACKAGE/'data/pets.json',PetCatalogue).pets)
        readings=ReadingConsensus();bosses=BossConsensus();consensus=MenuConsensus();previous=None
        try:
            with mss.MSS() as capture:
                while not self.stopped.is_set():
                    with self.lock: job=self.job;scope=self.pet_scope;boss_scope=self.boss_scope
                    if job!=previous:
                        consensus=MenuConsensus();readings=ReadingConsensus();bosses=BossConsensus();previous=job
                    if job is not None:
                        game,_=job
                        if self.probe.game_foreground() == game:
                            captured=datetime.now(UTC)
                            frame=np.asarray(capture.grab(dict(left=game.left,top=game.top,width=game.width,height=round(game.height*.45))))[:,:,:3].copy()
                            # No image/text is saved or logged. Capture only the active game.
                            if self.probe.game_foreground() == game:
                                close=fullscreen_close(frame,game.height)
                                # Wait for header recognition; an isolated X also occurs
                                # during normal gameplay and must never suppress the HUD.
                                width=min(1920,game.width);height=round(game.height*width/game.width)
                                image=cv2.resize(frame,(width,round(height*.45)))
                                lines=self.ocr.recognize(image)
                                rule=fullscreen_header_rule(frame,game.height) if close else False
                                mode=classify_lines(lines,width,height,close,rule) if lines else (
                                    'play' if self.ocr.closed else None)
                                self.observed.emit(job,consensus.observe(mode))
                                boss=read_gartua(lines) if boss_scope is not None else None
                                confirmed_boss=bosses.observe(boss_scope,boss,captured)
                                if confirmed_boss is not None and self.probe.game_foreground()==game:
                                    self.boss_observed.emit(job,boss_scope,confirmed_boss,captured)
                                reading=None
                                if scope is not None and pet_menu(lines,width,height):
                                    # Native pixels keep small Insight text legible on 4K/150%.
                                    reading=reader.recognize(frame[round(game.height*.12):,round(game.width*.74):])
                                confirmed=readings.observe(scope,reading)
                                if confirmed is not None and self.probe.game_foreground()==game:
                                    self.pet_observed.emit(job,scope,confirmed)
                                elif reading is None:readings.observe(None,None)
                    self.stopped.wait(.65)
        except (OSError,ValueError,mss.ScreenShotError):
            pass  # Foreground gating remains active if visual recognition is unavailable.
        finally: self.ocr.close()
